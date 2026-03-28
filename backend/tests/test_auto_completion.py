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
