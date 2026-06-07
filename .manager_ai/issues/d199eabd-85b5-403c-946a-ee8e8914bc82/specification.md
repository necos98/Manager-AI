# Specification: Frontend Query Refresh After Agent/Pipeline Import

## Summary

When users import agents or pipelines via the JSON import feature, the React Query caches for both entity types are not properly refreshed. This causes:
1. Pipelines display "Unknown" for step agent names (stale agent list query)
2. The Agents tab doesn't show newly imported agents from pipeline imports
3. Cross-tab changes are invisible — no WebSocket events broadcast

## Scope

This issue covers **two layers** of the same problem:

### Layer 1: Immediate Query Invalidation Fix (Frontend)
- Add cross-entity query invalidation in import mutation hooks
- Fix applies to both `useImportAgentsConfirm` and `useImportPipelinesConfirm`

### Layer 2: Structural WebSocket Event Wiring (Backend + Frontend)
- Define new event type constants for agent/pipeline CRUD operations
- Emit events from backend routers after every state-changing operation
- Handle those events in the frontend EventProvider to invalidate relevant React Query caches

## Root Causes (from BrainstormAgent analysis)

1. **Cross-entity invalidation missing**: `useImportPipelinesConfirm` only invalidates `pipelineKeys.all()`, but `PipelineService.import_pipelines` creates agents as a side effect when step agent IDs don't exist in the database (pipeline_service.py:249-258, 279-288). Similarly, agent import should refresh pipeline queries since pipelines reference agents.

2. **No WebSocket events**: Zero `event_service.emit()` calls in `backend/app/routers/agents.py` or `pipelines.py`. All CRUD operations are silent — no broadcasts to other tabs or windows.

3. **"Unknown" display**: `PipelinesTab` builds its `agentMap` from `useAgents()`. After pipeline import creates new agents, the agents query isn't invalidated, so the map lacks entries for newly created agents — step names resolve to "Unknown".

4. **Detail query coverage already correct**: React Query's default fuzzy matching means `invalidateQueries({ queryKey: ["agents"] })` (what `agentKeys.all()` returns) already matches `["agents", "<id>"]` (detail keys). No additional detail invalidation calls needed. All existing mutation hooks already invalidate both list and detail queries implicitly.

## Requirements

### R1: Cross-Entity Query Invalidation in Import Hooks

**File**: `frontend/src/features/agents/hooks.ts`
- `useImportAgentsConfirm.onSuccess`: add `queryClient.invalidateQueries({ queryKey: pipelineKeys.all() })` — importing agents may introduce agent IDs referenced by pipelines

**File**: `frontend/src/features/pipelines/hooks.ts`
- `useImportPipelinesConfirm.onSuccess`: add `queryClient.invalidateQueries({ queryKey: agentKeys.all() })` — pipeline import creates agents inline as a side effect
- Import `agentKeys` from `@/features/agents/hooks` in the pipelines hooks file

### R2: WebSocket Event Types

Define the following event type constants in the backend event system:

| Event Type | Trigger | Data Fields |
|---|---|---|
| `agent_created` | POST `/api/agents` | `agent_id`, `agent_name` |
| `agent_updated` | PUT `/api/agents/{id}` | `agent_id`, `agent_name` |
| `agent_deleted` | DELETE `/api/agents/{id}` | `agent_id` |
| `agent_seeded` | POST `/api/agents/seed` | — |
| `agent_imported` | POST `/api/agents/import/confirm` | `import_count` |
| `pipeline_created` | POST `/api/pipelines` | `pipeline_id`, `pipeline_name` |
| `pipeline_updated` | PUT `/api/pipelines/{id}` | `pipeline_id`, `pipeline_name` |
| `pipeline_deleted` | DELETE `/api/pipelines/{id}` | `pipeline_id` |
| `pipeline_seeded` | POST `/api/pipelines/seed` | `pipeline_id` |
| `pipeline_imported` | POST `/api/pipelines/import/confirm` | `import_count` |
| `pipeline_step_added` | POST `/api/pipelines/{id}/steps` | `pipeline_id` |
| `pipeline_step_removed` | DELETE `/api/pipelines/{id}/steps/{sid}` | `pipeline_id` |
| `pipeline_steps_reordered` | PUT `/api/pipelines/{id}/steps/reorder` | `pipeline_id` |
| `pipeline_event_rule_created` | POST `/api/pipelines/{id}/event-rules` | `pipeline_id` |
| `pipeline_event_rule_deleted` | DELETE `/api/pipelines/{id}/event-rules/{rid}` | `pipeline_id` |

