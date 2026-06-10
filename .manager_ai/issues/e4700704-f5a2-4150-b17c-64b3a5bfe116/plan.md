# Implementation Plan

**Goal:** Add "Remove from Queue" button to global `/queue` page.

**Architecture:** Backend endpoint already exists (`POST /api/queue/remove`), frontend API/hooks/button/dialog already committed. Plan verifies and closes.

**Tech Stack:** FastAPI, React, React Query, Radix Dialog

---

### Task 1: Verify Backend Endpoint
- `POST /api/queue/remove` in `backend/app/routers/queue.py:289-308` accepts `{project_id, issue_id}` body, delegates to `IssueQueueService.remove_from_queue()` with `_queue_remove_direct` fallback
- WebSocket event `queue_entry_removed` emitted on removal in `issue_queue_service.py`
- Event context in `frontend/src/shared/context/event-context.tsx` handles `queue_entry_removed` for query invalidation

### Task 2: Verify Frontend Implementation
- `removeFromQueue(projectId, issueId)` in `frontend/src/features/queue/api.ts:61-63` via `apiPost("/queue/remove", ...)`
- `useRemoveFromQueue` mutation in `frontend/src/features/queue/hooks.ts:67-78` with proper invalidation
- Trash2 icon button per row + Radix confirm dialog in `frontend/src/routes/queue.tsx:256-321`

### Task 3: Accept Plan and Complete Issue
- Move to Accepted, write recap, complete