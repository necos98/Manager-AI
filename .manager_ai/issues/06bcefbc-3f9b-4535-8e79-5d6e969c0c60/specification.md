## Part 1: Add missing MCP Pipeline CRUD tools

### Scope

Add 6 new MCP tools to `backend/app/mcp/server.py` for full pipeline lifecycle management, plus corresponding descriptions in `backend/app/mcp/default_settings.json`.

The service layer (`backend/app/services/pipeline_service.py`) already implements all required logic. The MCP tools must wrap these existing service methods following established patterns (see Agent CRUD tools at `server.py:962-1065`).

### Tools to add

1. **get_pipeline(pipeline_id: str) -> dict** — Return single pipeline with its steps by ID. Uses `PipelineService.get_pipeline()`. Returns pipeline details or error.

2. **update_pipeline(pipeline_id: str, name: str) -> dict** — Rename a pipeline. Uses `PipelineService.update_pipeline()`. Returns updated pipeline.

3. **delete_pipeline(pipeline_id: str) -> dict** — Delete a pipeline. Uses `PipelineService.delete_pipeline()`. Returns `{"deleted": true}`.

4. **add_step(pipeline_id: str, agent_id: str, order_index: int = 0) -> dict** — Add a step to a pipeline. Uses `PipelineService.add_step()`. Auto-assigns next order_index if argument is 0. Returns updated pipeline.

5. **remove_step(step_id: str) -> dict** — Remove a step from a pipeline. Uses `PipelineService.remove_step()`. Returns `{"deleted": true}`.

6. **reorder_steps(pipeline_id: str, step_ids: list[str]) -> dict** — Reorder pipeline steps. Uses `PipelineService.reorder_steps()`. Returns pipeline with steps in new order.

### Implementation pattern (per tool)

- `async with async_session() as session:` — open a session
- `PipelineService(session)` — instantiate service
- Call the service method
- `await session.commit()` — commit before returning
- `except AppError as e: return {"error": e.message}` — error handling consistent with existing tools

### Affected files

- `backend/app/mcp/server.py` — add 6 tools after the `list_pipelines` tool (after line 1128)
- `backend/app/mcp/default_settings.json` — add tool descriptions for each new tool

### Constraints

- `reorder_steps` uses two-pass logic with `no_autoflush` to avoid UNIQUE(pipeline_id, order_index) constraint violations — must call the service method directly, not reimplement
- Follow exact naming convention of existing tools: snake_case tool names
- Descriptions in `default_settings.json` must be referenced by matching keys

---

## Part 2: Update /manage-agent command to support pipelines

### Scope

Extend the `/manage-agent` command (source: `claude_resources/commands/manage-agent.md`) so it also handles pipeline management alongside existing agent management.

### Requirements

1. **List pipelines** — After listing agents, also call `list_pipelines` to show existing pipelines with their steps and agents in each step.

2. **Add "Create pipeline" action** — Add a new action to the action menu for creating a pipeline. Flow:
   - Prompt the user for a pipeline name
   - Call `list_agents` to display available agents
   - Let the user select which agents to include (in order)
   - Call `create_pipeline(name, steps=[{agent_id, order_index}])` to create

3. **Existing agent CRUD actions must remain intact** — The current agent management functionality (create/edit/delete/inspect agents) must not be affected.

### Affected files

- `claude_resources/commands/manage-agent.md` — add pipeline listings and creation flow
- `.claude/commands/manage-agent.md` — must NOT be edited (it's a generated distribution copy; only `claude_resources/` is source of truth)

### Constraints

- Only `claude_resources/` files are source of truth for commands. `.claude/` is a generated distribution copy and must not be edited.
- The existing agent CRUD flow must remain fully functional.

---

## Acceptance criteria

1. `get_pipeline` returns a single pipeline by ID with all its steps
2. `update_pipeline` renames a pipeline and returns the updated object
3. `delete_pipeline` removes a pipeline and returns `{"deleted": true}`
4. `add_step` adds a step at the specified order index (or auto-assigns if 0)
5. `remove_step` removes a step and returns `{"deleted": true}`
6. `reorder_steps` accepts a list of step IDs and reorders them without constraint violations
7. All new tools handle errors consistently (AppError → `{"error": message}`)
8. `/manage-agent` command lists pipelines after listing agents
9. `/manage-agent` command includes a "Create pipeline" action with the described flow
10. Existing agent CRUD functionality in `/manage-agent` is unchanged

## Non-goals

- No changes to the REST API (`/api/pipelines` endpoints) — all endpoints already exist
- No changes to the service layer (`PipelineService`) — all methods already exist
- No changes to pipeline schemas
- No new frontend components for pipeline management in the web UI
- No changes to the pipeline execution/orchestration logic
