## Part 1: Add 6 MCP Pipeline CRUD tools

Insert 6 new tools in `backend/app/mcp/server.py` after `list_pipelines` (line 1128), before the "Pipeline run tools" section (line 1131). Add 6 corresponding description keys in `backend/app/mcp/default_settings.json` (after `tool.list_pipelines.description` on line 69).

Each tool follows the same pattern:
1. `async with async_session() as session:` — open session
2. `PipelineService(session)` — instantiate service
3. Call service method (service already has all methods ready)
4. `await session.commit()` — commit before returning
5. `except AppError as e: return {"error": e.message}` — error handling

### Tool 1: get_pipeline(pipeline_id: str) -> dict
- Calls `PipelineService.get_pipeline(pipeline_id)`
- Returns pipeline dict with id, name, steps (same step serialization as `list_pipelines`: id, pipeline_id, agent_id, order_index), created_at, updated_at
- No commit needed (read-only), but include for consistency

### Tool 2: update_pipeline(pipeline_id: str, name: str) -> dict
- Calls `PipelineService.update_pipeline(pipeline_id, name)`
- Commit, then fetch full pipeline via `svc.get_pipeline()`
- Returns full pipeline dict

### Tool 3: delete_pipeline(pipeline_id: str) -> dict
- Calls `PipelineService.delete_pipeline(pipeline_id)`
- Commit
- Returns {"deleted": true}

### Tool 4: add_step(pipeline_id: str, agent_id: str, order_index: int = 0) -> dict
- Calls `PipelineService.add_step(pipeline_id, agent_id, order_index)`
- Note: `add_step()` service method ignores `order_index` param — always auto-assigns max+1. The param is accepted in the MCP tool for API consistency but has no effect client-side.
- Commit, then fetch full pipeline via `svc.get_pipeline()`
- Returns full pipeline dict

### Tool 5: remove_step(step_id: str) -> dict
- Calls `PipelineService.remove_step(step_id)`
- Commit
- Returns {"deleted": true}

### Tool 6: reorder_steps(pipeline_id: str, step_ids: list[str]) -> dict
- Calls `PipelineService.reorder_steps(pipeline_id, step_ids)`
- Commit, then fetch full pipeline via `svc.get_pipeline()`
- Returns full pipeline dict
- **Critical**: service uses `no_autoflush` two-pass to avoid UNIQUE constraint violation — do NOT reimplement, just call the service method directly

### default_settings.json additions (after line 69)
```json
"tool.get_pipeline.description": "Get a single pipeline by ID. Parameters: pipeline_id (required). Returns the pipeline with id, name, steps, and timestamps.",
"tool.update_pipeline.description": "Update a pipeline's name. Parameters: pipeline_id (required), name (required). Returns the updated pipeline.",
"tool.delete_pipeline.description": "Delete a pipeline. Parameters: pipeline_id (required). Returns {deleted: true}.",
"tool.add_step.description": "Add a step to a pipeline. Parameters: pipeline_id (required), agent_id (required), order_index (optional int, auto-assigned if 0). Returns the updated pipeline.",
"tool.remove_step.description": "Remove a step from a pipeline. Parameters: step_id (required). Returns {deleted: true}.",
"tool.reorder_steps.description": "Reorder steps in a pipeline. Parameters: pipeline_id (required), step_ids (required list of step IDs in new order). Returns the pipeline with steps in the new order."
```

---

## Part 2: Update /manage-agent command

Edit `claude_resources/commands/manage-agent.md` (NOT `.claude/commands/manage-agent.md` — that's a generated copy).

### Step 1: Add pipeline listing
After step 1 (which does `list_agents`), add a step to call `list_pipelines` and display existing pipelines with their steps/agents.

### Step 2: Add "Create pipeline" action to action menu
Add to the existing action menu (step 2 in current file, which lists actions). Insert before "Inspect" or after "Delete":

```
- **Create a pipeline**
```

### Step 3: Add pipeline creation flow
After the existing agent management flow (step 4), add a new step for pipeline creation:
- Ask user for pipeline name
- Call `list_agents` to display available agents
- Let user pick agents in order
- Call `create_pipeline(name, steps=[{agent_id, order_index}])`
- Show created pipeline

### Existing agent CRUD must remain intact
All existing agent management actions (create/edit/delete/inspect) stay unchanged.

---

## Files modified
1. `backend/app/mcp/server.py` — add 6 tools (after line 1128)
2. `backend/app/mcp/default_settings.json` — add 6 description keys (after line 69)
3. `claude_resources/commands/manage-agent.md` — add pipeline listing + creation flow
