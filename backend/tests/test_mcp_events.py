from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

import app.mcp.server as mcp_server
from app.services.project_service import ProjectService
from app.services.issue_service import IssueService


@pytest_asyncio.fixture
async def project(db_session):
    svc = ProjectService(db_session)
    return await svc.create(name="MCP Events", path="/tmp/mcp_events", description="")


@pytest_asyncio.fixture
async def issue(db_session, project):
    svc = IssueService(db_session)
    return await svc.create(project_id=project.id, description="Test issue", priority=1)


def make_session_patcher(db_session):
    @asynccontextmanager
    async def _fake():
        yield db_session
    return _fake


@pytest.mark.asyncio
async def test_create_issue_spec_emits_event(db_session, project, issue):
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.create_issue_spec(
            project_id=project.id, issue_id=issue.id, spec="# Spec"
        )
    assert result["status"] == "Reasoning"
    emit_mock.assert_called_once()
    event = emit_mock.call_args[0][0]
    assert event["type"] == "issue_status_changed"
    assert event["project_id"] == project.id
    assert event["issue_id"] == issue.id


@pytest.mark.asyncio
async def test_create_issue_plan_emits_event(db_session, project, issue):
    svc = IssueService(db_session)
    await svc.create_spec(issue.id, project.id, "# Spec")
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.create_issue_plan(
            project_id=project.id, issue_id=issue.id, plan="# Plan"
        )
    assert result["status"] == "Planned"
    emit_mock.assert_called_once()
    event = emit_mock.call_args[0][0]
    assert event["type"] == "issue_status_changed"


@pytest.mark.asyncio
async def test_set_issue_name_emits_event(db_session, project, issue):
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.set_issue_name(
            project_id=project.id, issue_id=issue.id, name="My Issue Name"
        )
    assert result["name"] == "My Issue Name"
    emit_mock.assert_called_once()
    event = emit_mock.call_args[0][0]
    assert event["type"] == "issue_content_updated"
    assert event["content_type"] == "name"


@pytest_asyncio.fixture
async def planned_issue(db_session, project):
    """Issue with tasks, in Planned status"""
    svc = IssueService(db_session)
    issue = await svc.create(project_id=project.id, description="Task test issue", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    await svc.create_plan(issue.id, project.id, "# Plan")
    return issue


@pytest.mark.asyncio
async def test_create_plan_tasks_emits_event(db_session, project, planned_issue):
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.create_plan_tasks(
            issue_id=planned_issue.id,
            tasks=[{"name": "Task A"}, {"name": "Task B"}]
        )
    assert len(result["tasks"]) == 2
    emit_mock.assert_called_once()
    event = emit_mock.call_args[0][0]
    assert event["type"] == "task_updated"
    assert event["project_id"] == project.id
    assert event["issue_id"] == planned_issue.id


@pytest.mark.asyncio
async def test_update_task_status_emits_event(db_session, project, planned_issue):
    from app.services.task_service import TaskService
    task_svc = TaskService(db_session)
    tasks = await task_svc.create_bulk(planned_issue.id, [{"name": "Task X"}])
    task = tasks[0]

    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.update_task_status(task_id=task.id, status="In Progress")
    assert result["status"] == "In Progress"
    emit_mock.assert_called_once()
    event = emit_mock.call_args[0][0]
    assert event["type"] == "task_updated"
    assert event["project_id"] == project.id
    assert event["issue_id"] == planned_issue.id
