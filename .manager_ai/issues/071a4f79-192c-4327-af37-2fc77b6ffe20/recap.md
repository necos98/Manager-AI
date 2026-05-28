## Changes Made

### Backend
- **Migration** (`74be7f4de8b5`): Drop `project_id` column + FK + unique constraint from `agents` and `pipelines` tables (SQLite table rebuild)
- **Models**: Removed `project_id` from `Agent` and `Pipeline`, removed `project` relationship, removed `agents`/`pipelines` relationships from `Project`
- **Schemas**: Removed `project_id` from `AgentResponse`, `PipelineResponse`; added `project_id` to `PipelineRunStart`
- **Services**: Removed `project_id` param from `AgentService.seed_defaults()`, `create()`, `list_by_project()` → `list_all()`, `get_by_name()`. Same for `PipelineService`
- **Routers**: Moved agents to `/api/agents`, pipelines to `/api/pipelines`, pipeline-runs to `/api/pipeline-runs` (project_id passed in body for start)
- **MCP Server**: Removed `project_id` param from `create_agent`, `list_agents`, `create_pipeline`, `list_pipelines`
- **main.py**: Seed defaults once globally instead of per-project; updated `ProjectService.create()` to call parameterless `seed_defaults()`

### Frontend
- **Types**: Removed `project_id` from `Agent` and `Pipeline` interfaces; added `project_id` to `PipelineRunStart`
- **API layer**: Updated agents/pipelines API to top-level paths; pipeline-runs API passes `project_id` in body
- **Hooks**: Removed `projectId` param from agent/pipeline hooks (global queries); pipeline-run hooks keep `projectId` for cache scoping
- **Components**: `AgentsTab` and `PipelinesTab` no longer require `projectId` prop; `PipelineRunButton` passes `project_id` in mutation body
- **Routes**: Created top-level `/agents` and `/pipelines` routes; removed from project-scoped routes
- **Navigation**: Added Agents and Pipelines to global nav sidebar; removed from project nav

### Tests
- Updated `test_models_pipeline.py` and `test_pipeline_run_service.py`: removed `project_id` from Agent/Pipeline constructors, removed project-specific constraint tests
- All 15 pipeline tests pass; 181 total pass (1 unrelated pre-existing failure in test_db_backup.py)

### Documentation
- Updated `docs/agent-pipeline-architecture.md` to reflect global scope
