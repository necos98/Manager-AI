# Implementation Plan: Frontend Query Refresh After Agent/Pipeline Import

## Overview

Three-phase plan to fix stale queries and "Unknown" names. Each phase is independent
and can be implemented sequentially by the Developer agent.

---

## Phase 1: Cross-Entity Query Invalidation (R1)

**Goal:** When import mutations complete, invalidate queries for both entity types so
the UI shows fresh data without manual refresh.

### Step 1.1 — `frontend/src/features/agents/hooks.ts`

**Mutation:** `useImportAgentsConfirm` (lines 115-130). In `onSuccess`, add
cross-entity invalidation after the existing `agentKeys.all()` call:

```typescript
queryClient.invalidateQueries({ queryKey: ["pipelines"] });
```

**Why:** Importing agents may introduce agent IDs referenced by existing pipeline steps.
Without this invalidation, pipelines that reference these agents would show "Unknown"
until a manual refresh.

### Step 1.2 — `frontend/src/features/pipelines/hooks.ts`

**Mutation:** `useImportPipelinesConfirm` (lines 151-166). In `onSuccess`, add
cross-entity invalidation after the existing `pipelineKeys.all()` call:

```typescript
queryClient.invalidateQueries({ queryKey: ["agents"] });
```

**Why:** `PipelineService.import_pipelines` creates `Agent` records inline
(pipeline_service.py:249-258, 279-288) when step agent IDs from the import file
don't exist in the database. The pipeline import mutates both entity types in a single
transaction — the frontend must refresh both query caches.

