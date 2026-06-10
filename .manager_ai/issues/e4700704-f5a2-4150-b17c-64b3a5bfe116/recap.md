## Recap

**"Rimuovi dalla coda" button** — implementation was already committed. Verified:

### Backend
- `POST /api/queue/remove` endpoint in `backend/app/routers/queue.py:289-308` accepts `{project_id, issue_id}`, delegates to `IssueQueueService.remove_from_queue()` (validates QueueEntry exists, marks as dispatched) with `_queue_remove_direct` fallback
- Emits `queue_entry_removed` WebSocket event for real-time UI updates

### Frontend
- `removeFromQueue()` API function in `frontend/src/features/queue/api.ts:61-63` calls `apiPost("/queue/remove", ...)`
- `useRemoveFromQueue` mutation hook in `frontend/src/features/queue/hooks.ts:67-78` invalidates `queue.queued`, `queue.status`, `queue.all` on success
- Trash2 icon button per row in "In coda" table, disabled while pending
- Radix confirm dialog showing issue name with Cancel/Remove buttons
- Event context (`event-context.tsx:297-300`) invalidates `queue.position` on `queue_entry_removed`

### Working tree changes (related but not part of this issue)
- `issue_queue_service.py`: `add_to_queue` now registers QueueEntry synchronously + calls `_maybe_auto_start_first` directly instead of via event handler
- `_on_issue_queued` event handler made idempotent (checks `get_pending_entry` before registering)