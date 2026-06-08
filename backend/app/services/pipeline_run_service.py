import asyncio
import logging
import shlex

from app.utils.datetime import now
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.issue import Issue
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineMessage,
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.providers.registry import AgentProviderRegistry
from app.services.event_service import event_service
from app.services.pipeline_task_manager import pipeline_task_manager
from app.services.terminal_service import terminal_service
from app.services.terminal_session import _save_recording, _sessions, _stop_reader

logger = logging.getLogger(__name__)

# Maps (run_id, step_index) -> asyncio.Event for step completion signaling
_step_completion_events: dict[tuple[str, int], asyncio.Event] = {}


def set_step_completed(run_id: str, step_index: int) -> bool:
    """Signal that a pipeline step has completed. Called by finished_pipeline_step MCP tool."""
    key = (run_id, step_index)
    event = _step_completion_events.get(key)
    if event is None:
        return False
    event.set()
    return True


class PipelineRunService:
    def __init__(self, session: AsyncSession, session_factory=None):
        self.session = session
        self.session_factory = session_factory

    async def start(
        self, pipeline_id: str, issue_id: str, project_id: str, project_path: str,
        orchestrated: bool = False,
    ) -> dict:
        existing = await self.session.execute(
            select(PipelineRun).where(
                PipelineRun.issue_id == issue_id,
                PipelineRun.status.in_([
                    PipelineRunStatus.RUNNING,
                    PipelineRunStatus.WAITING_FOR_STEP,
                ]),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(
                f"A pipeline is already running or waiting for step for issue {issue_id}"
            )

        pipeline = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .options(
                selectinload(Pipeline.steps).selectinload(PipelineStep.agent)
            )
        )
        pipeline = pipeline.unique().scalar_one_or_none()
        if pipeline is None:
            raise NotFoundError(f"Pipeline not found: {pipeline_id}")

        run = PipelineRun(
            pipeline_id=pipeline_id,
            issue_id=issue_id,
            status=PipelineRunStatus.WAITING_FOR_STEP if orchestrated else PipelineRunStatus.RUNNING,
            current_step_index=0,
            orchestrated=orchestrated,
            started_at=now(),
        )
        self.session.add(run)
        await self.session.flush()

        step_responses = []
        for step in sorted(pipeline.steps, key=lambda s: s.order_index):
            step_run = PipelineStepRun(
                pipeline_run_id=run.id,
                pipeline_step_id=step.id,
                status=PipelineStepRunStatus.PENDING,
            )
            self.session.add(step_run)
            await self.session.flush()
            step_responses.append(
                {
                    "id": step_run.id,
                    "pipeline_run_id": run.id,
                    "pipeline_step_id": step.id,
                    "agent_name": step.agent.name if step.agent else "unknown",
                    "status": PipelineStepRunStatus.PENDING.value,
                    "terminal_id": None,
                }
            )

        if orchestrated:
            # Orchestrated mode: no auto-execution — Hermes controls each step
            await self.session.commit()
        else:
            # Auto mode: spawn background execution
            task = asyncio.create_task(
                self._execute(run.id, project_id, project_path)
            )
            await pipeline_task_manager.start_task(run.id, task)
            await self.session.commit()

        return {
            "id": run.id,
            "pipeline_id": run.pipeline_id,
            "pipeline_name": pipeline.name,
            "issue_id": run.issue_id,
            "status": run.status.value,
            "current_step_index": run.current_step_index,
            "steps": step_responses,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    async def resolve_rejection_target(
        self, run_id: str, step_id: str
    ) -> int | None:
        """Check event rules for rejection redirect. Returns target order_index or None."""
        from app.services.pipeline_service import PipelineService

        run = await self._get_run_with_session(run_id, self.session)
        pipeline_svc = PipelineService(self.session)
        rule = await pipeline_svc.get_event_rule_for_step(
            run.pipeline_id, "step_rejected", step_id
        )
        if rule is None:
            return None
        pipeline = await self.session.get(Pipeline, run.pipeline_id)
        if pipeline is None:
            return None
        for s in pipeline.steps:
            if s.id == rule.target_step_id:
                return s.order_index
        return None

    async def reject_step(
        self, run_id: str, reason: str, target_step_index: int, project_id: str
    ) -> dict:
        """Reject current pipeline step and regress to target step.

        Sets current step_run to REJECTED, creates new RUNNING step_run for
        the target step, and signals _execute() to pick up the change.
        """
        run = await self._get_run_with_session(run_id, self.session)

        if run.status in (PipelineRunStatus.COMPLETED, PipelineRunStatus.FAILED):
            raise ValidationError("Can only reject steps in a running pipeline")

        if target_step_index < 0:
            raise ValidationError("target_step_index must be >= 0")
        if target_step_index >= run.current_step_index:
            raise ValidationError(
                f"target_step_index ({target_step_index}) must be less than "
                f"current_step_index ({run.current_step_index})"
            )

        # Find the current RUNNING step run
        current_sr = None
        for sr in run.step_runs:
            if sr.status == PipelineStepRunStatus.RUNNING:
                current_sr = sr
                break

        if current_sr is None:
            raise ValidationError("No RUNNING step run found")

        agent_name = "unknown"
        if current_sr.pipeline_step and current_sr.pipeline_step.agent:
            agent_name = current_sr.pipeline_step.agent.name

        # Mark current step as REJECTED
        current_sr.status = PipelineStepRunStatus.REJECTED
        current_sr.finished_at = now()

        # Find pipeline step at target index and create new step run
        pipeline = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == run.pipeline_id)
            .options(
                selectinload(Pipeline.steps).selectinload(PipelineStep.agent)
            )
        )
        pipeline = pipeline.unique().scalar_one_or_none()
        if pipeline is None:
            raise NotFoundError(f"Pipeline not found: {run.pipeline_id}")

        steps = sorted(pipeline.steps, key=lambda s: s.order_index)
        if target_step_index >= len(steps):
            raise ValidationError(
                f"target_step_index ({target_step_index}) out of bounds "
                f"(pipeline has {len(steps)} steps)"
            )

        target_step = steps[target_step_index]
        new_step_run = PipelineStepRun(
            pipeline_run_id=run.id,
            pipeline_step_id=target_step.id,
            status=PipelineStepRunStatus.RUNNING,
        )
        self.session.add(new_step_run)
        new_step_run.started_at = now()
        await self.session.flush()

        # Update run state
        run.current_step_index = target_step_index
        run.rejection_count = (run.rejection_count or 0) + 1

        max_reached = False
        if run.rejection_count >= 3:
            run.status = PipelineRunStatus.FAILED
            run.finished_at = now()
            max_reached = True

        # Save rejection reason as pipeline message
        msg = PipelineMessage(
            pipeline_run_id=run.id,
            sender_agent_name=agent_name,
            content=f"**Step rejected — regressing to step {target_step_index}**\n\n"
                    f"Reason: {reason}",
        )
        self.session.add(msg)

        # Emit WebSocket event
        await event_service.emit({
            "type": "pipeline_step_rejected",
            "project_id": project_id,
            "issue_id": run.issue_id,
            "run_id": run_id,
            "step_run_id": current_sr.id,
            "agent_name": agent_name,
            "reason": reason,
            "target_step_index": target_step_index,
            "rejection_count": run.rejection_count,
        })

        # Commit so _execute()'s session.refresh() sees REJECTED status + new step_run
        await self.session.commit()

        # Signal _execute() to wake up and pick up changes
        current_idx = run.current_step_index
        # Need to signal at the OLD step index since that's what _execute is waiting on
        old_idx = None
        for i, step in enumerate(steps):
            if step.id == current_sr.pipeline_step_id:
                old_idx = i
                break

        if old_idx is not None:
            set_step_completed(run_id, old_idx)

        return {
            "success": True,
            "rejection_count": run.rejection_count,
            "max_reached": max_reached,
        }

    async def _execute(
        self, run_id: str, project_id: str, project_path: str
    ) -> None:
        session = self.session
        if self.session_factory is not None:
            session = self.session_factory()

        try:
            run, steps = await self._wait_for_run(run_id, session)
            if run is None:
                return

            while run.current_step_index < len(steps) and run.status != PipelineRunStatus.FAILED:
                i = run.current_step_index
                step = steps[i]

                term_id, agent_name, step_run, step = await self._setup_step_environment(
                    step, run, session, project_id, project_path, run_id
                )
                if step_run is None:
                    continue

                try:
                    success = await self._run_step(
                        term_id=term_id,
                        agent_name=agent_name,
                        intent=step.agent.intent if step.agent else "",
                        issue_id=run.issue_id,
                        run_id=run_id,
                        step_index=i,
                    )

                    await session.refresh(run)
                    await session.refresh(step_run)

                    if step_run.status == PipelineStepRunStatus.REJECTED:
                        step_run.finished_at = now()
                        await self._safe_commit_session(session)
                        continue

                    should_continue = await self._handle_step_completion(
                        run, step_run, session, success, agent_name,
                        project_id, run.issue_id,
                    )
                    if not should_continue:
                        break

                    step_run.finished_at = now()
                    await self._safe_commit_session(session)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Step %s failed with exception", agent_name)
                    step_run.status = PipelineStepRunStatus.FAILED
                    run.status = PipelineRunStatus.FAILED
                    step_run.finished_at = now()
                    await self._safe_commit_session(session)
                    await event_service.emit({
                        "type": "agent_step_failed",
                        "project_id": project_id,
                        "issue_id": run.issue_id,
                        "agent_name": agent_name,
                        "step_run_id": step_run.id,
                    })
                    break
                finally:
                    await self._cleanup_step(term_id)

            await self._finalize_run(run, session, project_id, run.issue_id, run_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Pipeline %s failed with unexpected error", run_id)
            try:
                run.status = PipelineRunStatus.FAILED
                run.finished_at = now()
                await self._safe_commit_session(session)
            except Exception:
                pass
            await event_service.emit({
                "type": "pipeline_completed",
                "project_id": project_id,
                "issue_id": run.issue_id,
                "run_id": run_id,
                "status": PipelineRunStatus.FAILED.value,
            })
        finally:
            if self.session_factory is not None:
                try:
                    await session.close()
                except Exception:
                    pass
            await pipeline_task_manager.cleanup_task(run_id)

    async def _wait_for_run(
        self, run_id: str, session: AsyncSession
    ) -> tuple[PipelineRun | None, list[PipelineStep] | None]:
        run = None
        for _ in range(50):
            try:
                run = await self._get_run_with_session(run_id, session)
                break
            except NotFoundError:
                await asyncio.sleep(0.1)
        if run is None:
            logger.error("Pipeline run %s not found — _execute started before commit finished", run_id)
            return None, None
        pipeline = await session.execute(
            select(Pipeline)
            .where(Pipeline.id == run.pipeline_id)
            .options(
                selectinload(Pipeline.steps).selectinload(PipelineStep.agent)
            )
        )
        pipeline = pipeline.unique().scalar_one_or_none()
        if pipeline is None:
            return None, None

        steps = sorted(pipeline.steps, key=lambda s: s.order_index)
        return run, steps

    async def _setup_step_environment(
        self,
        step: PipelineStep,
        run: PipelineRun,
        session: AsyncSession,
        project_id: str,
        project_path: str,
        run_id: str,
    ) -> tuple[str | None, str | None, PipelineStepRun | None, PipelineStep | None]:
        i = run.current_step_index

        step_run_result = await session.execute(
            select(PipelineStepRun).where(
                PipelineStepRun.pipeline_run_id == run_id,
                PipelineStepRun.pipeline_step_id == step.id,
            ).order_by(PipelineStepRun.started_at.desc().nulls_last())
        )
        step_run = step_run_result.scalars().first()
        if step_run is None:
            return None, None, None, step

        step_run.status = PipelineStepRunStatus.RUNNING
        step_run.started_at = now()
        run.current_step_index = i
        await self._safe_flush_session(session)

        agent = step.agent
        agent_name = agent.name if agent else "unknown"

        from app.models.project import Project
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
        await self._safe_commit_session(session)

        if project_shell:
            from app.services.wsl_support import (
                is_wsl_shell,
                win_to_wsl_path,
            )

            if is_wsl_shell(project_shell):
                cwd_wsl = win_to_wsl_path(project_path)
                pty_for_cd = terminal_service.get_pty(term_id)
                pty_for_cd.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

        await event_service.emit({
            "type": "agent_step_started",
            "project_id": project_id,
            "issue_id": run.issue_id,
            "agent_name": agent_name,
            "step_run_id": step_run.id,
            "terminal_id": term_id,
        })

        await event_service.emit({
            "type": "terminal_created",
            "terminal_id": term_id,
            "issue_id": run.issue_id,
            "project_id": project_id,
        })

        return term_id, agent_name, step_run, step

    async def _handle_step_completion(
        self,
        run: PipelineRun,
        step_run: PipelineStepRun,
        session: AsyncSession,
        success: bool,
        agent_name: str,
        project_id: str,
        issue_id: str,
    ) -> bool:
        if success:
            step_run.status = PipelineStepRunStatus.COMPLETED
            run.current_step_index += 1
            await event_service.emit({
                "type": "agent_step_completed",
                "project_id": project_id,
                "issue_id": issue_id,
                "agent_name": agent_name,
                "step_run_id": step_run.id,
            })
            return True
        else:
            step_run.status = PipelineStepRunStatus.FAILED
            run.status = PipelineRunStatus.FAILED
            step_run.finished_at = now()
            await self._safe_commit_session(session)
            await event_service.emit({
                "type": "agent_step_failed",
                "project_id": project_id,
                "issue_id": issue_id,
                "agent_name": agent_name,
                "step_run_id": step_run.id,
            })
            return False

    async def _cleanup_step(self, term_id: str) -> None:
        _save_recording(term_id, terminal_service.get_buffered_output(term_id))
        _stop_reader(term_id)
        _sessions.pop(term_id, None)
        terminal_service.kill(term_id)

    async def _finalize_run(
        self,
        run: PipelineRun,
        session: AsyncSession,
        project_id: str,
        issue_id: str,
        run_id: str,
    ) -> None:
        await session.refresh(run)
        if run.status != PipelineRunStatus.FAILED:
            run.status = PipelineRunStatus.COMPLETED
        run.finished_at = now()
        await self._safe_commit_session(session)

        await event_service.emit({
            "type": "pipeline_completed",
            "project_id": project_id,
            "issue_id": issue_id,
            "run_id": run_id,
            "status": run.status.value,
        })

    async def _safe_flush_session(self, session: AsyncSession) -> None:
        try:
            await session.flush()
        except Exception:
            logger.warning("_safe_flush_session: flush failed, rolling back", exc_info=True)
            await session.rollback()
            await session.flush()

    async def _safe_commit_session(self, session: AsyncSession) -> None:
        """Commit and release SQLite write lock.

        Called before/after pipeline steps so the long-running background
        task doesn't hold an open transaction that blocks MCP tool writes
        from the claude subprocess.
        """
        try:
            await session.commit()
        except Exception:
            logger.warning("_safe_commit_session: commit failed, rolling back", exc_info=True)
            await session.rollback()
            await session.commit()

    async def _run_step(
        self,
        term_id: str,
        agent_name: str,
        intent: str,
        issue_id: str,
        run_id: str,
        step_index: int,
    ) -> bool:
        import platform as _platform
        from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

        pty = terminal_service.get_pty(term_id)

        session = TerminalSession()
        _sessions[term_id] = session
        _ensure_reader(term_id, terminal_service)

        is_windows = _platform.system() == "Windows"
        provider = AgentProviderRegistry.get("claude")
        command = provider.build_run_pipeline_command(issue_id)

        if is_windows:
            pty.write(f"{command} & exit\r\n")
        else:
            pty.write(f"{command}; exit\r\n")

        # Wait for step completion event or PTY death
        event = asyncio.Event()
        _step_completion_events[(run_id, step_index)] = event

        async def wait_pty_death():
            await session.pty_dead.wait()

        pty_task = asyncio.create_task(wait_pty_death())
        event_task = asyncio.create_task(event.wait())

        try:
            done, pending = await asyncio.wait(
                [pty_task, event_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if event_task in done:
                success = True
            elif pty_task in done:
                logger.error(
                    "Step %s failed: PTY died before finished_pipeline_step called", agent_name
                )
                success = False

            for t in pending:
                t.cancel()
        finally:
            _step_completion_events.pop((run_id, step_index), None)

        return success

    async def _get_run(self, run_id: str) -> PipelineRun:
        return await self._get_run_with_session(run_id, self.session)

    async def _get_run_with_session(self, run_id: str, session: AsyncSession) -> PipelineRun:
        result = await session.execute(
            select(PipelineRun)
            .where(PipelineRun.id == run_id)
            .options(
                selectinload(PipelineRun.pipeline),
                selectinload(PipelineRun.step_runs)
                .selectinload(PipelineStepRun.pipeline_step)
                .selectinload(PipelineStep.agent),
            )
        )
        run = result.unique().scalar_one_or_none()
        if run is None:
            raise NotFoundError(f"Pipeline run not found: {run_id}")
        return run

    async def get_run(self, run_id: str) -> dict:
        run = await self._get_run(run_id)
        steps = []
        for sr in sorted(
            run.step_runs,
            key=lambda s: s.pipeline_step.order_index if s.pipeline_step else 0,
        ):
            agent_name = "unknown"
            agent_intent = ""
            if sr.pipeline_step and sr.pipeline_step.agent:
                agent_name = sr.pipeline_step.agent.name
                agent_intent = sr.pipeline_step.agent.intent or ""
            steps.append(
                {
                    "id": sr.id,
                    "pipeline_run_id": sr.pipeline_run_id,
                    "pipeline_step_id": sr.pipeline_step_id,
                    "agent_name": agent_name,
                    "agent_intent": agent_intent,
                    "status": sr.status.value,
                    "terminal_id": sr.terminal_id,
                    "started_at": sr.started_at.isoformat() if sr.started_at else None,
                    "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
                }
            )
        return {
            "id": run.id,
            "pipeline_id": run.pipeline_id,
            "pipeline_name": run.pipeline.name if run.pipeline else "",
            "issue_id": run.issue_id,
            "status": run.status.value,
            "current_step_index": run.current_step_index,
            "steps": steps,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    async def get_runs_for_issue(self, issue_id: str) -> list[dict]:
        result = await self.session.execute(
            select(PipelineRun)
            .where(PipelineRun.issue_id == issue_id)
            .options(
                selectinload(PipelineRun.pipeline),
                selectinload(PipelineRun.step_runs)
                .selectinload(PipelineStepRun.pipeline_step)
                .selectinload(PipelineStep.agent),
            )
            .order_by(PipelineRun.created_at.desc())
        )
        runs = result.unique().scalars().all()
        return [
            {
                "id": r.id,
                "pipeline_id": r.pipeline_id,
                "pipeline_name": r.pipeline.name if r.pipeline else "",
                "issue_id": r.issue_id,
                "status": r.status.value,
                "current_step_index": r.current_step_index,
                "steps": [
                    {
                        "id": sr.id,
                        "pipeline_run_id": sr.pipeline_run_id,
                        "pipeline_step_id": sr.pipeline_step_id,
                        "agent_name": sr.pipeline_step.agent.name if sr.pipeline_step and sr.pipeline_step.agent else "unknown",
                        "agent_intent": sr.pipeline_step.agent.intent if sr.pipeline_step and sr.pipeline_step.agent else "",
                        "status": sr.status.value,
                        "terminal_id": sr.terminal_id,
                        "started_at": sr.started_at.isoformat() if sr.started_at else None,
                        "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
                    }
                    for sr in sorted(r.step_runs, key=lambda s: s.pipeline_step.order_index if s.pipeline_step else 0)
                ],
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]

    async def get_active_runs_for_issues(self, issue_ids: list[str]) -> dict[str, dict | None]:
        """Return active (RUNNING) pipeline runs for given issue ids.

        Returns dict: issue_id -> {pipeline_name, status} or None for issues
        without an active run.
        """
        result = await self.session.execute(
            select(PipelineRun)
            .where(
                PipelineRun.issue_id.in_(issue_ids),
                PipelineRun.status == PipelineRunStatus.RUNNING,
            )
            .options(selectinload(PipelineRun.pipeline))
        )
        runs = result.unique().scalars().all()
        run_by_issue: dict[str, dict | None] = {iid: None for iid in issue_ids}
        for r in runs:
            run_by_issue[r.issue_id] = {
                "pipeline_name": r.pipeline.name if r.pipeline else "",
                "status": r.status.value,
            }
        return run_by_issue

    async def get_active_runs_for_project(self, project_id: str) -> list[dict]:
        """Return active (RUNNING) pipeline runs for a project via Issue JOIN.

        PipelineRun has no project_id column, so JOIN through issues table.
        """
        result = await self.session.execute(
            select(PipelineRun)
            .join(Issue, PipelineRun.issue_id == Issue.id)
            .where(
                Issue.project_id == project_id,
                PipelineRun.status == PipelineRunStatus.RUNNING,
            )
            .options(
                selectinload(PipelineRun.pipeline),
                selectinload(PipelineRun.step_runs)
                .selectinload(PipelineStepRun.pipeline_step)
                .selectinload(PipelineStep.agent),
            )
            .order_by(PipelineRun.created_at.desc())
        )
        runs = result.unique().scalars().all()
        return [
            {
                "id": r.id,
                "pipeline_id": r.pipeline_id,
                "pipeline_name": r.pipeline.name if r.pipeline else "",
                "issue_id": r.issue_id,
                "status": r.status.value,
                "current_step_index": r.current_step_index,
                "steps": [
                    {
                        "id": sr.id,
                        "pipeline_run_id": sr.pipeline_run_id,
                        "pipeline_step_id": sr.pipeline_step_id,
                        "agent_name": sr.pipeline_step.agent.name if sr.pipeline_step and sr.pipeline_step.agent else "unknown",
                        "status": sr.status.value,
                        "terminal_id": sr.terminal_id,
                        "started_at": sr.started_at.isoformat() if sr.started_at else None,
                        "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
                    }
                    for sr in sorted(r.step_runs, key=lambda s: s.pipeline_step.order_index if s.pipeline_step else 0)
                ],
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]

    async def cancel_run(self, run_id: str) -> bool:
        run = await self._get_run(run_id)
        if run.status != PipelineRunStatus.RUNNING:
            raise ValidationError(f"Can only cancel active pipelines (status: {run.status.value})")
        await pipeline_task_manager.cancel_task(run_id)
        run.status = PipelineRunStatus.FAILED
        run.finished_at = now()
        await self._safe_flush_session(self.session)
        return True

    async def add_message(
        self, run_id: str, sender_agent_name: str, content: str
    ) -> dict:
        msg = PipelineMessage(
            pipeline_run_id=run_id,
            sender_agent_name=sender_agent_name,
            content=content,
        )
        self.session.add(msg)
        await self.session.flush()
        return {
            "id": msg.id,
            "pipeline_run_id": msg.pipeline_run_id,
            "sender_agent_name": msg.sender_agent_name,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }

    async def get_messages(self, run_id: str) -> list[dict]:
        result = await self.session.execute(
            select(PipelineMessage)
            .where(PipelineMessage.pipeline_run_id == run_id)
            .order_by(PipelineMessage.created_at)
        )
        msgs = result.scalars().all()
        return [
            {
                "id": m.id,
                "pipeline_run_id": m.pipeline_run_id,
                "sender_agent_name": m.sender_agent_name,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ]


    # ── Orchestrated pipeline methods (Hermes orchestrator) ──────────

    async def start_step(
        self, run_id: str, project_id: str, project_path: str,
    ) -> dict:
        """Spawn the PTY terminal + Claude for the current pipeline step.

        Called by Hermes via the start_pipeline_step MCP tool.
        The pipeline MUST be in WAITING_FOR_STEP status.
        """
        run = await self._get_run(run_id)
        if run.status != PipelineRunStatus.WAITING_FOR_STEP:
            raise ValidationError(
                f"Cannot start step: pipeline is {run.status.value}, "
                f"expected WAITING_FOR_STEP"
            )

        pipeline = await self.session.execute(
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
            raise ValidationError(
                f"No more steps available (index {i} >= {len(steps)})"
            )

        step = steps[i]

        step_run_result = await self.session.execute(
            select(PipelineStepRun).where(
                PipelineStepRun.pipeline_run_id == run_id,
                PipelineStepRun.pipeline_step_id == step.id,
            ).order_by(PipelineStepRun.started_at.desc().nulls_last())
        )
        step_run = step_run_result.scalars().first()
        if step_run is None:
            raise NotFoundError(f"StepRun not found for pipeline_step {step.id}")

        if step_run.status != PipelineStepRunStatus.PENDING:
            raise ValidationError(
                f"Step {i} is {step_run.status.value}, expected PENDING"
            )

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
        await self._safe_commit_session(self.session)

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

        event = asyncio.Event()
        _step_completion_events[(run_id, i)] = event

        asyncio.create_task(self._monitor_step(
            run_id=run_id, step_index=i, term_id=term_id,
        ))

        await event_service.emit({
            "type": "agent_step_started",
            "project_id": project_id,
            "issue_id": run.issue_id,
            "agent_name": agent_name,
            "step_run_id": step_run.id,
            "terminal_id": term_id,
        })

        return {
            "term_id": term_id,
            "agent_name": agent_name,
            "agent_intent": step.agent.intent if step.agent else "",
            "step_index": i,
            "step_run_id": step_run.id,
        }

    async def _monitor_step(
        self, run_id: str, step_index: int, term_id: str,
    ) -> None:
        """Background task: wait for step completion or PTY death."""
        from app.services.terminal_session import (
            TerminalSession, _sessions, _ensure_reader,
        )

        session = TerminalSession()
        _sessions[term_id] = session
        _ensure_reader(term_id, terminal_service)

        event = _step_completion_events.get((run_id, step_index))

        async def wait_pty_death():
            await session.pty_dead.wait()

        if event is None:
            logger.warning(
                "_monitor_step: no completion event for (%s, %d)",
                run_id, step_index,
            )
            return

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
                logger.error(
                    "Step %d of run %s: PTY died before finished_pipeline_step",
                    step_index, run_id,
                )
                async with async_session() as fresh_session:
                    run = await self._get_run_with_session(run_id, fresh_session)
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
                        await fresh_session.commit()
        finally:
            _step_completion_events.pop((run_id, step_index), None)

    async def advance_step(self, run_id: str) -> dict:
        """Advance the pipeline to the next step."""
        run = await self._get_run(run_id)
        if run.status != PipelineRunStatus.WAITING_FOR_STEP:
            raise ValidationError(
                f"Cannot advance: pipeline is {run.status.value}, "
                f"expected WAITING_FOR_STEP"
            )

        i = run.current_step_index
        current_completed = False
        for sr in run.step_runs:
            if sr.pipeline_step and sr.pipeline_step.order_index == i:
                if sr.status == PipelineStepRunStatus.COMPLETED:
                    current_completed = True
                break

        if not current_completed:
            raise ValidationError(
                f"Cannot advance: step {i} is not COMPLETED"
            )

        total_steps = len(run.step_runs)
        if i + 1 >= total_steps:
            run.status = PipelineRunStatus.COMPLETED
            run.finished_at = now()
            await self._safe_commit_session(self.session)

            issue = await self.session.get(Issue, run.issue_id)

            await event_service.emit({
                "type": "pipeline_completed",
                "project_id": issue.project_id if issue else "",
                "issue_id": run.issue_id,
                "run_id": run_id,
                "status": PipelineRunStatus.COMPLETED.value,
            })
            return {
                "status": "COMPLETED",
                "next_step_index": None,
                "pipeline_finished": True,
            }

        run.current_step_index = i + 1
        run.status = PipelineRunStatus.WAITING_FOR_STEP
        await self._safe_commit_session(self.session)

        await event_service.emit({
            "type": "pipeline_step_advanced",
            "run_id": run_id,
            "issue_id": run.issue_id,
            "from_step": i,
            "to_step": i + 1,
            "status": PipelineRunStatus.WAITING_FOR_STEP.value,
        })

        return {
            "status": "WAITING_FOR_STEP",
            "next_step_index": i + 1,
            "pipeline_finished": False,
        }

    async def pause_run(self, run_id: str) -> dict:
        """Pause a pipeline run."""
        run = await self._get_run(run_id)
        if run.status not in (
            PipelineRunStatus.RUNNING,
            PipelineRunStatus.WAITING_FOR_STEP,
        ):
            raise ValidationError(
                f"Cannot pause: pipeline is {run.status.value}, "
                f"expected RUNNING or WAITING_FOR_STEP"
            )

        if run.status == PipelineRunStatus.RUNNING:
            step_idx = run.current_step_index
            for sr in run.step_runs:
                if (
                    sr.pipeline_step
                    and sr.pipeline_step.order_index == step_idx
                    and sr.terminal_id
                ):
                    _save_recording(
                        sr.terminal_id,
                        terminal_service.get_buffered_output(sr.terminal_id),
                    )
                    _stop_reader(sr.terminal_id)
                    _sessions.pop(sr.terminal_id, None)
                    terminal_service.kill(sr.terminal_id)
                    sr.status = PipelineStepRunStatus.FAILED
                    sr.finished_at = now()
                    break

        run.status = PipelineRunStatus.PAUSED
        await self._safe_commit_session(self.session)

        await event_service.emit({
            "type": "pipeline_paused",
            "run_id": run_id,
            "issue_id": run.issue_id,
        })

        return {"status": "PAUSED"}

    async def resume_run(self, run_id: str) -> dict:
        """Resume a paused pipeline."""
        run = await self._get_run(run_id)
        if run.status != PipelineRunStatus.PAUSED:
            raise ValidationError(
                f"Cannot resume: pipeline is {run.status.value}, "
                f"expected PAUSED"
            )

        run.status = PipelineRunStatus.WAITING_FOR_STEP
        await self._safe_commit_session(self.session)

        await event_service.emit({
            "type": "pipeline_resumed",
            "run_id": run_id,
            "issue_id": run.issue_id,
        })

        return {"status": "WAITING_FOR_STEP"}
