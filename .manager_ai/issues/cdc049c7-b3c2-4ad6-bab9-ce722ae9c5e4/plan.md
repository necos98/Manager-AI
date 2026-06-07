## Implementation Plan: Optimize active-by-issue endpoint and polling

### Overview

Replace N+1 ID query pattern with project-scoped JOIN query. Add adaptive polling. Fix WebSocket invalidation via query key alignment. Remove old endpoint.

### 1. Backend: Add `get_active_runs_for_project` to PipelineRunService

**File:** `backend/app/services/pipeline_run_service.py`

Add new method:
```python
async def get_active_runs_for_project(self, project_id: str) -> list[dict]:
```
- JOIN `PipelineRun.issue_id` → `Issue.id` via SQLAlchemy relationship
- Filter: `Issue.project_id == project_id` AND `PipelineRun.status == RUNNING`
- Eager-load `Pipeline` (for pipeline_name) and `step_runs` → `pipeline_step` → `agent`
- Sort by `PipelineRun.created_at.desc()`
- Return list of dicts in same shape as `get_run()` (full PipelineRunResponse)

**Import needed:** `from app.models.issue import Issue`

**Why:** No `project_id` column on `PipelineRun`. JOIN through `issues` table avoids schema/migration changes.

### 2. Backend: Add new GET endpoint, remove old one

**File:** `backend/app/routers/pipeline_runs.py`

- Add `GET /api/pipeline-runs/active-by-project?project_id=X`
  - Query param: `project_id: str = Query(...)`
  - Returns `list[PipelineRunResponse]` (reuse existing schema)
  - Calls `svc.get_active_runs_for_project(project_id)`
- Remove `GET /api/pipeline-runs/active-by-issue` handler entirely
  - Remove the `issue_ids` Query import too (keep it if used elsewhere)

### 3. Frontend: Update API layer

**File:** `frontend/src/features/pipeline-runs/api.ts`

- Replace `fetchActivePipelineRuns(issueIds)` with `fetchActivePipelineRunsByProject(projectId: string)`
  - Calls `GET /api/pipeline-runs/active-by-project?project_id=${projectId}`
  - Returns `Promise<PipelineRun[]>` (full runs, not dict)
- Remove the old function

### 4. Frontend: Rewrite `useActivePipelineRuns` hook with smart polling

**File:** `frontend/src/features/pipeline-runs/hooks.ts`

- Change signature: `useActivePipelineRuns(projectId: string)` (was `issueIds: string[]`)
- New query key: `pipelineRunKeys.activeByProject(projectId)` → `["pipeline-runs", projectId, "active-by-project"]`
  - This prefix matches WebSocket invalidation in event-context.tsx line 310: `["pipeline-runs", data.project_id]`
- Adaptive `refetchInterval`:
  ```ts
  refetchInterval: (query) => {
    const data = query.state.data;
    return data && Object.keys(data).length > 0 ? 5000 : 30000;
  }
  ```
- Transform response: `PipelineRun[]` → `Record<string, {pipeline_name: string, status: string} | null>` for backward compat with KanbanBoard
  - `return Object.fromEntries((runs ?? []).map(r => [r.issue_id, { pipeline_name: r.pipeline_name, status: r.status }]));`
- Remove `activeByIssue` key from `pipelineRunKeys`
- Set `enabled: Boolean(projectId)` instead of `issueIds.length > 0`

### 5. Frontend: Update caller in issues page

**File:** `frontend/src/routes/projects/$projectId/issues/index.tsx`

- Change line 41: `const { data: activePipelineRuns } = useActivePipelineRuns(issueIds);`
  → `const { data: activePipelineRuns } = useActivePipelineRuns(projectId);`
- Remove line 40: `const issueIds = issues?.map((i) => i.id) ?? [];` (only used for this call)
- Everything downstream (KanbanBoard, KanbanColumn, individual issue cards) stays unchanged since the hook returns the same dict format

### 6. Verify WebSocket invalidation works

**File:** `frontend/src/shared/context/event-context.tsx` (no changes needed)

Line 310 already invalidates `["pipeline-runs", data.project_id]`. New query key `["pipeline-runs", projectId, "active-by-project"]` starts with `["pipeline-runs", projectId]`, so React Query's prefix matching in `invalidateQueries` finds it automatically.

### Edge Cases & Gotchas

- **Empty project**: 0 issues → `get_active_runs_for_project` returns `[]` → hook returns `{}` → polling stays at 30s. Correct.
- **Many active runs**: Single JOIN query, no N+1. One UUID param instead of N.
- **Component unmount**: React Query auto-cancels polling. `enabled` flag prevents fetch when no projectId.
- **Old endpoint removal**: Only caller is `fetchActivePipelineRuns` in api.ts — being replaced in same PR. No orphans.
