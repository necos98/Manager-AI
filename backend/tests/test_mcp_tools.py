import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio

from app.models.task import TaskStatus
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
import app.mcp.server as mcp_server
from unittest.mock import patch


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="MCP Test", path="/tmp/mcp", description="MCP test project", tech_stack="Python, FastAPI")


@pytest.fixture
def task_service(db_session):
    return TaskService(db_session)


@pytest.fixture
def project_service(db_session):
    return ProjectService(db_session)


@pytest.mark.asyncio
async def test_mcp_autonomous_workflow(task_service, project):
    """Simulates full autonomous flow: create_spec → create_plan → accept → complete"""
    task = await task_service.create(project_id=project.id, description="Feature Z", priority=1)

    # Claude writes spec
    await task_service.create_spec(task.id, project.id, "# Spec\n\nBuild feature Z.")
    assert task.status == TaskStatus.REASONING
    assert task.specification == "# Spec\n\nBuild feature Z."

    # Claude refines spec after user feedback
    await task_service.edit_spec(task.id, project.id, "# Spec v2\n\nBuild feature Z with extra.")
    assert task.specification == "# Spec v2\n\nBuild feature Z with extra."
    assert task.status == TaskStatus.REASONING

    # Claude writes plan
    await task_service.create_plan(task.id, project.id, "# Plan\n\nStep 1: Do it.")
    assert task.status == TaskStatus.PLANNED

    # User approves in conversation, Claude accepts
    await task_service.accept_task(task.id, project.id)
    assert task.status == TaskStatus.ACCEPTED

    # Claude completes
    result = await task_service.complete_task(task.id, project.id, "Done.")
    assert result.status == TaskStatus.FINISHED


@pytest.mark.asyncio
async def test_mcp_complete_flow(task_service, project):
    """Simulates: spec → plan → accept → complete with recap"""
    task = await task_service.create(project_id=project.id, description="Feature Y", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec")
    await task_service.create_plan(task.id, project.id, "# Plan")
    await task_service.accept_task(task.id, project.id)
    assert task.status == TaskStatus.ACCEPTED

    result = await task_service.complete_task(task.id, project.id, "Implemented feature Y successfully")
    assert result.status == TaskStatus.FINISHED
    assert result.recap == "Implemented feature Y successfully"


@pytest.mark.asyncio
async def test_mcp_cancel_flow(task_service, project):
    """Claude can cancel from any status"""
    task = await task_service.create(project_id=project.id, description="Cancel me", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec")
    result = await task_service.cancel_task(task.id, project.id)
    assert result.status == TaskStatus.CANCELED


@pytest.mark.asyncio
async def test_mcp_project_context(project_service, project):
    """get_project_context returns project info"""
    fetched = await project_service.get_by_id(project.id)
    assert fetched.name == "MCP Test"
    assert fetched.path == "/tmp/mcp"
    assert fetched.description == "MCP test project"
    assert fetched.tech_stack == "Python, FastAPI"


@pytest.mark.asyncio
async def test_mcp_get_project_context_includes_tech_stack(db_session, project):
    """get_project_context tool returns tech_stack in its dict"""

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_project_context(str(project.id))

    assert result["tech_stack"] == "Python, FastAPI"
    assert result["name"] == "MCP Test"


@pytest.mark.asyncio
async def test_mcp_get_task_details_includes_specification(db_session, project):
    """get_task_details returns specification field"""
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="Spec task", priority=1)
    await task_service.create_spec(task.id, project.id, "# My Spec")
    await db_session.refresh(task)  # populate server_default fields (created_at, updated_at)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_task_details(str(project.id), str(task.id))

    assert result["specification"] == "# My Spec"
    assert result["status"] == "Reasoning"


@pytest.mark.asyncio
async def test_mcp_task_project_validation(task_service, project):
    """All MCP tools must validate project_id ownership"""
    task = await task_service.create(project_id=project.id, description="Test", priority=1)
    fake_project_id = uuid.uuid4()

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.set_name(task.id, fake_project_id, "Name")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.create_spec(task.id, fake_project_id, "Spec")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.complete_task(task.id, fake_project_id, "Recap")
