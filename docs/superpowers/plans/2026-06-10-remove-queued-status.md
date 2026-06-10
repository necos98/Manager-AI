# Remove QUEUED Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `QUEUED` from `IssueStatus` enum and replace synthetic `issue_status_changed → Queued` events with dedicated `queue_entry_created`/`queue_entry_removed` event types.

**Architecture:** Queue membership already tracked via `QueueEntry` table — `QUEUED` enum value is vestigial. Change event emissions in `IssueQueueService` and listeners in frontend/backend to use new event type. No behavior change, only event type naming.

**Tech Stack:** Python/FastAPI backend, React/TypeScript frontend

---

### Task 1: Remove QUEUED from IssueStatus enum

**Files:**
- Modify: `backend/app/models/issue.py:14`

- [ ] **Step 1: Remove QUEUED line from IssueStatus enum**

Remove line 14: `QUEUED = "Queued"`

- [ ] **Step 2: Verify no syntax errors**

Run: `cd backend && python -c "from app.models.issue import IssueStatus; print(list(IssueStatus))"`
Expected: QUEUED not in list

### Task 2: Change add_to_queue event emission

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:361-368` — `add_to_queue()` event
- Modify: `backend/app/services/issue_queue_service.py:703-710` — `_queue_add_direct()` event

- [ ] **Step 1: Change event in add_to_queue()**

Replace:
```python
await event_service.emit({
    "type": "issue_status_changed",
    "new_status": IssueStatus.QUEUED.value,
    "project_id": project_id,
    "issue_id": issue_id,
    "issue_name": issue.name or "",
    "timestamp": iso_now(),
})
```

With:
```python
await event_service.emit({
    "type": "queue_entry_created",
    "project_id": project_id,
    "issue_id": issue_id,
    "issue_name": issue.name or "",
    "timestamp": iso_now(),
})
```

- [ ] **Step 2: Same change in _queue_add_direct()**

Same pattern — emit `queue_entry_created` instead of `issue_status_changed → Queued`.

### Task 3: Change remove_from_queue event emission

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:406-413` — `remove_from_queue()` event
- Modify: `backend/app/services/issue_queue_service.py:760-768` — `_queue_remove_direct()` event

- [ ] **Step 1: Change event in remove_from_queue()**

Replace `issue_status_changed` with `queue_entry_removed`:
```python
await event_service.emit({
    "type": "queue_entry_removed",
    "project_id": project_id,
    "issue_id": issue_id,
    "issue_name": issue.name or "",
    "timestamp": iso_now(),
})
```

- [ ] **Step 2: Same change in _queue_remove_direct()**

### Task 4: Update notify() to listen for queue_entry_created

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:468-492` — `notify()` method

- [ ] **Step 1: Change event type check**

Replace:
```python
elif new_status == "Queued" and project_id and issue_id:
```

With:
```python
elif event.get("type") == "queue_entry_created" and project_id and issue_id:
```

### Task 5: Update frontend event handlers

**Files:**
- Modify: `frontend/src/shared/context/event-context.tsx:299`
- Modify: `frontend/src/routes/queue.tsx:42`

- [ ] **Step 1: Update event-context.tsx**

Replace:
```typescript
if (ns === "Queued" || ns === "Reasoning" || ns === "Finished") {
```
With:
```typescript
if (data.type === "queue_entry_created" || ns === "Reasoning" || ns === "Finished") {
```

- [ ] **Step 2: Update queue.tsx**

Replace:
```typescript
if (ns === "Queued" || ns === "Reasoning" || ns === "Finished") {
```
With:
```typescript
if (event.type === "queue_entry_created" || ns === "Reasoning" || ns === "Finished") {
```

### Task 6: Clean up comments referencing QUEUED

**Files:**
- Modify: `backend/app/routers/queue.py` — lines 4, 89, 191
- Modify: `backend/app/mcp/shared_tools.py` — line 1623
- Modify: `backend/app/mcp/orchestrator_server.py` — line 420
- Modify: `backend/app/services/issue_queue_service.py` — docstring line 9, comments lines 250, 555, 612

- [ ] **Step 1: Update router comments**
- [ ] **Step 2: Update MCP tool descriptions**
- [ ] **Step 3: Update service docstrings and comments**

### Task 7: Update tests

**Files:**
- Modify: `backend/tests/test_issue_queue_service.py` — lines 504-514, 554-583

- [ ] **Step 1: Update test event payloads**

Change `"new_status": "Queued"` events to use type `queue_entry_created`.
Update test names and docstrings.

- [ ] **Step 2: Run tests to verify**

Run: `cd backend && python -m pytest tests/test_issue_queue_service.py -v`
Expected: All tests pass

### Task 8: Write project memory

- [ ] **Step 1: Create memory about the QUEUED removal**

Via `memory_create` — record that QUEUED was removed from IssueStatus enum, events now use `queue_entry_created`/`queue_entry_removed`.
