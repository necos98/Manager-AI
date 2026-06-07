# Implementation Plan: Replace threading.Lock with asyncio.Lock in TerminalService

## Summary

Replace `threading.Lock` with `asyncio.Lock` in `TerminalService.__init__()` and convert all 10 lock-using methods from sync to async. Update ~31 caller sites across 5 files. Rewrite the `threading.Thread`-based concurrent test with `asyncio` tasks.

All lock accesses are single-thread (event loop thread), making `asyncio.Lock` safe. No new `ThreadPoolExecutor` or background threads call these methods.

---

## Step 1: `terminal_service.py` — Core lock replacement

**File:** `backend/app/services/terminal_service.py`

### 1a. Imports
- Remove `import threading` (line 8) — no longer needed after Lock removal.

### 1b. `__init__` (line 105-109)
- Change `self._lock = threading.Lock()` to `self._lock = asyncio.Lock()`.
  - `asyncio` is already imported as `asyncio_mod` (line 3), use `asyncio_mod.Lock()`.

### 1c. Convert 10 sync methods to async

| # | Method | Line | Current sig | New sig | Change |
|---|--------|------|-------------|---------|--------|
| 1 | `create()` | 111 | `def create(...)` | `async def create(...)` | `with self._lock:` → `async with self._lock:` |
| 2 | `create_log()` | 168 | already `async def` | unchanged | `with self._lock:` → `async with self._lock:` |
| 3 | `push_output()` | 197 | already `async def` | unchanged | `with self._lock:` → `async with self._lock:` |
| 4 | `destroy_log()` | 203 | already `async def` | unchanged | `with self._lock:` → `async with self._lock:` |
| 5 | `append_output()` | 238 | `def append_output(...)` | `async def append_output(...)` | `with self._lock:` → `async with self._lock:` |
| 6 | `get_buffered_output()` | 250 | `def get_buffered(...)` | `async def get_buffered(...)` | `with self._lock:` → `async with self._lock:` |
| 7 | `kill()` | 258 | `def kill(...)` | `async def kill(...)` | `with self._lock:` → `async with self._lock:` |
| 8 | `mark_closed()` | 272 | `def mark_closed(...)` | `async def mark_closed(...)` | `with self._lock:` → `async with self._lock:` |
| 9 | `is_alive()` | 286 | `def is_alive(...)` | `async def is_alive(...)` | `with self._lock:` → `async with self._lock:` |
| 10 | `resize()` | 291 | `def resize(...)` | `async def resize(...)` | `with self._lock:` → `async with self._lock:` |

### 1d. Add public `get_log_queue()` helper

The `_terminal_reader()` in `terminal_session.py` currently accesses `service._queues` directly under `service._lock`. After making the lock async, this direct access breaks encapsulation and the threading context.

Add a public async method:
```python
async def get_log_queue(self, terminal_id: str) -> asyncio_mod.Queue | None:
    """Return the log queue for a log-mode terminal, or None."""
    async with self._lock:
        return self._queues.get(terminal_id)
```

---

## Step 2: `terminal_session.py` — Replace private member access + add awaits

**File:** `backend/app/services/terminal_session.py`

### 2a. `_terminal_reader()` line 99-100 — existence check

Replace:
```python
with service._lock:
    entry = service._terminals.get(terminal_id)
if entry is None:
    return
```

With:
```python
try:
    entry_response = service.get(terminal_id)  # get() stays sync — no lock used
except KeyError:
    return
is_log = entry_response.get("mode") == "log"
```

### 2b. `_terminal_reader()` line 108-109 — log queue access

Replace:
```python
with service._lock:
    q = service._queues.get(terminal_id)
```

With:
```python
q = await service.get_log_queue(terminal_id)
```

### 2c. `_terminal_reader()` internal async calls — add await

The following calls inside `_terminal_reader()` target methods that become async in Step 1. Prepend `await`:

- Line 116: `buf = service.get_buffered_output(terminal_id)` → `buf = await service.get_buffered_output(terminal_id)`
- Line 118: `service.mark_closed(terminal_id)` → `await service.mark_closed(terminal_id)`
- Line 122: `service.append_output(terminal_id, data)` → `await service.append_output(terminal_id, data)`
- Line 140: `buf = service.get_buffered_output(terminal_id)` → `buf = await service.get_buffered_output(terminal_id)`
- Line 142: `service.mark_closed(terminal_id)` → `await service.mark_closed(terminal_id)`
- Line 146: `service.append_output(terminal_id, data)` → `await service.append_output(terminal_id, data)`

