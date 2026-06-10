# Remove QUEUED Status from Issues

## Problem
`IssueStatus.QUEUED` still exists in the enum but is deprecated — queue membership is already tracked exclusively via the `QueueEntry` table. The synthetic `issue_status_changed → Queued` event is still emitted for frontend cache invalidation and `IssueQueueService` event triggering. This causes issues to disappear from the kanban when queued (since QUEUED isn't a kanban column) and creates confusion.

## Solution
1. Remove `QUEUED = "Queued"` from `IssueStatus` enum
2. Replace `issue_status_changed → Queued` events with dedicated `queue_entry_created` event type
3. Replace `issue_status_changed` (with current status) in remove_from_queue with `queue_entry_removed`
4. Update backend event listeners to listen for `queue_entry_created` instead of `new_status == "Queued"`
5. Update frontend event handlers to invalidate queue cache on `queue_entry_created` events
6. Clean up comments referencing QUEUED status

## Non-goals
- No changes to QueueEntry model or table
- No changes to queue FIFO behavior
- No changes to issue status transition logic

## Files
- Backend: models/issue.py, services/issue_queue_service.py, routers/queue.py, mcp/shared_tools.py, mcp/orchestrator_server.py
- Frontend: shared/context/event-context.tsx, routes/queue.tsx
- Tests: tests/test_issue_queue_service.py