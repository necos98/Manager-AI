## Queue auto-resume after restart

### Problem
When Manager AI is shut down and restarted, the issue queue does not automatically resume processing QUEUED issues. The system is purely event-driven: `IssueQueueService` registers as an event listener at startup but never scans for already-queued issues. Users must manually add a new issue to "wake up" the queue.

### Root Cause
In `backend/app/main.py:306`, the line `_ = IssueQueueService()` only registers the listener on EventService. There is no startup scan of existing QUEUED issues / pending QueueEntries to trigger the first dequeue.

The queue system relies on events:
- `issue_queued` → `_on_issue_queued` → `_maybe_auto_start_first` (works when a new issue is added after startup)
- `issue_finished` → `_on_issue_finished` → `_dequeue_and_run` (works when an issue completes)
- **No event fires at startup** for issues that were already QUEUED before shutdown — they remain in limbo.

### Solution
1. **Add `startup_resume()` method to `IssueQueueService`** that:
   - Queries distinct project IDs from `QueueEntry` where status = `PENDING`
   - For each such project, checks if any issue is currently running (REASONING status)
   - If nothing is running, fires `_dequeue_and_run` for that project
   - Catches and logs exceptions so a single failure doesn't block startup

2. **Call `startup_resume()` in `main.py`** immediately after `_ = IssueQueueService()` on line 306, as a fire-and-forget `asyncio.create_task()` (non-blocking to startup).

### Files to modify
- `backend/app/services/issue_queue_service.py` — add `startup_resume()` method
- `backend/app/main.py` — call `startup_resume()` after IssueQueueService registration

### Why not scan `QUEUED` issue status directly?
The QueueEntry table is the authoritative registry. A `QUEUED` status on the issue might exist without a corresponding pending QueueEntry (e.g., if the registry was already dispatched). Using QueueEntry ensures we only auto-start issues that are truly pending in the queue.
