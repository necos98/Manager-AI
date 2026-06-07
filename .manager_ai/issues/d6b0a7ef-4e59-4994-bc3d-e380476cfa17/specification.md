# Fix _issue_completion_locks Memory Leak

## Problem
`_issue_completion_locks` (module-level `dict[str, asyncio.Lock]` at `issue_service.py:38`) grows unbounded. Each call to `complete_issue()` via `setdefault` on line 351 creates a lock entry if one doesn't exist, but no code ever removes entries after completion.

Over time, every completed issue leaves a stale lock in the dict — a memory leak proportional to issue count.

## Scope
Add one line to `complete_issue()` to pop the lock entry after it's no longer needed.

## Location
`backend/app/services/issue_service.py`, inside `async def complete_issue()` (line 348).

## Constraint — pop inside the lock block
The `_issue_completion_locks.pop(issue_id, None)` MUST be placed **inside** `async with lock:` block, immediately before `return rec` (line 394). Reasons:

1. **Safety with concurrent callers** — if two threads call `complete_issue(id)` simultaneously, both get the same lock via `setdefault`. The first acquires, completes, pops, and returns. The second acquires after the pop, finds status already FINISHED, and raises `InvalidTransitionError`. This is correct behavior.
2. **Python scoping** — `return rec` exits the function; any cleanup after it is dead code. The pop cannot go after `return rec`.
3. **Idempotency** — `pop(key, None)` is safe whether or not the key exists.

## Acceptance Criteria
1. `_issue_completion_locks` no longer grows monotonically — after `complete_issue()` returns, the issue's lock entry is removed from the dict.
2. Existing test `test_complete_issue_blocks_when_lock_held` still passes without modification.
3. Concurrent callers to `complete_issue()` with the same issue_id still serialize correctly (first succeeds, second gets `InvalidTransitionError`).
4. `cancel_issue()` and `force_finish_issue()` are untouched — they intentionally bypass the lock mechanism.

## Non-goals
- No changes to `cancel_issue()` or `force_finish_issue()`. These are intentional bypasses that don't use the lock dict.
- No structural refactoring of the locking mechanism (e.g. converting to LRU or weak-ref dict).
- No adding locks to other methods.
- No test changes — existing coverage is sufficient.
