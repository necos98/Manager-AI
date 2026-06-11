# Fix Auto-Queue Not Starting Issues — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 root causes that prevent queued issues from auto-starting when auto-process is enabled.

**Architecture:** All changes in `backend/app/services/issue_queue_service.py`. Each fix is independent — they address different guard conditions in the auto-start pipeline. Tests in `backend/tests/test_issue_queue_service.py`.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, asyncio, pytest

---

### Task 1: Fix `_queue_add_direct` to support auto-start

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:672-729`

**Problem:** `_queue_add_direct` creates a QueueEntry but never calls `_maybe_auto_start_first`. If `issue_queue_service_ref` becomes available between the router's null-check and this function executing, the entry sits in the queue forever.

**Fix:** At the end of `_queue_add_direct`, re-check `issue_queue_service_ref`. If the service exists and `_enabled`, delegate to its `_maybe_auto_start_first`.

- [ ] **Step 1: Add auto-start call at end of `_queue_add_direct`**

After the `event_service.emit(...)` call (line 717-723) and before the return, add:

```python
    # If the queue service is now available and auto-process is enabled,
    # attempt to auto-start the first pending issue
    if issue_queue_service_ref and issue_queue_service_ref._enabled:
        await issue_queue_service_ref._maybe_auto_start_first(project_id, issue_id)
```

### Task 2: Tighten `load_state()` error handling

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:296-312`

**Problem:** `load_state()` catches ALL exceptions silently (just a warning log). A transient DB error or misconfiguration silently sets `_enabled = False` with no traceback, making debugging impossible.

**Fix:** Only catch `KeyError` (setting doesn't exist yet = expected) silently. Log full traceback for unexpected exceptions.

- [ ] **Step 1: Split exception handling**

Current (lines 308-312):
```python
except Exception:
    logger.warning(
        "Failed to load queue_auto_process setting; defaulting to disabled",
    )
    self._enabled = False
```

Replace with:
```python
except KeyError:
    self._enabled = False
except Exception:
    logger.exception(
        "Failed to load queue_auto_process setting; defaulting to disabled",
    )
    self._enabled = False
```

### Task 3: Add ghost REASONING recovery

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:623-666`
- Modify: `backend/app/services/issue_queue_service.py:244-290`

**Problem:** If `run_issue()` fails after QueueEntry is DISPATCHING but issue is REASONING, the issue stays REASONING forever. `_maybe_auto_start_first` and `startup_resume` check for any REASONING issue and skip the project — blocking all future auto-starts.

**Fix:** Add a helper that counts REASONING issues with an active (DISPATCHING or PENDING) QueueEntry. Replace the simple `running` check in both `_maybe_auto_start_first` and `startup_resume`.

- [ ] **Step 1: Add `_count_active_reasoning` helper**

After `_get_dispatching_by_issue` (after line 466), add:

```python
async def _count_active_reasoning(self, project_id: str) -> int:
    """Count REASONING issues that have an active QueueEntry.
    
    An active QueueEntry is one in PENDING or DISPATCHING state.
    REASONING issues whose QueueEntry is FAILED or DISPATCHED are
    considered "ghosts" — run_issue failed after marking the entry,
    leaving the issue stuck. They should not block the queue.
    """
    async with async_session() as session:
        issue_service = IssueService(session)
        running = await issue_service.list_by_project(
            project_id, status=IssueStatus.REASONING,
        )
        if not running:
            return 0
        active = 0
        for issue in running:
            result = await session.execute(
                select(QueueEntry)
                .where(
                    QueueEntry.issue_id == issue.id,
                    QueueEntry.status.in_([
                        QueueEntryStatus.PENDING,
                        QueueEntryStatus.DISPATCHING,
                    ]),
                )
                .limit(1)
            )
            if result.scalar_one_or_none():
                active += 1
        return active
```

- [ ] **Step 2: Update `_maybe_auto_start_first` to use new helper**

In `_maybe_auto_start_first` (line 650-656), replace:
```python
running = await issue_service.list_by_project(
    project_id,
    status=IssueStatus.REASONING,
)

if not running:
```
with:
```python
active_reasoning = await self._count_active_reasoning(project_id)
if active_reasoning == 0:
```

- [ ] **Step 3: Update `startup_resume` to use new helper**

In `startup_resume` (line 269-282), replace:
```python
async with async_session() as sess:
    issue_service = IssueService(sess)
    running = await issue_service.list_by_project(
        project_id,
        status=IssueStatus.REASONING,
    )

if running:
```
with:
```python
active_reasoning = await self._count_active_reasoning(project_id)
if active_reasoning > 0:
```

### Task 4: Remove redundant `create_task` from `add_to_queue`

**Files:**
- Modify: `backend/app/services/issue_queue_service.py:371-373`

**Problem:** `add_to_queue()` emits a `queue_entry_created` event AND separately dispatches `_maybe_auto_start_first` as a fire-and-forget task. The event handler `notify()` → `_on_issue_queued()` also calls `_maybe_auto_start_first`. Both paths converge on the per-project lock, making the second call a no-op. The `create_task` is redundant and its exceptions are silently lost (though the function has its own try/except).

**Fix:** Remove the redundant `create_task` from `add_to_queue()`. The event-driven path handles auto-start reliably.

- [ ] **Step 1: Remove redundant create_task**

In `add_to_queue` (lines 371-373), change:
```python
if self._enabled:
    asyncio.create_task(self._maybe_auto_start_first(project_id, issue_id))
```
to:
```python
# Auto-start is handled by the event-driven _on_issue_queued path
# (triggered by the queue_entry_created event emitted above)
```

### Task 5: Add/update tests

**Files:**
- Modify: `backend/tests/test_issue_queue_service.py`

- [ ] **Step 1: Test `_queue_add_direct` auto-starts when service is available**

Add test that calls `_queue_add_direct` after setting `_enabled = True` on the service and verifies `_maybe_auto_start_first` is triggered (e.g., the issue transitions to REASONING).

- [ ] **Step 2: Test ghost REASONING doesn't block queue**

Add test: create issue in REASONING status with FAILED QueueEntry, add another issue to queue, verify the second issue auto-starts.

- [ ] **Step 3: Test `load_state` KeyError vs Exception**

Mock `SettingsService.get()` to raise `KeyError`, then `Exception`, verify different log output but same fallback (`_enabled = False`).

- [ ] **Step 4: Run all existing tests**

```bash
cd backend
python -m pytest tests/test_issue_queue_service.py -v
```
Expected: all tests pass (existing 63 + new ones).

### Execution

**Option 1: Inline** — execute tasks directly in this session
**Option 2: Subagent** — dispatch subagent per task

Proceeding with inline execution per run-issue workflow.
