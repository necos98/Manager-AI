"""Event engine for pipeline event rules.

Decoupled event dispatch system:
- PipelineStepRunStatus event types are enumerated in PipelineEventType
- Actions are registered in ACTION_REGISTRY by name
- fire_event() queries matching rules and executes their actions
- Add new actions by registering a handler function, no model changes needed
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import Issue
from app.models.pipeline_event_rule import PipelineEventRule
from app.services.event_service import event_service

logger = logging.getLogger(__name__)


# ── Event Types ──────────────────────────────────────────────────────────────


class PipelineEventType(str, enum.Enum):
    """Canonical pipeline event types. Add new types here as needed."""

    STEP_COMPLETED = "step_completed"
    STEP_REJECTED = "step_rejected"
    STEP_FAILED = "step_failed"
    PIPELINE_COMPLETED = "pipeline_completed"


# ── Event Context ────────────────────────────────────────────────────────────


@dataclass
class PipelineEventContext:
    """Context payload passed to every action handler."""

    run_id: str
    issue_id: str
    project_id: str
    agent_name: str | None = None
    step_run_id: str | None = None
    step_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Action Registry ──────────────────────────────────────────────────────────

ActionHandler = Callable[
    [PipelineEventContext, dict[str, Any] | None, AsyncSession],
    Coroutine[Any, Any, None],
]

ACTION_REGISTRY: dict[str, ActionHandler] = {}


def register_action(name: str) -> Callable[[ActionHandler], ActionHandler]:
    """Decorator to register an action handler."""

    def decorator(fn: ActionHandler) -> ActionHandler:
        ACTION_REGISTRY[name] = fn
        return fn

    return decorator


# ── Action Handlers ──────────────────────────────────────────────────────────


@register_action("set_issue_status")
async def _action_set_issue_status(
    context: PipelineEventContext,
    params: dict[str, Any] | None,
    session: AsyncSession,
) -> None:
    """Set the issue status when a pipeline event fires.

    action_params (required):
        status (str): target issue status (e.g. "PLANNED", "FINISHED").
            Must be a valid IssueStatus value.
        recap_from (str, optional): if "summary", copies metadata.summary
            as issue recap. Used when setting FINISHED status.
    """
    if not params or "status" not in params:
        logger.warning("set_issue_status action missing 'status' param — skipping")
        return

    target_status = params["status"]

    # Validate status — case-insensitive match
    from app.models.issue import IssueStatus as IssueStatusEnum

    status_map = {s.value.lower(): s for s in IssueStatusEnum}
    target_enum = status_map.get(target_status.lower())
    if target_enum is None:
        logger.warning(
            "Invalid issue status %r for set_issue_status — skipping",
            target_status,
        )
        return

    issue = await session.get(Issue, context.issue_id)
    if issue is None:
        logger.warning("Issue %s not found (DB) — skipping set_issue_status", context.issue_id)
        return

    issue.status = target_enum
    if target_enum == IssueStatusEnum.FINISHED:
        from app.utils.datetime import now as _dt_now
        issue.finished_at = _dt_now()
        if params.get("recap_from") == "summary":
            issue.recap = context.metadata.get("summary", "")

    session.add(issue)
    await session.flush()
    logger.info(
        "Set issue %s status to %s (from event %s)",
        context.issue_id, target_status, context.metadata.get("event_type", "?"),
    )


@register_action("emit_event")
async def _action_emit_event(
    context: PipelineEventContext,
    params: dict[str, Any] | None,
    session: AsyncSession,
) -> None:
    """Emit a custom WebSocket event.

    action_params:
        event_type (str, required): the WebSocket event type string.
        Any other keys are forwarded as payload.
    """
    if not params or "event_type" not in params:
        logger.warning("emit_event action missing 'event_type' param — skipping")
        return

    payload = dict(params)
    payload["project_id"] = context.project_id
    payload["issue_id"] = context.issue_id
    payload["run_id"] = context.run_id
    if context.agent_name:
        payload["agent_name"] = context.agent_name
    from app.utils.datetime import now as _dt_now
    payload["timestamp"] = _dt_now().isoformat()

    await event_service.emit(payload)
    logger.debug("Emitted custom event %s for issue %s", params["event_type"], context.issue_id)


# ── Event Engine ─────────────────────────────────────────────────────────────


async def fire_event(
    pipeline_id: str,
    event_type: str,
    source_step_id: str | None,
    context: PipelineEventContext,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Query matching event rules and execute their actions.

    Returns a list of result dicts, one per executed action.
    """
    results: list[dict[str, Any]] = []

    query = select(PipelineEventRule).where(
        PipelineEventRule.pipeline_id == pipeline_id,
        PipelineEventRule.event_type == event_type,
        PipelineEventRule.enabled.is_(True),
    )

    # If source_step_id is provided, match it exactly.
    # For pipeline-level events (PIPELINE_COMPLETED), pass source_step_id=None
    # and we match all rules for that event_type regardless of source_step_id.
    if source_step_id is not None:
        query = query.where(PipelineEventRule.source_step_id == source_step_id)

    rows = (await session.execute(query)).scalars().all()

    for rule in rows:
        handler = ACTION_REGISTRY.get(rule.action_type)
        if handler is None:
            logger.warning(
                "Unknown action_type %r for rule %s — skipping",
                rule.action_type, rule.id,
            )
            results.append({"rule_id": rule.id, "action_type": rule.action_type, "status": "skipped"})
            continue

        try:
            await handler(context, rule.action_params, session)
            results.append({"rule_id": rule.id, "action_type": rule.action_type, "status": "executed"})
            logger.info(
                "Executed action %r (rule %s) for event %s on pipeline %s",
                rule.action_type, rule.id, event_type, pipeline_id,
            )
        except Exception:
            logger.exception(
                "Action %r (rule %s) failed for event %s on pipeline %s",
                rule.action_type, rule.id, event_type, pipeline_id,
            )
            results.append({"rule_id": rule.id, "action_type": rule.action_type, "status": "error"})

    return results
