"""Test hook registry error handling and observability."""
import asyncio
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


class SuccessHook(BaseHook):
    name = "success_hook"
    description = "A hook that succeeds"

    async def execute(self, context: HookContext) -> HookResult:
        return HookResult(success=True, output="done")


@patch("app.hooks.registry.event_service")
async def test_hook_events_include_issue_and_project_name(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    ctx = HookContext(
        project_id="p1",
        issue_id="i1",
        event=HookEvent.ISSUE_COMPLETED,
        metadata={"issue_name": "Fix login bug", "project_name": "My Project"},
    )
    await registry._run_hook(SuccessHook, ctx)
    # hook_started event
    started = mock_event_service.emit.call_args_list[0][0][0]
    assert started["issue_name"] == "Fix login bug"
    assert started["project_name"] == "My Project"
    # hook_completed event
    completed = mock_event_service.emit.call_args_list[1][0][0]
    assert completed["issue_name"] == "Fix login bug"
    assert completed["project_name"] == "My Project"


@patch("app.hooks.registry.event_service")
async def test_hook_failed_event_includes_names(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    ctx = HookContext(
        project_id="p1",
        issue_id="i1",
        event=HookEvent.ISSUE_COMPLETED,
        metadata={"issue_name": "Fix login bug", "project_name": "My Project"},
    )
    await registry._run_hook(FailingHook, ctx)
    failed = mock_event_service.emit.call_args_list[1][0][0]
    assert failed["issue_name"] == "Fix login bug"
    assert failed["project_name"] == "My Project"


class SlowHook(BaseHook):
    name = "slow_hook"
    description = "A hook that never completes"

    async def execute(self, context: HookContext) -> HookResult:
        await asyncio.sleep(999)
        return HookResult(success=True)


@patch("app.hooks.registry.event_service")
@patch("app.hooks.registry.HOOK_TIMEOUT", 0.05)
async def test_hook_timeout_emits_hook_failed(mock_event_service):
    """Hook che supera il timeout emette hook_failed."""
    import asyncio
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)
    await registry._run_hook(SlowHook, ctx)

    emitted_types = [call[0][0]["type"] for call in mock_event_service.emit.call_args_list]
    assert "hook_failed" in emitted_types
    failed = next(c[0][0] for c in mock_event_service.emit.call_args_list if c[0][0]["type"] == "hook_failed")
    assert "timed out" in failed["error"].lower()


@patch("app.hooks.registry.event_service")
async def test_fire_stores_task_in_background_set(mock_event_service):
    """fire() salva la task in _background_tasks e la rimuove al completamento."""
    import asyncio
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, SuccessHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)

    await registry.fire(HookEvent.ISSUE_COMPLETED, ctx)
    assert len(registry._background_tasks) == 1

    # Aspetta completamento
    await asyncio.sleep(0.1)
    assert len(registry._background_tasks) == 0


@patch("app.hooks.registry.event_service")
async def test_fire_does_not_raise_when_hook_throws(mock_event_service):
    """fire() è fire-and-forget: eccezioni nell'hook non raggiungono il chiamante."""
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, FailingHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)

    # Questo non deve sollevare eccezioni
    await registry.fire(HookEvent.ISSUE_COMPLETED, ctx)

    # Aspetta che la background task completi
    await asyncio.sleep(0.15)

    # Verifica che hook_failed sia stato emesso (prova che l'eccezione è stata gestita)
    emitted_types = [call[0][0]["type"] for call in mock_event_service.emit.call_args_list]
    assert "hook_failed" in emitted_types


async def test_issue_created_hook_end_to_end(db_session):
    """ISSUE_CREATED viene fired attraverso il registry reale (non mockato interamente)."""
    from unittest.mock import patch, AsyncMock
    from app.services.issue_service import IssueService
    from app.services.project_service import ProjectService
    import app.services.issue_service as issue_svc_module
    from app.hooks.registry import HookEvent

    project_service = ProjectService(db_session)
    project = await project_service.create(
        name="Hook E2E", path="/tmp/e2e", description="Test project"
    )

    fired_events = []

    async def recording_fire(event, ctx):
        fired_events.append(event)
        # Non eseguiamo i veri hook (richiederebbero claude CLI)

    # patch.object agisce sull'istanza singleton reale, non sulla reference nel modulo
    with patch.object(issue_svc_module.hook_registry, "fire", side_effect=recording_fire):
        svc = IssueService(db_session)
        await svc.create(project_id=project.id, description="E2E trigger test", priority=1)

    assert HookEvent.ISSUE_CREATED in fired_events, (
        "hook_registry.fire deve essere chiamato con HookEvent.ISSUE_CREATED "
        "alla creazione dell'issue (wiring service → registry verificato)"
    )
