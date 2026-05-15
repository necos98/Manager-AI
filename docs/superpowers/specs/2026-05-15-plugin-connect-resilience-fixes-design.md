# Plugin Connect Resilience — Fixes for issues found in self-review

Date: 2026-05-15
Status: approved
Parent issue: `21b7f956-cdac-4265-9c98-32a0929c5b6a`

## Context

The initial fix for `ClosedResourceError` on slow plugin startup added three-layer
defense: coordinated pre-connect, time-bounded connection, and graceful error
handling. A critical self-review found five remaining issues that need fixing.

## Changes

### Fix 1: `BaseException` → `Exception` in pre-connect tasks

**Files:** `backend/app/mcp/plugin_manager.py` (x2 — `_start_one` and `restart_plugin`)

The `_pre_connect()` closures catch `BaseException`, which includes
`asyncio.CancelledError`. When the task is cancelled, the exception is swallowed,
the task shows as `done()` instead of `cancelled()`, and the connection attempt
continues in background.

Change `except BaseException` to `except Exception` so `CancelledError` propagates
and the task is properly cancelled.

### Fix 2: `_connect_done` event — wake waiters on failure too

**Files:** `backend/app/mcp/plugin_client.py`

`ensure_connected()` waits on `_connect_ready` which is only set on success.
If the pre-connect fails quickly (e.g. 2s), the waiter still blocks for the
full `connect_timeout` (20s) because `Event.clear()` does not wake waiters.

New field `_connect_done: asyncio.Event` — set in a `finally` block inside
`connect()`, so it fires on both success and failure. `ensure_connected()` waits
on `_connect_done` instead. On wake: if `_connected` → return; else pre-connect
failed → try own connect immediately.

`_connect_done` is cleared in `disconnect()` and `_cleanup_on_connect_failure()`.

### Fix 3: Configurable `connect_timeout` in plugin catalog

**Files:** `backend/app/mcp/catalog.py`, `backend/app/mcp/plugin_config.py`, `backend/plugins/*/plugin.yaml`

`connect_timeout` is currently hardcoded to `min(cfg.timeout, 20)`. Plugins that
legitimately need more startup time (e.g. downloading models) have no escape hatch.

- Add `connect_timeout: int = 20` to `CatalogPlugin` and `PluginConfig`
- Read it from `plugin.yaml` catalog entries (optional, defaults to 20)
- `plugin_manager.py` uses `cfg.connect_timeout` directly instead of computing it

### Fix 4: Tests for pre-connect coordination

**Files:** `backend/tests/test_plugin_manager.py`

No existing test covers the new `ensure_connected()` behavior. Add:

- `test_ensure_connected_returns_error_when_pre_connect_running` — mocked
  `_pre_connect_task` not done → `ensure_connected()` raises `RuntimeError`
- `test_ensure_connected_returns_immediately_when_already_connected` —
  `_connected=True`, `_connect_ready` set → returns without waiting
- `test_ensure_connected_attempts_own_connect_when_pre_connect_failed` —
  pre-connect task done (failed) → falls back to own `connect()`
- `test_connect_timeout_raises_runtime_error` — `connect()` takes longer
  than `connect_timeout` → `RuntimeError` from `asyncio.wait_for`

### Fix 5: Close race window between `_connected` and `_connect_ready`

**Files:** `backend/app/mcp/plugin_client.py`

`_init_session()` sets `_connected = True`. `connect()` sets `_connect_ready.set()`
after `_init_session()` returns. In that window, `disconnect()` could set
`_connected = False` and clear the event, then `connect()` sets the event —
leaving `_connect_ready` set while `_connected` is False.

Move `_connect_ready.set()` inside `_init_session()`, immediately after
`self._connected = True`. Remove from `connect()`.

## Files affected

| File | Fixes |
|------|-------|
| `backend/app/mcp/plugin_client.py` | 2, 5 (+ `_connect_done` field, move `_connect_ready.set()`) |
| `backend/app/mcp/plugin_manager.py` | 1 (2 occurrences of `BaseException` → `Exception`) |
| `backend/app/mcp/catalog.py` | 3 (`connect_timeout` field) |
| `backend/app/mcp/plugin_config.py` | 3 (`connect_timeout` field) |
| `backend/tests/test_plugin_manager.py` | 4 (4 new test cases) |

## Order of implementation

1. Fix 3 first (schema changes, no behavior impact)
2. Fix 1 (safe change, no logic impact)
3. Fix 5 (move `_connect_ready.set()`)
4. Fix 2 (add `_connect_done`, rewrite waiter logic on top of it)
5. Fix 4 (tests — verify everything works end-to-end)
