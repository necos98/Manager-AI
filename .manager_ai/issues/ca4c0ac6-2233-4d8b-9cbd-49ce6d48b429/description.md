The pipeline orchestrator that executes pipeline steps sequentially by spawning Claude Code terminals.

**PipelineExecutorService:**
1. `start_pipeline(pipeline_id, issue_id)` — entry point:
   - Creates a `pipeline_run` record (status=RUNNING, current_step_index=0)
   - Creates `pipeline_step_run` records for all steps (status=PENDING)
   - Starts the first step via `_run_step(pipeline_step_run_id)`

2. `_run_step(pipeline_step_run_id)`:
   - Sets step_run status = RUNNING, updates pipeline_run.current_step_index
   - Creates a new terminal (PTY) with:
     - The step's `terminal_command` (resolved with $ISSUE_ID, $PIPELINE_RUN_ID, $STEP_ID variables)
     - Env vars injected: `MANAGER_AI_PIPELINE_RUN_ID`, `MANAGER_AI_PIPELINE_STEP_RUN_ID`
   - Associates terminal with step_run and issue
   - Emits WebSocket event: `pipeline_step_started`

3. `complete_step(pipeline_step_run_id)` — called by MCP tool or hook:
   - Sets step_run status = COMPLETED
   - If next step exists: calls `_run_step(next_step_run_id)`
   - If last step: marks pipeline_run as COMPLETED, emits `pipeline_completed`
   - Emits WebSocket event: `pipeline_step_completed`

4. `fail_step(pipeline_step_run_id, error)` — called on terminal close with non-zero exit:
   - Sets step_run status = FAILED, pipeline_run status = FAILED
   - Emits WebSocket event: `pipeline_step_failed`

**WebSocket events (realtime frontend updates):**
- `pipeline_started`
- `pipeline_step_started`
- `pipeline_step_completed`
- `pipeline_step_failed`
- `pipeline_completed`
- `pipeline_message_sent`

**PipelineRun GET endpoint:**
- `GET /api/pipeline-runs/{id}` — full status with steps and their current status
- `GET /api/issues/{issue_id}/pipeline-runs` — list pipeline runs for an issue

**Edge cases:**
- Cannot start pipeline if another pipeline is already RUNNING on the same issue
- Step timeout configurable per pipeline (default: no timeout)
- On backend startup, stale RUNNING steps should be marked as FAILED
- Terminal close event updates step_run accordingly