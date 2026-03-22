# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Manager AI is a full-stack web application for AI-powered project management with Claude Code integration. It provides issue tracking, terminal emulation, real-time event notifications, and an MCP server that exposes tools to Claude Code.

## Commands

### Development

```bash
python start.py          # Start full stack (backend + frontend, handles venv/deps/migrations)
```

Backend only:
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend only:
```bash
cd frontend
npm run dev
```

### Testing

```bash
cd backend
python -m pytest                           # Run all tests
python -m pytest tests/test_routers_issues.py  # Run a single test file
python -m pytest tests/test_routers_issues.py::test_create_issue -v  # Single test
```

Tests use async in-memory SQLite with `asyncio_mode = "auto"` (pyproject.toml). Vector columns are stripped from the schema during test table creation since SQLite can't handle them.

### Database Migrations

```bash
cd backend
python -m alembic upgrade head             # Apply migrations
python -m alembic revision --autogenerate -m "description"  # Create migration
```

### Linting

```bash
cd frontend
npm run lint    # ESLint
```

## Architecture

### Backend (Python/FastAPI)

- **Entry point:** `backend/app/main.py` — FastAPI app with lifespan, router registration, MCP mount at `/mcp`
- **Routers** (`app/routers/`) — REST endpoints per domain (projects, issues, tasks, terminals, files, events)
- **Services** (`app/services/`) — Business logic layer, instantiated with AsyncSession
- **Models** (`app/models/`) — SQLAlchemy async ORM (SQLite + aiosqlite). Core: Project, Issue, Task, ProjectFile, Setting, TerminalCommand
- **Schemas** (`app/schemas/`) — Pydantic v2 request/response validation

### Frontend (React/Vite)

- **Entry:** `frontend/src/main.jsx` → `App.jsx` (React Router)
- **Pages** (`src/pages/`) — Route components
- **API layer** (`src/api/`) — REST client functions
- **Context** (`src/context/`) — EventProvider for WebSocket-based real-time events
- Vite proxies `/api` requests to the backend

### Key Subsystems

**Hook System** (`app/hooks/`): Event-driven hooks fire on issue state transitions. `HookRegistry` manages registration; `ClaudeCodeExecutor` spawns `claude` CLI. Hooks execute asynchronously via `asyncio.create_task`.

**MCP Server** (`app/mcp/server.py`): FastMCP server exposing tools (get/update issue status, create specs/plans, project context) to Claude Code. Mounted at `/mcp` on the FastAPI app.

**Terminal Service** (`app/services/terminal_service.py`): Manages PTY instances via pywinpty. WebSocket streaming. Supports dynamic variable resolution (`$issue_id`, `$project_id`) and injects `MANAGER_AI_*` environment variables.

**Issue Lifecycle**: `IssueStatus` enum with valid transitions defined in `VALID_TRANSITIONS`. States: NEW → REASONING → PLANNED → ACCEPTED/DECLINED → FINISHED.

### Data

- SQLite database and LanceDB vectors stored in `data/`
- Config via `.env` file (see `.env.example`)
- `manager.json` holds project ID configuration
