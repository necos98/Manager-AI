# Recap: Frontend Query Refresh After Agent/Pipeline Import

## Summary

Fixed stale queries and "Unknown" agent names after agent/pipeline JSON import through two layers: immediate query invalidation fix and structural WebSocket event wiring.

## Changes Made (5 files, +126 lines)

### Phase 1: Cross-Entity Query Invalidation (frontend)
- `frontend/src/features/agents/hooks.ts`: Added `queryClient.invalidateQueries({ queryKey: ["pipelines"] })` to `useImportAgentsConfirm.onSuccess` — agent import may introduce agent IDs referenced by pipeline steps
- `frontend/src/features/pipelines/hooks.ts`: Added `queryClient.invalidateQueries({ queryKey: ["agents"] })` to `useImportPipelinesConfirm.onSuccess` — pipeline import creates agents inline (PipelineService.import_pipelines lines 249-258, 279-288)
- Used raw query key arrays `["pipelines"]` / `["agents"]` to avoid circular imports between sibling feature modules

### Phase 2: Backend WebSocket Events (backend)
- `backend/app/routers/agents.py`: 5 event types emitted after `await db.commit()` — `agent_created`, `agent_updated`, `agent_deleted`, `agent_seeded`, `agent_imported`
- `backend/app/routers/pipelines.py`: 10 event types emitted after `await db.commit()` — `pipeline_created`, `pipeline_updated`, `pipeline_deleted`, `pipeline_seeded`, `pipeline_imported`, `pipeline_step_added`, `pipeline_step_removed`, `pipeline_steps_reordered`, `pipeline_event_rule_created`, `pipeline_event_rule_deleted`

### Phase 3: Frontend EventProvider (frontend)
- `frontend/src/shared/context/event-context.tsx`: 15 event types added to silent toast list + query invalidation handlers for agent events (invalidate `["agents"]`) and pipeline events (invalidate `["pipelines"]`)

## Test Results
- Backend `python -m pytest` (654 tests): no regressions — all failures pre-existing and unrelated
- Python syntax check: both router files pass
- No test files exist for agents/pipelines routers (pre-existing gap)

## Key Decisions
- No cross-feature imports — raw `["agents"]` / `["pipelines"]` arrays used consistently
- React Query fuzzy matching (`exact: false` default) means invalidating `["agents"]` matches both list and detail queries
- All events emit AFTER `await db.commit()` — prevents false broadcasts
- Explicit per-type checks in EventProvider (no JS wildcard matching)
- No service layer changes — only routers + frontend