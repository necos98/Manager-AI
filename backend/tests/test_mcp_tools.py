import uuid

import pytest
import pytest_asyncio

from app.models.task import TaskStatus
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="MCP Test", path="/tmp/mcp", description="MCP test project")


@pytest.fixture
def task_service(db_session):
    return TaskService(db_session)


@pytest.fixture
def project_service(db_session):
    return ProjectService(db_session)


@pytest.mark.asyncio
async def test_mcp_get_next_task_flow(task_service, project):
    """Simulates the full MCP flow: get_next_task → set_name → save_plan"""
    await task_service.create(project_id=project.id, description="Low priority task", priority=3)
    await task_service.create(project_id=project.id, description="High priority task", priority=1)

    task = await task_service.get_next_task(project.id)
    assert task.description == "High priority task"

    await task_service.set_name(task.id, project.id, "Important Feature")
    assert task.name == "Important Feature"

    await task_service.save_plan(task.id, project.id, "# Plan\n\nStep 1: Do it")
    assert task.status == TaskStatus.PLANNED
    assert task.plan == "# Plan\n\nStep 1: Do it"


@pytest.mark.asyncio
async def test_mcp_decline_and_replan_flow(task_service, project):
    """Simulates: plan → decline with feedback → get_next_task returns declined → replan"""
    task = await task_service.create(project_id=project.id, description="Feature X", priority=1)

    await task_service.save_plan(task.id, project.id, "# Plan v1")
    assert task.status == TaskStatus.PLANNED

    await task_service.update_status(task.id, project.id, TaskStatus.DECLINED, decline_feedback="Need more detail")
    assert task.status == TaskStatus.DECLINED
    assert task.decline_feedback == "Need more detail"

    next_task = await task_service.get_next_task(project.id)
    assert next_task.id == task.id
    assert next_task.decline_feedback == "Need more detail"

    await task_service.save_plan(task.id, project.id, "# Plan v2\n\nMore detailed plan")
    assert task.status == TaskStatus.PLANNED


@pytest.mark.asyncio
async def test_mcp_complete_flow(task_service, project):
    """Simulates: plan → accept → complete with recap"""
    task = await task_service.create(project_id=project.id, description="Feature Y", priority=1)
    await task_service.save_plan(task.id, project.id, "# Plan")
    await task_service.update_status(task.id, project.id, TaskStatus.ACCEPTED)
    assert task.status == TaskStatus.ACCEPTED

    result = await task_service.complete_task(task.id, project.id, "Implemented feature Y successfully")
    assert result.status == TaskStatus.FINISHED
    assert result.recap == "Implemented feature Y successfully"


@pytest.mark.asyncio
async def test_mcp_project_context(project_service, project):
    """get_project_context returns project info"""
    fetched = await project_service.get_by_id(project.id)
    assert fetched.name == "MCP Test"
    assert fetched.path == "/tmp/mcp"
    assert fetched.description == "MCP test project"


@pytest.mark.asyncio
async def test_mcp_task_project_validation(task_service, project):
    """All MCP tools must validate project_id ownership"""
    task = await task_service.create(project_id=project.id, description="Test", priority=1)
    fake_project_id = uuid.uuid4()

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.set_name(task.id, fake_project_id, "Name")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.save_plan(task.id, fake_project_id, "Plan")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.complete_task(task.id, fake_project_id, "Recap")
