Fixed 3 bugs in pipeline_run_service.py caused by step rejection:

1. **scalar_one_or_none → scalars().first() at line 275**: reject_step() creates new PipelineStepRun for the same (run_id, pipeline_step_id) pair, making queries non-unique. `scalar_one_or_none()` crashed with MultipleResultsFound. Changed to `scalars().first()` with existing ORDER BY.

2. **Missing commit before signal in reject_step()**: reject_step() called `set_step_completed()` to wake _execute() but only flushed — never committed. _execute()'s session.refresh() saw stale pre-rejection data, incorrectly marking the step COMPLETED instead of detecting REJECTED. Added `await self.session.commit()` before the signal.

3. **Outer _execute() missing except Exception handler**: The MultipleResultsFound crash at line 275 propagated unhandled (outer try only caught CancelledError). Pipeline stayed RUNNING in DB silently — no FAILED event, no error visible. Added `except Exception` handler that sets run FAILED, commits, and emits pipeline_completed event.

All 8 pipeline tests pass (teardown DB lock warnings are pre-existing infrastructure issue).