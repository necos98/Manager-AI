## Problem

`/api/pipeline-runs/active-by-issue` makes heavy requests. Root cause analysis found three compounding issues:

1. **5s polling always** — `refetchInterval: 5000` fires every 5 seconds even when zero active pipeline runs exist.
2. **URL bloat from unbounded issue IDs** — frontend passes ALL issue IDs as query params (`?issue_ids=a,b,c,...`). 50+ issues = 50+ UUIDs. No pagination on issues list.
3. **WebSocket events miss this query key** — event-context invalidates `["pipeline-runs", projectId]` on pipeline events, but the active-by-issue hook uses `["pipeline-runs", "active-by-issue", ...issueIds]`. Events never reach the stale data.

Result: wasteful backend calls on every project page load and during normal navigation, worsening with issue count.

## Scope

Four areas must change. All four are in scope.

### 1. New project-level endpoint

Create `GET /api/pipeline-runs/active-by-project?project_id=X` that returns active pipeline runs for a project.

**Important:** `PipelineRun` model has no `project_id` column. Use a JOIN through the `issues` table (`PipelineRun.issue_id == Issue.id`) to filter by `Issue.project_id`. This avoids any schema change or DB migration.

- Single query: `SELECT ... FROM pipeline_runs pr JOIN issues i ON pr.issue_id = i.id WHERE i.project_id = :project_id AND pr.status = 'RUNNING'`
- No URL bloat — one UUID instead of N
- Sorted by creation time descending
- Response: list of active pipeline runs with step info (same shape as `GET /api/pipeline-runs/{run_id}`)

### 2. Smart polling in the frontend

Update the `useActivePipelineRuns` hook to use adaptive polling:

- When the response returns zero active runs: poll every 30 seconds (or longer)
- When the response returns at least one active run: poll every 5 seconds
- When the user navigates away from issues: stop polling entirely (React Query auto-stops when component unmounts)
- The hook must accept `projectId` instead of (or in addition to) `issueIds`

### 3. WebSocket event invalidation

The new query key must start with `["pipeline-runs", projectId]` so existing WebSocket invalidation in event-context.tsx (which invalidates `["pipeline-runs", data.project_id]` on pipeline events) works automatically. No changes needed to event-context.tsx itself — only the query key prefix.

Actual WebSocket event types that trigger pipeline invalidation (event-context.tsx lines 302-312):
- `agent_step_started`
- `agent_step_completed`
- `agent_step_failed`
- `pipeline_completed`
- `agent_terminal_created`

### 4. Stabilize query keys

Query keys for pipeline runs must not change on every render. If dynamic data (like issue IDs) currently sits in the query key, it must be removed or memoized.

## Existing endpoint to deprecate

`GET /api/pipeline-runs/active-by-issue` with `?issue_ids=...` should be removed once the new endpoint replaces all callers. No backwards-compat shim needed — update the single caller.

## Frontend callers

- `frontend/src/features/pipeline-runs/hooks.ts` — `useActivePipelineRuns` hook
- `frontend/src/features/pipeline-runs/api.ts` — `fetchActivePipelineRuns` function
- `frontend/src/routes/projects/$projectId/issues/index.tsx` — component that calls the hook
- `frontend/src/shared/context/event-context.tsx` — WebSocket event handler (likely no changes needed)

## Constraints

- No new npm dependencies
- No changes to the pipeline run data model (no DB migrations) — use JOIN through issues table instead
- Must work with existing WebSocket event types (agent_step_started, agent_step_completed, agent_step_failed, pipeline_completed, agent_terminal_created)
- The existing hook signature should remain usable — callers should not need major refactors

## Acceptance Criteria

1. `GET /api/pipeline-runs/active-by-project?project_id=X` returns correct active runs via JOIN through issues table
2. Frontend uses the new endpoint instead of `active-by-issue`
3. Polling interval adapts: ~5s when active runs exist, ~30s when none
4. Polling stops when component unmounts
5. WebSocket pipeline events trigger data refresh (no extra 30s wait) — works because query key starts with `["pipeline-runs", projectId]`
6. No more than one backend call per poll interval regardless of issue count
7. No regressions in the issues page — pipeline status indicators still update in real-time
8. Old endpoint `active-by-issue` is removed with no orphaned references

## Non-goals

- NOT changing the issue list pagination or adding issue list pagination
- NOT changing the pipeline run data model or schema
- NOT adding new WebSocket event types
- NOT changing how non-pipeline data is fetched on the issues page
- NOT adding caching beyond what React Query provides
