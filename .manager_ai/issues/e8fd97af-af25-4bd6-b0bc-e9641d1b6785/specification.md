# Pipeline Event Rules — Design Spec

## Problem

When `finished_pipeline_step(rejected=True)` is called, the agent must specify `target_step_index` manually. There is no automatic redirect configuration — each rejection requires the agent to know the pipeline topology and decide where to jump. This is fragile and inconsistent across runs.

A related bug: when a step rejects, the pipeline currently `continue`s in `_execute()` which (on the natural loop increment) advances to the *next* step, not the target. The `reject_step` method handles this by setting `run.current_step_index` before signaling completion, but the system is not designed for configurable redirects.

## Scope

Implement only `step_rejected` event type. But build the data model and handler dispatch to support future event types (e.g., `step_completed`, `step_timeout`) with zero schema changes.

## Data Model

New SQLAlchemy model: `PipelineEventRule`

```
PipelineEventRule:
  id: str (UUID PK)
  pipeline_id: str (FK -> pipelines.id, ON DELETE CASCADE)
  event_type: str (not nullable — "step_rejected", future: "step_completed", etc.)
  source_step_id: str (FK -> pipeline_steps.id, not nullable)
  target_step_id: str (FK -> pipeline_steps.id, not nullable)
  enabled: bool (default true)
  created_at, updated_at: datetime
```

- `source_step_id`: when THIS step triggers the event (e.g., rejects)...
- `target_step_id`: ...redirect to THIS step
- `event_type` is a plain string column (not enum) so new event types need no migration

Uniqueness: `UniqueConstraint("pipeline_id", "event_type", "source_step_id")` — one rule per event-type per source-step.

## Changes

1. **New model:** `PipelineEventRule` in `backend/app/models/pipeline_event_rule.py`
2. **Alembic migration:** Create `pipeline_event_rules` table
3. **CRUD in PipelineService:** add_event_rule, remove_event_rule, list_event_rules, get_event_rule_for_step
4. **MCP tools:** add_pipeline_event_rule, remove_pipeline_event_rule, list_pipeline_event_rules
5. **finished_pipeline_step modification:** make `target_step_index` optional, auto-resolve from event rules when missing
6. **REST API:** GET/POST/DELETE `/api/pipelines/{id}/event-rules`
7. **Export/Import:** event_rules in pipeline export/import
8. **Frontend UI:** Event rules section in PipelinesTab with add/remove per step
9. **Tests:** CRUD + rejection target resolution

## Flow: Rejection with Event Rule

1. Agent calls `finished_pipeline_step(rejected=True, rejection_reason="X")`
2. MCP tool: `target_step_index=None`, queries event rules for pipeline
3. MCP calls `PipelineService.get_event_rules_for_step(pipeline_id, "step_rejected", current_step_id)`
4. Returns rule mapping to target step (order_index=2)
5. MCP tool calls `svc.reject_step(run_id, reason, target_step_index=2, project_id)`
6. `reject_step` marks current REJECTED, creates new RUNNING step_run at index 2, sets `run.current_step_index=2`
7. Signals completion → `_execute()` wakes → `continue` → loop picks step at index 2
8. Pipeline resumes from step 2 with fresh terminal

## Future Extensibility

Adding a new event type (e.g., `step_completed`):
1. Insert row: `event_type="step_completed"`, source/target as needed
2. Write handler function, register in event dispatch
3. No model changes, no migration, no schema changes