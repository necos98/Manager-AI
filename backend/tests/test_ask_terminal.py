import pytest
import pytest_asyncio
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
    svc.list_active = MagicMock(return_value=[])
    return svc


@pytest_asyncio.fixture
async def client(mock_service, db_session):
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_terminal_service] = lambda: mock_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_create_ask_terminal(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=True):
        mock_path.return_value = "C:/fake"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "term-ask-1"
        assert data["project_id"] == "proj-1"


async def test_create_ask_terminal_invalid_project(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path:
        mock_path.side_effect = ValueError("Project not found")
        resp = await client.post("/api/terminals/ask", json={"project_id": "nonexistent"})
        assert resp.status_code == 400


async def test_create_ask_terminal_invalid_path(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=False):
        mock_path.return_value = "C:/does-not-exist"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 400


async def test_create_ask_terminal_kills_existing(client, mock_service):
    """Only one ask&brainstorming terminal per project may be active."""
    mock_service.list_active = MagicMock(return_value=[
        {
            "id": "term-old",
            "issue_id": "",
            "project_id": "proj-1",
            "project_path": "C:/fake",
            "status": "active",
            "created_at": "2026-03-28T00:00:00Z",
            "cols": 120,
            "rows": 30,
        }
    ])
    mock_service.get_buffered_output = MagicMock(return_value="")
    mock_service.kill = MagicMock()
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=True), \
         patch("app.routers.terminals._save_recording"):
        mock_path.return_value = "C:/fake"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 201
        mock_service.list_active.assert_any_call(project_id="proj-1", issue_id="")
        mock_service.kill.assert_called_once_with("term-old")


async def test_create_ask_terminal_writes_command(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=True):
        mock_path.return_value = "C:/fake"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 201
        # Verify the brainstorm command was written to the PTY, wrapped in quotes
        # so Claude CLI receives a single prompt string (so $ARGUMENTS resolves to the project id)
        pty_mock = mock_service.get_pty.return_value
        written_calls = [call.args[0] for call in pty_mock.write.call_args_list]
        assert any(
            '"/ask-and-brainstorm' in call and "proj-1" in call
            for call in written_calls
        )
