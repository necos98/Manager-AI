from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio

from app.hooks.registry import HookContext, HookEvent
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(
        name="Proj", path="/tmp/p", description="Desc", tech_stack="Python"
    )


@patch("app.hooks.handlers.auto_start_workflow.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_workflow.ProjectSettingService")
async def test_auto_start_runs_claude_when_enabled(MockSettingService, MockExecutor, db_session, project):
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(side_effect=lambda pid, key, default="": {
        "auto_workflow_enabled": "true",
        "auto_workflow_prompt": "",
        "auto_workflow_timeout": "600",
    }.get(key, default))
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    mock_exec.run = AsyncMock(return_value=MagicMock(success=True, output="done", error=None))
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_workflow import AutoStartWorkflow
    handler = AutoStartWorkflow()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_CREATED,
        metadata={
            "issue_description": "Build a login page",
            "project_name": project.name,
            "project_path": project.path,
            "project_description": project.description,
            "tech_stack": project.tech_stack,
        },
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_called_once()
    call_kwargs = mock_exec.run.call_args
    prompt_used = call_kwargs.kwargs.get("prompt") or call_kwargs.args[0]
    assert "Build a login page" in prompt_used


@patch("app.hooks.handlers.auto_start_workflow.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_workflow.ProjectSettingService")
async def test_auto_start_skips_when_disabled(MockSettingService, MockExecutor, db_session, project):
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="false")
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_workflow import AutoStartWorkflow
    handler = AutoStartWorkflow()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_CREATED,
        metadata={"issue_description": "Test", "project_path": project.path},
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_not_called()


@patch("app.hooks.handlers.auto_start_workflow.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_workflow.ProjectSettingService")
async def test_auto_start_uses_custom_prompt(MockSettingService, MockExecutor, db_session, project):
    custom = "Custom: {{issue_description}} per {{project_name}}"
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(side_effect=lambda pid, key, default="": {
        "auto_workflow_enabled": "true",
        "auto_workflow_prompt": custom,
        "auto_workflow_timeout": "300",
    }.get(key, default))
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    mock_exec.run = AsyncMock(return_value=MagicMock(success=True, output="ok", error=None))
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_workflow import AutoStartWorkflow
    handler = AutoStartWorkflow()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_CREATED,
        metadata={
            "issue_description": "Fix the bug",
            "project_name": "MyApp",
            "project_path": project.path,
            "project_description": "",
            "tech_stack": "",
        },
    )
    result = await handler.execute(ctx)
    prompt_used = mock_exec.run.call_args.kwargs.get("prompt") or mock_exec.run.call_args.args[0]
    assert "Fix the bug" in prompt_used
    assert "MyApp" in prompt_used
    assert "Custom:" in prompt_used
