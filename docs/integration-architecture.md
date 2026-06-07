# Integration Architecture

**Generated:** 2026-06-07

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   Claude Code CLI                            │
│         (via MCP tools at /mcp + claude CLI hooks)           │
└──────────┬──────────────────────────────┬────────────────────┘
           │ MCP (StreamableHTTP)         │ Hook execution
           ▼                              ▼
┌──────────────────────┐     ┌──────────────────────┐
│   Backend (FastAPI)  │◄───►│  Frontend (React)    │
│   localhost:8000     │     │  localhost:5173      │
│                      │     │                      │
│   REST API ──────────┼─────┼──► fetch wrapper     │
│   WebSocket ─────────┼─────┼──► EventProvider     │
│   Terminal WS ───────┼─────┼──► Xterm.js          │
│   MCP /mcp ──────────┤     │                      │
└──────────────────────┘     └──────────────────────┘
```

## Integration Points

### 1. REST API (frontend → backend)

- **Protocol:** HTTP/1.1 via Vite proxy
- **Transport:** Fetch API (custom `client.ts` wrapper)
- **Base:** Frontend `/api/*` → Vite proxy → Backend `localhost:8000/api/*`
- **Auth:** None built-in (CORS restricted to `localhost:5173`)
- **Data format:** JSON (request/response via Pydantic schemas)

### 2. Real-time Events (bidirectional)

- **Protocol:** WebSocket
- **Endpoint:** `WS /api/events/ws`
- **Frontend:** EventProvider context (`src/shared/context/event-context.tsx`)
- **Backend:** Event dispatch system
- **Purpose:** Live UI updates on data changes (issues, terminals, pipeline runs)

### 3. Terminal I/O (bidirectional)

- **Protocol:** WebSocket
- **Endpoint:** `WS /api/terminals/{terminal_id}/ws`
- **Frontend:** Xterm.js with addons (fit, search, web-links)
- **Backend:** PTY process managed by pywinpty (Windows) or built-in pty (Linux)
- **Purpose:** Interactive shell sessions in browser

### 4. MCP Server (Claude Code → Backend)

- **Protocol:** StreamableHTTP (SSE)
- **Endpoint:** `POST /mcp` (mounted on FastAPI app)
- **Tools exposed:** get_issue_status, update_issue_status, create_spec, create_plan, get_project_context, etc.
- **Purpose:** Allow Claude Code to interact with issues, specs, plans

### 5. Hook System (Backend → Claude Code)

- **Trigger:** Issue state transitions (NEW → REASONING → PLANNED → ACCEPTED → FINISHED)
- **Executor:** `ClaudeCodeExecutor` spawns `claude -p` subprocess
- **Execution:** Async via `asyncio.create_task`
- **Purpose:** Automated issue processing pipeline

### 6. WSL Bridge (Backend → WSL)

- **Condition:** When `project.shell == "wsl.exe"`
- **Function:** Path translation via `win_to_wsl_path()`, bash `export` for env vars
- **Network:** `MANAGER_AI_BASE_URL` resolved via `ip route show default`
- **Purpose:** Run Linux commands from Windows UI

## Shared Dependencies

| Component | Used By | Purpose |
|-----------|---------|---------|
| SQLite DB | Backend | Primary data store |
| LanceDB | Backend | Vector embeddings for memories/files |
| File system (.manager_ai/) | Backend | File-backed storage per project |
| Environment variables | Both | Config via `.env` |

## Data Flow: Issue Lifecycle

```
User creates issue (frontend)
  → POST /api/projects/{id}/issues (REST)
  → Service layer creates DB record
  → Event dispatched via WebSocket
  → Frontend updates UI
  → Hook system detects new issue
  → Spawns claude CLI via HookExecutor
  → Claude processes issue (MCP tools for updates)
  → Status transitions via PATCH /api/issues/{id}/status
  → Real-time UI updates via WebSocket
```
