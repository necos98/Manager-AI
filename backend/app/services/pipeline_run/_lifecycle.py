"""Pipeline run lifecycle: start, pause, resume, cancel, finalize."""

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
from app.services.pipeline_run import (
    _events,
    _execution,
    _queries,
    _responses,
    _safe_session,
    _terminal,
)
from app.services.pipeline_task_manager import pipeline_task_manager
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def start(
    pipeline_id: str,
    issue_id: str,
    project_id: str,
    project_path: str,
    session: AsyncSession,
    session_factory=None,
) -> dict:
    """Start a pipeline run (always auto-mode). Returns run details with step runs."""
    # Guard: no concurrent runs
    existing = await session.execute(
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

    # Load pipeline
    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
    )
    pipeline = pipeline.unique().scalar_one_or_none()
    if pipeline is None:
        raise NotFoundError(f"Pipeline not found: {pipeline_id}")

    # Create run — always RUNNING (auto-mode)
    run = PipelineRun(
        pipeline_id=pipeline_id,
        issue_id=issue_id,
        status=PipelineRunStatus.RUNNING,
        current_step_index=0,
        started_at=now(),
    )
    session.add(run)
    await session.flush()

    # Create step runs + build response
    step_responses = []
    for step in sorted(pipeline.steps, key=lambda s: s.order_index):
        step_run = PipelineStepRun(
            pipeline_run_id=run.id,
            pipeline_step_id=step.id,
            status=PipelineStepRunStatus.PENDING,
        )
        session.add(step_run)
        await session.flush()
        step_responses.append(_responses.start_step_run_to_dict(step_run))

    task = asyncio.create_task(
        _execution.execute(run.id, project_id, project_path, session, session_factory)
    )
    await pipeline_task_manager.start_task(run.id, task)
    await session.commit()

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


async def pause_run(run_id: str, session: AsyncSession) -> dict:
    """Pause a pipeline run."""
    run = await _queries.get_run_with_session(run_id, session)

    if run.status not in (PipelineRunStatus.RUNNING, PipelineRunStatus.WAITING_FOR_STEP):
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
                _terminal.cleanup_terminal(sr.terminal_id)
                sr.status = PipelineStepRunStatus.FAILED
                sr.finished_at = now()
                break

        await pipeline_task_manager.cancel_task(run_id)

    run.status = PipelineRunStatus.PAUSED
    await _safe_session.safe_commit(session)
    await _events.emit_pipeline_paused(run_id, run.issue_id)
    return {"status": "PAUSED"}


async def resume_run(run_id: str, session: AsyncSession) -> dict:
    """Resume a paused pipeline."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status != PipelineRunStatus.PAUSED:
        raise ValidationError(
            f"Cannot resume: pipeline is {run.status.value}, "
            f"expected PAUSED"
        )
    run.status = PipelineRunStatus.WAITING_FOR_STEP
    await _safe_session.safe_commit(session)
    await _events.emit_pipeline_resumed(run_id, run.issue_id)
    return {"status": "WAITING_FOR_STEP"}


async def cancel_run(run_id: str, session: AsyncSession) -> bool:
    """Cancel a running pipeline and clean up all resources."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status != PipelineRunStatus.RUNNING:
        raise ValidationError(
            f"Can only cancel active pipelines (status: {run.status.value})"
        )

    # Look up project_id from issue
    issue = await session.get(Issue, run.issue_id)
    project_id = issue.project_id if issue else ""

    # Kill active terminal first so the reader thread unblocks
    for sr in run.step_runs:
        if sr.status == PipelineStepRunStatus.RUNNING and sr.terminal_id:
            _terminal.cleanup_terminal(sr.terminal_id)
            sr.status = PipelineStepRunStatus.FAILED
            sr.finished_at = now()
            break

    # Cancel background task
    await pipeline_task_manager.cancel_task(run_id)

    run.status = PipelineRunStatus.FAILED
    run.finished_at = now()

    # Fire event engine BEFORE flush — action handlers run in same transaction
    try:
        await _events.fire_pipeline_event(
            run.pipeline_id, "pipeline_completed", None,
            run_id=run_id, issue_id=run.issue_id, project_id=project_id,
            metadata={"status": PipelineRunStatus.FAILED.value, "reason": "cancelled"},
            session=session,
        )
    except Exception:
        logger.exception("Event engine pipeline_completed action failed for cancel on run %s", run_id)

    await _safe_session.safe_flush(session)

    # WS emit (fire-and-forget, no session needed)
    await _events.emit_pipeline_completed(
        project_id, run.issue_id, run_id, PipelineRunStatus.FAILED.value,
    )
    return True
