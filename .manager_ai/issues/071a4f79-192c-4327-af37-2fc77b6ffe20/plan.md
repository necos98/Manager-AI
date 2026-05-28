# Implementation Plan: Remove project_id from Agent and Pipeline

## Files Map

### Backend - Models (3 files)
- **Modify** `backend/app/models/agent.py` — remove `project_id` column, `UniqueConstraint`, `project` relationship
- **Modify** `backend/app/models/pipeline.py` — remove `project_id` column, `project` relationship
- **Modify** `backend/app/models/project.py` — remove `agents` and `pipelines` relationships

### Backend - Schemas (2 files)
- **Modify** `backend/app/schemas/agent.py` — remove `project_id` from `AgentResponse`
- **Modify** `backend/app/schemas/pipeline.py` — remove `project_id` from `PipelineResponse`

### Backend - Services (2 files)
- **Modify** `backend/app/services/agent_service.py` — remove `project_id` params, query filters
- **Modify** `backend/app/services/pipeline_service.py` — remove `project_id` params, query filters

### Backend - Routers (3 files)
- **Modify** `backend/app/routers/agents.py` — top-level prefix `/api/agents`, drop `project_id` params
- **Modify** `backend/app/routers/pipelines.py` — top-level prefix `/api/pipelines`, drop `project_id` params
- **Modify** `backend/app/routers/pipeline_runs.py` — keep `project_id` (needed for terminal creation + event emission)

### Backend - MCP (1 file)
- **Modify** `backend/app/mcp/server.py` — remove `project_id` from agent/pipeline tools (keep on `run_pipeline`)

### Backend - Main (1 file)
- **Modify** `backend/app/main.py` — update router registration, remove per-project seed loop for agents/pipelines

### Backend - Migration (1 new file)
- **Create** Alembic migration — drop `project_id` column + index + FK from `agents` and `pipelines`

### Frontend - Types (1 file)
- **Modify** `frontend/src/shared/types/index.ts` — remove `project_id` from `Agent` and `Pipeline`

### Frontend - Features (6 files)
- **Modify** `frontend/src/features/agents/api.ts` — drop `projectId` param
- **Modify** `frontend/src/features/agents/hooks.ts` — drop `projectId` from query keys
- **Modify** `frontend/src/features/agents/components/AgentsTab.tsx` — drop `projectId` prop
- **Modify** `frontend/src/features/pipelines/api.ts` — drop `projectId` param
- **Modify** `frontend/src/features/pipelines/hooks.ts` — drop `projectId` from query keys
- **Modify** `frontend/src/features/pipelines/components/PipelinesTab.tsx` — drop `projectId` prop

### Frontend - Pipeline Runs (keep projectId — issue is project-scoped)
- **Modify** `frontend/src/features/pipeline-runs/api.ts` — keep `projectId` (runs still scoped to project)
- **Modify** `frontend/src/features/pipeline-runs/hooks.ts` — keep `projectId` in query keys
- **Modify** `frontend/src/features/pipeline-runs/components/PipelineRunButton.tsx` — keep `projectId`, but agents list from global API
- **Modify** `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx` — keep `projectId`
- **Modify** `frontend/src/features/pipeline-runs/components/AgentChat.tsx` — keep `projectId`

### Frontend - Routes (2 files)
- **Modify** `frontend/src/routes/projects/$projectId/agents.tsx` → **Create** `frontend/src/routes/agents.tsx` (top-level)
- **Modify** `frontend/src/routes/projects/$projectId/pipelines.tsx` → **Create** `frontend/src/routes/pipelines.tsx` (top-level)
- **Modify** `frontend/src/routes/__root.tsx` — add Agents/Pipelines to main nav

### Frontend - Event Context (1 file)
- **Modify** `frontend/src/shared/context/event-context.tsx` — no change needed (pipeline-run keys use `data.project_id`, which still exists on PipelineRun events)

### Tests (2 files)
- **Modify** `backend/tests/test_models_pipeline.py` — drop `project_id` from Agent/Pipeline constructors
- **Modify** `backend/tests/test_pipeline_run_service.py` — drop `project_id` from Agent/Pipeline constructors

### Documentation (1 file)
- **Modify** `docs/agent-pipeline-architecture.md` — update to reflect global scope

---

## Tasks

### Task 1: Alembic Migration
Create migration to drop `project_id` column, index, and FK from `agents` and `pipelines` tables. Drop `uq_agent_project_name` unique constraint.

### Task 2: Backend Models
Remove `project_id` from Agent, Pipeline. Remove `agents`/`pipelines` relationships from Project.

### Task 3: Backend Schemas
Remove `project_id` from `AgentResponse` and `PipelineResponse` Pydantic models.

### Task 4: Backend Services
Update `AgentService`: remove `project_id` from `create()`, `list_by_project()`, `get_by_name()`, `seed_defaults()`. Update `PipelineService`: remove `project_id` from `create_pipeline()`, `list_by_project()`, `seed_defaults()`.

### Task 5: Backend Routers — Agents & Pipelines
Move agents router to `/api/agents`, pipelines router to `/api/pipelines`. Remove all `project_id` route params. Update `_response()` helpers.

### Task 6: Backend Routers — Pipeline Runs
Remove `project_id` from pipeline-runs URL prefix. Keep `project_id` as internal param (from `manager.json` or issue lookup) for terminal creation and events.

### Task 7: Backend MCP Server
Remove `project_id` param from `create_agent`, `list_agents`, `create_pipeline`, `list_pipelines`. Keep on `run_pipeline`.

### Task 8: Backend main.py
Register agents/pipelines routers without project prefix. Change seed loop: seed defaults once (not per-project), or remove seed entirely and rely on `/seed` endpoints.

### Task 9: Frontend Types & API Layer
Remove `project_id` from `Agent` and `Pipeline` interfaces. Update agents API, pipelines API, hooks, and tab components to not require `projectId`.

### Task 10: Frontend Routes & Navigation
Create top-level `agents.tsx` and `pipelines.tsx` routes. Add Agents and Pipelines to main navigation in `__root.tsx`.

### Task 11: Update Tests
Remove `project_id` from Agent/Pipeline constructors in all test files. Update test assertions.

### Task 12: Update Documentation
Update `docs/agent-pipeline-architecture.md` to reflect global scope.

### Task 13: Verify & Finalize
Run full test suite, verify frontend builds, run pipeline execution smoke test.
