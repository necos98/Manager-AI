# Architecture — Backend

**Part:** backend
**Project Type:** Python/FastAPI
**Generated:** 2026-06-07

## Executive Summary

FastAPI-based backend providing REST API, WebSocket real-time events, MCP server for Claude Code integration, and terminal emulation. Uses SQLite + aiosqlite for persistence with Alembic migrations.

## Technology Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Runtime | Python | ≥3.12, <3.15 |
| Framework | FastAPI | 0.115.12 |
| Server | Uvicorn | 0.34.2 |
| ORM | SQLAlchemy 2.0+ (async) | ≥2.0.40 |
| Database | SQLite + aiosqlite | 0.21.0 |
| Migrations | Alembic | 1.15.2 |
| Validation | Pydantic v2 | ≥2.11.0 |
| MCP | FastMCP | 1.9.2 |
| Testing | pytest + pytest-asyncio | 8.3.5 / 0.25.3 |

## Architecture Pattern: Layered

```
Request → Router → Schema → Service → Model → Database
           ↑         ↑         ↑         ↑
         HTTP      Validate  Business   ORM
         routing   I/O       logic
```

### Layer Responsibilities

1. **Routers** (`app/routers/`): HTTP routing, dependency injection (AsyncSession via `get_db()`), response formatting via `schema.from_record()`
2. **Schemas** (`app/schemas/`): Pydantic v2 request validation (`model_validate()`) and response serialization (`model_dump()`)
3. **Services** (`app/services/`): Business logic, instantiated per-request with `AsyncSession`. **No commits here** — commit happens at router level
4. **Models** (`app/models/`): SQLAlchemy ORM with `Mapped` annotations, `mapped_column`, relationship definitions
5. **Database** (`app/database.py`): `AsyncSession` factory, `NullPool` + `check_same_thread=False` for aiosqlite

## Key Subsystems

### Hook System (`app/hooks/`)
- Event-driven hooks on issue state transitions
- `HookRegistry` manages registration
- `ClaudeCodeExecutor` spawns `claude -p` subprocess
- Executes async via `asyncio.create_task`

### MCP Server (`app/mcp/server.py`)
- FastMCP tools: get/update issue status, create specs/plans, project context
- Mounted via `streamable_http_app()` at `/mcp`
- Uses `_noop_lifespan` to prevent session manager conflicts

### Terminal Service (`app/services/terminal_service.py`)
- PTY management via pywinpty (Windows) / built-in pty (Linux)
- WebSocket I/O streaming
- Dynamic variable resolution (`$issue_id`, `$project_id`)
- WSL support with path translation

### Storage Layer (`app/storage/`)
- File-backed storage for issues, memories, project files
- `.manager_ai/` directory per project
- WriteQueue + BackgroundWriter for async I/O
- LanceDB for vector embeddings

## Data Architecture

- **Database:** 24 SQLAlchemy tables (see data-models-backend.md)
- **File storage:** `.manager_ai/` directory per project
- **Vector store:** LanceDB (separate from SQLite)
- **Constraints:** Single-process writes only (`uvicorn --workers 1`)

## API Design

- **REST API:** CRUD endpoints organized by domain (see api-contracts-backend.md)
- **WebSocket:** Real-time event streaming at `/api/events/ws`
- **Terminal WS:** PTY I/O at `/api/terminals/{id}/ws`

## Error Handling

- `AppError` base exception with `status_code` + `message`
- Centralized handler in `main.py`
- Client disconnect suppression for MCP StreamableHTTP

## Development

See development-guide-backend.md for setup and testing.
