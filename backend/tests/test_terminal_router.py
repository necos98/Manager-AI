import pytest
import pytest_asyncio
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


def test_evaluate_condition_no_condition():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition(None, "NEW") is True

def test_evaluate_condition_match():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition("$issue_status == ACCEPTED", "ACCEPTED") is True

def test_evaluate_condition_no_match():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition("$issue_status == ACCEPTED", "NEW") is False

def test_evaluate_condition_unknown_returns_true():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition("$something_unknown", "foo") is True


# --- resize su terminal inesistente -----------------------------------------

def test_resize_nonexistent_terminal_raises_key_error():
    """service.resize() con terminal_id inesistente solleva KeyError (comportamento '404-equivalente').

    Il resize avviene via messaggio WebSocket, non via endpoint REST.
    Questo test documenta il contratto a livello servizio.
    """
    from app.services.terminal_service import TerminalService

    svc = TerminalService()
    with pytest.raises(KeyError):
        svc.resize("nonexistent-id", 100, 25)


# --- WebSocket disconnect → PTY cleanup -------------------------------------

def test_websocket_disconnect_calls_cleanup():
    """Disconnessione brusca del WebSocket deve chiamare service.cleanup(terminal_id)."""
    from starlette.testclient import TestClient
    from app.main import app
    from app.routers.terminals import get_terminal_service

    mock_svc = MagicMock()

    # pty.read(blocking=True) viene chiamato in run_in_executor.
    # Restituire "output" mantiene pty_to_ws in loop (non tocca il path EOF).
    # La disconnessione del client fa vincere ws_to_pty (WebSocketDisconnect),
    # che cancella pty_to_ws e triggerà il finally → cleanup.
    mock_pty = MagicMock()
    mock_pty.read.return_value = "output"

    mock_svc.get.return_value = {
        "id": "term-ws-1",
        "issue_id": "i1",
        "project_id": "p1",
        "project_path": "C:/fake",
        "status": "active",
        "created_at": "2026-03-29T00:00:00Z",
        "cols": 120,
        "rows": 30,
    }
    mock_svc.get_pty.return_value = mock_pty
    mock_svc.get_buffered_output.return_value = ""
    mock_svc.cleanup = MagicMock()
    mock_svc.mark_closed = MagicMock()
    mock_svc.append_output = MagicMock()
    mock_svc.resize = MagicMock()

    app.dependency_overrides[get_terminal_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            with client.websocket_connect("/api/terminals/term-ws-1/ws"):
                pass  # disconnessione immediata
    finally:
        app.dependency_overrides.clear()

    mock_svc.cleanup.assert_called_once_with("term-ws-1")
