# Web Terminals — Design Spec

Spawn interactive terminals from the web UI, one per task, with split-view layout and persistent background processes.

## Requirements

- Terminal associated to a specific task, opens in the project directory
- User starts claude manually (no auto-prompting)
- Split view in TaskDetailPage: task details left (40%), terminal right (60%), draggable divider
- Project page: green dot indicator + badge on tasks with active terminals, count in header
- Dashboard page (`/terminals`): minimal list of active terminals (task name, project, time, Go to Task / Kill buttons)
- Navbar: "Terminals" link with active count badge
- Processes persist in background when navigating away, reconnect automatically on return
- Soft limit on concurrent terminals, configurable (default: 5), shows warning with "Open Anyway" / "Cancel"
- One terminal per task — reopening connects to existing session, no duplicates

## Architecture

### Approach: Python pure (pywinpty + FastAPI WebSocket)

Everything in the existing FastAPI backend. No Node.js sidecar.

- `pywinpty` spawns PTY processes on Windows (ConPTY)
- FastAPI WebSocket endpoint bridges browser ↔ PTY
- `xterm.js` in the frontend renders the terminal
- Raw byte passthrough — no interpretation of escape sequences

### Backend Components

```
backend/app/
├── services/
│   └── terminal_service.py    # Lifecycle management, in-memory registry
├── routers/
│   └── terminals.py           # REST + WebSocket endpoints
```

No database model — terminals are in-memory only (they don't survive server restart, which is correct behavior).

#### Terminal Registry (in-memory dict)

```python
{
    "term-uuid": {
        "id": "term-uuid",
        "task_id": "task-uuid",
        "project_id": "project-uuid",
        "project_path": "/path/to/project",
        "pty_process": <pywinpty.PTY>,
        "status": "active",        # active | closed
        "created_at": datetime,
        "cols": 120,
        "rows": 30
    }
}
```

#### REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/terminals` | Create terminal (task_id, project_id) → spawns PTY |
| `GET` | `/api/terminals` | List active terminals (optional `?project_id=X` or `?task_id=X` filter) |
| `DELETE` | `/api/terminals/{id}` | Kill terminal process, remove from registry |

#### WebSocket Endpoint

| Method | Path | Purpose |
|--------|------|---------|
| `WS` | `/api/terminals/{id}/ws` | Bidirectional I/O bridge |

WebSocket message protocol:
- **Text from browser → PTY stdin**: raw keystrokes
- **Text from PTY stdout → browser**: raw output (ANSI escape sequences preserved)
- **Resize message**: `{"type": "resize", "cols": 120, "rows": 30}` → PTY resize

Asyncio loop with two concurrent tasks:
1. PTY → WS: read output, send to browser
2. WS → PTY: receive input, write to PTY

#### Configuration

`terminal_soft_limit` stored in existing `settings` table (default: 5).

### Frontend Components

**New dependencies:** `xterm`, `@xterm/addon-fit`, `@xterm/addon-web-links`

**New components:**
- `TerminalPanel.jsx` — wraps xterm.js, manages WebSocket connection, handles resize

**Modified pages:**
- `TaskDetailPage.jsx` — add "Open Terminal" button, split view layout when terminal is active
- `ProjectDetailPage.jsx` — green dot + badge on tasks with active terminals, count in header
- `App.jsx` — add `/terminals` route
- Navbar — add "Terminals" link with badge count

**New pages:**
- `TerminalsPage.jsx` — dashboard listing active terminals

**New API client methods:**
- `createTerminal(taskId, projectId)`
- `listTerminals(filters?)`
- `killTerminal(terminalId)`

## Lifecycle

### Open Terminal
1. User clicks "Open Terminal" on TaskDetailPage
2. Frontend: `POST /api/terminals` with task_id, project_id
3. Backend: check soft limit (warn if exceeded), spawn PTY with `cwd=project_path`
4. Return `{id, task_id, status: "active"}`
5. Frontend: open WebSocket to `/api/terminals/{id}/ws`, attach xterm.js

### Navigate Away
1. WebSocket closes
2. PTY stays alive in memory
3. Registry marks: no client connected

### Return to Task
1. Frontend: `GET /api/terminals?task_id=X` → finds existing terminal
2. Reopen WebSocket → reconnect to existing PTY
3. xterm.js resumes (output during disconnection is lost in v1)

### Close Terminal
1. User clicks "Close Terminal" → confirmation dialog
2. `DELETE /api/terminals/{id}`
3. Backend: kill PTY process, remove from registry
4. Frontend: close xterm.js, return to full-width layout

### Process Dies (user types `exit`)
1. PTY read loop detects EOF
2. Backend updates status to "closed", removes from registry
3. Frontend: WebSocket closes, shows "Terminal session ended" message

### Server Restart
1. All PTY processes die (child processes of server)
2. Registry recreated empty
3. Frontend handles gracefully: "Terminal session ended"

## Error Handling

- PTY spawn fails → HTTP 500 with clear message
- WebSocket drops → frontend auto-retry with exponential backoff (1s, 2s, 4s)
- Project path doesn't exist → HTTP 400 at POST time
- Soft limit reached → HTTP 200 with `warning: true`, frontend shows warning modal

## Future Enhancements (not in v1)

- Circular buffer for output replay on reconnect
- Pre-configured claude prompts per task
- Terminal session recording/playback
