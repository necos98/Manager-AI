# Implementation Plan: Remove QUEUED Status

## Architecture
Queue membership already tracked via `QueueEntry` table — `IssueStatus.QUEUED` is vestigial. Replace `issue_status_changed → Queued` synthetic events with `queue_entry_created`/`queue_entry_removed` events. No behavior changes.

## Files to modify
1. `backend/app/models/issue.py` — Remove QUEUED from IssueStatus enum
2. `backend/app/services/issue_queue_service.py` — Change event emissions + listener
3. `backend/app/routers/queue.py` — Clean up comments
4. `backend/app/mcp/shared_tools.py` — Clean up comments
5. `backend/app/mcp/orchestrator_server.py` — Clean up comments
6. `frontend/src/shared/context/event-context.tsx` — Listen for new event types
7. `frontend/src/routes/queue.tsx` — Listen for new event types
8. `backend/tests/test_issue_queue_service.py` — Update test events