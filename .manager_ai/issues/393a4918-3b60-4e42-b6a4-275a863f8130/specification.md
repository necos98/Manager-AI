# Fix race condition in pipeline start — commit before create_task leaves stuck runs

## Scope

Fix two race conditions in `PipelineRunService.start()` and `_execute()` in `backend/app/services/pipeline_run_service.py`:

1. **Crash window gap**: `commit()` runs before `asyncio.create_task(self._execute())`. A crash or cancellation between these two lines persists the run as RUNNING in the DB but the background task never starts — pipeline stuck forever, caller sees HTTP 201 success.
2. **Early-execution race**: Swapping to `create_task`-first introduces a new race where `_execute()` runs before `commit()` finishes, queries with its own session, finds no data, and raises `NotFoundError`.

## Constraints

- No change to the public API signature of `PipelineRunService.start()`
- No change to the `_execute()` error handling structure — only the initial `_get_run_with_session` call gets a retry loop
- The caller (`start_pipeline` in `pipeline_service.py`) must still receive a valid `PipelineRunResponse` on success
- Must handle server crash between `create_task` and `commit` without leaving zombie RUNNING runs

## Requirements

### R1: Swap order in `start()`

Reorder lines 104-109 in `pipeline_run_service.py` so `create_task` and `start_task` execute **before** `commit()`:

```
Before: commit → create_task → start_task
After:  create_task → start_task → commit
```

This eliminates the crash window where the DB says RUNNING but `_execute` was never spawned. If crash happens before commit, the transaction rolls back — the run is never persisted as RUNNING.

### R2: Add retry loop in `_execute()`

Replace the single `_get_run_with_session(run_id, session)` call at line ~253 with a retry loop that waits up to 5 seconds for the run data to appear:

- Retry up to 50 times with 100ms delay between attempts
- On success, break and proceed normally
- On exhaustion, log an error and `return` (do not crash or propagate)

This handles the timing window where `_execute` is scheduled and runs before the outer `commit()` completes. Normal case adds ~100ms delay.

## Non-goals

- No changes to `pipeline_task_manager`, `session_factory()`, or the session management pattern
- No changes to the `start_pipeline` endpoint or router
- No test changes in this scope
- No refactoring of the `start()` method beyond the swap
- No changes to `pipeline_service.py` or other services

## Acceptance criteria

1. A server crash between `create_task` and `commit` does not leave a stuck RUNNING pipeline in the DB
2. `_execute()` reliably finds the run data even when it runs before `commit()` completes
3. Existing pipeline runs start and execute normally (no regression)
4. No change to the HTTP response the caller receives
5. Error logs are clear and actionable if the retry loop exhausts
