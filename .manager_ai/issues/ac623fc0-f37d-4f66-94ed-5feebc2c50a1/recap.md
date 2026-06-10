## Changes

Two-file fix for queue status not appearing for 2nd+ queued items:

**Backend** (`backend/app/services/issue_queue_service.py`):
- `add_to_queue()` now calls `self.register()` synchronously before emitting the `queue_entry_created` event. This closes the race where the QueueEntry didn't exist when the frontend checked position after mutation success.
- `_on_issue_queued()` made idempotent: checks `get_pending_entry()` first, skips `register()` if entry already exists. This handles the case where `add_to_queue` already registered synchronously.
- `_maybe_auto_start_first()` is now triggered directly from `add_to_queue()` (not reliant on event handler chain), ensuring auto-start still works.

**Frontend** (`frontend/src/shared/context/event-context.tsx`):
- `queue_entry_created`/`queue_entry_removed` WebSocket event handler now also invalidates `["queue", "position"]` query prefix. Previously only invalidated `queued` and `status`, so the position badge in issue detail could be stale for up to 10s polling interval.

**Tests**: 63/63 queue service tests pass. No regressions.