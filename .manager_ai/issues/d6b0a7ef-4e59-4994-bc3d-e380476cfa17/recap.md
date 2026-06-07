## Fix _issue_completion_locks memory leak

### Problem
Module-level `_issue_completion_locks` dict in `issue_service.py` grew unbounded. `setdefault` created entries in `complete_issue()` but they were never removed.

### Fix
Added `_issue_completion_locks.pop(issue_id, None)` at `issue_service.py:394` — inside `async with lock:` block, immediately before `return rec`.

This ensures each lock entry is cleaned up after the issue completes. Idempotent via `.pop(key, None)`. Safe with concurrent callers — they share the same lock ref via `setdefault`, and the second caller finds FINISHED status, raising `InvalidTransitionError`.

### Testing
All 9 `complete_issue` tests pass, including lock-blocking and concurrent-caller scenarios.

### Files changed
- `backend/app/services/issue_service.py` — one-line fix