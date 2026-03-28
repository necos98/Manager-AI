import pytest_asyncio
from app.models.task import TaskStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(name="Test", path="/tmp/t", description="")


async def test_all_completed_true_when_all_done(db_session, project):
    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)
    issue = await issue_svc.create(project_id=project.id, description="Test")
    await task_svc.create_bulk(issue.id, [{"name": "Task A"}, {"name": "Task B"}])
    await db_session.commit()
    tasks = await task_svc.list_by_issue(issue.id)
    for t in tasks:
        await task_svc.update(t.id, status=TaskStatus.IN_PROGRESS)
        await task_svc.update(t.id, status=TaskStatus.COMPLETED)
    result = await task_svc.all_completed(issue.id)
    assert result is True


async def test_all_completed_false_when_some_pending(db_session, project):
    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)
    issue = await issue_svc.create(project_id=project.id, description="Test")
    await task_svc.create_bulk(issue.id, [{"name": "Task A"}, {"name": "Task B"}])
    await db_session.commit()
    tasks = await task_svc.list_by_issue(issue.id)
    await task_svc.update(tasks[0].id, status=TaskStatus.IN_PROGRESS)
    await task_svc.update(tasks[0].id, status=TaskStatus.COMPLETED)
    # tasks[1] remains PENDING
    result = await task_svc.all_completed(issue.id)
    assert result is False


async def test_all_completed_false_when_no_tasks(db_session, project):
    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)
    issue = await issue_svc.create(project_id=project.id, description="Test")
    await db_session.commit()
    result = await task_svc.all_completed(issue.id)
    assert result is False


from unittest.mock import AsyncMock, MagicMock, patch


@patch("app.hooks.handlers.auto_completion.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_completion.ProjectSettingService")
async def test_auto_completion_notifies_when_mode_notify(MockSettingService, MockExecutor, db_session):
    from app.hooks.handlers.auto_completion import AutoCompletion
    from app.hooks.registry import HookContext, HookEvent

    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="notify")
    MockSettingService.return_value = mock_svc

    with patch("app.hooks.handlers.auto_completion.event_service") as mock_events:
        mock_events.emit = AsyncMock()
        handler = AutoCompletion()
        ctx = HookContext(
            project_id="proj-1",
            issue_id="issue-1",
            event=HookEvent.ALL_TASKS_COMPLETED,
            metadata={"issue_name": "Fix login", "project_path": "/tmp"},
        )
        result = await handler.execute(ctx)
    assert result.success is True
    mock_events.emit.assert_called_once()
    emitted = mock_events.emit.call_args[0][0]
    assert emitted["type"] == "notification"
    assert "Fix login" in emitted.get("message", "")


@patch("app.hooks.handlers.auto_completion.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_completion.ProjectSettingService")
async def test_auto_completion_skips_when_off(MockSettingService, MockExecutor, db_session):
    from app.hooks.handlers.auto_completion import AutoCompletion
    from app.hooks.registry import HookContext, HookEvent

    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="off")
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    MockExecutor.return_value = mock_exec

    handler = AutoCompletion()
    ctx = HookContext(
        project_id="proj-1",
        issue_id="issue-1",
        event=HookEvent.ALL_TASKS_COMPLETED,
        metadata={"issue_name": "Test", "project_path": "/tmp"},
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_not_called()


@patch("app.hooks.handlers.auto_completion.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_completion.ProjectSettingService")
async def test_auto_completion_auto_mode_runs_claude(MockSettingService, MockExecutor, db_session):
    from app.hooks.handlers.auto_completion import AutoCompletion
    from app.hooks.registry import HookContext, HookEvent

    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="auto")
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    mock_exec.run = AsyncMock(return_value=MagicMock(success=True, output="done", error=None))
    MockExecutor.return_value = mock_exec

    handler = AutoCompletion()
    ctx = HookContext(
        project_id="proj-1",
        issue_id="issue-1",
        event=HookEvent.ALL_TASKS_COMPLETED,
        metadata={"issue_name": "Build API", "project_path": "/tmp/project"},
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_called_once()
    prompt_used = mock_exec.run.call_args.kwargs.get("prompt") or mock_exec.run.call_args.args[0]
    assert "Build API" in prompt_used
