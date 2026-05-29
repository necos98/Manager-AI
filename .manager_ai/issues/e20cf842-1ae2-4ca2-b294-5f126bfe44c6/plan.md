# Remove system_prompt — Implementation Plan

**Goal:** Remove all `system_prompt` references from 9 files (model, schema, service, router, MCP server, frontend component, 2 test files, docs).

**Architecture:** Search-and-destroy cleanup. Migration already dropped DB column. Frontend types already clean. Remove from model definition, schemas, service layer, API layer, MCP tool signatures, frontend form, tests, and docs.

**Tech Stack:** Python/FastAPI/SQLAlchemy backend, React/TypeScript frontend.

---

### Task 1: Backend model — drop system_prompt column
**File:** `backend/app/models/agent.py`
Remove line 16 (`system_prompt` mapped column). If kept, app crashes on startup because migration already dropped column.

### Task 2: Backend schemas — drop system_prompt from AgentCreate, AgentUpdate, AgentResponse
**File:** `backend/app/schemas/agent.py`
Remove `system_prompt` field from all 3 Pydantic models.

### Task 3: Backend service — drop system_prompt from DEFAULT_AGENTS and create()
**File:** `backend/app/services/agent_service.py`
Remove `system_prompt` key from all 6 DEFAULT_AGENTS entries. Remove parameter from `create()`.

### Task 4: Backend router — drop system_prompt from route handlers
**File:** `backend/app/routers/agents.py`
Remove `system_prompt` from `_response()`, `create_agent()`, `update_agent()`.

### Task 5: MCP server — drop system_prompt from agent tools
**File:** `backend/app/mcp/server.py`
Remove `system_prompt` param from `create_agent` MCP tool and from `list_agents` response dict.

### Task 6: Frontend AgentsTab — remove system_prompt from form
**File:** `frontend/src/features/agents/components/AgentsTab.tsx`
Remove from `AgentFormData`, `EMPTY_FORM`, all mapping functions, validation, and form JSX.

### Task 7: Tests — remove system_prompt kwarg from Agent() calls
**Files:** `backend/tests/test_pipeline_run_service.py`, `backend/tests/test_models_pipeline.py`
Remove `system_prompt="..."` from all 12 Agent constructor calls (6 per file).

### Task 8: Docs — remove system_prompt from agent-pipeline-architecture.md
**File:** `docs/agent-pipeline-architecture.md`
Remove from table schema row and create_agent tool parameters.

### Task 9: Run tests and verify
Run backend tests. Grep for remaining `system_prompt` in app and frontend source.