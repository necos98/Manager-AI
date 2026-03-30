import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.services.activity_service import ActivityService
from app.services.project_service import ProjectService
from app.services.issue_service import IssueService


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def project(db_session):
    svc = ProjectService(db_session)
    return await svc.create(name="Activity Router Test", path="/tmp/ar", description="")


@pytest_asyncio.fixture
async def issue(db_session, project):
    svc = IssueService(db_session)
    return await svc.create(project_id=project.id, description="Test issue", priority=1)


@pytest.mark.asyncio
async def test_list_activity_empty(client, project):
    resp = await client.get(f"/api/projects/{project.id}/activity")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_activity_returns_logs(client, db_session, project):
    pid = project.id
    svc = ActivityService(db_session)
    await svc.log(project_id=pid, issue_id=None, event_type="test_event", details={"key": "value"})
    await db_session.flush()
    resp = await client.get(f"/api/projects/{pid}/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_type"] == "test_event"
    assert data[0]["details"] == {"key": "value"}


@pytest.mark.asyncio
async def test_list_activity_filter_by_issue(client, db_session, project, issue):
    pid = project.id
    svc = ActivityService(db_session)
    await svc.log(project_id=pid, issue_id=issue.id, event_type="issue_event")
    await svc.log(project_id=pid, issue_id=None, event_type="project_event")
    await db_session.flush()
    resp = await client.get(f"/api/projects/{pid}/activity?issue_id={issue.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_type"] == "issue_event"


@pytest.mark.asyncio
async def test_list_activity_project_not_found(client):
    resp = await client.get("/api/projects/nonexistent-id/activity")
    assert resp.status_code == 404
