## Fix: Add missing current_step_index increment after step completion

**Goal:** Fix pipeline infinite loop by incrementing `run.current_step_index` after a step completes successfully.

**Root Cause:** In `PipelineRunService._execute()` (pipeline_run_service.py:262), the while-loop is driven by `run.current_step_index`. When converting from for-loop to while-loop during the rejection feature implementation, the `run.current_step_index += 1` for normal step completion was omitted. After each successful step, the loop variable never advances, causing the same step to restart infinitely.

**Fix:** One line addition at pipeline_run_service.py:331 — add `run.current_step_index += 1` after `step_run.status = PipelineStepRunStatus.COMPLETED`.

**Risk:** Low. Single line. Rejection and failure paths unaffected. Rejection already sets index via `reject_step()`, failure does `break`.

### Task 1: Add missing increment & test

**Files:**
- Modify: `backend/app/services/pipeline_run_service.py:330-332`

**Steps:**
1. Add `run.current_step_index += 1` after line 331
2. Run existing pipeline tests to verify
3. Commit