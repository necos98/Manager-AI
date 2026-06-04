## Recap

**Bug:** Pipeline infinite loops on first agent after reject_status implementation.

**Root Cause:** When `_execute()` was refactored from for-loop to while-loop (driven by `run.current_step_index`) to support step rejection/regression, the `run.current_step_index += 1` increment for normal step completion was omitted. After each successful step completion, the while-loop variable never advanced, causing the same step to restart infinitely.

**Fix:** Added `run.current_step_index += 1` at `backend/app/services/pipeline_run_service.py:332`, after `step_run.status = PipelineStepRunStatus.COMPLETED`.

**Verification:** All 24 pipeline tests pass (models, rejection, run service).

**Note:** Memory `9310761a` had previously documented this exact bug pattern during the rejection feature code review, but the fix was never applied to the code until now.