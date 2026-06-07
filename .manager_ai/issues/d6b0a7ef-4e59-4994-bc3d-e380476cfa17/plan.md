# Implementation Plan: Fix `_issue_completion_locks` Memory Leak

## Overview
One-line fix in `backend/app/services/issue_service.py`. Pop the per-issue lock from `_issue_completion_locks` after `complete_issue()` finishes, preventing unbounded dict growth.

## File Changed
- `backend/app/services/issue_service.py` — one line added

## Step-by-step

### 1. Add `pop()` before `return rec` in `complete_issue()`
- **Location:** `issue_service.py`, line 394 — inside `async with lock:` block, immediately before `return rec`
- **Code to insert:**
  ```python
  _issue_completion_locks.pop(issue_id, None)
  ```
- **Why this placement:**
  - `return rec` (line 394) is inside the `async with lock:` block — pop must precede it since Python exits the function at `return`
  - `setdefault` on line 351 ensures concurrent callers share the same lock ref; first caller pops after completion, second caller acquires lock, finds FINISHED status, raises `InvalidTransitionError`
  - `.pop(key, None)` is idempotent — safe if key already removed

### 2. Verify
- `test_complete_issue_blocks_when_lock_held` passes unchanged (its manual `pop` becomes harmless no-op)
- No other file changes needed

## Dependencies & Constraints
- **Only `complete_issue()` is modified** — `cancel_issue()` and `force_finish_issue()` intentionally bypass the lock dict
- **No test changes required** — existing coverage suffices
- **No structural refactoring** — not converting to LRU/weak-ref, not adding locks to other methods

## Acceptance Criteria
1. `_issue_completion_locks` stops growing monotonically — entry removed after `complete_issue()` returns
2. Existing lock-behavior test passes without modification
3. Concurrent callers serialize correctly: first succeeds, second gets `InvalidTransitionError`
4. `cancel_issue()` and `force_finish_issue()` untouched
