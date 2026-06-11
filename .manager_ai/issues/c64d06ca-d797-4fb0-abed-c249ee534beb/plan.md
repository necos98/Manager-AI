## Fix 1: Auto-start from `_queue_add_direct`

`_queue_add_direct` creates QueueEntry but never calls `_maybe_auto_start_first`. At function end, re-check `issue_queue_service_ref`. If service exists and `_enabled`, delegate auto-start.

**File:** `backend/app/services/issue_queue_service.py:672-729`

## Fix 2: Tighten `load_state()` error handling

Currently catches ALL exceptions silently. Only `KeyError` (setting not found) is expected — log traceback for unexpected exceptions.

**File:** `backend/app/services/issue_queue_service.py:308-312`

## Fix 3: Ghost REASONING recovery

If `run_issue()` fails after QueueEntry → DISPATCHING but issue stays REASONING, subsequent auto-starts are blocked forever. Add `_count_active_reasoning()` helper that checks QueueEntry status. Replace simple `running` check in both `_maybe_auto_start_first` and `startup_resume`.

**File:** `backend/app/services/issue_queue_service.py:623-666, 244-290`

## Fix 4: Remove redundant `create_task` from `add_to_queue()`

`add_to_queue()` emits `queue_entry_created` event AND separately dispatches `_maybe_auto_start_first` as fire-and-forget task. Event handler `notify()` → `_on_issue_queued()` also calls it. Per-project lock makes second call a no-op. Remove redundant `create_task`.

**File:** `backend/app/services/issue_queue_service.py:371-373`

## Tests

All changes testable in `backend/tests/test_issue_queue_service.py`. Existing 63 tests must pass.