### R3: Backend Event Emission

In every state-changing endpoint in `backend/app/routers/agents.py` and `backend/app/routers/pipelines.py`, after successful `await db.commit()`, emit a WebSocket event via `await event_service.emit(event_dict)`.

**Constraints**:
- Events must be emitted only after `db.commit()` succeeds — if the commit throws, no event should fire
- The `event_service` singleton is already imported in `events.py` as `from app.services.event_service import event_service`
- Follow the existing event dict structure: `{ type, timestamp, ... }` with relevant entity fields
- Agents and pipelines are global (not per-project), so `project_id` field will be `null`/absent

### R4: Frontend Event Handling

In `frontend/src/shared/context/event-context.tsx`, add handlers for the new event types that invalidate the correct React Query caches:

- **Agent events** (`agent_created`, `agent_updated`, `agent_deleted`, `agent_seeded`, `agent_imported`): invalidate `["agents"]` query key
- **Pipeline events** (`pipeline_created`, `pipeline_updated`, `pipeline_deleted`, `pipeline_seeded`, `pipeline_imported`, `pipeline_step_added`, `pipeline_step_removed`, `pipeline_steps_reordered`, `pipeline_event_rule_created`, `pipeline_event_rule_deleted`): invalidate `["pipelines"]` query key

Add all 15 event types to the silent toast array at lines 198-208 in `buildToastContent` (group with the existing silent events like `memory_created`, `file_updated`, etc.). No toast notification needed.

**Important**: These events carry no `project_id`, so the generic `projectId` guard at line 340 won't apply. Use explicit per-event-type checks following the pattern already established for pipeline-run events (lines 301-312). Must list all 15 event types explicitly — JavaScript has no wildcard string matching in switch/case or if-statements.

## Acceptance Criteria

1. After importing agents via JSON, the Agents tab shows the newly imported agents immediately without manual refresh.
2. After importing pipelines via JSON, the Pipelines tab shows correct agent names (not "Unknown") for all steps immediately without manual refresh.
3. After importing pipelines that reference agents not in the database, those agents appear in the Agents tab immediately.
4. After any CRUD operation (create, update, delete, seed, import) on agents or pipelines, a second browser tab viewing the same page shows updated data within seconds.
5. Detail views (single agent, single pipeline) refresh after mutations that affect the viewed entity. (Already handled by React Query's fuzzy key matching — no code changes needed.)
6. No new toast notifications appear for agent/pipeline events (they should be silent).
7. Existing event handling (pipeline-run, terminal, memory, question, project/issue) continues to work unchanged.

## Non-Goals

- Changing the import/export JSON format or version
- Modifying the backend service layer logic (AgentService, PipelineService)
- Adding per-project scoping to agents or pipelines (they remain global)
- UI redesign of Agents or Pipelines tabs
- Real-time collaborative editing or conflict resolution
- Rate limiting or debouncing of query invalidations
- Backend unit tests for event emission (the Tester agent handles verification)
- Adding detail query invalidation to mutation hooks (React Query partial matching already covers this)

## Constraints

- **React Query version**: uses `@tanstack/react-query` — `invalidateQueries` with default `exact: false` uses fuzzy matching. Invalidating `["agents"]` matches `["agents"]` and `["agents", "<id>"]` — no separate detail invalidation needed.
- **Event service**: singleton `event_service` from `app.services.event_service` — `await event_service.emit(dict)` broadcasts to all connected WebSocket clients
- **WebSocket frontend**: `EventProvider` in `event-context.tsx` handles `ws.onmessage` — add new event type handlers in this function
- **No project_id**: Agents and pipelines are global entities — event payloads won't include `project_id`, so the generic project-scoped invalidation code path won't fire. Use explicit per-type checks, same as pipeline-run events (lines 301-312)
- **Type safety**: TypeScript types for `WsEventData` and `buildToastContent` switch cases already handle unknown event types gracefully via the `default` case — adding new types is additive and safe
- **Import side effects**: The backend `PipelineService.import_pipelines` method (pipeline_service.py:211-290) creates `Agent` records inline at lines 249-258 and 279-288 when step agent IDs from the import file don't exist in the database. This is a single DB transaction — both agent and pipeline mutations are committed atomically
