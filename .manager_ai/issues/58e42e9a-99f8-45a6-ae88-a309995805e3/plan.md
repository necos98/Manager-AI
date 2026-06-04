# Implementation Plan: Show Pipeline Name When Running on Issue

## Overview

5 work items: (1) batch endpoint for kanban, (2) TS PipelineRun type fix, (3) issue detail pipeline name badge, (4) PipelineProgress header name, (5) kanban card pipeline indicator.

## Files to Change

### Backend

| File | Action |
|------|--------|
| `backend/app/routers/pipeline_runs.py` | Add GET `/api/pipeline-runs/active-by-issue` endpoint |
| `backend/app/services/pipeline_run_service.py` | Add `get_active_runs_for_issues()` method |
| `backend/app/schemas/pipeline_run.py` | Add `ActivePipelineRunByIssueResponse` schema |

### Frontend

| File | Action |
|------|--------|
| `frontend/src/shared/types/index.ts` | Add `pipeline_name: string` to `PipelineRun` interface |
| `frontend/src/features/pipeline-runs/api.ts` | Add `fetchActivePipelineRuns()` function |
| `frontend/src/features/issues/components/issue-detail.tsx` | Add pipeline name badge in header metadata area |
| `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx` | Replace hardcoded "Pipeline" with `activeRun.pipeline_name` |
| `frontend/src/features/issues/components/kanban-card.tsx` | Add pipeline indicator (colored dot + name) |
| `frontend/src/features/issues/hooks.ts` or new hook | Add hook for batch active pipeline runs |
| `frontend/src/routes/projects/$projectId/issues/index.tsx` | Fetch active pipeline runs for all issues |

## Step-by-Step

### Step 1: Backend — batch endpoint for active pipeline runs

**File: `backend/app/schemas/pipeline_run.py`**

Add a new response model for the batch endpoint (minimal — only needs pipeline_name and status):

```python
class ActivePipelineRunResponse(BaseModel):
    pipeline_name: str
    status: str

class ActivePipelineRunByIssueResponse(BaseModel):
    __root__: dict[str, ActivePipelineRunResponse | None]
```

**File: `backend/app/services/pipeline_run_service.py`**

Add method `get_active_runs_for_issues(issue_ids: list[str]) -> dict[str, dict]`:
- Query PipelineRun WHERE issue_id IN issue_ids AND status = 'RUNNING'
- Eager-load pipeline relationship for pipeline.name
- Return dict: issue_id → {pipeline_name, status} or null for issues without active run

**File: `backend/app/routers/pipeline_runs.py`**

Add endpoint:
```python
@router.get("/active-by-issue", response_model=dict[str, ActivePipelineRunResponse | None])
async def get_active_pipeline_runs_by_issue(
    issue_ids: str = Query(..., min_length=1),  # comma-separated
    db: AsyncSession = Depends(get_db),
):
    ids = [id.strip() for id in issue_ids.split(",") if id.strip()]
    svc = PipelineRunService(db)
    return await svc.get_active_runs_for_issues(ids)
```

### Step 2: Frontend — fix TS PipelineRun type

**File: `frontend/src/shared/types/index.ts`** (line 561)

Add `pipeline_name: string;` to `PipelineRun` interface.

### Step 3: Frontend — issue detail pipeline name badge

**File: `frontend/src/features/issues/components/issue-detail.tsx`**

After line 62 (`const { data: pipelineRuns } = usePipelineRuns(projectId, issue.id)`):
- Derive `activeRun = pipelineRuns?.find(r => r.status === "RUNNING")` — but this already matches existing fetch pattern. Actually, since PipelineRun has pipeline_name now, find the RUNNING run.

In the header metadata area (near StatusBadge), render when `activeRun` exists:
```
{activeRun && (
  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
    Pipeline: {activeRun.pipeline_name}
  </Badge>
)}
```

### Step 4: Frontend — PipelineProgress header name

**File: `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx`** (line 153)

Replace `<span className="text-sm font-semibold">Pipeline</span>` with the actual pipeline name from `runs[0]?.pipeline_name`. The component already has `runs` from `usePipelineRuns`. Show `runs[0]?.pipeline_name || "Pipeline"`.

Wait — the pipeline_run_id from activeRun in the issue detail context needs to match. Actually, the running pipeline's data already comes through `usePipelineRuns`. The first run (most recent) is the active one. A safer approach: `activeRun = runs?.find(r => r.status === "RUNNING")`, then use `activeRun?.pipeline_name`. But actually the entire PipelineProgress is shown conditionally only when there's an active run, so `runs[0]` is fine.

Simpler fix: line 153, replace `Pipeline` with `runs[0]?.pipeline_name || "Pipeline"`.

### Step 5: Frontend — batch fetch hook for kanban

**File: `frontend/src/features/pipeline-runs/api.ts`**

Add:
```typescript
export function fetchActivePipelineRuns(issueIds: string[]): Promise<Record<string, { pipeline_name: string; status: string } | null>> {
  return apiGet(`/pipeline-runs/active-by-issue?issue_ids=${issueIds.join(",")}`);
}
```

Create new hook file or add to existing hooks: `frontend/src/features/pipeline-runs/hooks.ts`:

```typescript
export function useActivePipelineRuns(issueIds: string[]) {
  return useQuery({
    queryKey: ["active-pipeline-runs", issueIds],
    queryFn: () => fetchActivePipelineRuns(issueIds),
    enabled: issueIds.length > 0,
    refetchInterval: 5000,
  });
}
```

### Step 6: Frontend — kanban card pipeline indicator

**File: `frontend/src/features/issues/components/kanban-card.tsx`**

Add small colored dot + pipeline name in the top metadata area. The kanban card receives `issue.id` — it needs access to pipeline run data. Pass it via props (e.g., `activePipelineName?: string`), or fetch from the parent.

**Better approach: integrate at the `KanbanBoard` level.**

In `frontend/src/routes/projects/$projectId/issues/index.tsx`:
- After fetching issues, extract their IDs and call `useActivePipelineRuns(issueIds)`
- Pass the active runs map to `KanbanBoard`, which passes it to each `KanbanCard`

Actually, `KanbanBoard` → `KanbanColumn` → `KanbanCard`. Pass through props.

**File: `frontend/src/features/issues/components/kanban-card.tsx`**

Add prop: `activePipelineName?: string`. In the render, inside the card content near the terminal icon, show:
```tsx
{activePipelineName && (
  <span className="flex items-center gap-1 text-xs text-blue-600">
    <span className="size-2 rounded-full bg-blue-500" />
    <span className="max-w-24 truncate">{activePipelineName}</span>
  </span>
)}
```

**File: `frontend/src/features/issues/components/kanban-board.tsx`**: Add prop `activeRunsByIssue: Record<string, { pipeline_name: string; status: string } | null>` and pass to KanbanColumn → KanbanCard.

**File: `frontend/src/features/issues/components/kanban-column.tsx`**: Add same prop and pass through.

## Execution Order

1. Backend: schema + service method + router endpoint
2. Frontend: TS type fix (pipeline_name on PipelineRun)
3. Frontend: API client function + hook for batch fetch
4. Frontend: Issue detail pipeline name badge
5. Frontend: PipelineProgress header name
6. Frontend: Kanban card pipeline indicator (board → column → card prop drilling)

## Dependencies

- Steps 3-6 depend on steps 1-2 (types must exist, endpoint must exist)
- Step 6 depends on step 3 (hook)
- Steps 4 and 5 are independent of each other
