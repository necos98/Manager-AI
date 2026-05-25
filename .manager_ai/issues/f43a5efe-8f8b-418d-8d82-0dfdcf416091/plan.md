# Implementation Plan: Remove Agents & Pipeline Feature

## Task 1: Delete Backend Agent/Pipeline Files (10 files)

**Files to delete:**
- `backend/app/models/agent.py`
- `backend/app/models/agent_message.py`
- `backend/app/models/pipeline.py`
- `backend/app/schemas/agent.py`
- `backend/app/schemas/agent_message.py`
- `backend/app/schemas/pipeline.py`
- `backend/app/routers/agents.py`
- `backend/app/routers/pipelines.py`
- `backend/app/services/orchestrator_service.py`
- `backend/app/hooks/executor.py`

- [ ] Delete all 10 files
- [ ] Commit: `feat: remove agent/pipeline backend files`

## Task 2: Clean Backend Models __init__.py

**File:** `backend/app/models/__init__.py`

- [ ] Remove line 3: `from app.models.agent import Agent`
- [ ] Remove line 4: `from app.models.agent_message import AgentMessage`
- [ ] Remove line 9: `from app.models.pipeline import AgentStepRun, Pipeline, PipelineRun`
- [ ] Remove `"Agent"`, `"AgentMessage"`, `"AgentStepRun"`, `"Pipeline"`, `"PipelineRun"` from `__all__` list
- [ ] Commit: `feat: remove agent/pipeline model imports`

## Task 3: Clean Backend main.py

**File:** `backend/app/main.py`

- [ ] Line 27: remove `agents,` and `pipelines,` from router import
- [ ] Lines 311-317: remove zombie cleanup block (`from app.services.orchestrator_service import OrchestratorService` + `cleanup_zombie_runs` call)
- [ ] Lines 411-412: remove `app.include_router(agents.router)` and `app.include_router(pipelines.router)`
- [ ] Commit: `feat: remove agent/pipeline from main.py`

## Task 4: Clean Backend Routers

**File:** `backend/app/routers/issues.py`

- [ ] Line 16: remove `from app.services.orchestrator_service import OrchestratorService`
- [ ] Lines 123-142: remove `start_pipeline_for_issue` endpoint

**File:** `backend/app/routers/library.py`

- [ ] Lines 16-18: remove `list_agents` endpoint
- [ ] Lines 26-28: remove `get_agent` endpoint
- [ ] Lines 36-38: remove `create_agent` endpoint
- [ ] Lines 46-48: remove `update_agent` endpoint

- [ ] Commit: `feat: remove agent/pipeline router endpoints`

## Task 5: Clean SkillLibraryService

**File:** `backend/app/services/skill_library_service.py`

- [ ] `_dir()` method (line 39-40): remove `"agents"` branch, only return `skills` dir
- [ ] `_update_claude_md()` method: remove lines 183-195 (agent_lines build and "Active Agents" section)
- [ ] `get_skills_context()` method: remove lines 238-242 (agents_dir reading)
- [ ] `assign()` method: remove agent directory references in path construction (line 135)
- [ ] `unassign()` method: remove agent directory references (line 159)
- [ ] Commit: `feat: remove agent type from SkillLibraryService`

## Task 6: Clean MCP Server Tools

**File:** `backend/app/mcp/server.py`

- [ ] Remove imports of Agent, AgentMessage, Pipeline models/schemas and OrchestratorService
- [ ] Remove MCP tools: `list_agents`, `create_agent`, `update_agent`, `delete_agent`
- [ ] Remove MCP tools: `list_pipelines`, `create_pipeline`, `update_pipeline`, `delete_pipeline`
- [ ] Remove MCP tools: `send_agent_message`, `get_agent_messages`
- [ ] Remove MCP tools: `complete_agent_step`, `get_pipeline_status`, `start_pipeline`
- [ ] Remove any remaining agent/pipeline helper functions

**File:** `backend/app/mcp/default_settings.json`

- [ ] Remove agent tool descriptions (lines 61-73 area)
- [ ] Remove pipeline tool descriptions
- [ ] Clean "pipeline" references from remaining tool descriptions

- [ ] Commit: `feat: remove agent/pipeline MCP tools`

## Task 7: Database Migration

- [ ] Run: `cd backend && python -m alembic revision --autogenerate -m "drop_agents_pipelines_tables"`
- [ ] Review generated migration to ensure correct table drops
- [ ] Tables to drop (FK order): `agent_step_runs`, `pipeline_runs`, `pipelines`, `agent_messages`, `agents`
- [ ] Run: `cd backend && python -m alembic upgrade head`
- [ ] Commit: `feat: add migration to drop agent/pipeline tables`

## Task 8: Delete Frontend Agents Directory

- [ ] Delete entire `frontend/src/features/agents/` directory (6 files)
- [ ] Commit: `feat: remove frontend agents/ directory`

## Task 9: Clean Frontend Issue Components

**File:** `frontend/src/features/issues/components/issue-detail.tsx`

- [ ] Remove imports: `AgentChat`, `PipelineProgress`, agent/pipeline hooks
- [ ] Remove pipeline state fetching for tab label badge
- [ ] Remove "chat", "pipeline", "agent-terminal" tabs
- [ ] Remove pipeline status badge rendering
- [ ] Remove AgentChat and PipelineProgress JSX

**File:** `frontend/src/features/issues/components/issue-actions.tsx`

- [ ] Remove pipeline hook imports
- [ ] Remove Start Pipeline button and related state

- [ ] Commit: `feat: remove agent/pipeline UI from issue components`

## Task 10: Clean Frontend Project Settings

**File:** `frontend/src/features/projects/components/project-settings-dialog.tsx`

- [ ] Remove imports of `AgentsSection`, `PipelinesSection`
- [ ] Remove rendering of those components in JSX

- [ ] Commit: `feat: remove agent/pipeline sections from project settings`

## Task 11: Clean Frontend Event Context

**File:** `frontend/src/shared/context/event-context.tsx`

- [ ] Remove SSE event handlers for: `agent_step_started`, `agent_step_completed`, `agent_step_failed`, `agent_terminal_created`, `pipeline_completed`, `pipeline_paused`
- [ ] Remove pipeline-run query invalidation for agent terminal events

- [ ] Commit: `feat: remove agent/pipeline event handlers`

## Task 12: Clean Frontend Library References

**File:** `frontend/src/features/library/api.ts`
- [ ] Remove agent API functions (`fetchAgents`, agent routing)

**File:** `frontend/src/features/library/hooks.ts`
- [ ] Remove `useAgents`, `useAgentDetail` hooks

**File:** `frontend/src/routes/library.tsx`
- [ ] Remove agent imports and references

**File:** `frontend/src/features/projects/components/library-tab.tsx`
- [ ] Remove agent fetch and rendering

- [ ] Commit: `feat: remove agent references from library`

## Task 13: Delete Test File

- [ ] Delete `backend/tests/test_orchestrator.py`
- [ ] Commit: `feat: remove orchestrator tests`

## Task 14: Verification

- [ ] Run `cd backend && python -m pytest` — all tests pass
- [ ] Run `cd frontend && npm run build` — builds without errors
- [ ] Run `python start.py` — app starts successfully
- [ ] Grep codebase for remaining `agent`, `pipeline`, `orchestrator` references (excluding unrelated matches)
- [ ] Fix any broken imports or references found
- [ ] Commit any fixes: `fix: remaining agent/pipeline cleanup`