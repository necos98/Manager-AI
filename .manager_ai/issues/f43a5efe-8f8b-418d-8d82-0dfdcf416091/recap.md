## Recap: Remove Agents & Pipeline Feature

### What was done
- Deleted 10 backend files: agent/pipeline models, schemas, routers, orchestrator_service, hooks/executor
- Deleted 1 test file: test_orchestrator.py (1203 lines)
- Deleted entire frontend/src/features/agents/ directory (6 files)
- Cleaned 16+ files: models/__init__.py, main.py, routers/issues.py, routers/library.py, skill_library_service.py, MCP server.py + default_settings.json, conftest.py, issue-detail.tsx, issue-actions.tsx, project-settings-dialog.tsx, event-context.tsx, library api.ts/hooks.ts, library.tsx, library-tab.tsx
- Created Alembic migration to drop 5 tables: agent_step_runs, pipeline_runs, pipelines, agent_messages, agents

### Verification
- 543 backend tests pass (32 pre-existing failures unrelated — KeyError in test_routers_tasks.py)
- Frontend `npm run build` succeeds with no errors
- All agent/pipeline files confirmed deleted via glob