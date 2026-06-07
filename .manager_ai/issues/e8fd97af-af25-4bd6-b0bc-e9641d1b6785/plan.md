Implementation plan: Pipeline event rules system.

**Architecture:** New `PipelineEventRule` model (SQLAlchemy, DB-backed). CRUD via PipelineService. MCP tools for agent-side. REST endpoints for frontend UI. Auto-resolve in `finished_pipeline_step` when `target_step_index` omitted.

**Tasks:**

1. **Model + migration** — Create `PipelineEventRule` model, add relationship to Pipeline, register in __init__, generate+apply Alembic migration
2. **CRUD + resolver** — Add event rule CRUD to `PipelineService`, add `resolve_rejection_target` to `PipelineRunService`
3. **MCP: finished_pipeline_step** — Make `target_step_index` optional, auto-resolve from event rules when missing
4. **MCP: event rule tools** — Add `add_pipeline_event_rule`, `remove_pipeline_event_rule`, `list_pipeline_event_rules` tools to MCP server
5. **REST API** — GET/POST/DELETE endpoints at `/api/pipelines/{id}/event-rules`
6. **Frontend types/API/hooks** — TypeScript types, API functions, React Query hooks
7. **Frontend UI** — Event rules section in PipelinesTab with add/remove per step
8. **Export/Import** — Include event_rules in pipeline export/import
9. **Tests** — CRUD tests + rejection target resolution tests