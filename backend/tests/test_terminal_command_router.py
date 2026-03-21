import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.project import Project


@pytest_asyncio.fixture
async def project(db_session):
    p = Project(name="Test Project", path="/tmp/test")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def client(db_session):
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_global_commands_empty(client):
    resp = await client.get("/api/terminal-commands")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_global_command(client):
    resp = await client.post(
        "/api/terminal-commands",
        json={"command": "echo hello", "sort_order": 0},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["command"] == "echo hello"
    assert data["sort_order"] == 0
    assert data["project_id"] is None


@pytest.mark.asyncio
async def test_create_project_command(client, project):
    resp = await client.post(
        "/api/terminal-commands",
        json={"command": "npm install", "sort_order": 0, "project_id": project.id},
    )
    assert resp.status_code == 201
    assert resp.json()["project_id"] == project.id


@pytest.mark.asyncio
async def test_list_filters_by_project_id(client, project):
    await client.post(
        "/api/terminal-commands",
        json={"command": "global", "sort_order": 0},
    )
    await client.post(
        "/api/terminal-commands",
        json={"command": "project", "sort_order": 0, "project_id": project.id},
    )
    resp = await client.get("/api/terminal-commands")
    assert len(resp.json()) == 1
    assert resp.json()[0]["command"] == "global"
    resp = await client.get(f"/api/terminal-commands?project_id={project.id}")
    assert len(resp.json()) == 1
    assert resp.json()[0]["command"] == "project"


@pytest.mark.asyncio
async def test_update_command(client):
    create = await client.post(
        "/api/terminal-commands",
        json={"command": "old", "sort_order": 0},
    )
    cmd_id = create.json()["id"]
    resp = await client.put(
        f"/api/terminal-commands/{cmd_id}",
        json={"command": "new"},
    )
    assert resp.status_code == 200
    assert resp.json()["command"] == "new"


@pytest.mark.asyncio
async def test_update_nonexistent_returns_404(client):
    resp = await client.put(
        "/api/terminal-commands/9999",
        json={"command": "new"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reorder(client):
    r1 = await client.post(
        "/api/terminal-commands",
        json={"command": "first", "sort_order": 0},
    )
    r2 = await client.post(
        "/api/terminal-commands",
        json={"command": "second", "sort_order": 1},
    )
    resp = await client.put(
        "/api/terminal-commands/reorder",
        json={"commands": [
            {"id": r1.json()["id"], "sort_order": 1},
            {"id": r2.json()["id"], "sort_order": 0},
        ]},
    )
    assert resp.status_code == 200
    listing = await client.get("/api/terminal-commands")
    cmds = listing.json()
    assert cmds[0]["command"] == "second"
    assert cmds[1]["command"] == "first"


@pytest.mark.asyncio
async def test_delete_command(client):
    create = await client.post(
        "/api/terminal-commands",
        json={"command": "to delete", "sort_order": 0},
    )
    cmd_id = create.json()["id"]
    resp = await client.delete(f"/api/terminal-commands/{cmd_id}")
    assert resp.status_code == 204
    listing = await client.get("/api/terminal-commands")
    assert len(listing.json()) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client):
    resp = await client.delete("/api/terminal-commands/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_command_with_newlines_rejected(client):
    resp = await client.post(
        "/api/terminal-commands",
        json={"command": "echo\nhello", "sort_order": 0},
    )
    assert resp.status_code == 422
