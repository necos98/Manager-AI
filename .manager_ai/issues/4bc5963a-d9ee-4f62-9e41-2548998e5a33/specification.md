## Pipeline step rejection: crash + race condition + silent hang

### Problem

When `reject_step()` fires in a running pipeline, three bugs cascade:

1. **`scalar_one_or_none()` crash (line 275).** `reject_step()` creates a new `PipelineStepRun` for the target `(run_id, pipeline_step_id)` pair. The next while-loop iteration queries by that pair and finds 2+ rows. `scalar_one_or_none()` raises `MultipleResultsFound`.

2. **Signal-before-commit race (reject_step, ~line 234).** `reject_step()` calls `set_step_completed()` to wake `_execute()`, but has only `flush()`ed — no `commit()`. `_execute()` refreshes from DB, sees stale pre-rejection state, incorrectly marks the step COMPLETED instead of detecting REJECTED.

3. **Outer try has no `except Exception` handler.** The MultipleResultsFound (and any other non-CancelledError) propagates unhandled from `_execute()`. Pipeline stays RUNNING in DB, no FAILED event emitted, no error visible. Logged only as "Task exception was never retrieved".

### Fixes

- **Fix 1 — `pipeline_run_service.py:275`**: Replace `step_run_result.scalar_one_or_none()` with `step_run_result.scalars().first()`. The query already has ORDER BY `started_at DESC NULLS LAST`, so the first row is the latest.

- **Fix 2 — `pipeline_run_service.py:reject_step()`**: Add `await self.session.commit()` between the flush/update block and `set_step_completed()` call. Ensures `_execute()`'s session.refresh() sees committed data (REJECTED status, new step_run, updated current_step_index).

- **Fix 3 — `_execute()` outer except block (~line 417)**: Add `except Exception` handler that sets `run.status = FAILED`, `run.finished_at = now`, emits `pipeline_completed` event with status `failed`, and logs the error. Prevents silent hangs.

### Testing

- **Unit test**: Create pipeline run, reject a step, verify step_run query returns latest row without crash.
- **Integration**: Full pipeline with step rejection — verify pipeline ends in FAILED status, events fire, terminal cleaned up.
- **Regression**: Normal pipeline (no rejection) still completes successfully.