**⚠️ IMPORTANT — No cross-file imports:** Use raw string arrays `["pipelines"]` /
`["agents"]` (NOT `pipelineKeys.all()` / `agentKeys.all()` which require importing
from the other feature's hooks file). Importing `{ pipelineKeys }` from
`@/features/pipelines/hooks` into `agents/hooks.ts` AND `{ agentKeys }` from
`@/features/agents/hooks` into `pipelines/hooks.ts` creates a **circular import**.
Raw query key arrays are equivalent (React Query fuzzy matching works identically)
and avoid the circular dependency entirely. This is the same approach used in Phase 3's
EventProvider handlers.

**Files changed:** 2
**Lines added:** ~2 (no new imports)

---

## Phase 2: Backend WebSocket Event Emission (R2 + R3)

**Goal:** Broadcast events after every agent/pipeline state-changing operation so
other browser tabs/windows see updates within seconds.

### Event Type Constants

These are string literals used in both backend emission and frontend handling.
No separate constants file — defined inline in emit calls and event handlers.

**Agent events (5):**
| Type | Trigger endpoint | Payload fields |
|---|---|---|
| `agent_created` | POST `/api/agents` | `agent_id`, `agent_name` |
| `agent_updated` | PUT `/api/agents/{id}` | `agent_id`, `agent_name` |
| `agent_deleted` | DELETE `/api/agents/{id}` | `agent_id` |
| `agent_seeded` | POST `/api/agents/seed` | — |
| `agent_imported` | POST `/api/agents/import/confirm` | `import_count` |

**Pipeline events (10):**
| Type | Trigger endpoint | Payload fields |
|---|---|---|
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

**Event dict structure** (follows existing pattern in events.py):
```python
{
    "type": "agent_created",
    "agent_id": "...",
    "agent_name": "...",
    "timestamp": datetime.now(timezone.utc).isoformat(),
}
```

### Step 2.1 — `backend/app/routers/agents.py`

**Imports** (add after line 3, `from fastapi import ...`):
```python
from datetime import datetime, timezone
```
Add after the last existing import (line 18, after `from app.services.agent_service import AgentService`):
```python
from app.services.event_service import event_service
```

**Emit events after `await db.commit()` in 5 endpoints:**

1. `create_agent` (line 46-56): after `await db.commit()` at line 55, emit:
```python
await event_service.emit({
    "type": "agent_created",
    "agent_id": agent.id,
    "agent_name": agent.name,
    "timestamp": datetime.now(timezone.utc).isoformat(),
})
```

2. `seed_agents` (line 59-65): after `await db.commit()` at line 64, emit:
```python
await event_service.emit({
    "type": "agent_seeded",
    "timestamp": datetime.now(timezone.utc).isoformat(),
})
```

3. `import_agents_confirm` (line 163-190): after `await db.commit()` at line 189, emit:
```python
await event_service.emit({
    "type": "agent_imported",
    "import_count": result.imported,
    "timestamp": datetime.now(timezone.utc).isoformat(),
})
```

4. `update_agent` (line 203-222): after `await db.commit()` at line 221, emit:
```python
await event_service.emit({
    "type": "agent_updated",
    "agent_id": agent.id,
    "agent_name": agent.name,
    "timestamp": datetime.now(timezone.utc).isoformat(),
})
```

5. `delete_agent` (line 225-229): after `await db.commit()` at line 229, emit:
```python
await event_service.emit({
    "type": "agent_deleted",
    "agent_id": agent_id,
    "timestamp": datetime.now(timezone.utc).isoformat(),
})
```

### Step 2.2 — `backend/app/routers/pipelines.py`

**Imports** (add after line 3, `from fastapi import ...`):
```python
from datetime import datetime, timezone
```
Add after the last existing import (line 31, after `from app.services.pipeline_service import PipelineService`):
```python
from app.services.event_service import event_service
```

**Emit events after `await db.commit()` in 10 endpoints:**

1. `create_pipeline` (line 66-76): after commit at line 75, emit `pipeline_created` with `pipeline_id` + `pipeline_name`. Use `data.name` for the name field (still in scope after commit).

2. `seed_pipeline` (line 79-84): after commit at line 83, emit `pipeline_seeded` with `pipeline_id = pipeline.id`. Note: returns single `PipelineResponse`, not a list.

3. `import_pipelines_confirm` (line 225-262): after commit at line 261, emit `pipeline_imported` with `import_count = result.imported`.

4. `update_pipeline` (line 275-284): after commit at line 283, emit `pipeline_updated` with `pipeline_id` + `pipeline_name = data.name`. `data` is a Pydantic model still in scope after commit — no pre-capture needed.

5. `delete_pipeline` (line 287-291): after commit at line 291, emit `pipeline_deleted` with `pipeline_id`.

6. `add_step` (line 299-312): after commit at line 311, emit `pipeline_step_added` with `pipeline_id`.

7. `remove_step` (line 315-323): after commit at line 323, emit `pipeline_step_removed` with `pipeline_id`.

8. `reorder_steps` (line 326-339): after commit at line 338, emit `pipeline_steps_reordered` with `pipeline_id`.

9. `create_event_rule` (line 365-386): after commit at line 385, emit `pipeline_event_rule_created` with `pipeline_id`.

10. `delete_event_rule` (line 389-403): after commit at line 403, emit `pipeline_event_rule_deleted` with `pipeline_id`.

**Critical constraint for all endpoints:** Events MUST emit AFTER `await db.commit()` succeeds. If commit throws, no event fires — this prevents false broadcasts for failed operations. This matches the existing pattern in events.py.

**Files changed:** 2
**Lines added:** ~50 (imports + emit calls)

---

## Phase 3: Frontend Event Handling (R4)

**Goal:** Handle the 15 new event types in the EventProvider to invalidate React Query
caches, and add them to the silent toast list.

### Step 3.1 — `frontend/src/shared/context/event-context.tsx`

**Silent toast entries** (lines 198-208): Add all 15 event types to the existing
comma-separated `case` block so no toast notification appears for them:

```typescript
case "project_updated":
case "memory_created":
// ... existing entries ...
case "question_answered":
case "agent_created":
case "agent_updated":
case "agent_deleted":
case "agent_seeded":
case "agent_imported":
case "pipeline_created":
case "pipeline_updated":
case "pipeline_deleted":
case "pipeline_seeded":
case "pipeline_imported":
case "pipeline_step_added":
case "pipeline_step_removed":
case "pipeline_steps_reordered":
case "pipeline_event_rule_created":
case "pipeline_event_rule_deleted":
  return { title: "", message: "", variant: "default", silent: true };
```

**Query invalidation handlers** (after line 337, before the closing of
`ws.onmessage`): Add explicit per-type checks for agent and pipeline events.
Follow the pattern established for pipeline-run events at lines 301-312:

```typescript
// Invalidate agent queries on agent events
if (
  data.type === "agent_created" ||
  data.type === "agent_updated" ||
  data.type === "agent_deleted" ||
  data.type === "agent_seeded" ||
  data.type === "agent_imported"
) {
  queryClient.invalidateQueries({ queryKey: ["agents"] });
}

// Invalidate pipeline queries on pipeline events
if (
  data.type === "pipeline_created" ||
  data.type === "pipeline_updated" ||
  data.type === "pipeline_deleted" ||
  data.type === "pipeline_seeded" ||
  data.type === "pipeline_imported" ||
  data.type === "pipeline_step_added" ||
  data.type === "pipeline_step_removed" ||
  data.type === "pipeline_steps_reordered" ||
  data.type === "pipeline_event_rule_created" ||
  data.type === "pipeline_event_rule_deleted"
) {
  queryClient.invalidateQueries({ queryKey: ["pipelines"] });
}
```

**Why explicit per-type checks:** Agents and pipelines are global entities (not
per-project). Event payloads carry no `project_id`, so the generic `projectId`-scoped
invalidation at lines 340-351 won't fire. Must use explicit type checks, same pattern
as pipeline-run events at lines 301-312.

**Why `["agents"]` not `agentKeys.all()`:** The EventProvider is framework-level
infrastructure that shouldn't import feature-specific key factories.
`queryClient.invalidateQueries({ queryKey: ["agents"] })` is equivalent — React
Query's fuzzy matching (`exact: false` default) means it matches `["agents"]` and
`["agents", "<id>"]`.

**Files changed:** 1
**Lines added:** ~30

---

## Implementation Order

1. **Phase 1 first** — immediate fix with lowest risk (~2 lines, no backend changes, no cross-module imports).
   Testable immediately: import a pipeline, verify Agents tab updates.
2. **Phase 2 second** — backend events wired. Testable with browser dev tools
   (WebSocket frames tab) before Phase 3 handles them.
3. **Phase 3 third** — frontend EventProvider handles the events Phase 2 emits.

## Testing Notes (for Tester agent)

- After Phase 1: Import a pipeline JSON that references agents not in the DB.
  Verify Agents tab shows new agents without manual refresh.
- After Phase 2+3: Open two browser tabs. Perform CRUD operations in Tab A.
  Verify Tab B shows updates within seconds.
- Verify no toast notifications appear for agent/pipeline events.
- Verify existing event handling (pipeline-run, terminal, memory, question,
  project/issue) continues to work.
- Run backend unit tests: `python -m pytest` from backend directory.
- Run frontend lint: `npm run lint` from frontend directory.

## Constraints

- React Query `invalidateQueries` with default `exact: false` uses fuzzy matching.
  Invalidating `["agents"]` matches `["agents"]` and `["agents", "<id>"]`.
- `event_service` is a singleton imported as `from app.services.event_service import event_service`.
- `event_service.emit(dict)` is async — must `await`.
- Events must emit AFTER `await db.commit()` — never before.
- Agents and pipelines are global (no `project_id` in event payloads).
- TypeScript `WsEventData` uses `Record<string, unknown>` — no type changes needed.
- JavaScript has no wildcard matching in `switch`/`if` — all 15 types must be listed.
- No changes to service layer (AgentService, PipelineService) — only routers + frontend.
- **No cross-feature imports in Phase 1** — use raw `["agents"]` / `["pipelines"]` query key arrays to avoid circular imports between agents/hooks.ts and pipelines/hooks.ts.
