import uuid

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
async def test_create_project(client):
    response = await client.post("/api/projects", json={"name": "Test", "path": "/tmp/test", "description": "Desc"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client):
    await client.post("/api/projects", json={"name": "P1", "path": "/p1"})
    await client.post("/api/projects", json={"name": "P2", "path": "/p2"})
    response = await client.get("/api/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_get_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test"


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    response = await client.get(f"/api/projects/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Old", "path": "/old"})
    project_id = create_resp.json()["id"]
    response = await client.put(f"/api/projects/{project_id}", json={"name": "New"})
    assert response.status_code == 200
    assert response.json()["name"] == "New"


@pytest.mark.asyncio
async def test_delete_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Del", "path": "/del"})
    project_id = create_resp.json()["id"]
    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_project_with_tech_stack(client):
    response = await client.post(
        "/api/projects",
        json={"name": "Test", "path": "/tmp/test", "tech_stack": "Python, FastAPI"},
    )
    assert response.status_code == 201
    assert response.json()["tech_stack"] == "Python, FastAPI"


@pytest.mark.asyncio
async def test_create_project_tech_stack_defaults_to_empty(client):
    response = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    assert response.status_code == 201
    assert response.json()["tech_stack"] == ""


@pytest.mark.asyncio
async def test_update_project_tech_stack(client):
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Test", "path": "/tmp", "tech_stack": "Python"},
    )
    project_id = create_resp.json()["id"]
    response = await client.put(
        f"/api/projects/{project_id}", json={"tech_stack": "Python, React"}
    )
    assert response.status_code == 200
    assert response.json()["tech_stack"] == "Python, React"


@pytest.mark.asyncio
async def test_list_projects_excludes_archived_by_default(client):
    active = await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/projects")
    ids = [p["id"] for p in response.json()]

    assert active.json()["id"] in ids
    assert archived.json()["id"] not in ids


@pytest.mark.asyncio
async def test_list_projects_archived_true_returns_archived_only(client):
    await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/projects?archived=true")
    ids = [p["id"] for p in response.json()]

    assert ids == [archived.json()["id"]]


@pytest.mark.asyncio
async def test_list_projects_alphabetical(client):
    await client.post("/api/projects", json={"name": "banana", "path": "/b"})
    await client.post("/api/projects", json={"name": "Apple", "path": "/a"})
    await client.post("/api/projects", json={"name": "cherry", "path": "/c"})

    response = await client.get("/api/projects")
    names = [p["name"] for p in response.json()]

    assert names == ["Apple", "banana", "cherry"]


@pytest.mark.asyncio
async def test_archive_project_sets_archived_at_and_returns_response(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]

    response = await client.post(f"/api/projects/{project_id}/archive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is not None


@pytest.mark.asyncio
async def test_archive_project_not_found(client):
    response = await client.post(f"/api/projects/{uuid.uuid4()}/archive")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unarchive_project_clears_archived_at(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]
    await client.post(f"/api/projects/{project_id}/archive")

    response = await client.post(f"/api/projects/{project_id}/unarchive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_archive_is_idempotent(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]

    first = await client.post(f"/api/projects/{project_id}/archive")
    second = await client.post(f"/api/projects/{project_id}/archive")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["archived_at"] == second.json()["archived_at"]
