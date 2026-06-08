"""Pipeline-specific WebSocket event emissions + event engine integration."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_service import event_service

logger = logging.getLogger(__name__)


async def fire_pipeline_event(
    pipeline_id: str,
    event_type: str,
    source_step_id: str | None,
    *,
    run_id: str,
    issue_id: str,
    project_id: str,
    agent_name: str | None = None,
    step_run_id: str | None = None,
    step_index: int | None = None,
    metadata: dict | None = None,
    session: AsyncSession,
) -> list[dict]:
    """Fire a pipeline event through the event engine.

    This is the single entry point for triggering event rules from anywhere
    in the pipeline execution code. Import this function, not _events_engine
    directly.
    """
    from app.services.pipeline_run._events_engine import (
        PipelineEventContext,
        fire_event,
    )

    context = PipelineEventContext(
        run_id=run_id,
        issue_id=issue_id,
        project_id=project_id,
        agent_name=agent_name,
        step_run_id=step_run_id,
        step_index=step_index,
        metadata=metadata or {},
    )
    return await fire_event(pipeline_id, event_type, source_step_id, context, session)


async def emit_step_started(
    project_id: str,
    issue_id: str,
    agent_name: str,
    step_run_id: str,
    terminal_id: str,
) -> None:
    await event_service.emit({
        "type": "agent_step_started",
        "project_id": project_id,
        "issue_id": issue_id,
        "agent_name": agent_name,
        "step_run_id": step_run_id,
        "terminal_id": terminal_id,
    })


async def emit_terminal_created(
    terminal_id: str,
    issue_id: str,
    project_id: str,
) -> None:
    await event_service.emit({
        "type": "terminal_created",
        "terminal_id": terminal_id,
        "issue_id": issue_id,
        "project_id": project_id,
    })


async def emit_step_completed(
    project_id: str,
    issue_id: str,
    agent_name: str,
    step_run_id: str,
) -> None:
    await event_service.emit({
        "type": "agent_step_completed",
        "project_id": project_id,
        "issue_id": issue_id,
        "agent_name": agent_name,
        "step_run_id": step_run_id,
    })


async def emit_step_failed(
    project_id: str,
    issue_id: str,
    agent_name: str,
    step_run_id: str,
) -> None:
    await event_service.emit({
        "type": "agent_step_failed",
        "project_id": project_id,
        "issue_id": issue_id,
        "agent_name": agent_name,
        "step_run_id": step_run_id,
    })


async def emit_pipeline_completed(
    project_id: str,
    issue_id: str,
    run_id: str,
    status: str,
) -> None:
    await event_service.emit({
        "type": "pipeline_completed",
        "project_id": project_id,
        "issue_id": issue_id,
        "run_id": run_id,
        "status": status,
    })


async def emit_step_rejected(
    project_id: str,
    issue_id: str,
    run_id: str,
    step_run_id: str,
    agent_name: str,
    reason: str,
    target_step_index: int,
    rejection_count: int,
) -> None:
    await event_service.emit({
        "type": "pipeline_step_rejected",
        "project_id": project_id,
        "issue_id": issue_id,
        "run_id": run_id,
        "step_run_id": step_run_id,
        "agent_name": agent_name,
        "reason": reason,
        "target_step_index": target_step_index,
        "rejection_count": rejection_count,
    })


async def emit_step_advanced(
    run_id: str,
    issue_id: str,
    from_step: int,
    to_step: int,
) -> None:
    await event_service.emit({
        "type": "pipeline_step_advanced",
        "run_id": run_id,
        "issue_id": issue_id,
        "from_step": from_step,
        "to_step": to_step,
        "status": "WAITING_FOR_STEP",
    })


async def emit_pipeline_paused(
    run_id: str,
    issue_id: str,
) -> None:
    await event_service.emit({
        "type": "pipeline_paused",
        "run_id": run_id,
        "issue_id": issue_id,
    })


async def emit_pipeline_resumed(
    run_id: str,
    issue_id: str,
) -> None:
    await event_service.emit({
        "type": "pipeline_resumed",
        "run_id": run_id,
        "issue_id": issue_id,
    })
