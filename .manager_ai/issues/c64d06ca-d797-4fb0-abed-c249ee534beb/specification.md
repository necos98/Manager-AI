# Fix Auto-Queue Not Starting Issues

## Problem

Issues added to the queue with auto-process enabled never execute. The entry appears in the queue but no terminal launches and no issue processing begins.

## Root Causes

### 1. `_enabled` defaults to False (primary)
`queue_auto_process` in `default_settings.json` is `"false"`. `load_state()` catches all exceptions silently — transient DB error at startup looks identical to "auto-process is off."

### 2. `_queue_add_direct` bypasses auto-start
When `issue_queue_service_ref` is None (service not yet initialized), `add_to_queue()` falls back to `_queue_add_direct` — creates QueueEntry but never calls `_maybe_auto_start_first()`.

### 3. Startup resume loses toggle state
`startup_resume()` is gated by `_enabled`, which depends on `load_state()` reading `queue_auto_process = "true"` from DB. If value wasn't persisted or read fails, restart = reset to off.

### 4. Ghost REASONING issue blocks pipeline
If `run_issue()` fails after QueueEntry is DISPATCHING (PTY creation failure, terminal crash), QueueEntry → FAILED but issue stays REASONING. All subsequent auto-starts blocked forever.

### 5. Fire-and-forget create_task loses exceptions
`add_to_queue()` dispatches `_maybe_auto_start_first` as `asyncio.create_task(...)` — unawaited, fire-and-forget. Any exception inside is silently lost.

## Proposed Fixes

1. **Add `_enabled` guard to `_queue_add_direct`** — call `_maybe_auto_start_first` after adding entry
2. **Tighten `load_state()` error handling** — log exceptions, only silence KeyError
3. **Add recovery for ghost REASONING issues** — in `_maybe_auto_start_first`, check if blocking REASONING issue has a terminal-state QueueEntry (FAILED/DISPATCHED/CANCELLED) and skip it
4. **Remove fire-and-forget `create_task`** — replace with awaited call (notify() path already awaits)
5. **Improve startup persistence** — ensure `set_enabled()` DB write commits synchronously

All changes in `backend/app/services/issue_queue_service.py`.

## Test Plan
- Unit tests for each fix in existing test file
- Existing 63 tests must still pass
- Manual: enable auto-process → add issue → verify terminal starts
- Manual: restart app → verify auto-process persists