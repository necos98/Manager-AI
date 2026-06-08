"""Auto-mode: background execution loop for non-orchestrated pipelines."""

import asyncio
import logging
import shlex

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.pipeline import Pipeline, PipelineStep
from app.models.project import Project
from app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.providers.registry import AgentProviderRegistry
from app.services.pipeline_run import _completion, _events, _queries, _safe_session, _terminal
from app.services.pipeline_task_manager import pipeline_task_manager
from app.services.terminal_service import terminal_service
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def execute(
    run_id: str,
    project_id: str,
    project_path: str,
    session: AsyncSession,
    session_factory=None,
) -> None:
    """Main execution loop for auto-mode pipelines."""
    exec_session = session
    if session_factory is not None:
        exec_session = session_factory()

    try:
        run, steps = await _wait_for_run(run_id, exec_session)
        if run is None:
            return

        while run.current_step_index < len(steps) and run.status != PipelineRunStatus.FAILED:
            i = run.current_step_index
            step = steps[i]

            term_id, agent_name, step_run = await _setup_step_environment(
                step, run, exec_session, project_id, project_path, run_id,
            )
            if step_run is None:
                continue

            try:
                provider_name = step.agent.provider if step.agent else "claude"
                success = await _run_step(
                    term_id=term_id,
                    agent_name=agent_name,
                    intent=step.agent.intent if step.agent else "",
                    issue_id=run.issue_id,
                    run_id=run_id,
                    step_index=i,
                    provider_name=provider_name,
                )

                await exec_session.refresh(run)
                await exec_session.refresh(step_run)

                if step_run.status == PipelineStepRunStatus.REJECTED:
                    step_run.finished_at = now()
                    await _safe_session.safe_commit(exec_session)
                    continue

                should_continue = await _handle_step_completion(
                    run, step_run, exec_session, success, agent_name,
                    project_id, run.issue_id,
                )
                if not should_continue:
                    break

                step_run.finished_at = now()
                await _safe_session.safe_commit(exec_session)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Step %s failed with exception", agent_name)
                step_run.status = PipelineStepRunStatus.FAILED
                run.status = PipelineRunStatus.FAILED
                step_run.finished_at = now()
                # Fire event engine BEFORE commit
                try:
                    await _events.fire_pipeline_event(
                        run.pipeline_id, "step_failed",
                        step_run.pipeline_step_id,
                        run_id=run.id, issue_id=run.issue_id,
                        project_id=project_id,
                        agent_name=agent_name, step_run_id=step_run.id,
                        step_index=run.current_step_index,
                        session=exec_session,
                    )
                except Exception:
                    logger.exception("Event engine step_failed action failed for run %s", run.id)
                await _safe_session.safe_commit(exec_session)
                await _events.emit_step_failed(
                    project_id, run.issue_id, agent_name, step_run.id,
                )
                break
            finally:
                if term_id:
                    _terminal.cleanup_terminal(term_id)

        await _finalize_run(run, exec_session, project_id, run.issue_id, run_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Pipeline %s failed with unexpected error", run_id)
        try:
            run.status = PipelineRunStatus.FAILED
            run.finished_at = now()
            await _safe_session.safe_commit(exec_session)
        except Exception:
            pass
        await _events.emit_pipeline_completed(
            project_id, run.issue_id, run_id, PipelineRunStatus.FAILED.value,
        )
    finally:
        if session_factory is not None:
            try:
                await exec_session.close()
            except Exception:
                pass
        await pipeline_task_manager.cleanup_task(run_id)


async def _wait_for_run(
    run_id: str, session: AsyncSession,
) -> tuple[PipelineRun | None, list | None]:
    """Wait for the pipeline run to be committed by the caller."""
    run = None
    for _ in range(50):
        try:
            run = await _queries.get_run_with_session(run_id, session)
            break
        except NotFoundError:
            await asyncio.sleep(0.1)
    if run is None:
        logger.error(
            "Pipeline run %s not found -- execute started before commit finished", run_id
        )
        return None, None

    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == run.pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
    )
    pipeline = pipeline.unique().scalar_one_or_none()
    if pipeline is None:
        return None, None
    steps = sorted(pipeline.steps, key=lambda s: s.order_index)
    return run, steps


