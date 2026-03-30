import pytest
import pytest_asyncio

from app.services.project_service import ProjectService
from app.services.issue_service import IssueService
from app.services.activity_service import ActivityService


@pytest_asyncio.fixture
async def project(db_session):
    svc = ProjectService(db_session)
    return await svc.create(name="Activity Test", path="/tmp/activity", description="")


@pytest_asyncio.fixture
async def issue(db_session, project):
    svc = IssueService(db_session)
    return await svc.create(project_id=project.id, description="Test issue", priority=1)


@pytest.mark.asyncio
async def test_log_creates_entry(db_session, project, issue):
    svc = ActivityService(db_session)
    log = await svc.log(
        project_id=project.id,
        issue_id=issue.id,
        event_type="status_changed",
        details={"new_status": "Reasoning"},
    )
    assert log.id is not None
    assert log.project_id == project.id
    assert log.issue_id == issue.id
    assert log.event_type == "status_changed"
    assert log.get_details() == {"new_status": "Reasoning"}


@pytest.mark.asyncio
async def test_log_without_issue(db_session, project):
    svc = ActivityService(db_session)
    log = await svc.log(project_id=project.id, issue_id=None, event_type="project_updated")
    assert log.issue_id is None


@pytest.mark.asyncio
async def test_list_for_project_returns_logs(db_session, project, issue):
    svc = ActivityService(db_session)
    await svc.log(project_id=project.id, issue_id=issue.id, event_type="status_changed")
    await svc.log(project_id=project.id, issue_id=issue.id, event_type="spec_created")
    logs = await svc.list_for_project(project.id)
    assert len(logs) == 2


@pytest.mark.asyncio
async def test_list_for_project_filters_by_issue(db_session, project, issue):
    svc_issue = IssueService(db_session)
    other_issue = await svc_issue.create(project_id=project.id, description="Other", priority=2)
    svc = ActivityService(db_session)
    await svc.log(project_id=project.id, issue_id=issue.id, event_type="status_changed")
    await svc.log(project_id=project.id, issue_id=other_issue.id, event_type="status_changed")
    logs = await svc.list_for_project(project.id, issue_id=issue.id)
    assert len(logs) == 1
    assert logs[0].issue_id == issue.id


@pytest.mark.asyncio
async def test_list_for_project_ordered_newest_first(db_session, project):
    svc = ActivityService(db_session)
    await svc.log(project_id=project.id, issue_id=None, event_type="first")
    await svc.log(project_id=project.id, issue_id=None, event_type="second")
    logs = await svc.list_for_project(project.id)
    assert logs[0].event_type == "second"
