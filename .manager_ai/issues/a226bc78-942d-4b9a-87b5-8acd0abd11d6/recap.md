## Summary
Implemented PipelineRunService (orchestrator), PipelineTaskManager (asyncio task registry), and ArtifactService (artifact file I/O) for the agent pipeline system.

## Files Created
- `backend/app/services/pipeline_run_service.py` — Core orchestrator: start(), _execute() loop with subprocess spawning, exit code detection, session management
- `backend/app/services/pipeline_task_manager.py` — Module-level singleton registry for asyncio background tasks with cancel/cleanup
- `backend/app/services/artifact_service.py` — Static file I/O: save/read/list artifacts under `.manager_ai/issues/{id}/artifacts/`
- `backend/app/routers/pipeline_runs.py` — REST endpoints: POST start, GET status/list, DELETE cancel, GET/POST messages
- `backend/app/schemas/pipeline_run.py` — Pydantic models: PipelineRunStart, PipelineRunResponse, PipelineStepRunResponse, PipelineMessageCreate/Response
- `backend/tests/test_pipeline_run_service.py` — 8 tests covering start, double-start rejection, status, messages, cancel, and empty pipeline

## Files Modified
- `backend/app/schemas/__init__.py` — Export new pipeline_run schemas
- `backend/app/main.py` — Register pipeline_runs router + startup orphan cleanup (RUNNING → FAILED)

## Key Decisions
- **Session factory pattern**: PipelineRunService accepts optional session_factory for background _execute() to create its own DB session. Router passes async_session; tests pass None (shared session). This avoids stale/corrupted sessions in production.
- **Subprocess + log terminal**: Uses asyncio.create_subprocess_shell + terminal_service.create_log() for streaming. Not PTY — subprocess pipes are simpler and log terminals already support WebSocket streaming.
- **CancelledError handling**: _run_step() kills subprocess and cancels stream task on CancelledError (from PipelineTaskManager.cancel_task). _execute() cleanly exits without touching DB on cancel.
- **Startup cleanup**: Orphaned RUNNING PipelineRuns are marked FAILED on server restart in main.py lifespan.
- **Minimal ArtifactService**: Static methods, no DB. Simple filesystem I/O to `.manager_ai/issues/{id}/artifacts/`.
