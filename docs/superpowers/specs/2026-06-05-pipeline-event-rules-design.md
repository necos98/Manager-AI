# Pipeline Event Rules — Design Spec

**Issue:** Pipeline failure recovery system — retry step config
**Date:** 2026-06-05
**Status:** Draft

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

## Event Handler Dispatch

Central switch in `PipelineRunService` (or thin helper):

```python
EVENT_HANDLERS: dict[str, Callable] = {
    "step_rejected": _handle_step_rejected,
}

async def _handle_step_rejected(self, run, step_run, session, ...):
    # Query PipelineEventRule WHERE enabled AND event_type='step_rejected'
    # AND source_step_id = step_run.pipeline_step_id
    # If found, set run.current_step_index = target_step's order_index
    # If not found, log warning and continue normally
```

Future event types add a new handler function + register in `EVENT_HANDLERS`. No switch/if-chain changes needed in `_execute()`.

## Changes

### 1. New model: `PipelineEventRule`

File: `backend/app/models/pipeline_event_rule.py` (new, or inline in `pipeline.py`)

### 2. Alembic migration

Create `pipeline_event_rules` table.

### 3. CRUD in PipelineService

Add methods:
- `add_event_rule(pipeline_id, event_type, source_step_id, target_step_id)` — create rule
- `remove_event_rule(rule_id)` — delete rule
- `list_event_rules(pipeline_id)` — list rules for pipeline
- `get_event_rules_for_step(pipeline_id, event_type, source_step_id)` — lookup for runtime

### 4. MCP tools

- `add_pipeline_event_rule(pipeline_id, event_type, source_step_id, target_step_id)`
- `remove_pipeline_event_rule(rule_id)`
- `list_pipeline_event_rules(pipeline_id)`

### 5. Export/Import

Extend `PipelineExportItem` schema to include event rules.
Extend `format_pipeline_export` to export them.
Import handles them in `import_pipelines`.

### 6. REST API (optional — if UI needs it)

`GET /api/pipelines/{id}/event-rules` — list rules
`POST /api/pipelines/{id}/event-rules` — create rule
`DELETE /api/pipelines/{id}/event-rules/{rule_id}` — delete rule

### 7. No changes needed in `_execute()`

`reject_step()` already sets `run.current_step_index = target_step_index` and creates a new RUNNING step_run. When `_execute()` wakes up from the completion signal, it `continue`s, and the loop naturally picks the correct step. No runtime rule resolution needed in `_execute()` — the redirect is fully handled at the MCP tool level (step 8).

The existing `continue` on line 283 is correct and unchanged.

### 8. Modify `finished_pipeline_step` MCP tool

Make `target_step_index` optional. When `rejected=True` and `target_step_index is None`:
- Query event rules for the pipeline to auto-resolve target
- If no rule found and no explicit target → error

### 9. Frontend: PipelinesTab

Add "Event Rules" section in pipeline config view:
- Shows table: Event Type | Source Step | Target Step | Enabled
- Add/remove rule controls
- Dropdown for source/target step populated from pipeline steps
- Event type dropdown: initially only "step_rejected"

## Flow: Rejection with Event Rule

1. Agent calls `finished_pipeline_step(rejected=True, rejection_reason="X")`
2. MCP tool: `target_step_index=None`, queries event rules for pipeline
3. MCP calls `PipelineService.get_event_rules_for_step(pipeline_id, "step_rejected", current_step_id)`
4. Returns rule mapping to target step (order_index=2)
5. MCP tool calls `svc.reject_step(run_id, reason, target_step_index=2, project_id)`
6. `reject_step` marks current REJECTED, creates new RUNNING step_run at index 2, sets `run.current_step_index=2`
7. Signals completion → `_execute()` wakes → `continue` → loop picks step at index 2
8. Pipeline resumes from step 2 with fresh terminal

## Flow: Rejection without Event Rule (fallback)

1. Agent calls `finished_pipeline_step(rejected=True, rejection_reason="X", target_step_index=0)`
2. MCP tool: explicit target provided → calls `reject_step` directly, same as current behavior
3. No event rule lookup — backward compatible

## Testing

- Unit test: create event rule, verify `_resolve_rejection_redirect` returns correct target
- Unit test: no matching rule → returns None
- Integration test: pipeline with event rule, reject step, verify run resumes at target step
- Integration test: pipeline without rules, reject with explicit target → works as before

## Future Extensibility

Adding a new event type (e.g., `step_completed`):
1. Insert row: `event_type="step_completed"`, source/target as needed
2. Write handler function, register in `EVENT_HANDLERS`
3. No model changes, no migration, no schema changes

The `event_type` string column + `EVENT_HANDLERS` dict pattern keeps extensibility without over-engineering the first implementation.
