"""Hooks package: event-driven hook system for Manager AI issue lifecycle events."""

from app.hooks.executor import ClaudeCodeExecutor, ExecutorResult
from app.hooks.registry import (
    BaseHook,
    HookContext,
    HookEvent,
    HookResult,
    hook,
    hook_registry,
)

__all__ = [
    "hook_registry",
    "HookEvent",
    "HookContext",
    "HookResult",
    "BaseHook",
    "hook",
    "ClaudeCodeExecutor",
    "ExecutorResult",
]
