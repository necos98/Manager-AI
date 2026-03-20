import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


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
async def project(client):
    resp = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    return resp.json()


@pytest.mark.asyncio
async def test_create_issue(client, project):
    resp = await client.post(
        f"/api/projects/{project['id']}/issues",
        json={"description": "Do something", "priority": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Do something"
    assert data["status"] == "New"


@pytest.mark.asyncio
async def test_create_issue_invalid_priority(client, project):
    resp = await client.post(
        f"/api/projects/{project['id']}/issues",
        json={"description": "Bad priority", "priority": 0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_issues(client, project):
    await client.post(f"/api/projects/{project['id']}/issues", json={"description": "T1", "priority": 1})
    await client.post(f"/api/projects/{project['id']}/issues", json={"description": "T2", "priority": 2})
    resp = await client.get(f"/api/projects/{project['id']}/issues")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_list_issues_filter_status(client, project):
    await client.post(f"/api/projects/{project['id']}/issues", json={"description": "T1", "priority": 1})
    resp = await client.get(f"/api/projects/{project['id']}/issues?status=New")
    assert len(resp.json()) == 1
    resp = await client.get(f"/api/projects/{project['id']}/issues?status=Planned")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_get_issue(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/issues", json={"description": "Get me", "priority": 1}
    )
    issue_id = create_resp.json()["id"]
    resp = await client.get(f"/api/projects/{project['id']}/issues/{issue_id}")
    assert resp.status_code == 200
    assert resp.json()["description"] == "Get me"


@pytest.mark.asyncio
async def test_update_issue(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/issues", json={"description": "Update me", "priority": 3}
    )
    issue_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/projects/{project['id']}/issues/{issue_id}", json={"priority": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == 1


@pytest.mark.asyncio
async def test_update_status_valid(client, project):
    """Test a valid status transition via REST: any state can be Canceled."""
    create_resp = await client.post(
        f"/api/projects/{project['id']}/issues", json={"description": "Cancel me", "priority": 1}
    )
    issue_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/projects/{project['id']}/issues/{issue_id}/status",
        json={"status": "Canceled"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Canceled"


@pytest.mark.asyncio
async def test_update_status_invalid(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/issues", json={"description": "Skip", "priority": 1}
    )
    issue_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/projects/{project['id']}/issues/{issue_id}/status",
        json={"status": "Finished"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_decline_with_feedback(client, project, db_session):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/issues", json={"description": "Decline me", "priority": 1}
    )
    issue_id = create_resp.json()["id"]
    # Use service to advance to PLANNED (no REST endpoint for create_spec)
    from app.services.issue_service import IssueService
    service = IssueService(db_session)
    await service.create_spec(issue_id, project["id"], "# Spec")
    await service.create_plan(issue_id, project["id"], "# Plan")
    # Now decline via REST
    resp = await client.patch(
        f"/api/projects/{project['id']}/issues/{issue_id}/status",
        json={"status": "Declined", "decline_feedback": "Not good enough"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Declined"
    assert resp.json()["decline_feedback"] == "Not good enough"


@pytest.mark.asyncio
async def test_delete_issue(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/issues", json={"description": "Delete me", "priority": 1}
    )
    issue_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/projects/{project['id']}/issues/{issue_id}")
    assert resp.status_code == 204
