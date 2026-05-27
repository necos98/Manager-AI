## Recap

### Root Cause
`pipeline_step_runs.terminal_id` was defined as `Integer` with FK to `terminal_commands.id`, but the code assigned a UUID string from `terminal_service.create_log()`. SQLAlchemy silently failed on flush (caught by `_safe_flush_session`), transaction rolled back, `terminal_id` stayed NULL. Frontend polled API, got `terminal_id: null`, never rendered `TerminalPanel`.

### Changes Made

1. **Migration** (`f0b1c2d3e4f5_fix_pipeline_step_runs_terminal_id_to_.py`): Recreated `pipeline_step_runs` table with `terminal_id` as `VARCHAR(36)` instead of `INTEGER`, removed FK to `terminal_commands`.

2. **Model** (`backend/app/models/pipeline_run.py:48`): Changed `terminal_id` from `Mapped[Optional[int]]` with `Integer + ForeignKey` to `Mapped[Optional[str]]` with `String(36)`. Removed `terminal = relationship("TerminalCommand")`.

3. **Schema** (`backend/app/schemas/pipeline_run.py:15`): Changed `terminal_id` from `int | None` to `str | None`.

4. **Frontend types** (`frontend/src/shared/types/index.ts:556`): Changed `terminal_id` from `number | null` to `string | null`.

5. **Frontend PipelineProgress** (`frontend/src/features/pipeline-runs/components/PipelineProgress.tsx`): Added `terminalIds` state map to store terminal IDs from WebSocket `agent_step_started` events, enabling immediate terminal display without waiting for next API poll.

### Why Pipeline Terminals Are Not terminal_commands
Pipeline step terminals are in-memory log sessions (no PTY) created via `terminal_service.create_log()`. They are ephemeral and destroyed after each step. They never correspond to persisted `terminal_commands` rows, so the FK was always wrong.