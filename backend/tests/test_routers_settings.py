import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client(db_session):
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_list_settings_returns_all_defaults(client):
    response = await client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 12
    keys = [s["key"] for s in data]
    assert "server.name" in keys
    assert all(not s["is_customized"] for s in data)


async def test_update_setting(client):
    response = await client.put(
        "/api/settings/server.name",
        json={"value": "My Manager"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "server.name"
    assert data["value"] == "My Manager"
    assert data["is_customized"] is True
    assert data["default"] == "Manager AI"


async def test_update_setting_unknown_key_returns_404(client):
    response = await client.put(
        "/api/settings/nonexistent.key",
        json={"value": "test"},
    )
    assert response.status_code == 404


async def test_reset_setting(client):
    await client.put("/api/settings/server.name", json={"value": "Custom"})
    response = await client.delete("/api/settings/server.name")
    assert response.status_code == 204
    # Verify it's back to default
    list_response = await client.get("/api/settings")
    settings = list_response.json()
    server = next(s for s in settings if s["key"] == "server.name")
    assert server["is_customized"] is False
    assert server["value"] == "Manager AI"


async def test_reset_all_settings(client):
    await client.put("/api/settings/server.name", json={"value": "Custom 1"})
    await client.put(
        "/api/settings/tool.get_task_status.description",
        json={"value": "Custom 2"},
    )
    response = await client.delete("/api/settings")
    assert response.status_code == 204
    list_response = await client.get("/api/settings")
    settings = list_response.json()
    assert all(not s["is_customized"] for s in settings)
