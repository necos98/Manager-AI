## Summary

Removed `system_prompt` from all 9 files where it still existed. Migration `3ce16a284d05` had already dropped the DB column but the application code wasn't cleaned up — the model still defined the column (would crash on startup), schemas required it, and the frontend form showed it as a required field.

## Changes

### Backend (5 files)
- **`backend/app/models/agent.py`** — Removed `system_prompt` mapped column
- **`backend/app/schemas/agent.py`** — Removed from `AgentCreate`, `AgentUpdate`, `AgentResponse`
- **`backend/app/services/agent_service.py`** — Removed from all 6 `DEFAULT_AGENTS` entries and `create()` method
- **`backend/app/routers/agents.py`** — Removed from `_response()`, `create_agent()`, `update_agent()`
- **`backend/app/mcp/server.py`** — Removed from `create_agent` MCP tool params and `list_agents` response

### Frontend (1 file)
- **`frontend/src/features/agents/components/AgentsTab.tsx`** — Removed from `AgentFormData`, form fields, validation, mapping functions, and `Textarea` import

### Tests (2 files)
- **`backend/tests/test_pipeline_run_service.py`** — Removed `system_prompt=` kwarg from 6 `Agent()` calls
- **`backend/tests/test_models_pipeline.py`** — Removed `system_prompt=` kwarg from 6 `Agent()` calls

### Docs (1 file)
- **`docs/agent-pipeline-architecture.md`** — Removed from table schema and MCP tools table

## Verification
- All 17 pipeline/agent tests pass
- `grep -r "system_prompt" backend/app/` — zero matches
- `grep -r "system_prompt" frontend/src/` — zero matches
- Frontend types (`Agent`, `AgentCreate`, `AgentUpdate`) were already clean — no changes needed