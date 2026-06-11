# Fix Auto-Queue Not Starting Issues

## Problem

Issues added to the queue with auto-process enabled never execute. The entry appears in the queue but no terminal launches, no issue processing begins. This happens in all cases: first issue added to an empty queue, subsequent issues, and after restart with auto-process previously enabled.

## Root Causes

### 1. `_enabled` defaults to False (primary)

`queue_auto_process` in `backend/app/mcp/default_settings.json` is `"false"`. At startup, `load_state()` reads this from DB — if the key doesn't exist yet or the read fails, `_enabled` stays False and all auto-processing paths are dead code.

The `load_state()` method catches all exceptions silently (`except Exception: pass`), so a transient DB error at startup looks identical to "auto-process is off."

### 2. `_queue_add_direct` bypasses auto-start

When `issue_queue_service_ref` is `None` (service not yet initialized), `add_to_queue()` falls back to `_queue_add_direct`. This creates a QueueEntry but never calls `_maybe_auto_start_first()`. The entry lands in the queue but nothing processes it.

### 3. Startup resume loses toggle state

`startup_resume()` is gated by `_enabled`, which depends on `load_state()` reading `queue_auto_process = "true"` from DB. If the value wasn't persisted (shutdown race, transaction not committed), restart = reset to off.

### 4. Ghost REASONING issue blocks pipeline

`_maybe_auto_start_first()` checks for any existing REASONING issue before dequeuing. If `run_issue()` fails after QueueEntry is marked DISPATCHING (e.g., PTY creation failure, terminal service crash, invalid project config), the QueueEntry → FAILED but the issue stays REASONING. All subsequent auto-starts are blocked forever.

### 5. Fire-and-forget create_task loses exceptions

`add_to_queue()` dispatches `_maybe_auto_start_first` as `asyncio.create_task(...)` — unawaited, fire-and-forget. Any exception raised inside is silently lost. The awaited call from `notify()` → `_on_issue_queued()` is also unbounded and could be cancelled or delayed by EventService's sequential notifier iteration.

## Proposed Fixes

All five fixes are independent but should be implemented together for robustness.

### Fix 1: Add `_enabled` guard to `_queue_add_direct`

The direct fallback path should support auto-start just like the primary path. Add an `_enabled` check + `_maybe_auto_start_first` call to `_queue_add_direct`.

**File:** `backend/app/services/issue_queue_service.py`

### Fix 2: Tighten `load_state()` error handling

Log the exception instead of silently passing. Return a meaningful default only on setting-not-found (KeyError), not on arbitrary failures.

**File:** `backend/app/services/issue_queue_service.py`

### Fix 3: Add recovery for ghost REASONING issues

In `_maybe_auto_start_first()`, when detecting a blocking REASONING issue, check if its QueueEntry has a terminal state (FAILED, DISPATCHED, CANCELLED). If so, count it as non-blocking. Alternatively, add a startup sweep that fails REASONING issues with no active terminal.

**File:** `backend/app/services/issue_queue_service.py`

### Fix 4: Remove fire-and-forget `create_task`

Replace the `create_task` in `add_to_queue()` with an awaited call. The `notify()` path already awaits `_on_issue_queued()` → `_maybe_auto_start_first()`. The dual dispatch is redundant and dangerous.

**File:** `backend/app/services/issue_queue_service.py`

### Fix 5: Improve startup persistence

In `set_enabled()`, commit the DB write synchronously (within the same session) so the toggle survives a crash. Currently the setting write may be in a transaction that hasn't committed.

**File:** `backend/app/services/issue_queue_service.py`

## Test Plan

- Unit tests for each fix in `backend/tests/test_issue_queue_service.py`
- Existing 63 tests must still pass
- Manual test: enable auto-process → add issue → verify terminal starts
- Manual test: restart app with auto-process on → add issue → verify auto-process works
- Manual test: add issue while `issue_queue_service_ref` is None → verify auto-start doesn't crash
