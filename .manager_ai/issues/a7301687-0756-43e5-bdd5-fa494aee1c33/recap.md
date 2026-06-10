## Recap: Fix race condition doppio start coda

### Problem
When `_on_issue_finished()` was called twice (from pipeline + `complete_issue`), `_dequeue_and_run()` could start the same issue in two parallel terminals because:
1. `QueueEntry` was marked `DISPATCHING` asynchronously via `_on_issue_reasoning` (after `_emit_event` → `create_task`), leaving a window where `get_next_pending()` still returned the same entry
2. No per-project mutual exclusion on `_dequeue_and_run()`

### Changes (single file)
**`backend/app/services/issue_queue_service.py`**:

1. **Lock per-progetto**: `self._dequeue_locks: dict[str, asyncio.Lock]` in `__init__()`. `_dequeue_and_run()` acquires the lock at entry, ensuring serialized execution per project.

2. **Marcatura sincrona QueueEntry**: `await self.mark_dispatching(next_entry.issue_id)` called immediately after `get_next_pending()` and the None check, BEFORE `update_status()` and `_emit_event()`. This closes the race window: even if a second `_on_issue_finished` arrives, `get_next_pending()` won't return the same entry.

3. **`mark_dispatching()` tollerante**: if no PENDING entry is found, checks for DISPATCHING entry (from the synchronous mark) and returns silently with debug log, instead of logging a warning. This prevents false positives when `_on_issue_reasoning` fires after the queue entry is already DISPATCHING.