## Summary
Removed `IssueStatus.QUEUED` from the enum and replaced synthetic `issue_status_changed → Queued` events with dedicated `queue_entry_created`/`queue_entry_removed` event types.

## Changes
- **models/issue.py**: Removed `QUEUED = "Queued"` from `IssueStatus` enum
- **services/issue_queue_service.py**:
  - `add_to_queue()` emits `queue_entry_created` instead of `issue_status_changed → Queued`
  - `remove_from_queue()` emits `queue_entry_removed` instead of `issue_status_changed`
  - `notify()` listens for `queue_entry_created` event type instead of `new_status == "Queued"`
  - Same changes in fallback `_queue_add_direct()`/`_queue_remove_direct()`
- **routers/queue.py**: Cleaned up comments referencing `IssueStatus.QUEUED`
- **mcp/shared_tools.py, orchestrator_server.py**: Cleaned up QUEUED references in docstrings
- **main.py**: Cleaned up QUEUED comment
- **Frontend event handlers**: Listen for `queue_entry_created`/`queue_entry_removed` event types to invalidate queue cache
- **Tests**: Updated to use `queue_entry_created` event type; all 63 tests pass

## Effect
Adding/removing from queue no longer changes issue status. Queue membership tracked exclusively via `QueueEntry` table. No behavioral changes to FIFO queue logic.