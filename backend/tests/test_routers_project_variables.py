"""Tests for the project variables router, focused on secret masking."""
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
    resp = await client.post(
        "/api/projects",
        json={"name": "SecretTest", "path": "/tmp/secret", "description": ""},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_masks_secret_values(client, project_id):
    await client.post(
        "/api/project-variables",
        params={"project_id": project_id},
        json={"name": "API_KEY", "value": "super-secret", "is_secret": True},
    )
    resp = await client.get("/api/project-variables", params={"project_id": project_id})
    assert resp.status_code == 200
    rows = resp.json()
    secret = next(v for v in rows if v["name"] == "API_KEY")
    assert secret["value"] == ""
    assert secret["has_value"] is True
    assert secret["is_secret"] is True


@pytest.mark.asyncio
async def test_list_does_not_mask_non_secret(client, project_id):
    await client.post(
        "/api/project-variables",
        params={"project_id": project_id},
        json={"name": "DB_URL", "value": "sqlite:///x.db", "is_secret": False},
    )
    resp = await client.get("/api/project-variables", params={"project_id": project_id})
    row = next(v for v in resp.json() if v["name"] == "DB_URL")
    assert row["value"] == "sqlite:///x.db"
    assert row["has_value"] is True
    assert row["is_secret"] is False


@pytest.mark.asyncio
async def test_create_response_masks_secret_value(client, project_id):
    resp = await client.post(
        "/api/project-variables",
        params={"project_id": project_id},
        json={"name": "TOKEN", "value": "tkn123", "is_secret": True},
    )
    body = resp.json()
    assert body["value"] == ""
    assert body["has_value"] is True


@pytest.mark.asyncio
async def test_reveal_endpoint_returns_plaintext(client, project_id):
    create = await client.post(
        "/api/project-variables",
        params={"project_id": project_id},
        json={"name": "SECRET_TOKEN", "value": "plaintext-ok", "is_secret": True},
    )
    var_id = create.json()["id"]
    resp = await client.get(f"/api/project-variables/{var_id}/reveal")
    assert resp.status_code == 200
    assert resp.json()["value"] == "plaintext-ok"


@pytest.mark.asyncio
async def test_reveal_unknown_id_returns_404(client):
    resp = await client.get("/api/project-variables/999999/reveal")
    assert resp.status_code == 404
