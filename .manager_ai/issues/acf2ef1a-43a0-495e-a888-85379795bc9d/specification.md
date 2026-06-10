## Analysis

### Problem
The "Add to queue" button on the issue detail page sends `POST /api/queue/add`, which returns HTTP 503 "Queue service not initialized". The same happens for `POST /api/queue/remove`.

### Root Cause
The REST endpoints `POST /api/queue/add` and `POST /api/queue/remove` depend on the `issue_queue_service_ref` singleton. This ref is set when `IssueQueueService()` is created during the lifespan startup (main.py line 306-307).

If any preceding startup step fails (even though each has its own try/except), the outer try block skips the IssueQueueService creation entirely. The result: `issue_queue_service_ref` stays None and all queue write operations fail with 503.

Meanwhile, `GET /api/queue` and `GET /api/queue/status` work fine because they query the QueueEntry table directly and don't depend on the ref.

### Fix Requirements ("senza spaghetti code")
1. **Resilience**: `POST /api/queue/add` should work even when IssueQueueService hasn't been initialized, by performing the add operation directly (validate issue, create QueueEntry, emit event).
2. **Same for remove**: `POST /api/queue/remove` should also handle the case gracefully.
3. **No duplicated logic**: extract a standalone helper in `issue_queue_service.py` that can be called both by the IssueQueueService method and directly by the REST endpoint.
4. **No EventService notifier pollution**: don't create throwaway IssueQueueService instances.

### Current behavior vs fixed behavior

| Scenario | Current | Fixed |
|---|---|---|
| IssueQueueService initialized | Works | Works (same) |
| IssueQueueService NOT initialized | 503 "Queue service not initialized" | Performs add/remove directly via standalone function |
| MCP queue_add with ref=None | Returns error dict | Stays same (MCP handles errors gracefully) |

### Design

Extract a standalone `_queue_add_direct(session, project_id, issue_id) -> dict` function in `issue_queue_service.py` that:
1. Validates issue is in NEW or ACCEPTED status (via IssueService)
2. Creates the QueueEntry directly (bypasses event listener, creates entry synchronously)
3. Emits the `issue_status_changed → Queued` event for other listeners

Same for remove: `_queue_remove_direct(session, project_id, issue_id) -> dict`.

Then in `routers/queue.py`:
- When `issue_queue_service_ref` is None, call the standalone function instead of returning 503.
- When available, delegate to `issue_queue_service_ref.add_to_queue()` as before (creates QueueEntry via event listener).

This keeps existing behavior unchanged for the normal case, and adds a resilient fallback for the edge case.
