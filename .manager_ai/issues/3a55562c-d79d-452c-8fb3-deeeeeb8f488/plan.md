## Plan: Fix pipeline terminal_id type mismatch

### Root Cause
`pipeline_step_runs.terminal_id` is `Integer` with FK to `terminal_commands.id`, but `PipelineRunService._execute()` assigns a UUID string from `terminal_service.create_log()`. DB flush fails silently, `terminal_id` stays `NULL`, frontend never renders `TerminalPanel`.

### Files to modify

| Action | File | Change |
|--------|------|--------|
| Create | `backend/alembic/versions/<new>_fix_pipeline_step_runs_terminal_id_to_string.py` | Migration: ALTER column, drop FK |
| Modify | `backend/app/models/pipeline_run.py:48` | `Integer` FK → `String(36)` |
| Modify | `backend/app/schemas/pipeline_run.py:15` | `int \| None` → `str \| None` |
| Modify | `frontend/src/shared/types/index.ts:556` | `number \| null` → `string \| null` |
| Modify | `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx:79-92` | Store `event.terminal_id` from WebSocket event |

### Tasks

1. **Create Alembic migration** — ALTER `pipeline_step_runs.terminal_id` from `Integer` to `String(36)`, drop FK constraint
2. **Fix model** — Change `terminal_id` column type in `pipeline_run.py`, remove FK + relationship
3. **Fix backend schema** — Change `terminal_id` type in `pipeline_run.py` Pydantic schema
4. **Fix frontend types** — Change `terminal_id` from `number` to `string` in TypeScript interface
5. **Fix frontend PipelineProgress** — Use `event.terminal_id` from WebSocket for immediate terminal display
6. **Run migration and verify** — Apply migration, start server, run pipeline, confirm terminal appears