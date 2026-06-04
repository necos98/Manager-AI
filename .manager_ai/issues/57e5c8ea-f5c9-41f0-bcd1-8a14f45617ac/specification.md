## Bug Analysis: Pipeline Infinite Loop on First Agent

### Symptom
When a pipeline starts, the first agent step completes but the loop immediately restarts the same agent. This repeats forever with no rejection — the agent runs → finishes → loop restarts → agent runs again.

### Root Cause
`PipelineRunService._execute()` uses a while-loop driven by `run.current_step_index` (refactored from a for-loop during the rejection feature implementation). After a step completes successfully, `current_step_index` is **never incremented**, so the while-loop condition `run.current_step_index < len(steps)` stays true on the same index forever.

Location: `backend/app/services/pipeline_run_service.py`, line ~331:
```python
if success:
    step_run.status = PipelineStepRunStatus.COMPLETED
    # MISSING: run.current_step_index += 1
```

### Additional Context
Memory `9310761a` previously documented this exact pattern: "When converting _execute() from for-loop to while-loop, the run.current_step_index += 1 for normal step completion was omitted." The fix was documented but never applied to the code.

### Fix
Add `run.current_step_index += 1` after setting `step_run.status = PipelineStepRunStatus.COMPLETED` (around line 331). This ensures the while-loop advances to the next step on success.

No change needed for:
- **Rejection**: `reject_step()` already sets `current_step_index = target_step_index`, code does `continue`
- **Failure**: `run.status = FAILED` + `break` exits the loop

### Risk Assessment
Low risk. Single line addition. The rejection and failure code paths are unaffected. Tests at `backend/tests/` cover pipeline runs — verify they still pass.