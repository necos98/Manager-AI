"""Orchestrated mode: Hermes-controlled step execution."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.issue import Issue
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.providers.registry import AgentProviderRegistry
from app.database import async_session
from app.services.pipeline_run import _completion, _events, _queries, _safe_session, _terminal
from app.services.terminal_service import terminal_service
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def start_step(
    run_id: str,
    project_id: str,
    project_path: str,
    session: AsyncSession,
) -> dict:
    """Spawn PTY terminal + Claude for the current pipeline step (orchestrated mode)."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status != PipelineRunStatus.WAITING_FOR_STEP:
        raise ValidationError(
            f"Cannot start step: pipeline is {run.status.value}, "
            f"expected WAITING_FOR_STEP"
        )

    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == run.pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
    )
    pipeline = pipeline.unique().scalar_one_or_none()
    if pipeline is None:
        raise NotFoundError(f"Pipeline not found: {run.pipeline_id}")

    steps = sorted(pipeline.steps, key=lambda s: s.order_index)
    i = run.current_step_index
    if i >= len(steps):
        raise ValidationError(f"No more steps available (index {i} >= {len(steps)})")

    step = steps[i]
    step_run_result = await session.execute(
        select(PipelineStepRun).where(
            PipelineStepRun.pipeline_run_id == run_id,
            PipelineStepRun.pipeline_step_id == step.id,
        ).order_by(PipelineStepRun.started_at.desc().nulls_last())
    )
    step_run = step_run_result.scalars().first()
    if step_run is None:
        raise NotFoundError(f"StepRun not found for pipeline_step {step.id}")
    if step_run.status != PipelineStepRunStatus.PENDING:
        raise ValidationError(f"Step {i} is {step_run.status.value}, expected PENDING")

    # Create terminal
    term = terminal_service.create(
        issue_id=run.issue_id,
        project_id=project_id,
        project_path=project_path,
    )
    term_id = term["id"]
    step_run.terminal_id = term_id
    step_run.status = PipelineStepRunStatus.RUNNING
    step_run.started_at = now()
    run.status = PipelineRunStatus.RUNNING
    await _safe_session.safe_commit(session)

    agent = step.agent
    agent_name = agent.name if agent else "unknown"
    provider_name = getattr(agent, "provider", "claude") if agent else "claude"

    pty = terminal_service.get_pty(term_id)
    try:
        provider = AgentProviderRegistry.get(provider_name)
        command = provider.build_run_pipeline_command(run.issue_id)
    except KeyError:
        logger.warning(
            "Unknown provider %r for agent %r, falling back to claude",
            provider_name, agent_name,
        )
        provider = AgentProviderRegistry.get("claude")
        command = provider.build_run_pipeline_command(run.issue_id)
    pty.write(command + "\r\n")

    _completion.register_completion_event(run_id, i)
    asyncio.create_task(monitor_step(run_id=run_id, step_index=i, term_id=term_id))

    await _events.emit_step_started(project_id, run.issue_id, agent_name, step_run.id, term_id)

    return {
        "term_id": term_id,
        "agent_name": agent_name,
        "agent_intent": step.agent.intent if step.agent else "",
        "step_index": i,
        "step_run_id": step_run.id,
    }


async def monitor_step(
    run_id: str,
    step_index: int,
    term_id: str,
) -> None:
    """Background task: wait for step completion or PTY death (orchestrated mode).

    Cleans up the terminal when done (both normal completion and PTY death).
    """
    from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

    term_session = TerminalSession()
    _sessions[term_id] = term_session
    _ensure_reader(term_id, terminal_service)

    event = _completion.get_completion_event(run_id, step_index)
    if event is None:
        logger.warning("monitor_step: no completion event for (%s, %d)", run_id, step_index)
        return

    async def wait_pty_death():
        await term_session.pty_dead.wait()

    pty_task = asyncio.create_task(wait_pty_death())
    event_task = asyncio.create_task(event.wait())

    try:
        done, pending = await asyncio.wait(
            [pty_task, event_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()

        if pty_task in done and event_task not in done:
            # PTY died before step completed -- mark as FAILED
            logger.error(
                "Step %d of run %s: PTY died before finished_pipeline_step",
                step_index, run_id,
            )
            async with async_session() as fresh_session:
                run = await _queries.get_run_with_session(run_id, fresh_session)
                if run.status == PipelineRunStatus.RUNNING:
                    run.status = PipelineRunStatus.FAILED
                    run.finished_at = now()
                    for sr in run.step_runs:
                        if (
                            sr.pipeline_step
                            and sr.pipeline_step.order_index == step_index
                            and sr.status == PipelineStepRunStatus.RUNNING
                        ):
                            sr.status = PipelineStepRunStatus.FAILED
                            sr.finished_at = now()
                            break
                    # Fire event engine BEFORE commit
                    try:
                        issue = await fresh_session.get(Issue, run.issue_id)
                        await _events.fire_pipeline_event(
                            run.pipeline_id, "step_failed", None,
                            run_id=run_id, issue_id=run.issue_id,
                            project_id=issue.project_id if issue else "",
                            step_index=step_index,
                            session=fresh_session,
                        )
                    except Exception:
                        logger.exception("Event engine step_failed failed for PTY death run %s", run_id)
                    await fresh_session.commit()
        else:
            # Normal completion
            async with async_session() as fresh_session:
                run = await _queries.get_run_with_session(run_id, fresh_session)
                if run.status == PipelineRunStatus.RUNNING:
                    run.status = PipelineRunStatus.WAITING_FOR_STEP
                completed_step_run_id = None
                completed_agent_name = None
                for sr in run.step_runs:
                    if (
                        sr.pipeline_step
                        and sr.pipeline_step.order_index == step_index
                        and sr.status == PipelineStepRunStatus.RUNNING
                    ):
                        sr.status = PipelineStepRunStatus.COMPLETED
                        sr.finished_at = now()
                        completed_step_run_id = sr.id
                        if sr.pipeline_step and sr.pipeline_step.agent:
                            completed_agent_name = sr.pipeline_step.agent.name
                        break
                await fresh_session.commit()

                # Fire event engine for step_completed
                if completed_step_run_id:
                    try:
                        # Resolve project_id from issue
                        issue = await fresh_session.get(Issue, run.issue_id)
                        project_id = issue.project_id if issue else ""
                        await _events.fire_pipeline_event(
                            run.pipeline_id, "step_completed",
                            None,
                            run_id=run_id, issue_id=run.issue_id,
                            project_id=project_id,
                            agent_name=completed_agent_name,
                            step_run_id=completed_step_run_id,
                            step_index=step_index,
                            session=fresh_session,
                        )
                    except Exception:
                        logger.exception("Failed to fire step_completed event for run %s", run_id)
    finally:
        _completion.unregister_completion_event(run_id, step_index)
        _terminal.cleanup_terminal(term_id)
