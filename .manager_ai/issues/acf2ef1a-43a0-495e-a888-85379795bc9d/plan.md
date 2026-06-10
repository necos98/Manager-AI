## Implementation Plan

### Task 1: Add standalone `_queue_add_direct()` function in issue_queue_service.py

Add a module-level async function that performs the queue-add operation directly:
1. Validate issue is in NEW or ACCEPTED status (via IssueService)
2. Call `IssueQueueService.register()` to create the QueueEntry synchronously
3. Emit the `issue_status_changed → Queued` event via event_service
4. Return standardized dict `{id, project_id, status}`

This function reuses the existing `register()` method from IssueQueueService (it's the same async method, just called on an instance that IS initialized). When IssueQueueService is not available, we need to call it directly.

Wait — `register()` is an instance method on IssueQueueService. We can't call it without an instance. So instead, the standalone function should directly create the QueueEntry in the DB rather than calling `register()`.

Revised approach for the standalone function:
1. Validate the issue (IssueService)
2. Create QueueEntry directly via async_session (same logic as IssueQueueService.register())
3. Emit the event

### Task 2: Add standalone `_queue_remove_direct()` function in issue_queue_service.py

Same pattern for remove:
1. Validate the issue exists
2. Find the pending QueueEntry for this issue
3. Mark it as dispatched
4. Emit the event

Reuses the existing `get_pending_entry()` and `mark_dispatched()` from IssueQueueService (available via module-level ref), but also works when the ref is None by doing the DB operations directly.

### Task 3: Update REST endpoint in queue.py

In `POST /api/queue/add`:
- When `issue_queue_service_ref` is not None → delegate to `registry.add_to_queue()` (existing behavior, unchanged)
- When None → call the standalone function and return the result

In `POST /api/queue/remove`:
- Same pattern: fallback to standalone function when ref is None
