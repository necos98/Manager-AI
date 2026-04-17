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


@pytest.mark.asyncio
async def test_dashboard_empty(client):
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_dashboard_shows_active_issues(client):
    proj = (await client.post("/api/projects", json={"name": "P1", "path": "/tmp"})).json()
    await client.post(f"/api/projects/{proj['id']}/issues", json={"description": "Active issue"})
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == proj["id"]
    assert len(data[0]["active_issues"]) == 1


@pytest.mark.asyncio
async def test_dashboard_project_structure(client):
    proj = (await client.post("/api/projects", json={"name": "My Project", "path": "/tmp"})).json()
    resp = await client.get("/api/dashboard")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "My Project"
    assert "active_issues" in data[0]
    assert data[0]["active_issues"] == []


@pytest.mark.asyncio
async def test_dashboard_excludes_archived_projects(client):
    active = await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/dashboard")
    ids = [p["id"] for p in response.json()]

    assert active.json()["id"] in ids
    assert archived.json()["id"] not in ids
