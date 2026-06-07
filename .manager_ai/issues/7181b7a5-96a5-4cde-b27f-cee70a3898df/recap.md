## Recap: Replace threading.Lock with asyncio.Lock in TerminalService

### Changes Made

**`backend/app/services/terminal_service.py`** — Core lock replacement:
- Removed `import threading` (no longer needed)
- Changed `self._lock = threading.Lock()` → `self._lock = asyncio_mod.Lock()`
- Converted 7 sync methods to async: `create()`, `append_output()`, `get_buffered_output()`, `kill()`, `mark_closed()`, `is_alive()`, `resize()`
- Changed `with self._lock:` → `async with self._lock:` in all 10 lock-using methods (including 3 already-async: `create_log`, `push_output`, `destroy_log`)
- Added public `async def get_log_queue()` helper so `terminal_session.py` doesn't access `_queues` directly under lock

**`backend/app/services/terminal_session.py`** — Private member access eliminated:
- Replaced `with service._lock: entry = service._terminals.get(terminal_id)` with `try/except KeyError` using public `service.get()`
- Replaced `with service._lock: q = service._queues.get(terminal_id)` with `await service.get_log_queue(terminal_id)`
- Added `await` on 6 async method calls

**`backend/app/routers/terminals.py`** — ~12 await additions across 7 endpoints
**`backend/app/routers/projects.py`** — 3 await additions (kill, create ×2)
**`backend/app/services/pipeline_run_service.py`** — 3 await additions (create, get_buffered_output, kill)

**`backend/tests/test_terminal_service.py`** — Full async conversion:
- Async generator fixture with `await svc.kill(tid)` in cleanup
- All test methods converted to `async def`
- Concurrent test rewritten from `threading.Thread` to `asyncio.create_task` + `asyncio.gather`
- Fixed `test_kill_nonexistent` → `test_kill_nonexistent_is_noop` (method used `.pop(None)`, never raised)

### Verification
- All 20 tests pass
- Non-lock-using methods remain sync (pre-existing race unchanged per non-goals)
- `PTY.write()` remains sync in event loop — accepted trade-off
- `asyncio.Lock` is safe: all lock access is event-loop-thread only