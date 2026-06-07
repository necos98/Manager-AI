# Development Guide — Backend

**Part:** backend
**Generated:** 2026-06-07

## Prerequisites

- Python ≥3.12, <3.15
- Virtual environment (auto-managed by start.py)

## Setup

```bash
# Full stack (auto venv + deps + migrations)
python start.py

# Backend only
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Dependencies

Managed via `backend/requirements.txt`:
```bash
pip install -r requirements.txt
```

## Database Migrations

```bash
cd backend
python -m alembic upgrade head              # Apply migrations
python -m alembic revision --autogenerate -m "description"  # Create migration
```

## Testing

```bash
cd backend
python -m pytest                            # Run all tests
python -m pytest tests/test_file.py -v      # Single test file
python -m pytest tests/test_file.py::test_func -v  # Single test
```

**Note:** Tests use async in-memory SQLite with `asyncio_mode = "auto"`. Vector columns stripped from schema during test table creation (SQLite can't handle them).

## Environment

- `.env` at project root for config
- `manager.json` for project ID
- `data/secret.key` auto-generated for Fernet encryption

## Important Constraints

- **Single-process only:** `uvicorn --workers 1` (aiosqlite serializes writes)
- **Windows-first:** pywinpty for PTY terminals. Linux uses built-in pty module.
- **MCP version pinned:** `mcp==1.9.2` — do not upgrade without thorough testing
