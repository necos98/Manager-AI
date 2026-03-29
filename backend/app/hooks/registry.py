"""Hook registry: defines events, hook base class, and the registry that fires hooks."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from app.services.event_service import event_service

logger = logging.getLogger(__name__)


class HookEvent(str, Enum):
    ISSUE_COMPLETED = "issue_completed"
    ISSUE_ACCEPTED = "issue_accepted"
    ISSUE_CANCELLED = "issue_cancelled"
    ISSUE_CREATED = "issue_created"
    ALL_TASKS_COMPLETED = "all_tasks_completed"


@dataclass
class HookContext:
    project_id: str
    issue_id: str
    event: HookEvent
    metadata: dict = field(default_factory=dict)


@dataclass
class HookResult:
    success: bool
    output: str | None = None
    error: str | None = None


class BaseHook(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, context: HookContext) -> HookResult:
        """Execute the hook logic and return a result."""


class HookRegistry:
    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[type[BaseHook]]] = {}

    def register(self, event: HookEvent, hook_class: type[BaseHook]) -> None:
        """Register a hook class to be fired when the given event occurs."""
        self._hooks.setdefault(event, []).append(hook_class)

    async def fire(self, event: HookEvent, context: HookContext) -> None:
        """
        Fire all hooks registered for the given event.

        Non-blocking: spawns an asyncio task per hook and returns immediately.
        Each task emits hook_started, then hook_completed or hook_failed events.
        """
        hook_classes = self._hooks.get(event, [])
        for hook_class in hook_classes:
            asyncio.create_task(self._run_hook(hook_class, context))

    async def _run_hook(
        self, hook_class: type[BaseHook], context: HookContext
    ) -> None:
        hook = hook_class()
        now = datetime.now(timezone.utc).isoformat()

        await event_service.emit(
            {
                "type": "hook_started",
                "hook_name": hook.name,
                "hook_description": hook.description,
                "issue_id": context.issue_id,
                "project_id": context.project_id,
                "issue_name": context.metadata.get("issue_name", ""),
                "project_name": context.metadata.get("project_name", ""),
                "timestamp": now,
            }
        )

        try:
            result = await hook.execute(context)
        except Exception as exc:  # noqa: BLE001
            logger.error("Hook %s failed with exception: %s", hook.name, exc)
            await event_service.emit(
                {
                    "type": "hook_failed",
                    "hook_name": hook.name,
                    "issue_id": context.issue_id,
                    "project_id": context.project_id,
                    "issue_name": context.metadata.get("issue_name", ""),
                    "project_name": context.metadata.get("project_name", ""),
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await self._log_activity(context.project_id, context.issue_id, "hook_failed", {
                "hook_name": hook.name, "error": str(exc)
            })
            return

        if result.success:
            await event_service.emit(
                {
                    "type": "hook_completed",
                    "hook_name": hook.name,
                    "issue_id": context.issue_id,
                    "project_id": context.project_id,
                    "issue_name": context.metadata.get("issue_name", ""),
                    "project_name": context.metadata.get("project_name", ""),
                    "output": result.output,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await self._log_activity(context.project_id, context.issue_id, "hook_completed", {
                "hook_name": hook.name
            })
        else:
            logger.warning("Hook %s returned error: %s", hook.name, result.error)
            await event_service.emit(
                {
                    "type": "hook_failed",
                    "hook_name": hook.name,
                    "issue_id": context.issue_id,
                    "project_id": context.project_id,
                    "issue_name": context.metadata.get("issue_name", ""),
                    "project_name": context.metadata.get("project_name", ""),
                    "error": result.error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await self._log_activity(context.project_id, context.issue_id, "hook_failed", {
                "hook_name": hook.name, "error": result.error
            })

    async def _log_activity(
        self, project_id: str, issue_id: str, event_type: str, details: dict
    ) -> None:
        try:
            from app.database import async_session
            from app.services.activity_service import ActivityService
            async with async_session() as session:
                svc = ActivityService(session)
                await svc.log(
                    project_id=project_id,
                    issue_id=issue_id,
                    event_type=event_type,
                    details=details,
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to log activity for hook event: %s", exc)


# Global singleton
hook_registry = HookRegistry()


def hook(event: HookEvent) -> Callable[[type[BaseHook]], type[BaseHook]]:
    """Class decorator that registers a BaseHook subclass with the global registry."""

    def decorator(cls: type[BaseHook]) -> type[BaseHook]:
        hook_registry.register(event, cls)
        return cls

    return decorator
