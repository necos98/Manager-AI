## Bug Analysis

When a second issue is added to the queue, the "In Queue" badge doesn't appear immediately (or at all until the 10s polling catches up). The user expects to see queue membership reflected instantly.

### Root Cause: Backend Race Condition

`IssueQueueService.add_to_queue()` emits a `queue_entry_created` event via `event_service.emit()` and returns immediately. The actual QueueEntry registration (`register()`) happens asynchronously through the event handler:

1. `add_to_queue()` → `event_service.emit("queue_entry_created")` → returns success
2. Frontend gets 200 OK → invalidates position query → `GET /queue/position/{id}` → no QueueEntry yet → `in_queue: false`
3. `IssueQueueService.notify()` receives event → `asyncio.create_task(_on_issue_queued())` → `register()` creates QueueEntry

The serialisation via `event_service.emit()` + `asyncio.create_task` means the QueueEntry is guaranteed to NOT exist when add_to_queue returns. The frontend position check always misses for a newly queued item until the 10s polling interval catches up.

### Root Cause: Frontend Missing Invalidation

The WebSocket event handler in `event-context.tsx` only invalidates `["queue", "queued"]` and `["queue", "status"]` on `queue_entry_created`. It does NOT invalidate `["queue", "position", issueId]`, so the position query depends entirely on the 10s polling interval.

## Fix

### 1. Backend: Register queue entry synchronously in add_to_queue

Move `self.register()` call into `add_to_queue()` before the event emit. Keep `_on_issue_queued` as a fallback for external event producers, but make it check if entry already exists before registering (idempotent).

**`backend/app/services/issue_queue_service.py`:**
- In `add_to_queue()`: call `await self.register(issue_id, project_id)` before `event_service.emit()`
- In `_on_issue_queued()`: check `await self.get_pending_entry(issue_id)` first, skip `register()` if already exists

### 2. Frontend: Invalidate position query on queue_entry_created

**`frontend/src/shared/context/event-context.tsx`:**
- Add `queryClient.invalidateQueries({ queryKey: ["queue", "position"] })` to the `queue_entry_created` handler

This ensures both the badge in `issue-detail.tsx` and the button state in `issue-actions.tsx` update immediately when an issue is queued.

## Scope

Two files changed. No DB migration. No new tests needed for this targeted fix.
