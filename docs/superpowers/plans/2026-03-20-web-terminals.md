# Web Terminals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive web terminals to Manager AI, one per task, with split-view layout, persistent background processes, and a dashboard.

**Architecture:** Python-pure approach using `pywinpty` for PTY spawning on Windows, FastAPI WebSocket for bidirectional I/O, and `xterm.js` in the frontend. Terminals are in-memory only (no DB model). The backend gets a new `TerminalService` (registry) and `terminals` router. The frontend gets a `TerminalPanel` component, modifications to `TaskDetailPage` for split-view, and a new `TerminalsPage` dashboard.

**Tech Stack:** pywinpty, FastAPI WebSocket, xterm.js, @xterm/addon-fit, @xterm/addon-web-links

**Spec:** `docs/superpowers/specs/2026-03-20-web-terminals-design.md`

---

## File Structure

### Backend (new files)
- `backend/app/services/terminal_service.py` — In-memory terminal registry, PTY lifecycle management
- `backend/app/routers/terminals.py` — REST endpoints (POST/GET/DELETE) + WebSocket endpoint
- `backend/app/schemas/terminal.py` — Pydantic schemas for terminal create/response
- `backend/tests/test_terminal_service.py` — Unit tests for TerminalService
- `backend/tests/test_terminal_router.py` — Integration tests for terminal endpoints

### Backend (modified files)
- `backend/requirements.txt` — Add `pywinpty`
- `backend/app/main.py` — Register terminals router

### Frontend (new files)
- `frontend/src/components/TerminalPanel.jsx` — xterm.js wrapper with WebSocket connection
- `frontend/src/pages/TerminalsPage.jsx` — Dashboard of active terminals

### Frontend (modified files)
- `frontend/package.json` — Add xterm dependencies
- `frontend/src/api/client.js` — Add terminal API methods
- `frontend/src/pages/TaskDetailPage.jsx` — Split view layout with terminal
- `frontend/src/pages/ProjectDetailPage.jsx` — Active terminal indicators on tasks
- `frontend/src/components/TaskList.jsx` — Green dot for tasks with active terminals
- `frontend/src/App.jsx` — Add `/terminals` route, update navbar
- `frontend/vite.config.js` — Add WebSocket proxy

---

### Task 1: Add pywinpty dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add pywinpty to requirements.txt**

Add at the end of `backend/requirements.txt`:
```
pywinpty>=2.0.0
```

- [ ] **Step 2: Install the dependency**

Run: `cd backend && pip install pywinpty`
Expected: Successfully installed pywinpty

- [ ] **Step 3: Verify import works**

Run: `python -c "import winpty; print(winpty.__version__)"`
Expected: Prints version number without error

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat(terminal): add pywinpty dependency"
```

---

### Task 2: Terminal Pydantic schemas

**Files:**
- Create: `backend/app/schemas/terminal.py`

- [ ] **Step 1: Create the schema file**

```python
from datetime import datetime

from pydantic import BaseModel


class TerminalCreate(BaseModel):
    task_id: str
    project_id: str


class TerminalResponse(BaseModel):
    id: str
    task_id: str
    project_id: str
    project_path: str
    status: str
    created_at: datetime
    cols: int
    rows: int


class TerminalListResponse(BaseModel):
    id: str
    task_id: str
    project_id: str
    project_path: str
    status: str
    created_at: datetime
```

- [ ] **Step 2: Verify schema imports**

Run: `cd backend && python -c "from app.schemas.terminal import TerminalCreate, TerminalResponse, TerminalListResponse; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/terminal.py
git commit -m "feat(terminal): add Pydantic schemas for terminal endpoints"
```

---

### Task 3: TerminalService — in-memory registry and PTY lifecycle

**Files:**
- Create: `backend/app/services/terminal_service.py`
- Create: `backend/tests/test_terminal_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_terminal_service.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.terminal_service import TerminalService


@pytest.fixture
def service():
    svc = TerminalService()
    yield svc
    # Cleanup: kill any spawned terminals
    for tid in list(svc._terminals.keys()):
        try:
            svc.kill(tid)
        except Exception:
            pass


