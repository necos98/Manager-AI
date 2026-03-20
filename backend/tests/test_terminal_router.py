import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.routers.terminals import get_terminal_service


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.list_active = MagicMock(return_value=[])
    svc.active_count = MagicMock(return_value=0)
    svc.create = MagicMock(return_value={
        "id": "term-1",
        "issue_id": "task-1",
        "project_id": "proj-1",
        "project_path": "C:/fake",
        "status": "active",
        "created_at": "2026-03-20T00:00:00Z",
        "cols": 120,
        "rows": 30,
    })
    svc.kill = MagicMock()
    svc.get = MagicMock(return_value={
        "id": "term-1",
        "issue_id": "task-1",
        "project_id": "proj-1",
        "project_path": "C:/fake",
        "status": "active",
        "created_at": "2026-03-20T00:00:00Z",
        "cols": 120,
        "rows": 30,
    })
    return svc


@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_terminal_service] = lambda: mock_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_terminals_empty(client, mock_service):
    resp = await client.get("/api/terminals")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_terminal(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=True):
        mock_path.return_value = "C:/fake"
        resp = await client.post("/api/terminals", json={
            "issue_id": "task-1",
            "project_id": "proj-1",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "term-1"
        assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_terminal_invalid_project(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path:
        mock_path.side_effect = ValueError("Project not found")
        resp = await client.post("/api/terminals", json={
            "issue_id": "task-1",
            "project_id": "nonexistent",
        })
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_terminal(client, mock_service):
    resp = await client.delete("/api/terminals/term-1")
    assert resp.status_code == 204
    mock_service.kill.assert_called_once_with("term-1")


@pytest.mark.asyncio
async def test_delete_terminal_not_found(client, mock_service):
    mock_service.kill.side_effect = KeyError("not found")
    resp = await client.delete("/api/terminals/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_terminals_with_project_filter(client, mock_service):
    resp = await client.get("/api/terminals?project_id=proj-1")
    assert resp.status_code == 200
    mock_service.list_active.assert_called_with(project_id="proj-1", issue_id=None)
