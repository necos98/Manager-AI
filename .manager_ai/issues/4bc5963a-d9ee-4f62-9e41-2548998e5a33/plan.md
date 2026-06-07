## Fix pipeline step rejection crash and terminal cleanup

**Goal:** Fix 3 bugs in pipeline_run_service.py that cause MultipleResultsFound crash, race condition on rejection signaling, and silent pipeline hang.

**Architecture:** Single-file fix in pipeline_run_service.py. Change query method, add missing commit in reject_step(), and add outer exception handler in _execute().

### Tasks

1. **Fix 1 — scalar_one_or_none → scalars().first()** at line 275. Safe query when multiple step_runs exist for same (run_id, pipeline_step_id) after rejection.

2. **Fix 2 — commit before signal in reject_step()**. Add `await self.session.commit()` between the update block and `set_step_completed()` call to prevent race condition.

3. **Fix 3 — outer except handler in _execute()**. Add `except Exception` to set run FAILED + emit event, preventing silent hang.

4. **Run tests** — verify no regressions.