import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.routers.terminals import get_terminal_service


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.create = MagicMock(return_value={
        "id": "term-ask-1",
        "issue_id": "",
        "project_id": "proj-1",
        "project_path": "C:/fake",
        "status": "active",
        "created_at": "2026-03-29T00:00:00Z",
        "cols": 120,
        "rows": 30,
    })
    svc.get_pty = MagicMock(return_value=MagicMock())
    return svc


@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_terminal_service] = lambda: mock_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_ask_terminal(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=True):
        mock_path.return_value = "C:/fake"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "term-ask-1"
        assert data["project_id"] == "proj-1"


@pytest.mark.asyncio
async def test_create_ask_terminal_invalid_project(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path:
        mock_path.side_effect = ValueError("Project not found")
        resp = await client.post("/api/terminals/ask", json={"project_id": "nonexistent"})
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_ask_terminal_invalid_path(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=False):
        mock_path.return_value = "C:/does-not-exist"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 400
