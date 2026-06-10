## Recap: Queue Auto-Resume After Restart

### Changes made

**1. `backend/app/services/issue_queue_service.py`** — Added `startup_resume()` method:
- Queries distinct project IDs from `QueueEntry` where `status = PENDING`
- For each project, checks if any issue is currently running (REASONING status)
- If nothing is running, fires `_dequeue_and_run(project_id)` as a fire-and-forget task
- Fully wrapped in try/except — failures are logged, never crash startup

**2. `backend/app/main.py`** — Changed `_ = IssueQueueService()` to `issue_queue_service = IssueQueueService()` and added `asyncio.create_task(issue_queue_service.startup_resume())` immediately after, so the queue resumes at startup.

### Edge cases handled
- No pending QueueEntries → no-op, just debug log
- A project has pending entries but an issue is already running → skip that project
- Multiple projects with pending entries → each checked independently
- Exception in one project → logged, doesn't block other projects
- Fire-and-forget task → startup doesn't wait for queue processing

### Verification
- Syntax check passed on both modified files
- `startup_resume()` method found in IssueQueueService class
- Module imports cleanly
- All 3 tasks completed (method added, wiring in main.py, verification)