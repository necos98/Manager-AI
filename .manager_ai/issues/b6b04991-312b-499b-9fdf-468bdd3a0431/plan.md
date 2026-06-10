## Implementation Plan: Queue Auto-Resume After Restart

### Overview
Two small changes: add `startup_resume()` to `IssueQueueService` and call it from `main.py` during lifespan startup.

### Task 1: Add `startup_resume()` to IssueQueueService
- File: `backend/app/services/issue_queue_service.py`
- New method `async def startup_resume(self) -> None`
- Query distinct `project_id` from `QueueEntry` where `status = PENDING`
- For each project, check if any issue is in REASONING (running) via `issue_service.list_by_project`
- If nothing is running, fire `asyncio.create_task(self._dequeue_and_run(project_id))`
- Wrap everything in try/except with logger.exception so failures don't crash startup

### Task 2: Call `startup_resume()` from main.py
- File: `backend/app/main.py`
- After line 306 (`_ = IssueQueueService()`), add:
  ```python
  # Resume queue processing: auto-start pending QUEUED issues
  asyncio.create_task(issue_queue_service.startup_resume())
  ```
- Need to capture the IssueQueueService instance: change `_ = IssueQueueService()` to `issue_queue_service = IssueQueueService()`

### Verification
- Import the module and verify syntax
- Check that `startup_resume()` logically handles the edge cases:
  - No pending QueueEntries → no-op
  - A project has pending QueueEntry but issue is already running → skip that project
  - Multiple projects with pending entries → each checked independently
  - Exception in one project → logged, not blocking other projects
