## Problem

Pipeline run terminal never appears. User starts pipeline, sees no terminal output, gets no error.

## Root Cause

`pipeline_step_runs.terminal_id` is defined as `Integer` with ForeignKey to `terminal_commands.id`. But `PipelineRunService._execute()` assigns a UUID string (from `terminal_service.create_log()`) to this column. SQLAlchemy flush fails with `ValueError`, caught silently by `_safe_flush_session`, transaction rolls back, `terminal_id` stays `NULL`. Frontend polls API, gets `terminal_id: null`, never renders `TerminalPanel`.

**File**: `backend/app/services/pipeline_run_service.py:159`
```python
step_run.terminal_id = term_id  # term_id is UUID string, column is Integer
```

## Fix

### 1. Database migration
- New Alembic migration to change `pipeline_step_runs.terminal_id` from `Integer` to `String(36)`
- Drop the ForeignKey constraint to `terminal_commands.id` — pipeline terminals are in-memory log sessions, not persisted `terminal_commands` rows

### 2. Model update
- `backend/app/models/pipeline_run.py`: Change `terminal_id` column from `Integer` to `String(36)`, remove `ForeignKey("terminal_commands.id")`

### 3. Schema update
- `backend/app/schemas/pipeline_run.py`: Change `terminal_id` type from `int | None` to `str | None`

### 4. Frontend immediate terminal display (bonus)
- `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx`: In `agent_step_started` event handler, also store `event.terminal_id` so `TerminalPanel` mounts immediately without waiting for next API poll

## Verification

1. Create a pipeline with at least one agent step
2. Run the pipeline on an issue
3. Terminal panel should appear showing agent output as it streams
4. Check that `agent_step_started` WebSocket event delivers `terminal_id` and frontend uses it immediately