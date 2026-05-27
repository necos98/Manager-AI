## Recap

Added 8 MCP tools to `server.py` wrapping existing AgentService, PipelineService, and PipelineRunService methods. All tools follow the existing pattern: `async_session()`, service call, return dict, AppError → `{"error": e.message}`.

### Changes Made

**backend/app/mcp/default_settings.json** — Added 8 tool description entries:
- `tool.create_agent.description`, `tool.list_agents.description`
- `tool.create_pipeline.description`, `tool.list_pipelines.description`
- `tool.run_pipeline.description`, `tool.get_pipeline_run_status.description`
- `tool.send_agent_message.description`, `tool.get_pipeline_messages.description`

**backend/app/mcp/server.py** — Added 8 MCP tool functions (~170 lines):
- `create_agent` / `list_agents` — wrap AgentService
- `create_pipeline` / `list_pipelines` — wrap PipelineService
- `run_pipeline` — fetches project path via ProjectService, then PipelineRunService.start()
- `get_pipeline_run_status` — wraps PipelineRunService.get_run()
- `send_agent_message` / `get_pipeline_messages` — wrap PipelineRunService.add_message/get_messages
- Added imports: AgentService, PipelineService, PipelineRunService

**backend/app/services/project_service.py** — Added seed_defaults calls to `ProjectService.create()`:
- After flush, calls `AgentService.seed_defaults(project.id)` then `PipelineService.seed_defaults(project.id)`
- Uses local imports to avoid circular dependency issues
- Ensures new projects created at runtime get default agents/pipelines (startup seed only covers existing projects)

### Pre-existing (Not Changed)
- Routers (`agents`, `pipelines`, `pipeline_runs`) already registered in main.py lines 463-465
- Seed defaults already in main.py lifespan for startup
- All models, services, schemas, routers already existed as untracked files

### Verification
- 8 new MCP tools confirmed registered (47 total tools)
- 181 tests pass (1 pre-existing failure in test_db_backup.py unrelated)
- server.py imports cleanly
