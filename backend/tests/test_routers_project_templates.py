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
async def project_id(client):
    resp = await client.post("/api/projects", json={"name": "P", "path": "/tmp/p"})
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_templates_returns_all_types(client, project_id):
    response = await client.get(f"/api/projects/{project_id}/templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    types = {item["type"] for item in data}
    assert "workflow" in types
    assert "implementation" in types
    assert all(not item["is_overridden"] for item in data)


@pytest.mark.asyncio
async def test_get_single_template(client, project_id):
    response = await client.get(f"/api/projects/{project_id}/templates/workflow")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "workflow"
    assert "is_overridden" in data


@pytest.mark.asyncio
async def test_save_and_retrieve_override(client, project_id):
    resp = await client.put(
        f"/api/projects/{project_id}/templates/workflow",
        json={"content": "Custom prompt {{project_name}}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_overridden"] is True
    assert resp.json()["content"] == "Custom prompt {{project_name}}"

    get_resp = await client.get(f"/api/projects/{project_id}/templates/workflow")
    assert get_resp.json()["content"] == "Custom prompt {{project_name}}"
    assert get_resp.json()["is_overridden"] is True


@pytest.mark.asyncio
async def test_delete_override_restores_default(client, project_id):
    await client.put(
        f"/api/projects/{project_id}/templates/workflow",
        json={"content": "Override"},
    )
    del_resp = await client.delete(f"/api/projects/{project_id}/templates/workflow")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/projects/{project_id}/templates/workflow")
    assert get_resp.json()["is_overridden"] is False
