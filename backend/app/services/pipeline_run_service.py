import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineMessage,
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.services.event_service import event_service
from app.services.pipeline_task_manager import pipeline_task_manager
from app.services.terminal_service import terminal_service

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
        self, pipeline_id: str, issue_id: str, project_id: str, project_path: str
    ) -> dict:
        existing = await self.session.execute(
            select(PipelineRun).where(
                PipelineRun.issue_id == issue_id,
                PipelineRun.status == PipelineRunStatus.RUNNING,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(
                f"A pipeline is already running for issue {issue_id}"
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
            status=PipelineRunStatus.RUNNING,
            current_step_index=0,
            started_at=datetime.now(timezone.utc),
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

        task = asyncio.create_task(
            self._execute(run.id, project_id, project_path)
        )
        await pipeline_task_manager.start_task(run.id, task)

        return {
            "id": run.id,
            "pipeline_id": run.pipeline_id,
            "issue_id": run.issue_id,
            "status": run.status.value,
            "current_step_index": run.current_step_index,
            "steps": step_responses,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    async def _execute(
        self, run_id: str, project_id: str, project_path: str
    ) -> None:
        session = self.session
        if self.session_factory is not None:
            session = self.session_factory()

        try:
            run = await self._get_run_with_session(run_id, session)
            pipeline = await session.execute(
                select(Pipeline)
                .where(Pipeline.id == run.pipeline_id)
                .options(
                    selectinload(Pipeline.steps).selectinload(PipelineStep.agent)
                )
            )
            pipeline = pipeline.unique().scalar_one_or_none()
            if pipeline is None:
                return

            steps = sorted(pipeline.steps, key=lambda s: s.order_index)

            for i, step in enumerate(steps):
                step_run_result = await session.execute(
                    select(PipelineStepRun).where(
                        PipelineStepRun.pipeline_run_id == run_id,
                        PipelineStepRun.pipeline_step_id == step.id,
                    )
                )
                step_run = step_run_result.scalar_one_or_none()
                if step_run is None:
                    continue

                step_run.status = PipelineStepRunStatus.RUNNING
                step_run.started_at = datetime.now(timezone.utc)
                run.current_step_index = i
                await self._safe_flush_session(session)

                agent = step.agent
                agent_name = agent.name if agent else "unknown"
                agent_prompt = agent.intent if agent else ""

                term = terminal_service.create(
                    issue_id=run.issue_id,
                    project_id=project_id,
                    project_path=project_path,
                )
                term_id = term["id"]
                step_run.terminal_id = term_id
                await self._safe_commit_session(session)

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

                try:
                    success = await self._run_step(
                        term_id=term_id,
                        agent_name=agent_name,
                        intent=agent_prompt,
                        issue_id=run.issue_id,
                        run_id=run_id,
                        step_index=i,
                    )

                    if success:
                        step_run.status = PipelineStepRunStatus.COMPLETED
                        await event_service.emit({
                            "type": "agent_step_completed",
                            "project_id": project_id,
                            "issue_id": run.issue_id,
                            "agent_name": agent_name,
                            "step_run_id": step_run.id,
                        })
                    else:
                        step_run.status = PipelineStepRunStatus.FAILED
                        run.status = PipelineRunStatus.FAILED
                        step_run.finished_at = datetime.now(timezone.utc)
                        await self._safe_commit_session(session)
                        await event_service.emit({
                            "type": "agent_step_failed",
                            "project_id": project_id,
                            "issue_id": run.issue_id,
                            "agent_name": agent_name,
                            "step_run_id": step_run.id,
                        })
                        break

                    step_run.finished_at = datetime.now(timezone.utc)
                    await self._safe_commit_session(session)
                except asyncio.CancelledError:
                    terminal_service.kill(term_id)
                    raise
                except Exception:
                    logger.exception("Step %s failed with exception", agent_name)
                    step_run.status = PipelineStepRunStatus.FAILED
                    run.status = PipelineRunStatus.FAILED
                    step_run.finished_at = datetime.now(timezone.utc)
                    await self._safe_commit_session(session)
                    await event_service.emit({
                        "type": "agent_step_failed",
                        "project_id": project_id,
                        "issue_id": run.issue_id,
                        "agent_name": agent_name,
                        "step_run_id": step_run.id,
                    })
                    break

            await session.refresh(run)
            if run.status != PipelineRunStatus.FAILED:
                run.status = PipelineRunStatus.COMPLETED
            run.finished_at = datetime.now(timezone.utc)
            await self._safe_commit_session(session)

            await event_service.emit({
                "type": "pipeline_completed",
                "project_id": project_id,
                "issue_id": run.issue_id,
                "run_id": run_id,
                "status": run.status.value,
            })
        except asyncio.CancelledError:
            raise
        finally:
            if self.session_factory is not None:
                try:
                    await session.close()
                except Exception:
                    pass
            await pipeline_task_manager.cleanup_task(run_id)

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
        import os as _os
        from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

        pty = terminal_service.get_pty(term_id)

        session = TerminalSession()
        _sessions[term_id] = session
        _ensure_reader(term_id, terminal_service)

        is_windows = _platform.system() == "Windows"
        command = f'claude --dangerously-skip-permissions "/run-pipeline {issue_id}"'

        if is_windows:
            pty.write(f"{command}\r\n")
            pty.write("exit\r\n")
        else:
            pty.write(f"{command}; exit\r\n")

        # Wait for step completion event, PTY death, or timeout
        event = asyncio.Event()
        _step_completion_events[(run_id, step_index)] = event

        timeout = int(_os.environ.get("MANAGER_AI_PIPELINE_STEP_TIMEOUT", "1800"))

        async def wait_pty_death():
            await session.pty_dead.wait()

        pty_task = asyncio.create_task(wait_pty_death())
        event_task = asyncio.create_task(event.wait())

        try:
            done, pending = await asyncio.wait(
                [pty_task, event_task],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if event_task in done:
                success = True
            elif pty_task in done:
                logger.error(
                    "Step %s failed: PTY died before finished_pipeline_step called", agent_name
                )
                success = False
            else:
                logger.error("Step %s timed out after %ds", agent_name, timeout)
                terminal_service.kill(term_id)
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
                selectinload(PipelineRun.step_runs)
                .selectinload(PipelineStepRun.pipeline_step)
                .selectinload(PipelineStep.agent)
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
                selectinload(PipelineRun.step_runs)
                .selectinload(PipelineStepRun.pipeline_step)
                .selectinload(PipelineStep.agent)
            )
            .order_by(PipelineRun.created_at.desc())
        )
        runs = result.unique().scalars().all()
        return [
            {
                "id": r.id,
                "pipeline_id": r.pipeline_id,
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

    async def cancel_run(self, run_id: str) -> bool:
        run = await self._get_run(run_id)
        if run.status != PipelineRunStatus.RUNNING:
            raise ValidationError("Can only cancel running pipelines")
        await pipeline_task_manager.cancel_task(run_id)
        run.status = PipelineRunStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
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
