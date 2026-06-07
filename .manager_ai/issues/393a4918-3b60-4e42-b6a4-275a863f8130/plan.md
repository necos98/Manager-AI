# Implementation Plan: Fix pipeline start race condition

## File affected

`backend/app/services/pipeline_run_service.py` only.

## Change 1: Swap order in `start()` (lines 101-109)

Move `asyncio.create_task(self._execute(...))` and `pipeline_task_manager.start_task(run.id, task)` **before** `await self.session.commit()`.

**Before (lines 101-109):**
```
# Commit so _execute()'s new session can see the run.
await self.session.commit()

task = asyncio.create_task(self._execute(run.id, project_id, project_path))
await pipeline_task_manager.start_task(run.id, task)
```

**After:**
```
task = asyncio.create_task(self._execute(run.id, project_id, project_path))
await pipeline_task_manager.start_task(run.id, task)

# Commit so _execute()'s new session can see the run.
await self.session.commit()
```

If crash happens before commit → transaction rolls back → run never persisted as RUNNING. No zombie.

## Change 2: Add retry loop in `_execute()` (replace line 253)

After the swap, `_execute()` can be scheduled and run before `commit()` finishes. Replace the single `_get_run_with_session` call with a retry loop that waits up to 5 seconds for data:

```python
run = None
for attempt in range(50):
    try:
        run = await self._get_run_with_session(run_id, session)
        break
    except NotFoundError:
        await asyncio.sleep(0.1)
if run is None:
    logger.error("Pipeline run %s not found — _execute started before commit finished", run_id)
    return
```

Normal case adds ~100ms delay. Exhaustion = log + return silently (no crash).

## Change 3: Update stale project memories

Old memories `063ac32c` and `09ac88a3` document the previous fix (add commit before create_task). This fix supersedes that approach. Update both to reflect the new pattern: create_task first, commit after, with retry loop for timing safety.

## Acceptance criteria

1. Crash between create_task and commit leaves no stuck RUNNING run in DB
2. _execute() finds run data even when it runs before commit() completes
3. Existing pipeline runs start and execute normally
4. HTTP response unchanged
5. Clear error log if retry loop exhausts

## Non-goals (verified against spec)

- No changes to pipeline_task_manager, session_factory(), session management pattern
- No changes to start_pipeline endpoint or router
- No test changes in this scope
- No refactoring beyond the swap
- No changes to pipeline_service.py or other services
