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
