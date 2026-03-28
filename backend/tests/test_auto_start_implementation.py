from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio

from app.hooks.registry import HookContext, HookEvent
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(
        name="Test", path="/tmp/p", description="Desc", tech_stack="Python"
    )


@patch("app.hooks.handlers.auto_start_implementation.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_implementation.ProjectSettingService")
@patch("app.hooks.handlers.auto_start_implementation.SettingsService")
async def test_auto_implementation_runs_when_enabled(MockGlobalSettings, MockSettingService, MockExecutor, db_session, project):
    mock_global_svc = AsyncMock()
    mock_global_svc.get = AsyncMock(return_value="false")
    MockGlobalSettings.return_value = mock_global_svc
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(side_effect=lambda pid, key, default="": {
        "auto_implementation_enabled": "true",
        "auto_implementation_timeout": "900",
    }.get(key, default))
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    mock_exec.run = AsyncMock(return_value=MagicMock(success=True, output="done", error=None))
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_implementation import AutoStartImplementation
    handler = AutoStartImplementation()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_ACCEPTED,
        metadata={
            "issue_name": "Build login",
            "project_name": project.name,
            "project_path": project.path,
            "project_description": project.description,
            "tech_stack": project.tech_stack,
            "specification": "# Spec content",
            "plan": "# Plan content",
        },
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_called_once()
    prompt_used = mock_exec.run.call_args.kwargs.get("prompt") or mock_exec.run.call_args.args[0]
    assert "# Plan content" in prompt_used


@patch("app.hooks.handlers.auto_start_implementation.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_implementation.ProjectSettingService")
async def test_auto_implementation_skips_when_disabled(MockSettingService, MockExecutor, db_session, project):
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="false")
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_implementation import AutoStartImplementation
    handler = AutoStartImplementation()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_ACCEPTED,
        metadata={"project_path": project.path},
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_not_called()
