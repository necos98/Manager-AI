"""Hook registry: defines events, hook base class, and the registry that fires hooks."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from app.services.event_service import event_service


class HookEvent(Enum):
    ISSUE_COMPLETED = "issue_completed"
    ISSUE_ACCEPTED = "issue_accepted"
    ISSUE_CANCELLED = "issue_cancelled"
    ISSUE_DECLINED = "issue_declined"


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
                "timestamp": now,
            }
        )

        try:
            result = await hook.execute(context)
        except Exception as exc:  # noqa: BLE001
            await event_service.emit(
                {
                    "type": "hook_failed",
                    "hook_name": hook.name,
                    "issue_id": context.issue_id,
                    "project_id": context.project_id,
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return

        if result.success:
            await event_service.emit(
                {
                    "type": "hook_completed",
                    "hook_name": hook.name,
                    "issue_id": context.issue_id,
                    "project_id": context.project_id,
                    "output": result.output,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        else:
            await event_service.emit(
                {
                    "type": "hook_failed",
                    "hook_name": hook.name,
                    "issue_id": context.issue_id,
                    "project_id": context.project_id,
                    "error": result.error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )


# Global singleton
hook_registry = HookRegistry()


def hook(event: HookEvent) -> Callable[[type[BaseHook]], type[BaseHook]]:
    """Class decorator that registers a BaseHook subclass with the global registry."""

    def decorator(cls: type[BaseHook]) -> type[BaseHook]:
        hook_registry.register(event, cls)
        return cls

    return decorator
