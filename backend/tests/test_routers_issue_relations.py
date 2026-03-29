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


@pytest_asyncio.fixture
async def two_issues(client, project):
    r1 = await client.post(f"/api/projects/{project['id']}/issues", json={"description": "Issue A"})
    r2 = await client.post(f"/api/projects/{project['id']}/issues", json={"description": "Issue B"})
    return r1.json(), r2.json()


@pytest.mark.asyncio
async def test_add_relation(client, two_issues):
    a, b = two_issues
    resp = await client.post(
        f"/api/issues/{a['id']}/relations",
        json={"target_id": b["id"], "relation_type": "blocks"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_id"] == a["id"]
    assert data["target_id"] == b["id"]


@pytest.mark.asyncio
async def test_get_relations(client, two_issues):
    a, b = two_issues
    await client.post(f"/api/issues/{a['id']}/relations", json={"target_id": b["id"], "relation_type": "blocks"})
    resp = await client.get(f"/api/issues/{a['id']}/relations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_delete_relation(client, two_issues):
    a, b = two_issues
    rel = (await client.post(f"/api/issues/{a['id']}/relations", json={"target_id": b["id"], "relation_type": "blocks"})).json()
    resp = await client.delete(f"/api/issues/{a['id']}/relations/{rel['id']}")
    assert resp.status_code == 204
    remaining = (await client.get(f"/api/issues/{a['id']}/relations")).json()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_self_relation_rejected(client, two_issues):
    a, _ = two_issues
    resp = await client.post(f"/api/issues/{a['id']}/relations", json={"target_id": a["id"], "relation_type": "blocks"})
    assert resp.status_code == 422
