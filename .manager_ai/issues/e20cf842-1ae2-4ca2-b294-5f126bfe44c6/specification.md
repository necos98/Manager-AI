# Remove `system_prompt` from agents codebase

## Summary

Migration `3ce16a284d05` already dropped the `system_prompt` column from the `agents` table. Frontend types (`Agent`, `AgentCreate`, `AgentUpdate`) already exclude the field. But 9 files still reference `system_prompt` — the model column definition (causes runtime error), schemas, service, router, MCP server, frontend component, tests, and docs. Remove all remaining references.

## Scope

### Backend (5 files)

1. **`backend/app/models/agent.py`** — Remove `system_prompt` mapped column from `Agent` class. The DB column no longer exists after migration `3ce16a284d05`.

2. **`backend/app/schemas/agent.py`** — Remove `system_prompt` field from:
   - `AgentCreate` (currently `Field(..., min_length=1)` — required)
   - `AgentUpdate`
   - `AgentResponse`

3. **`backend/app/services/agent_service.py`** — Remove `system_prompt` from:
   - All 6 `DEFAULT_AGENTS` dict entries (the key-value pair)
   - `create()` method signature and body
   - `seed_defaults()` Agent constructor call

4. **`backend/app/routers/agents.py`** — Remove `system_prompt` from:
   - `_response()` helper
   - `create_agent()` — no longer pass `system_prompt=data.system_prompt` to service
   - `update_agent()` — no longer pass `system_prompt=data.system_prompt` to service

5. **`backend/app/mcp/server.py`** — Remove `system_prompt` from:
   - `create_agent()` MCP tool parameter and service call
   - `list_agents()` response dict

### Frontend (1 file)

6. **`frontend/src/features/agents/components/AgentsTab.tsx`** — Remove `system_prompt` from:
   - `AgentFormData` interface
   - `EMPTY_FORM` default
   - `agentToForm()` mapping
   - `formToCreate()` mapping
   - `formToUpdate()` mapping
   - `validateForm()` — remove the "System Prompt is required" check
   - Form JSX — remove the System Prompt `<label>` + `<Textarea>`

### Tests (2 files)

7. **`backend/tests/test_pipeline_run_service.py`** — Remove `system_prompt="..."` kwarg from all `Agent(...)` constructor calls (6 occurrences)

8. **`backend/tests/test_models_pipeline.py`** — Remove `system_prompt="..."` kwarg from all `Agent(...)` constructor calls (6 occurrences)

### Docs (1 file)

9. **`docs/agent-pipeline-architecture.md`** — Remove `system_prompt` row from the agents table schema and from the `create_agent` tool parameter list

## Not in scope

- Alembic migration files — historical, must not be modified
- `.manager_ai/` issue/memory/resource files — historical records
- Frontend `src/shared/types/index.ts` — already clean (no `system_prompt` in Agent interfaces)

## Success criteria

- `grep -r "system_prompt" backend/app/ frontend/src/` returns zero matches
- All existing tests pass
- Creating/editing agents via UI works without system_prompt field
- MCP `create_agent` and `list_agents` tools work without system_prompt