class TestTerminalServiceRegistry:
    def test_list_empty(self, service):
        assert service.list_active() == []

    def test_create_and_list(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )

            assert term["task_id"] == "task-1"
            assert term["project_id"] == "proj-1"
            assert term["status"] == "active"
            assert len(service.list_active()) == 1

    def test_create_duplicate_task_returns_existing(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term1 = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            term2 = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            assert term1["id"] == term2["id"]
            assert len(service.list_active()) == 1

    def test_kill_removes_terminal(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            service.kill(term["id"])
            assert len(service.list_active()) == 0

    def test_kill_nonexistent_raises(self, service):
        with pytest.raises(KeyError):
            service.kill("nonexistent")

    def test_get_by_id(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            found = service.get(term["id"])
            assert found["id"] == term["id"]

    def test_get_nonexistent_raises(self, service):
        with pytest.raises(KeyError):
            service.get("nonexistent")

    def test_list_filter_by_project(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            service.create(task_id="t1", project_id="p1", project_path="C:/a")
            service.create(task_id="t2", project_id="p2", project_path="C:/b")

            p1_terms = service.list_active(project_id="p1")
            assert len(p1_terms) == 1
            assert p1_terms[0]["project_id"] == "p1"

    def test_list_filter_by_task(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            service.create(task_id="t1", project_id="p1", project_path="C:/a")
            service.create(task_id="t2", project_id="p1", project_path="C:/a")

            t1_terms = service.list_active(task_id="t1")
            assert len(t1_terms) == 1

    def test_active_count(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            assert service.active_count() == 0
            service.create(task_id="t1", project_id="p1", project_path="C:/a")
            assert service.active_count() == 1

    def test_resize(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            service.resize(term["id"], 200, 50)
            updated = service.get(term["id"])
            assert updated["cols"] == 200
            assert updated["rows"] == 50
            mock_pty.set_size.assert_called_with(200, 50)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_terminal_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.terminal_service'`

- [ ] **Step 3: Implement TerminalService**

Create `backend/app/services/terminal_service.py`:

```python
import uuid
from datetime import datetime, timezone

from winpty import PTY


class TerminalService:
    """In-memory registry of active terminal sessions with PTY lifecycle management."""

    def __init__(self):
        self._terminals: dict[str, dict] = {}

    def create(
        self,
        task_id: str,
        project_id: str,
        project_path: str,
        cols: int = 120,
        rows: int = 30,
    ) -> dict:
        # Return existing terminal for this task (no duplicates)
        for term in self._terminals.values():
            if term["task_id"] == task_id and term["status"] == "active":
                return self._to_response(term)

        pty = PTY(cols, rows)
        pty.spawn(r"C:\Windows\System32\cmd.exe", cwd=project_path)

        term_id = str(uuid.uuid4())
        entry = {
            "id": term_id,
            "task_id": task_id,
            "project_id": project_id,
            "project_path": project_path,
            "pty": pty,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "cols": cols,
            "rows": rows,
        }
        self._terminals[term_id] = entry
        return self._to_response(entry)

    def get(self, terminal_id: str) -> dict:
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")
        return self._to_response(self._terminals[terminal_id])

    def get_pty(self, terminal_id: str) -> PTY:
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")
        return self._terminals[terminal_id]["pty"]

    def list_active(
        self,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> list[dict]:
        results = []
        for term in self._terminals.values():
            if term["status"] != "active":
                continue
            if project_id and term["project_id"] != project_id:
                continue
            if task_id and term["task_id"] != task_id:
                continue
            results.append(self._to_response(term))
        return results

    def active_count(self) -> int:
        return sum(1 for t in self._terminals.values() if t["status"] == "active")

    def kill(self, terminal_id: str) -> None:
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")
        entry = self._terminals.pop(terminal_id)
        try:
            pty = entry["pty"]
            # pywinpty doesn't have an explicit kill, but closing handles stops the process
            if hasattr(pty, "close"):
                pty.close()
        except Exception:
            pass

    def mark_closed(self, terminal_id: str) -> None:
        if terminal_id in self._terminals:
            self._terminals.pop(terminal_id)

    def resize(self, terminal_id: str, cols: int, rows: int) -> None:
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")
        entry = self._terminals[terminal_id]
        entry["cols"] = cols
        entry["rows"] = rows
        entry["pty"].set_size(cols, rows)

    def _to_response(self, entry: dict) -> dict:
        return {
            "id": entry["id"],
            "task_id": entry["task_id"],
            "project_id": entry["project_id"],
            "project_path": entry["project_path"],
            "status": entry["status"],
            "created_at": entry["created_at"],
            "cols": entry["cols"],
            "rows": entry["rows"],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_terminal_service.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/terminal_service.py backend/tests/test_terminal_service.py
git commit -m "feat(terminal): add TerminalService with in-memory registry and PTY lifecycle"
```

---

### Task 4: Terminal REST + WebSocket router

**Files:**
- Create: `backend/app/routers/terminals.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_terminal_router.py`

- [ ] **Step 1: Write failing tests for REST endpoints**

Create `backend/tests/test_terminal_router.py`:

```python
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
        "task_id": "task-1",
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
        "task_id": "task-1",
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
    # Mock project lookup
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path:
        mock_path.return_value = "C:/fake"
        resp = await client.post("/api/terminals", json={
            "task_id": "task-1",
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
            "task_id": "task-1",
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
    mock_service.list_active.assert_called_with(project_id="proj-1", task_id=None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_terminal_router.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement the router**

Create `backend/app/routers/terminals.py`:

```python
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.terminal import TerminalCreate, TerminalListResponse, TerminalResponse
from app.services.terminal_service import TerminalService

router = APIRouter(prefix="/api/terminals", tags=["terminals"])

# Singleton service instance
_terminal_service = TerminalService()


def get_terminal_service() -> TerminalService:
    return _terminal_service


async def get_project_path(project_id: str, db: AsyncSession) -> str:
    """Look up project path from DB. Raises ValueError if not found."""
    from app.models.project import Project

    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")
    return project.path


@router.post("", response_model=TerminalResponse, status_code=201)
async def create_terminal(
    data: TerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        project_path = await get_project_path(data.project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        terminal = service.create(
            task_id=data.task_id,
            project_id=data.project_id,
            project_path=project_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    response = TerminalResponse(**terminal)
    return response


@router.get("/config")
async def terminal_config(
    db: AsyncSession = Depends(get_db),
):
    """Return terminal configuration including soft limit."""
    from app.services.settings_service import SettingsService
    svc = SettingsService(db)
    try:
        limit = int(await svc.get("terminal_soft_limit"))
    except (KeyError, ValueError):
        limit = 5
    return {"soft_limit": limit}


@router.get("", response_model=list[TerminalListResponse])
async def list_terminals(
    project_id: str | None = Query(None),
    task_id: str | None = Query(None),
    service: TerminalService = Depends(get_terminal_service),
):
    return service.list_active(project_id=project_id, task_id=task_id)


@router.get("/count")
async def terminal_count(
    service: TerminalService = Depends(get_terminal_service),
):
    return {"count": service.active_count()}


@router.delete("/{terminal_id}", status_code=204)
async def delete_terminal(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        service.kill(terminal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Terminal not found")


@router.websocket("/{terminal_id}/ws")
async def terminal_ws(
    terminal_id: str,
    websocket: WebSocket,
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        service.get(terminal_id)
    except KeyError:
        await websocket.close(code=4004, reason="Terminal not found")
        return

    await websocket.accept()
    pty = service.get_pty(terminal_id)

    async def pty_to_ws():
        """Read from PTY, send to WebSocket."""
        loop = asyncio.get_event_loop()
        try:
            while True:
                data = await loop.run_in_executor(None, pty.read)
                if not data:
                    # PTY closed (process exited)
                    service.mark_closed(terminal_id)
                    await websocket.close(code=1000, reason="Terminal session ended")
                    break
                await websocket.send_text(data)
        except (WebSocketDisconnect, Exception):
            pass

    async def ws_to_pty():
        """Read from WebSocket, write to PTY."""
        try:
            while True:
                message = await websocket.receive_text()
                # Check for resize messages
                if message.startswith('{"type":"resize"'):
                    try:
                        msg = json.loads(message)
                        if msg.get("type") == "resize":
                            service.resize(terminal_id, msg["cols"], msg["rows"])
                            continue
                    except (json.JSONDecodeError, KeyError):
                        pass
                pty.write(message)
        except (WebSocketDisconnect, Exception):
            pass

    # Run both directions concurrently
    pty_read_task = asyncio.create_task(pty_to_ws())
    ws_read_task = asyncio.create_task(ws_to_pty())

    try:
        done, pending = await asyncio.wait(
            [pty_read_task, ws_read_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception:
        pty_read_task.cancel()
        ws_read_task.cancel()
```

- [ ] **Step 4: Add terminal_soft_limit to default_settings.json**

In `backend/app/mcp/default_settings.json`, add this key:
```json
"terminal_soft_limit": "5"
```

- [ ] **Step 5: Register router in main.py**

In `backend/app/main.py`, add import and include:

```python
from app.routers import projects, settings, tasks, terminals
```

and:

```python
app.include_router(terminals.router)
```

- [ ] **Step 6: Add WebSocket proxy to vite config**

In `frontend/vite.config.js`, update the proxy section:

```javascript
proxy: {
  "/api": {
    target: process.env.BACKEND_URL || "http://localhost:8000",
    ws: true,
  },
},
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_terminal_router.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/terminals.py backend/app/main.py backend/app/mcp/default_settings.json backend/tests/test_terminal_router.py frontend/vite.config.js
git commit -m "feat(terminal): add REST + WebSocket router for terminals with configurable soft limit"
```

---

### Task 5: Frontend — install xterm.js dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install xterm packages**

Run: `cd frontend && npm install xterm @xterm/addon-fit @xterm/addon-web-links`
Expected: Added 3 packages

- [ ] **Step 2: Verify installation**

Run: `cd frontend && node -e "require('xterm'); console.log('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(terminal): add xterm.js frontend dependencies"
```

---

### Task 6: Frontend — API client terminal methods

**Files:**
- Modify: `frontend/src/api/client.js`

- [ ] **Step 1: Add terminal API methods**

Add to the `api` object in `frontend/src/api/client.js`:

```javascript
// Terminals
listTerminals: (projectId, taskId) => {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (taskId) params.set("task_id", taskId);
  const qs = params.toString();
  return request(`/terminals${qs ? `?${qs}` : ""}`);
},
createTerminal: (taskId, projectId) =>
  request("/terminals", { method: "POST", body: JSON.stringify({ task_id: taskId, project_id: projectId }) }),
killTerminal: (terminalId) =>
  request(`/terminals/${terminalId}`, { method: "DELETE" }),
terminalCount: () => request("/terminals/count"),
terminalConfig: () => request("/terminals/config"),
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.js
git commit -m "feat(terminal): add terminal API client methods"
```

---

### Task 7: Frontend — TerminalPanel component

**Files:**
- Create: `frontend/src/components/TerminalPanel.jsx`

- [ ] **Step 1: Create TerminalPanel component**

```jsx
import { useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "xterm/css/xterm.css";

export default function TerminalPanel({ terminalId, onSessionEnd }) {
  const containerRef = useRef(null);
  const terminalRef = useRef(null);
  const wsRef = useRef(null);
  const fitAddonRef = useRef(null);
  const [status, setStatus] = useState("connecting");
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 5;

  useEffect(() => {
    if (!terminalId || !containerRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Consolas', monospace",
      theme: {
        background: "#0d0d0d",
        foreground: "#cdd6f4",
        cursor: "#89b4fa",
      },
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(containerRef.current);
    fitAddon.fit();

    terminalRef.current = term;
    fitAddonRef.current = fitAddon;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/terminals/${terminalId}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        retryCountRef.current = 0;
        // Send initial size
        const dims = fitAddon.proposeDimensions();
        if (dims) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        term.write(event.data);
      };

      ws.onclose = (event) => {
        if (event.code === 1000 && event.reason === "Terminal session ended") {
          setStatus("ended");
          if (onSessionEnd) onSessionEnd();
          return;
        }
        setStatus("disconnected");
        // Retry with exponential backoff
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current++;
          setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        // onclose will fire after this
      };
    }

    connect();

    // Forward terminal input to WebSocket
    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      }
    });

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      fitAddon.fit();
      const dims = fitAddon.proposeDimensions();
      if (dims && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      ws?.close();
      term.dispose();
    };
  }, [terminalId]);

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d]">
      {status === "ended" && (
        <div className="px-3 py-2 bg-gray-800 text-gray-400 text-sm text-center">
          Terminal session ended
        </div>
      )}
      {status === "disconnected" && (
        <div className="px-3 py-2 bg-yellow-900 text-yellow-300 text-sm text-center">
          Reconnecting...
        </div>
      )}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
```

- [ ] **Step 2: Verify no syntax errors**

Run: `cd frontend && npx vite build 2>&1 | head -5`
Expected: No syntax errors (build may fail on other imports but the file itself is valid)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TerminalPanel.jsx
git commit -m "feat(terminal): add TerminalPanel xterm.js wrapper component"
```

---

### Task 8: Frontend — TaskDetailPage split view

**Files:**
- Modify: `frontend/src/pages/TaskDetailPage.jsx`

- [ ] **Step 1: Rewrite TaskDetailPage with split view**

Replace the contents of `frontend/src/pages/TaskDetailPage.jsx` with:

```jsx
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import MarkdownViewer from "../components/MarkdownViewer";
import StatusBadge from "../components/StatusBadge";
import TerminalPanel from "../components/TerminalPanel";

function SplitView({ terminalId, onSessionEnd, leftPanel }) {
  const containerRef = useRef(null);
  const [leftWidth, setLeftWidth] = useState(40); // percentage
  const dragging = useRef(false);

  const onMouseDown = useCallback((e) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setLeftWidth(Math.min(Math.max(pct, 20), 80));
    };
    const onMouseUp = () => {
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <div ref={containerRef} className="flex bg-white rounded-lg shadow-sm border" style={{ height: "calc(100vh - 160px)" }}>
      <div className="overflow-y-auto" style={{ width: `${leftWidth}%` }}>
        {leftPanel}
      </div>
      <div
        className="w-1 bg-gray-200 hover:bg-blue-400 cursor-col-resize flex-shrink-0 transition-colors"
        onMouseDown={onMouseDown}
      />
      <div className="flex-1 min-w-0">
        <TerminalPanel terminalId={terminalId} onSessionEnd={onSessionEnd} />
      </div>
    </div>
  );
}

export default function TaskDetailPage() {
  const { id: projectId, taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [terminalId, setTerminalId] = useState(null);
  const [terminalLoading, setTerminalLoading] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [showLimitWarning, setShowLimitWarning] = useState(false);

  // Load task and check for existing terminal
  useEffect(() => {
    Promise.all([
      api.getTask(projectId, taskId),
      api.listTerminals(null, taskId),
    ]).then(([t, terminals]) => {
      setTask(t);
      if (terminals.length > 0) {
        setTerminalId(terminals[0].id);
      }
    }).finally(() => setLoading(false));
  }, [projectId, taskId]);

  const openTerminal = async () => {
    // Check soft limit from settings
    const [{ count }, { soft_limit }] = await Promise.all([
      api.terminalCount(),
      api.terminalConfig(),
    ]);
    if (count >= soft_limit) {
      setShowLimitWarning(true);
      return;
    }
    await doOpenTerminal();
  };

  const doOpenTerminal = async () => {
    setShowLimitWarning(false);
    setTerminalLoading(true);
    try {
      const term = await api.createTerminal(taskId, projectId);
      setTerminalId(term.id);
    } catch (err) {
      alert("Failed to open terminal: " + err.message);
    } finally {
      setTerminalLoading(false);
    }
  };

  const closeTerminal = async () => {
    setShowCloseConfirm(false);
    if (terminalId) {
      try {
        await api.killTerminal(terminalId);
      } catch {
        // Terminal may already be dead
      }
      setTerminalId(null);
    }
  };

  if (loading) return <p>Loading...</p>;
  if (!task) return <p>Task not found.</p>;

  const taskDetails = (
    <div className={terminalId ? "overflow-y-auto p-4" : "p-6"}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h1 className={`font-bold ${terminalId ? "text-lg" : "text-2xl"}`}>
            {task.name || "Untitled Task"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">Priority: {task.priority}</p>
        </div>
        <StatusBadge status={task.status} />
      </div>

      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Description</h2>
        <p className="text-gray-700 text-sm">{task.description}</p>
      </div>

      {task.specification && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Specification</h2>
          <div className="bg-indigo-50 rounded p-3">
            <MarkdownViewer content={task.specification} />
          </div>
        </div>
      )}

      {task.plan && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Plan</h2>
          <div className="bg-gray-50 rounded p-3">
            <MarkdownViewer content={task.plan} />
          </div>
        </div>
      )}

      {task.recap && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Recap</h2>
          <div className="bg-green-50 rounded p-3">
            <MarkdownViewer content={task.recap} />
          </div>
        </div>
      )}

      {task.decline_feedback && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Decline Feedback</h2>
          <p className="text-red-700 bg-red-50 rounded p-3 text-sm">{task.decline_feedback}</p>
        </div>
      )}
    </div>
  );

  return (
    <div>
      {/* Header bar */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline">
          &larr; Back to tasks
        </button>
        {terminalId ? (
          <button
            onClick={() => setShowCloseConfirm(true)}
            className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 flex items-center gap-2 text-sm"
          >
            <span className="font-mono">&#9632;</span> Close Terminal
          </button>
        ) : (
          <button
            onClick={openTerminal}
            disabled={terminalLoading}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 text-sm"
          >
            <span className="font-mono">&#9654;</span> {terminalLoading ? "Opening..." : "Open Terminal"}
          </button>
        )}
      </div>

      {/* Content: full-width or split */}
      {terminalId ? (
        <SplitView
          terminalId={terminalId}
          onSessionEnd={() => setTerminalId(null)}
          leftPanel={taskDetails}
        />
      ) : (
        <div className="bg-white rounded-lg shadow-sm border">
          {taskDetails}
        </div>
      )}

      {/* Close confirmation modal */}
      {showCloseConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={(e) => { if (e.target === e.currentTarget) setShowCloseConfirm(false); }}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4">
            <h3 className="text-lg font-bold mb-2">Close Terminal?</h3>
            <p className="text-gray-600 text-sm mb-4">This will kill the terminal process. Any running commands will be terminated.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCloseConfirm(false)} className="px-4 py-2 rounded border hover:bg-gray-50 text-sm">Cancel</button>
              <button onClick={closeTerminal} className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 text-sm">Close Terminal</button>
            </div>
          </div>
        </div>
      )}

      {/* Soft limit warning modal */}
      {showLimitWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={(e) => { if (e.target === e.currentTarget) setShowLimitWarning(false); }}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4">
            <h3 className="text-lg font-bold mb-2 text-amber-600">Terminal Limit Reached</h3>
            <p className="text-gray-600 text-sm mb-4">You have reached the soft limit of open terminals. Consider closing unused terminals to free resources.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowLimitWarning(false)} className="px-4 py-2 rounded border hover:bg-gray-50 text-sm">Cancel</button>
              <button onClick={doOpenTerminal} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">Open Anyway</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TaskDetailPage.jsx
git commit -m "feat(terminal): add split view layout to TaskDetailPage"
```

---

### Task 9: Frontend — TaskList terminal indicator

**Files:**
- Modify: `frontend/src/components/TaskList.jsx`

- [ ] **Step 1: Update TaskList to show terminal indicators**

Replace `frontend/src/components/TaskList.jsx`:

```jsx
import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function TaskList({ tasks, projectId, activeTerminalTaskIds = [] }) {
  if (tasks.length === 0) return <p className="text-gray-500">No tasks yet.</p>;

  return (
    <div className="space-y-2">
      {tasks.map((task) => {
        const hasTerminal = activeTerminalTaskIds.includes(task.id);
        return (
          <Link
            key={task.id}
            to={`/projects/${projectId}/tasks/${task.id}`}
            className="flex items-center justify-between bg-white rounded border p-3 hover:shadow-sm transition-shadow"
          >
            <div className="flex items-center flex-1 min-w-0">
              {hasTerminal && (
                <span
                  className="w-2 h-2 rounded-full bg-green-400 mr-3 flex-shrink-0"
                  style={{ boxShadow: "0 0 6px #4ade80" }}
                  title="Terminal active"
                />
              )}
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">{task.name || task.description}</p>
                {task.name && <p className="text-sm text-gray-500 truncate">{task.description}</p>}
              </div>
            </div>
            <div className="flex items-center gap-3 ml-4">
              {hasTerminal && (
                <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">terminal</span>
              )}
              <span className="text-sm text-gray-400">P{task.priority}</span>
              <StatusBadge status={task.status} />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TaskList.jsx
git commit -m "feat(terminal): add green dot indicator for active terminals in TaskList"
```

---

### Task 10: Frontend — ProjectDetailPage terminal indicators

**Files:**
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`

- [ ] **Step 1: Fetch active terminals and pass to TaskList**

In `frontend/src/pages/ProjectDetailPage.jsx`, update the component:

1. Add state: `const [activeTerminalTaskIds, setActiveTerminalTaskIds] = useState([]);`

2. Update the `useEffect` to also fetch terminals:
```javascript
useEffect(() => {
  Promise.all([
    api.getProject(id),
    api.listTasks(id, filter === "All" ? null : filter),
    api.listTerminals(id),
  ]).then(([p, t, terms]) => {
    setProject(p);
    setTasks(t);
    setActiveTerminalTaskIds(terms.map((term) => term.task_id));
  }).finally(() => setLoading(false));
}, [id, filter]);
```

3. Add a terminal count display after the project name:
```jsx
{activeTerminalTaskIds.length > 0 && (
  <span className="text-sm text-green-600 ml-3">
    ● {activeTerminalTaskIds.length} terminal{activeTerminalTaskIds.length > 1 ? "s" : ""} active
  </span>
)}
```

4. Pass to TaskList:
```jsx
<TaskList tasks={tasks} projectId={id} activeTerminalTaskIds={activeTerminalTaskIds} />
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ProjectDetailPage.jsx
git commit -m "feat(terminal): show active terminal indicators in ProjectDetailPage"
```

---

### Task 11: Frontend — TerminalsPage dashboard

**Files:**
- Create: `frontend/src/pages/TerminalsPage.jsx`

- [ ] **Step 1: Create the dashboard page**

```jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function TerminalsPage() {
  const [terminals, setTerminals] = useState([]);
  const [softLimit, setSoftLimit] = useState(5);
  const [loading, setLoading] = useState(true);

  const fetchTerminals = () => {
    api.listTerminals().then(setTerminals).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTerminals();
    api.terminalConfig().then((cfg) => setSoftLimit(cfg.soft_limit)).catch(() => {});
    const interval = setInterval(fetchTerminals, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleKill = async (terminalId) => {
    if (!confirm("Kill this terminal? Any running commands will be terminated.")) return;
    try {
      await api.killTerminal(terminalId);
      setTerminals((prev) => prev.filter((t) => t.id !== terminalId));
    } catch (err) {
      alert("Failed to kill terminal: " + err.message);
    }
  };

  const formatAge = (createdAt) => {
    const diff = Date.now() - new Date(createdAt).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m ago`;
  };

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Active Terminals</h1>
        <span className="text-sm text-gray-500">{terminals.length} / {softLimit} (soft limit)</span>
      </div>

      {terminals.length === 0 ? (
        <p className="text-gray-500">No active terminals.</p>
      ) : (
        <div className="space-y-3">
          {terminals.map((term) => (
            <div key={term.id} className="flex items-center bg-white rounded-lg border p-4">
              <span
                className="w-2.5 h-2.5 rounded-full bg-green-400 mr-4 flex-shrink-0"
                style={{ boxShadow: "0 0 6px #4ade80" }}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900">{term.task_id}</p>
                <p className="text-sm text-gray-500">
                  <span className="text-blue-600">{term.project_id}</span>
                  {" · "}Started {formatAge(term.created_at)}
                </p>
              </div>
              <div className="flex gap-2 ml-4">
                <Link
                  to={`/projects/${term.project_id}/tasks/${term.task_id}`}
                  className="text-sm text-blue-600 border border-blue-200 px-3 py-1.5 rounded hover:bg-blue-50"
                >
                  Go to Task
                </Link>
                <button
                  onClick={() => handleKill(term.id)}
                  className="text-sm text-red-600 border border-red-200 px-3 py-1.5 rounded hover:bg-red-50"
                >
                  Kill
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/TerminalsPage.jsx
git commit -m "feat(terminal): add TerminalsPage dashboard"
```

---

### Task 12: Frontend — App.jsx routes and navbar

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Update App.jsx with new route and navbar link**

Replace `frontend/src/App.jsx`:

```jsx
import { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import NewProjectPage from "./pages/NewProjectPage";
import NewTaskPage from "./pages/NewTaskPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import TaskDetailPage from "./pages/TaskDetailPage";
import TerminalsPage from "./pages/TerminalsPage";
import SettingsPage from "./pages/SettingsPage";

function Navbar() {
  const [terminalCount, setTerminalCount] = useState(0);

  useEffect(() => {
    const fetchCount = () => {
      api.terminalCount().then((data) => setTerminalCount(data.count)).catch(() => {});
    };
    fetchCount();
    const interval = setInterval(fetchCount, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        <a href="/" className="text-xl font-bold text-gray-900">
          Manager AI
        </a>
        <div className="flex items-center gap-4">
          <Link to="/terminals" className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1.5">
            Terminals
            {terminalCount > 0 && (
              <span className="bg-green-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                {terminalCount}
              </span>
            )}
          </Link>
          <Link to="/settings" className="text-sm text-gray-500 hover:text-gray-900">
            Settings
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="max-w-5xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/projects/new" element={<NewProjectPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/projects/:id/tasks/new" element={<NewTaskPage />} />
            <Route path="/projects/:id/tasks/:taskId" element={<TaskDetailPage />} />
            <Route path="/terminals" element={<TerminalsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat(terminal): add Terminals route and navbar badge"
```

---

### Task 13: Manual end-to-end verification

**Files:** None (testing only)

- [ ] **Step 1: Start the application**

Run: `python start.py`
Expected: Both backend and frontend start successfully

- [ ] **Step 2: Create a project with a valid path**

Open http://localhost:5173, create a project with a real directory path (e.g., `C:\Users\jacob\Desktop\manager_ai`).

- [ ] **Step 3: Create a task in the project**

Create a new task with any description.

- [ ] **Step 4: Open terminal from TaskDetailPage**

Navigate to the task detail page, click "Open Terminal". Verify:
- Split view appears (details left, terminal right)
- Terminal shows a cmd.exe prompt in the project directory
- You can type commands and see output

- [ ] **Step 5: Navigate away and back**

Navigate to the project page, then back to the task. Verify:
- Terminal reconnects automatically
- Green dot shows in task list

- [ ] **Step 6: Check dashboard**

Navigate to /terminals. Verify:
- Terminal appears in the list
- "Go to Task" navigates correctly
- "Kill" kills the terminal

- [ ] **Step 7: Test soft limit warning**

Open 5+ terminals. Verify the warning modal appears on the 6th.

- [ ] **Step 8: Commit any fixes if needed**

```bash
git add -A
git commit -m "fix(terminal): end-to-end testing fixes"
```
