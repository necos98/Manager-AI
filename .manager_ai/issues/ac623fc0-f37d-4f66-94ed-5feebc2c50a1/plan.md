# Queue Status Race Condition Fix

**Goal:** Fix race condition where "In Queue" badge doesn't appear for newly queued issues because QueueEntry registration is deferred to async event handler.

**Architecture:** Two changes: (1) backend — register QueueEntry synchronously in `add_to_queue()` before returning, make `_on_issue_queued` idempotent. (2) frontend — invalidate position query on `queue_entry_created` WebSocket event so the badge updates immediately.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), React/TanStack Query (frontend)

---

### Task 1: Sync QueueEntry registration in add_to_queue

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:331-372`

**Changes:**
1. In `add_to_queue()`: call `await self.register(issue_id, project_id)` before `event_service.emit()`
2. After emit, if `self._enabled`, spawn `_maybe_auto_start_first` as background task
3. In `_on_issue_queued()`: check `self.get_pending_entry(issue_id)` first, skip `register()` if already exists

- [ ] **Step 1: Modify add_to_queue to register synchronously**

In `add_to_queue()`, after validation and before event emit, add synchronous registration. Also trigger `_maybe_auto_start_first` as background task (not via event handler):

Current code at line 360:
```python
await event_service.emit({
    "type": "queue_entry_created",
    "project_id": project_id,
    "issue_id": issue_id,
    "issue_name": issue.name or "",
    "timestamp": iso_now(),
})

return {
    "id": issue_id,
    "project_id": project_id,
    "status": issue.status,
}
```

Replace with:
```python
# Register synchronously so QueueEntry exists when response returns
await self.register(issue_id, project_id)

await event_service.emit({
    "type": "queue_entry_created",
    "project_id": project_id,
    "issue_id": issue_id,
    "issue_name": issue.name or "",
    "timestamp": iso_now(),
})

# Auto-start if enabled (runs as background task, not via event handler)
if self._enabled:
    asyncio.create_task(self._maybe_auto_start_first(project_id, issue_id))

return {
    "id": issue_id,
    "project_id": project_id,
    "status": issue.status,
}
```

- [ ] **Step 2: Make _on_issue_queued idempotent**

In `_on_issue_queued()`, check if entry already exists before registering:

Current code at line 505-514:
```python
async def _on_issue_queued(self, project_id: str, issue_id: str) -> None:
    """Handle a newly queued issue: register entry + maybe auto-start."""
    try:
        await self.register(issue_id, project_id)
        if self._enabled:
            await self._maybe_auto_start_first(project_id, issue_id)
    except Exception:
        logger.exception(
            "IssueQueueService failed on queued for project %s", project_id,
        )
```

Replace with:
```python
async def _on_issue_queued(self, project_id: str, issue_id: str) -> None:
    """Handle a newly queued issue: register entry + maybe auto-start.
    
    Registration is idempotent — skips if entry already exists
    (e.g., from synchronous register() in add_to_queue).
    """
    try:
        # Check if already registered (e.g., by add_to_queue)
        existing = await self.get_pending_entry(issue_id)
        if existing is None:
            await self.register(issue_id, project_id)
        if self._enabled:
            await self._maybe_auto_start_first(project_id, issue_id)
    except Exception:
        logger.exception(
            "IssueQueueService failed on queued for project %s", project_id,
        )
```

- [ ] **Step 3: Run existing queue tests to verify nothing broke**

Run: `cd backend && python -m pytest tests/test_issue_queue_service.py -v`
Expected: all tests pass

### Task 2: Frontend — invalidate position query on queue_entry_created

**Files:**
- Modify: `frontend/src/shared/context/event-context.tsx:296-300`

**Changes:**
Add `queryClient.invalidateQueries({ queryKey: ["queue", "position"] })` to the `queue_entry_created`/`queue_entry_removed` handler block.

- [ ] **Step 1: Add position invalidation to event handler**

Current code at line 296-300:
```javascript
if (data.type === "queue_entry_created" || data.type === "queue_entry_removed") {
    queryClient.invalidateQueries({ queryKey: ["queue", "queued"] });
    queryClient.invalidateQueries({ queryKey: ["queue", "status"] });
}
```

Replace with:
```javascript
if (data.type === "queue_entry_created" || data.type === "queue_entry_removed") {
    queryClient.invalidateQueries({ queryKey: ["queue", "queued"] });
    queryClient.invalidateQueries({ queryKey: ["queue", "status"] });
    queryClient.invalidateQueries({ queryKey: ["queue", "position"] });
}
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

### Task 3: Verify end-to-end

- [ ] **Step 1: Start backend and test queue flow**

Run: `cd backend && python -m pytest tests/test_issue_queue_service.py -v`
Expected: all tests pass

- [ ] **Step 2: Manual verification**
  1. Start the app
  2. Add issue 1 to queue → verify it starts processing (status → Reasoning)
  3. Add issue 2 to queue → verify "In Queue (#1)" badge appears immediately in issue detail
  4. Verify Remove from Queue button shows correctly in issue-actions