async def _setup_step_environment(
    step: PipelineStep,
    run: PipelineRun,
    session: AsyncSession,
    project_id: str,
    project_path: str,
    run_id: str,
) -> tuple[str | None, str | None, PipelineStepRun | None]:
    """Set up terminal and mark step run as RUNNING."""
    i = run.current_step_index

    step_run_result = await session.execute(
        select(PipelineStepRun).where(
            PipelineStepRun.pipeline_run_id == run_id,
            PipelineStepRun.pipeline_step_id == step.id,
        ).order_by(PipelineStepRun.started_at.desc().nulls_last())
    )
    step_run = step_run_result.scalars().first()
    if step_run is None:
        return None, None, None

    step_run.status = PipelineStepRunStatus.RUNNING
    step_run.started_at = now()
    run.current_step_index = i
    await _safe_session.safe_flush(session)

    agent = step.agent
    agent_name = agent.name if agent else "unknown"

    project_row = await session.get(Project, project_id)
    project_shell = project_row.shell if project_row else None
    project_wsl_distro = project_row.wsl_distro if project_row else None

    term = terminal_service.create(
        issue_id=run.issue_id,
        project_id=project_id,
        project_path=project_path,
        shell=project_shell,
        wsl_distro=project_wsl_distro,
    )
    term_id = term["id"]
    step_run.terminal_id = term_id
    await _safe_session.safe_commit(session)

    if project_shell:
        from app.services.wsl_support import is_wsl_shell, win_to_wsl_path
        if is_wsl_shell(project_shell):
            cwd_wsl = win_to_wsl_path(project_path)
            pty_for_cd = terminal_service.get_pty(term_id)
            pty_for_cd.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

    await _events.emit_step_started(project_id, run.issue_id, agent_name, step_run.id, term_id)
    await _events.emit_terminal_created(term_id, run.issue_id, project_id)

    return term_id, agent_name, step_run


async def _handle_step_completion(
    run: PipelineRun,
    step_run: PipelineStepRun,
    session: AsyncSession,
    success: bool,
    agent_name: str,
    project_id: str,
    issue_id: str,
) -> bool:
    """Handle step completion result. Returns False if pipeline should stop."""
    pipeline_id = run.pipeline_id
    if success:
        step_run.status = PipelineStepRunStatus.COMPLETED
        run.current_step_index += 1
        await _events.emit_step_completed(project_id, issue_id, agent_name, step_run.id)
        # Fire event engine for step_completed
        await _events.fire_pipeline_event(
            pipeline_id, "step_completed",
            step_run.pipeline_step_id,
            run_id=run.id, issue_id=issue_id, project_id=project_id,
            agent_name=agent_name, step_run_id=step_run.id,
            step_index=run.current_step_index - 1,
            session=session,
        )
        return True
    else:
        step_run.status = PipelineStepRunStatus.FAILED
        run.status = PipelineRunStatus.FAILED
        step_run.finished_at = now()
        await _safe_session.safe_commit(session)
        await _events.emit_step_failed(project_id, issue_id, agent_name, step_run.id)
        # Fire event engine for step_failed
        await _events.fire_pipeline_event(
            pipeline_id, "step_failed",
            step_run.pipeline_step_id,
            run_id=run.id, issue_id=issue_id, project_id=project_id,
            agent_name=agent_name, step_run_id=step_run.id,
            step_index=run.current_step_index,
            session=session,
        )
        return False


async def _finalize_run(
    run: PipelineRun,
    session: AsyncSession,
    project_id: str,
    issue_id: str,
    run_id: str,
) -> None:
    """Finalize pipeline run: mark COMPLETED if not already FAILED."""
    await session.refresh(run)
    if run.status != PipelineRunStatus.FAILED:
        run.status = PipelineRunStatus.COMPLETED
    run.finished_at = now()
    # Fire event engine BEFORE commit — action handlers run in same transaction
    await _events.fire_pipeline_event(
        run.pipeline_id, "pipeline_completed", None,
        run_id=run_id, issue_id=issue_id, project_id=project_id,
        metadata={"status": run.status.value},
        session=session,
    )
    await _safe_session.safe_commit(session)
    await _events.emit_pipeline_completed(project_id, issue_id, run_id, run.status.value)



async def _run_step(
    term_id: str,
    agent_name: str,
    intent: str,
    issue_id: str,
    run_id: str,
    step_index: int,
    provider_name: str = "claude",
) -> bool:
    """Execute a single step via PTY and wait for completion."""
    import platform as _platform
    from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

    pty = terminal_service.get_pty(term_id)
    tsession = TerminalSession()
    _sessions[term_id] = tsession
    _ensure_reader(term_id, terminal_service)

    is_windows = _platform.system() == "Windows"
    provider = AgentProviderRegistry.get(provider_name)
    command = provider.build_run_pipeline_command(issue_id)

    pty.write(f"{command} {'&' if is_windows else ';'} exit\r\n")

    event = _completion.register_completion_event(run_id, step_index)

    async def wait_pty_death():
        await tsession.pty_dead.wait()

    pty_task = asyncio.create_task(wait_pty_death())
    event_task = asyncio.create_task(event.wait())

    try:
        done, pending = await asyncio.wait(
            [pty_task, event_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        success = event_task in done
        if pty_task in done and event_task not in done:
            logger.error(
                "Step %s failed: PTY died before finished_pipeline_step called", agent_name
            )
            success = False

        for t in pending:
            t.cancel()
    finally:
        _completion.unregister_completion_event(run_id, step_index)

    return success
