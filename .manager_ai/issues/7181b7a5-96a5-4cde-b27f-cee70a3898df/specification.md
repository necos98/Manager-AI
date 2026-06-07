## Specification: Replace threading.Lock with asyncio.Lock in TerminalService

### Scope

Replace the single `threading.Lock` in `TerminalService` with `asyncio.Lock` and convert all lock-using sync methods to async, ensuring no blocking calls run on the event loop. Update all callers across the codebase to use `await` on the newly-async methods.

### Background

`TerminalService.__init__` creates `self._lock = threading.Lock()`. This lock protects shared dicts (`_terminals`, `_buffers`, `_queues`) accessed by both sync methods and async methods. Three methods (`create_log`, `push_output`, `destroy_log`) are already `async def` but use blocking `with self._lock:` — a correctness anti-pattern that can stall the event loop if the lock is ever contended. All other lock-using methods are sync but called exclusively from async contexts (event loop thread), meaning the lock serializes coroutines without ever yielding the event loop.

The codebase already uses `asyncio.Lock` in `pipeline_task_manager.py` and `plugin_client.py`, so the pattern is well-understood.

### Files to Modify

1. **`backend/app/services/terminal_service.py`** — Core change: replace `threading.Lock` with `asyncio.Lock`, convert all sync lock-using methods to async, update `import threading` to `from asyncio import Lock` (or similar).
2. **`backend/app/services/terminal_session.py`** — `_terminal_reader()` accesses `service._lock` and `service._terminals` directly (lines 99, 108). Must be updated to use public async methods instead.
3. **`backend/app/routers/terminals.py`** — All callers of newly-async methods need `await` prepended.
4. **`backend/app/routers/projects.py`** — Same: any caller of newly-async methods.
5. **`backend/app/services/pipeline_run_service.py`** — Same.
6. **`backend/tests/test_terminal_service.py`** — All tests calling newly-async methods need `await`. The concurrent resize+kill test (line 214) uses `threading.Thread` — must be rewritten with `asyncio` tasks.

### Affected Methods in TerminalService

These use `self._lock` and must become async:

| Method | Line | Currently | Change |
|--------|------|-----------|--------|
| `create()` | 111 | sync, `with self._lock:` | `async def`, `async with self._lock:` |
| `create_log()` | 168 | `async def`, `with` | Change to `async with` |
| `push_output()` | 197 | `async def`, `with` | Change to `async with` |
| `destroy_log()` | 203 | `async def`, `with` | Change to `async with` |
| `append_output()` | 238 | sync, `with self._lock:` | `async def`, `async with` |
| `get_buffered_output()` | 250 | sync, `with self._lock:` | `async def`, `async with` |
| `kill()` | 258 | sync, `with self._lock:` | `async def`, `async with` |
| `mark_closed()` | 272 | sync, `with self._lock:` | `async def`, `async with` |
| `is_alive()` | 286 | sync, `with self._lock:` | `async def`, `async with` |
| `resize()` | 291 | sync, `with self._lock:` | `async def`, `async with` |

Methods that do NOT use `self._lock` (e.g. `get()`, `get_pty()`, `list_active()`, `active_count()`, `cleanup()`) remain sync.

### Constraints

1. **All lock accesses single-thread** — `asyncio.Lock` is **not** thread-safe. All callers currently execute in the event loop thread. This must remain true after the change. No new `ThreadPoolExecutor` or background thread should call these methods.
2. **No behavior change** — Lock granularity stays identical. Only the locking primitive and method signatures change.
3. **`PTY.write()` remains sync** — It's called from async handlers and may block on winpty writes. Fixing this is **out of scope** (noted as acceptable trade-off by analysis).
4. **Backward compatible** — All existing functionality must work identically. No API contract changes beyond sync→async.

### Acceptance Criteria

1. All 10 lock-using methods in `TerminalService` use `async with self._lock:` (not `with`).
2. `terminal_session.py` no longer accesses `service._lock` or `service._terminals` directly — uses public methods only.
3. All callers (routers, services) have `await` prepended for all calls to newly-async methods.
4. All existing tests pass with minimal structural changes (async test functions, `await` for async calls).
5. The concurrent resize+kill test uses `asyncio` tasks instead of `threading.Thread`.
6. No new `threading` imports remain in `terminal_service.py` (remove import if no longer needed).
7. No deadlocks under normal operation: `asyncio.Lock` must never be awaited from a sync context.

### Non-Goals

- NOT converting `PTY.write()` to async (blocking write acceptable).
- NOT changing lock granularity or splitting into multiple locks.
- NOT adding new tests for async lock behavior (existing test coverage sufficient).
- NOT refactoring terminal_service.py beyond the lock change.
- NOT touching non-lock-using methods (`get`, `get_pty`, `list_active`, `active_count`, `cleanup`).
- NOT changing the test fixture or project-level configuration.