These are all inside `async def _terminal_reader()` — no function signature change needed, only `await` additions.

---

## Step 3: `terminals.py` — Add await to callers

**File:** `backend/app/routers/terminals.py`

### 3a. `_teardown_terminal()` (lines 35-52)
- L38: `service.get_buffered_output(...)` → `await service.get_buffered_output(...)`
- L50: `service.kill(...)` → `await service.kill(...)`

### 3b. `create_terminal()` (lines 92-230)
- L112: `service.create(...)` → `await service.create(...)`

### 3c. `create_ask_terminal()` (lines 233-339)
- L258: `service.create(...)` → `await service.create(...)`

### 3d. `create_manage_agent_terminal()` (lines 342-420)
- L361: `service.create(...)` → `await service.create(...)`

### 3e. `/log` endpoint (lines 423-443)
- L434: `await service.create_log(...)` — already awaited, no change needed

### 3f. `get_terminal_recording()` (lines 517-544)
- L529: `service.get_buffered_output(...)` → `await service.get_buffered_output(...)`

### 3g. `delete_terminal()` (lines 547-562)
- L552: `service.get_buffered_output(...)` → `await service.get_buffered_output(...)`
- L562: `service.kill(...)` → `await service.kill(...)`

### 3h. `terminal_ws()` (lines 565-633)
- L581: `service.get_buffered_output(...)` → `await service.get_buffered_output(...)`
- L612: `service.resize(...)` → `await service.resize(...)`

---

## Step 4: `projects.py` — Add await to callers

**File:** `backend/app/routers/projects.py`

### 4a. `delete_project()` (lines 349-363)
- L359: `terminal_service.kill(...)` → `await terminal_service.kill(...)`

### 4b. `install_mcp()` (lines 435-490)
- L450: `terminal_service.create(...)` → `await terminal_service.create(...)`

### 4c. `install_playwright_mcp()` (lines 493-538)
- L507: `terminal_service.create(...)` → `await terminal_service.create(...)`

---

## Step 5: `pipeline_run_service.py` — Add await to callers

**File:** `backend/app/services/pipeline_run_service.py`

### 5a. `_setup_step_environment()` (lines 387-459)
- L421: `terminal_service.create(...)` → `await terminal_service.create(...)`

### 5b. `_cleanup_step()` (lines 496-500)
- L497: `terminal_service.get_buffered_output(...)` → `await terminal_service.get_buffered_output(...)`
- L500: `terminal_service.kill(...)` → `await terminal_service.kill(...)`

### 5c. `_run_step()` (lines 546-608)
- L601: `terminal_service.kill(...)` → `await terminal_service.kill(...)`

---

## Step 6: `test_terminal_service.py` — Async test conversion

**File:** `backend/tests/test_terminal_service.py`

### 6a. Convert fixture to async generator

```python
@pytest.fixture
async def service():
    svc = TerminalService()
    yield svc
    for tid in list(svc._terminals.keys()):
        try:
            await svc.kill(tid)
        except Exception:
            pass
```

### 6b. Convert all test methods that call async methods to `async def`

Tests that call `create()`, `kill()`, `resize()`, `is_alive()`, `append_output()`, or `get_buffered_output()` must become `async def` with `await` on each async call.

Tests that only call sync methods (`list_active`, `get`, `active_count`, `cleanup`):
- `test_list_empty` — stays sync (only calls `list_active()`)
- `test_get_nonexistent_raises` — stays sync (only calls `get()`)
- `test_cleanup_is_noop_terminal_persists` — calls `create()` → needs `await`, rest stays
- `test_cleanup_is_idempotent` — calls `create()` → needs `await`

All other test methods need full async conversion.

### 6c. Rewrite concurrent test (line 214-249)

Replace `threading.Thread` with `asyncio` tasks:

