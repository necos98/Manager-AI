"""Test hook registry error handling and observability."""
from unittest.mock import AsyncMock, patch

from app.hooks.registry import BaseHook, HookContext, HookEvent, HookRegistry, HookResult


class FailingHook(BaseHook):
    name = "failing_hook"
    description = "A hook that always fails"

    async def execute(self, context: HookContext) -> HookResult:
        raise RuntimeError("Something broke")


class ErrorResultHook(BaseHook):
    name = "error_result_hook"
    description = "A hook that returns error result"

    async def execute(self, context: HookContext) -> HookResult:
        return HookResult(success=False, error="CLI not found")


@patch("app.hooks.registry.event_service")
async def test_hook_exception_emits_hook_failed_event(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, FailingHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)
    await registry._run_hook(FailingHook, ctx)
    # Should have emitted hook_started and hook_failed
    assert mock_event_service.emit.call_count == 2
    failed_call = mock_event_service.emit.call_args_list[1][0][0]
    assert failed_call["type"] == "hook_failed"
    assert "Something broke" in failed_call["error"]


@patch("app.hooks.registry.event_service")
async def test_hook_error_result_emits_hook_failed_event(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, ErrorResultHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)
    await registry._run_hook(ErrorResultHook, ctx)
    assert mock_event_service.emit.call_count == 2
    failed_call = mock_event_service.emit.call_args_list[1][0][0]
    assert failed_call["type"] == "hook_failed"
    assert "CLI not found" in failed_call["error"]
