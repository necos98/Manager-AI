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
async def project_and_issue(client):
    proj = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    pid = proj.json()["id"]
    issue = await client.post(f"/api/projects/{pid}/issues", json={"description": "Test issue", "priority": 1})
    return pid, issue.json()["id"]


@pytest.mark.asyncio
async def test_create_tasks(client, project_and_issue):
    pid, iid = project_and_issue
    resp = await client.post(
        f"/api/projects/{pid}/issues/{iid}/tasks",
        json={"tasks": [{"name": "Step 1"}, {"name": "Step 2"}]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Step 1"
    assert data[0]["status"] == "Pending"


@pytest.mark.asyncio
async def test_list_tasks(client, project_and_issue):
    pid, iid = project_and_issue
    await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "T1"}]})
    resp = await client.get(f"/api/projects/{pid}/issues/{iid}/tasks")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_update_task_status(client, project_and_issue):
    pid, iid = project_and_issue
    create_resp = await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "T1"}]})
    tid = create_resp.json()[0]["id"]
    resp = await client.patch(f"/api/projects/{pid}/issues/{iid}/tasks/{tid}", json={"status": "In Progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "In Progress"


@pytest.mark.asyncio
async def test_replace_tasks(client, project_and_issue):
    pid, iid = project_and_issue
    await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "Old"}]})
    resp = await client.put(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "New 1"}, {"name": "New 2"}]})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_delete_task(client, project_and_issue):
    pid, iid = project_and_issue
    create_resp = await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "Del"}]})
    tid = create_resp.json()[0]["id"]
    resp = await client.delete(f"/api/projects/{pid}/issues/{iid}/tasks/{tid}")
    assert resp.status_code == 204