```python
async def test_resize_concurrent_with_kill_does_not_crash(self, service):
    """resize() inside async lock prevents races with concurrent kill."""
    with patch("app.services.terminal_service.PTY") as MockPTY:
        mock_pty = MagicMock()
        mock_pty.spawn = MagicMock()
        mock_pty.set_size = MagicMock()
        MockPTY.return_value = mock_pty

        term = await service.create(issue_id="t1", project_id="p1", project_path="C:/a")
        errors = []

        async def do_resize():
            try:
                await service.resize(term["id"], 100, 25)
            except KeyError:
                pass
            except Exception as exc:
                errors.append(exc)

        async def do_kill():
            try:
                await service.kill(term["id"])
            except KeyError:
                pass

        task1 = asyncio.create_task(do_resize())
        task2 = asyncio.create_task(do_kill())
        await asyncio.gather(task1, task2)

        assert errors == [], f"Unexpected exceptions: {errors}"
```

---

## Step 7: Verify `import threading` removal

- After changes, confirm no other code in `terminal_service.py` uses `threading`.
- The file imports `threading` ONLY for `threading.Lock()` (line 8, used at line 109).
- After replacement with `asyncio_mod.Lock()`, completely remove `import threading`.

---

## Caller summary — all await changes

| File | Method/Location | Call | Change |
|------|----------------|------|--------|
| terminal_service.py | create() → async | — | sig change |
| terminal_service.py | append_output() → async | — | sig change |
| terminal_service.py | get_buffered_output() → async | — | sig change |
| terminal_service.py | kill() → async | — | sig change |
| terminal_service.py | mark_closed() → async | — | sig change |
| terminal_service.py | is_alive() → async | — | sig change |
| terminal_service.py | resize() → async | — | sig change |
| terminal_session.py | _terminal_reader() L99 | service._lock + _terminals | → is_alive() + get() |
| terminal_session.py | _terminal_reader() L108 | service._lock + _queues | → get_log_queue() |
| terminal_session.py | _terminal_reader() L116 | get_buffered_output | +1 await |
| terminal_session.py | _terminal_reader() L118 | mark_closed | +1 await |
| terminal_session.py | _terminal_reader() L122 | append_output | +1 await |
| terminal_session.py | _terminal_reader() L140 | get_buffered_output | +1 await |
| terminal_session.py | _terminal_reader() L142 | mark_closed | +1 await |
| terminal_session.py | _terminal_reader() L146 | append_output | +1 await |
| terminals.py | _teardown_terminal() | get_buffered_output, kill | +2 await |
| terminals.py | create_terminal() | service.create | +1 await |
| terminals.py | create_ask_terminal() | service.create | +1 await |
| terminals.py | create_manage_agent_terminal() | service.create | +1 await |
| terminals.py | get_terminal_recording() | get_buffered_output | +1 await |
| terminals.py | delete_terminal() | get_buffered_output, kill | +2 await |
| terminals.py | terminal_ws() | get_buffered_output, resize | +2 await |
| projects.py | delete_project() | kill | +1 await |
| projects.py | install_mcp() | create | +1 await |
| projects.py | install_playwright_mcp() | create | +1 await |
| pipeline_run_service.py | _setup_step_environment() | create | +1 await |
| pipeline_run_service.py | _cleanup_step() | get_buffered_output, kill | +2 await |
| pipeline_run_service.py | _run_step() timeout | kill | +1 await |

**Total signature changes:** 7 methods (sync → async) + 3 methods (already async, signature unchanged)
**Total caller await additions:** ~28 await keywords across 5 files
**Total test method conversions:** ~17 test methods + fixture

---

## Architectural notes

1. **`asyncio.Lock` is not thread-safe** — all callers run on the event loop thread. PTY reads use `run_in_executor(_pty_executor, ...)` but these never touch the lock or shared dicts — they operate on the PTY file descriptor only, and `append_output()` is called from the async reader task, not the executor thread itself. The `_pty_executor` thread pool exists solely for blocking PTY reads and never enters any lock-using code path.

2. **`service.get()`, `service.get_pty()`, `service.list_active()`, `service.active_count()`** access `_terminals` dict without any lock. This is a pre-existing race condition (reading from a dict while async tasks write to it from the same thread). These remain sync and unchanged. This race existed before and is unchanged by this refactor.

3. **`PTY.write()`** is called from async handlers and is not wrapped in `run_in_executor`. This is accepted as an acceptable trade-off per spec non-goals.

4. **`_terminal_reader()`** accesses `_sessions` (module-level dict) without any lock — this is fine since it's only accessed from the event loop thread and is not protected by the service lock.
