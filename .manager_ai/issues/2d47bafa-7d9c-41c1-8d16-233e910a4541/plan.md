## Pipeline first-run race condition — Implementation Plan

**Goal:** Fix `_execute()` sometimes failing with `NotFoundError` on first pipeline run due to SQLite WAL visibility race with new sessions.

**Architecture:** Add retry loop with exponential delay in `_execute()` before raising NotFoundError on initial run lookup. Minimal change, no structural refactor.

**Files Modified:**
- `backend/app/services/pipeline_run_service.py` — retry in `_execute()` around `_get_run_with_session()` call

**Tech Stack:** Python/FastAPI, SQLAlchemy async, aiosqlite
