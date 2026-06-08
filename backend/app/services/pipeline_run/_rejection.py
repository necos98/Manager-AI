"""Pipeline step rejection logic."""

import logging

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
from app.services.pipeline_run import _completion, _events, _queries, _safe_session
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def resolve_rejection_target(
    run_id: str, step_id: str, session: AsyncSession,
) -> int | None:
    """Check event rules for rejection redirect. Returns target order_index or None."""
    from app.services.pipeline_service import PipelineService

    run = await _queries.get_run_with_session(run_id, session)
    pipeline_svc = PipelineService(session)
    rule = await pipeline_svc.get_event_rule_for_step(
        run.pipeline_id, "step_rejected", step_id,
    )
    if rule is None:
        return None
    pipeline = await session.get(Pipeline, run.pipeline_id)
    if pipeline is None:
        return None
    for s in pipeline.steps:
        if s.id == rule.target_step_id:
            return s.order_index
    return None


async def reject_step(
    run_id: str,
    reason: str,
    target_step_index: int,
    project_id: str,
    session: AsyncSession,
) -> dict:
    """Reject current pipeline step and regress to target step."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status in (PipelineRunStatus.COMPLETED, PipelineRunStatus.FAILED):
        raise ValidationError("Can only reject steps in a running pipeline")
    if target_step_index < 0:
        raise ValidationError("target_step_index must be >= 0")
    if target_step_index >= run.current_step_index:
        raise ValidationError(
            f"target_step_index ({target_step_index}) must be less than "
            f"current_step_index ({run.current_step_index})"
        )

    # Find current RUNNING step
    current_sr = next(
        (sr for sr in run.step_runs if sr.status == PipelineStepRunStatus.RUNNING),
        None,
    )
    if current_sr is None:
        raise ValidationError("No RUNNING step run found")

    agent_name = "unknown"
    if current_sr.pipeline_step and current_sr.pipeline_step.agent:
        agent_name = current_sr.pipeline_step.agent.name

    # Mark as REJECTED
    current_sr.status = PipelineStepRunStatus.REJECTED
    current_sr.finished_at = now()

    # Load pipeline, find target step
    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == run.pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
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
    session.add(new_step_run)
    new_step_run.started_at = now()
    await session.flush()

    # Update run state
    run.current_step_index = target_step_index
    run.rejection_count = (run.rejection_count or 0) + 1
    max_reached = False
    if run.rejection_count >= 3:
        run.status = PipelineRunStatus.FAILED
        run.finished_at = now()
        max_reached = True

    # Save rejection message
    msg = PipelineMessage(
        pipeline_run_id=run.id,
        sender_agent_name=agent_name,
        content=(
            f"**Step rejected -- regressing to step {target_step_index}**\n\n"
            f"Reason: {reason}"
        ),
    )
    session.add(msg)

    await _events.emit_step_rejected(
        project_id, run.issue_id, run_id, current_sr.id,
        agent_name, reason, target_step_index, run.rejection_count,
    )

    # Fire event engine BEFORE commit — action handlers run in same transaction
    try:
        await _events.fire_pipeline_event(
            run.pipeline_id, "step_rejected",
            current_sr.pipeline_step_id,
            run_id=run_id, issue_id=run.issue_id, project_id=project_id,
            agent_name=agent_name, step_run_id=current_sr.id,
            step_index=target_step_index,
            metadata={"reason": reason, "rejection_count": run.rejection_count},
            session=session,
        )
    except Exception:
        logger.exception("Event engine step_rejected action failed for run %s", run_id)

    await _safe_session.safe_commit(session)

    # Signal _execute() to wake up
    old_idx = None
    for i, step in enumerate(steps):
        if step.id == current_sr.pipeline_step_id:
            old_idx = i
            break

    if old_idx is not None:
        _completion.set_step_completed(run_id, old_idx)

    return {"success": True, "rejection_count": run.rejection_count, "max_reached": max_reached}
