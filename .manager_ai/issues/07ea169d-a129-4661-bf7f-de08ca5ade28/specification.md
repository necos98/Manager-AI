## Specification

### Overview
Add 8 MCP tools to `server.py` for Agent, Pipeline, and PipelineRun management. Add descriptions to `default_settings.json`. Wire `ProjectService.create()` to seed default agents/pipelines for new projects.

### 1. MCP Tools (server.py)

Follow existing pattern: `async_session()`, service call, return dict, AppError → `{"error": e.message}`.

**Agent tools:**
- `create_agent(project_id, name, system_prompt, model=None, allowed_tools=None)` → AgentService.create() → return agent dict
- `list_agents(project_id)` → AgentService.list_by_project() → return list of agent dicts

**Pipeline tools:**
- `create_pipeline(project_id, name, steps)` where steps is `list[dict]` with agent_id, order_index, terminal_command → PipelineService.create_pipeline() + add_step() → return pipeline dict
- `list_pipelines(project_id)` → PipelineService.list_by_project() → return list of pipeline dicts with steps

**Pipeline run tools:**
- `run_pipeline(project_id, pipeline_id, issue_id)` → fetch project path via ProjectService.get_by_id() → PipelineRunService.start() → return run dict
- `get_pipeline_run_status(run_id)` → PipelineRunService.get_run() → return run dict with steps
- `send_agent_message(run_id, sender_agent_name, content)` → PipelineRunService.add_message() → return message dict
- `get_pipeline_messages(run_id)` → PipelineRunService.get_messages() → return list of message dicts

### 2. default_settings.json

Add 8 description entries under keys:
- `tool.create_agent.description`
- `tool.list_agents.description`
- `tool.create_pipeline.description`
- `tool.list_pipelines.description`
- `tool.run_pipeline.description`
- `tool.get_pipeline_run_status.description`
- `tool.send_agent_message.description`
- `tool.get_pipeline_messages.description`

### 3. ProjectService.create() Seeding

After `await self.session.flush()` in `ProjectService.create()`, add calls to:
```python
await AgentService(self.session).seed_defaults(project.id)
await PipelineService(self.session).seed_defaults(project.id)
```

This ensures new projects created at runtime (not just at startup) get default agents and pipelines. Both seed methods are idempotent — skip if data already exists.

### Router Registration (Already Done)

The 3 routers (`agents`, `pipelines`, `pipeline_runs`) are already registered in `main.py` lines 463-465. No action needed.

### Notes
- All services follow pattern: `AsyncSession` per instance, `select()` + `scalar_one_or_none()`, `self.session.add()`, `self.session.delete()`
- Agent/Pipeline are DB-backed (not file-backed) — follow `CredentialService` pattern
- Seed methods are idempotent (check existing data, skip if present)
- Agent seed must run before pipeline seed (pipeline needs agent IDs)
