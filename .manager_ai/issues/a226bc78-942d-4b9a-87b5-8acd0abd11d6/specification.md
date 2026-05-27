# PipelineRunService + TaskManager + ArtifactService — Specification

## Overview

Implement the backend pipeline execution system: orchestrator service that runs pipeline steps sequentially via PTY terminals, a task registry for managing asyncio background tasks, and an artifact service for sharing files between pipeline steps.

## New Files

### 1. `backend/app/services/pipeline_run_service.py`

Core orchestrator. Takes `AsyncSession` + `TerminalService` as dependencies.

**start(pipeline_id, issue_id, project_id, project_path) → dict**
- Validate: no RUNNING PipelineRun exists for this issue (query DB)
- Load Pipeline with steps (eager load agent)
- Create PipelineRun(status=RUNNING, current_step_index=0)
- Create PipelineStepRun per step (status=PENDING)
- Flush to get IDs
- Launch `_execute(run_id)` via `asyncio.create_task()`
- Register task in PipelineTaskManager
- Return `{run_id, status, steps: [{step_run_id, agent_name, status}]}`

**_execute(run_id) → None**
- Run in background asyncio task
- For each step in order_index:
  1. Set PipelineStepRun.status = RUNNING, flush
  2. Create PTY via `terminal_service.create(issue_id, project_id, project_path, shell=...)`
  3. Resolve variables in terminal_command: `$issue_id`, `$project_id`, `$project_path`
  4. Build full command: `claude -p "<system_prompt> <terminal_command>"` with MANAGER_AI_AGENT_NAME and MANAGER_AI_AGENT_ROLE env vars
  5. Write command to PTY, append output to buffer
  6. Poll PTY for output → `terminal_service.append_output()` in a loop
  7. Detect exit via PTY EOF (read returns empty string after process dies)
  8. Exit code 0 → step_run.status = COMPLETED, update PipelineRun.current_step_index
  9. Exit code != 0 → step_run.status = FAILED, break loop
  10. Cleanup: close PTY, flush DB
- All steps COMPLETED → PipelineRun.status = COMPLETED
- Any step FAILED → PipelineRun.status = FAILED
- Cleanup: PipelineTaskManager.cleanup_task(run_id)
- Set finished_at timestamp

**get_run(run_id) → PipelineRun** with step_runs + agent names

**get_runs_for_issue(issue_id) → list[PipelineRun]**

**cancel_run(run_id) → bool**
- Set run.status = FAILED
- Cancel asyncio task via PipelineTaskManager
- Kill PTY if active

**add_message(run_id, sender_agent_name, content) → PipelineMessage**

**get_messages(run_id) → list[PipelineMessage]**

### 2. `backend/app/services/pipeline_task_manager.py`

Module-level singleton registry. No DB dependency.

**_registry: dict[str, asyncio.Task]**

- `start_task(run_id: str, task: asyncio.Task) → None` — store in registry
- `cancel_task(run_id: str) → None` — task.cancel(), wait for cancellation, remove from registry
- `cleanup_task(run_id: str) → None` — remove from registry
- `get_task(run_id: str) → asyncio.Task | None`
- `active_runs() → list[str]`

Thread safety: all access under `asyncio.Lock`.

### 3. `backend/app/services/artifact_service.py`

Stateless utility. No DB dependency.

**save_artifact(project_path, issue_id, filename, content) → str**
- Resolve path: `<project_path>/.manager_ai/issues/<issue_id>/artifacts/<filename>`
- Create directories if needed
- Write content to file atomically (temp + rename)
- Return full path

**read_artifact(project_path, issue_id, filename) → str**
- Resolve path
- Read and return content
- Raise NotFoundError if file missing

**list_artifacts(project_path, issue_id) → list[str]**
- List files in artifacts directory
- Return sorted filenames
- Return empty list if directory doesn't exist

### 4. `backend/app/routers/pipeline_runs.py`

Prefix: `/api/projects/{project_id}/pipeline-runs`

| Method | Path | Description |
|---|---|---|
| POST | `/` | Start a pipeline run. Body: `{pipeline_id, issue_id}` |
| GET | `/` | List runs for issue. Query: `?issue_id=X` |
| GET | `/{run_id}` | Get run status with step_runs |
| DELETE | `/{run_id}` | Cancel run |
| GET | `/{run_id}/messages` | Get agent chat messages |
| POST | `/{run_id}/messages` | Send message. Body: `{sender_agent_name, content}` |

### 5. `backend/app/schemas/pipeline_run.py`

- `PipelineRunStart` — `{pipeline_id: str, issue_id: str}`
- `PipelineRunResponse` — run fields + `steps: list[PipelineStepRunResponse]`
- `PipelineStepRunResponse` — step_run fields + `agent_name: str`
- `PipelineMessageCreate` — `{sender_agent_name: str, content: str}`
- `PipelineMessageResponse` — message fields

## Modified Files

### `backend/app/main.py`

Add router registration:
```python
from app.routers import pipeline_runs
app.include_router(pipeline_runs.router)
```

Also inject terminal_service into PipelineRunService. The singleton `terminal_service` is already importable from `app.services.terminal_service`.

## Execution Flow

```
POST /api/projects/{id}/pipeline-runs  {pipeline_id, issue_id}
  |
  |- Check no active run for this issue
  |- Create PipelineRun + PipelineStepRuns
  |- asyncio.create_task(_execute(run_id))
  |- Return run status immediately

_execute background task:
  STEP 0: CodebaseExplorer
    |- Create PTY terminal
    |- Write: claude -p "explore codebase..."
    |- Stream output via terminal_service
    |- Wait for EOF
    |- Exit 0 -> COMPLETED, else FAILED -> stop
  STEP 1-N: ... (same pattern)
  All done -> run.status = COMPLETED|FAILED
```

## Edge Cases

- **Double start**: Query DB for existing RUNNING run for same issue before creating new run
- **Server restart**: Orphaned RUNNING runs — add startup cleanup in main.py lifespan that marks them FAILED
- **Step timeout**: Configurable per-step timeout (default 30 min). Subprocess killed on timeout → step FAILED
- **Empty pipeline**: Pipeline with 0 steps → run COMPLETED immediately
- **Missing agent**: Agent referenced by step was deleted → step FAILED with clear error

## Patterns to Follow

- Services receive `AsyncSession` per instance (like PipelineService, AgentService)
- `session.flush()` in services, `session.commit()` in routers
- Use `select()` + `scalar_one_or_none()` for queries
- NotFoundError for missing resources
- Module-level singleton for PipelineTaskManager (like TerminalService)
- Atomic file writes via temp + rename for ArtifactService
