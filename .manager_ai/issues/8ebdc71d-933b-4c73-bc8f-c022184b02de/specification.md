## Root Cause

Two bugs combine to cause the 503 "Queue service not initialized" error:

### Bug 1: Module-level import creates stale `None` reference
In `backend/app/routers/queue.py`, `issue_queue_service_ref` is imported at the module level:
```python
from app.services.issue_queue_service import issue_queue_service_ref
```
In Python, `from X import var` creates a **local copy** of the value at import time. At module load time, `issue_queue_service_ref` is `None` (the initial module-level assignment). Later, when `IssueQueueService.__init__()` runs during lifespan startup and does `issue_queue_service_ref = self`, it only modifies the **source module's** attribute. The local binding in `queue.py` remains `None` forever.

The same pattern in `shared_tools.py` already fixed this correctly — it uses **lazy imports inside function bodies**, which re-evaluates the module attribute each call.

This affects ALL queue endpoints:
- `POST /api/queue/add` (add_to_queue)
- `POST /api/queue/remove` (remove_from_queue)
- `POST /api/queue/auto-process` (set_auto_process)
- `GET /api/queue/position/{issue_id}` (get_queue_position)

### Bug 2: DB schema mismatch causes startup failure
The database schema is out of sync with the models:
- `pipeline_runs` is missing `rejection_count` column
- `agents` is missing `intent` column
- `agents` still has `system_prompt` (should have been dropped)

These cause `_startup_cleanup_orphaned_runs()` and `_startup_seed_defaults()` to raise `OperationalError`, causing the entire startup try-block (main.py:298-337) to be caught by the broad except handler at line 338. `IssueQueueService()` at line 306 is **never executed**, so `issue_queue_service_ref` stays `None`.

## Fix

1. **queue.py**: Replace module-level import with lazy imports inside each function body — same pattern as `shared_tools.py`. Affects 4 functions.
2. **DB schema**: Fix the database by adding the missing columns (rejection_count on pipeline_runs, intent on agents) and dropping the extraneous system_prompt column from agents. This can be done via a new Alembic migration.
