# "Rimuovi dalla coda" Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Remove from Queue" button to the global `/queue` page with confirmation dialog.

**Architecture:** Backend already has `POST /api/queue/remove` endpoint delegating to `IssueQueueService.remove_from_queue()`. Frontend already has API function, mutation hook, and button with confirm dialog. This plan verifies the existing implementation.

**Tech Stack:** FastAPI, React, React Query, Radix Dialog

---

### Task 1: Verify Backend Endpoint

**Files:**
- Verify: `backend/app/routers/queue.py:289-308`
- Verify: `backend/app/services/issue_queue_service.py`

- [ ] **Step 1: Verify POST /api/queue/remove endpoint**

Endpoint exists at `backend/app/routers/queue.py:289-308`. Accepets `{project_id, issue_id}` body. Delegates to `IssueQueueService.remove_from_queue()` with fallback `_queue_remove_direct`. Returns `{id, message}`.

No test needed — unit tests already cover the service layer.

- [ ] **Step 2: Verify WebSocket event emission**

`remove_from_queue` in `issue_queue_service.py` emits `queue_entry_removed` event. Event context in `frontend/src/shared/context/event-context.tsx` handles `queue_entry_removed` to invalidate queue queries.

### Task 2: Verify Frontend Implementation

**Files:**
- Verify: `frontend/src/features/queue/api.ts:61-63`
- Verify: `frontend/src/features/queue/hooks.ts:67-78`
- Verify: `frontend/src/routes/queue.tsx:256-273,284-321`

- [ ] **Step 1: Verify API function**

`removeFromQueue(projectId, issueId)` in `api.ts` calls `apiPost("/queue/remove", {project_id, issue_id})`. Returns `{id, message}`.

- [ ] **Step 2: Verify mutation hook**

`useRemoveFromQueue` in `hooks.ts` wraps mutation with `queue.queued`, `queue.status`, `queue.all` invalidation on success.

- [ ] **Step 3: Verify UI button + confirm dialog**

Queue page (`queue.tsx`):
- Trash2 icon button per row in "In coda" table
- Button disabled while mutation pending
- Radix dialog for confirmation: shows issue name, Cancel/Remove buttons
- Remove button shows Loader2 spinner while pending

### Task 3: Write Recap and Complete Issue

**Files:**
- Modify: issue via MCP

- [ ] **Step 1: Accept the plan**

Call `accept_issue` to move to Accepted status.

- [ ] **Step 2: Verify nothing is broken**

No regressions expected — existing functionality unchanged.

- [ ] **Step 3: Complete the issue**

Call `complete_issue` with recap documenting what was achieved.
