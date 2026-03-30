import pytest
import pytest_asyncio

from app.exceptions import InvalidTransitionError, NotFoundError
from app.models.task import TaskStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test", path="/tmp/test")


@pytest_asyncio.fixture
async def issue(db_session, project):
    service = IssueService(db_session)
    return await service.create(project_id=project.id, description="Test issue")


async def test_create_bulk(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Task 1"}, {"name": "Task 2"}])
    assert len(tasks) == 2
    assert tasks[0].name == "Task 1"
    assert tasks[0].order == 0
    assert tasks[1].order == 1
    assert tasks[0].status == TaskStatus.PENDING


async def test_list_by_issue_ordered(db_session, issue):
    service = TaskService(db_session)
    await service.create_bulk(issue.id, [{"name": "B"}, {"name": "A"}])
    tasks = await service.list_by_issue(issue.id)
    assert tasks[0].name == "B"
    assert tasks[1].name == "A"


async def test_replace_all(db_session, issue):
    service = TaskService(db_session)
    await service.create_bulk(issue.id, [{"name": "Old"}])
    tasks = await service.replace_all(issue.id, [{"name": "New 1"}, {"name": "New 2"}])
    assert len(tasks) == 2
    all_tasks = await service.list_by_issue(issue.id)
    assert len(all_tasks) == 2
    assert all_tasks[0].name == "New 1"


async def test_update_status_valid(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Do it"}])
    updated = await service.update(tasks[0].id, status=TaskStatus.IN_PROGRESS)
    assert updated.status == TaskStatus.IN_PROGRESS


async def test_update_status_invalid(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Do it"}])
    with pytest.raises(InvalidTransitionError, match="Invalid task transition"):
        await service.update(tasks[0].id, status=TaskStatus.COMPLETED)


async def test_update_name(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Old name"}])
    updated = await service.update(tasks[0].id, name="New name")
    assert updated.name == "New name"


async def test_delete_task(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Delete me"}])
    await service.delete(tasks[0].id)
    remaining = await service.list_by_issue(issue.id)
    assert len(remaining) == 0


async def test_delete_nonexistent(db_session):
    service = TaskService(db_session)
    with pytest.raises(NotFoundError, match="Task not found"):
        await service.delete("nonexistent-id")
