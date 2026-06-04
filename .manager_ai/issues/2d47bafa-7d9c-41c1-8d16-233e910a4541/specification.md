## Bug: Pipeline first-run race condition

### Problem
When `start()` creates a pipeline run and spawns `_execute()` as background task, `_execute()` sometimes can't find the run record with `NotFoundError: Pipeline run not found: <id>`. Canceling the failed run and retrying works.

### Root Cause
`_execute()` creates a **new SQLAlchemy async session** via `self.session_factory()` (passed as `async_session` in production). With SQLite + aiosqlite + NullPool, each session opens an independent connection. Although `start()` calls `await self.session.commit()` before `asyncio.create_task(self._execute(...))`, the new session's connection sometimes doesn't see the just-committed data due to SQLite WAL visibility timing with concurrent async connections.

### Fix
In `_execute()`, before raising `NotFoundError` from `_get_run_with_session()`, retry the lookup with short sleep intervals:

- Sleep 200ms, retry
- Sleep 500ms, retry  
- Sleep 1000ms, retry
→ If all 3 fail, raise `NotFoundError` as before

This handles the transient WAL visibility edge case without architectural refactoring. The retry is limited to the **initial run lookup only** — not step execution.

### Files Affected
- `backend/app/services/pipeline_run_service.py` — add retry logic in `_execute()` or `_get_run_with_session()`
