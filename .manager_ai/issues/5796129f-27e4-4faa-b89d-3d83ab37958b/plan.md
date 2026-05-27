# Implementation Plan: Finished Issues — Pagination

## File Map

| # | File | Action |
|---|------|--------|
| 1 | `backend/app/models/issue.py` | Modify — add `finished_at` column |
| 2 | `backend/app/storage/issue_store.py` | Modify — add `finished_at` to IssueRecord + helpers |
| 3 | `backend/app/schemas/issue.py` | Modify — add `finished_at` to IssueResponse |
| 4 | `backend/app/services/issue_service.py` | Modify — set `finished_at` in complete_issue, sort + paginate in list_by_project |
| 5 | `backend/app/routers/issues.py` | Modify — add `limit`/`offset` params |
| 6 | `frontend/src/shared/types/index.ts` | Modify — add `finished_at` to Issue type |
| 7 | `frontend/src/features/issues/api.ts` | Modify — add pagination params to fetchIssues |
| 8 | `frontend/src/features/issues/hooks.ts` | Modify — add pagination params to useIssues |
| 9 | `frontend/src/features/issues/components/kanban-board.tsx` | Modify — separate Finished fetch + Load more |
| 10 | `frontend/src/features/issues/components/kanban-column.tsx` | Modify — optional Load more button |
| 11 | Migration | Create — Alembic migration for `finished_at` |

---

## Task 1: Backend model + dataclass — `finished_at`

**Files:** `backend/app/models/issue.py`, `backend/app/storage/issue_store.py`

### Step 1.1: Add column to Issue model
In `backend/app/models/issue.py`, after `updated_at`:
```python
finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

### Step 1.2: Add field to IssueRecord dataclass
In `backend/app/storage/issue_store.py`, in `IssueRecord` dataclass, after `updated_at`:
```python
finished_at: str | None = None
```

### Step 1.3: Update all helper functions in issue_store.py
- `_to_index_entry`: add `"finished_at": record.finished_at`
- `_index_to_light_record`: add `finished_at=_as_iso(entry.get("finished_at"))`
- `_record_to_payload`: add `"finished_at": record.finished_at`
- `_write_issue_record`: add `"finished_at": payload.get("finished_at")` to yaml_payload
- `rebuild_issues_index`: add `"finished_at": _as_iso(data.get("finished_at"))`

### Step 1.4: Create Alembic migration
```bash
cd backend && python -m alembic revision --autogenerate -m "add finished_at to issues"
```

### Step 1.5: Verify migration
```bash
cd backend && python -m alembic upgrade head
```

---

## Task 2: Backend service + router — pagination logic

**Files:** `backend/app/services/issue_service.py`, `backend/app/routers/issues.py`, `backend/app/schemas/issue.py`

### Step 2.1: Add `finished_at` to IssueResponse
In `backend/app/schemas/issue.py`, add field:
```python
finished_at: datetime | None = None
```
In `from_record`:
```python
finished_at=_parse_dt(record.finished_at) if getattr(record, 'finished_at', None) else None,
```

### Step 2.2: Set `finished_at` in complete_issue
In `backend/app/services/issue_service.py`, in `complete_issue()`, before `issue_store.update_issue`:
```python
rec.finished_at = _now_iso()
```

### Step 2.3: Add pagination to list_by_project
In `list_by_project`, add params `limit: int | None = None, offset: int = 0`.

Replace the sort line:
```python
if status and (status.value if isinstance(status, IssueStatus) else str(status)) == IssueStatus.FINISHED.value:
    records.sort(key=lambda r: (r.finished_at or r.updated_at or ""), reverse=True)
else:
    records.sort(key=lambda r: (r.priority, r.created_at))
```

Apply pagination (only when `limit` is set):
```python
if limit is not None:
    records = records[offset:offset + limit]
```

### Step 2.4: Add params to router
In `backend/app/routers/issues.py`, in `list_issues`:
```python
limit: int | None = Query(None),
offset: int = Query(0),
```
Pass to `service.list_by_project(..., limit=limit, offset=offset)`.

---

## Task 3: Frontend types + API + hooks

**Files:** `frontend/src/shared/types/index.ts`, `frontend/src/features/issues/api.ts`, `frontend/src/features/issues/hooks.ts`

### Step 3.1: Add `finished_at` to Issue type
In `frontend/src/shared/types/index.ts`, in `Issue` interface:
```typescript
finished_at: string | null;
```

### Step 3.2: Add pagination params to fetchIssues
In `frontend/src/features/issues/api.ts`:
```typescript
export function fetchIssues(
  projectId: string,
  status?: IssueStatus,
  search?: string,
  tag?: string,
  limit?: number,
  offset?: number,
): Promise<Issue[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search) params.set("search", search);
  if (tag) params.set("tag", tag);
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset) params.set("offset", String(offset));
  const qs = params.toString();
  return apiGet<Issue[]>(`/projects/${projectId}/issues${qs ? `?${qs}` : ""}`);
}
```

### Step 3.3: Update useIssues hook
In `frontend/src/features/issues/hooks.ts`:
```typescript
export function useIssues(projectId: string, status?: IssueStatus, search?: string, tag?: string, limit?: number, offset?: number) {
  return useQuery({
    queryKey: [...issueKeys.all(projectId), "list", { status, search, tag, limit, offset }],
    queryFn: () => api.fetchIssues(projectId, status, search, tag, limit, offset),
  });
}
```

---

## Task 4: Kanban UI — paginated Finished column

**Files:** `frontend/src/features/issues/components/kanban-board.tsx`, `frontend/src/features/issues/components/kanban-column.tsx`

### Step 4.1: Add Load more props to KanbanColumn
In `kanban-column.tsx`, add to interface:
```typescript
onLoadMore?: () => void;
hasMore?: boolean;
isLoadingMore?: boolean;
```
At bottom of the column scroll area, after the issue cards:
```tsx
{onLoadMore && hasMore && (
  <Button variant="ghost" size="sm" onClick={onLoadMore} disabled={isLoadingMore} className="mt-2 w-full">
    {isLoadingMore ? "Loading..." : "Load more"}
  </Button>
)}
```

### Step 4.2: Separate Finished fetch in KanbanBoard
In `kanban-board.tsx`:

Add imports for `useState`, `useEffect`:
```typescript
import { useState, useEffect } from "react";
```

Add constant:
```typescript
const FINISHED_PAGE_SIZE = 10;
```

Add state:
```typescript
const [finishedOffset, setFinishedOffset] = useState(0);
const [allFinished, setAllFinished] = useState<Issue[]>([]);
```

Add separate query for paginated Finished:
```typescript
const { data: finishedPage, isFetching: finishedLoading } = useIssues(
  projectId, "Finished", undefined, tag !== "all" ? tag : undefined, FINISHED_PAGE_SIZE, finishedOffset
);
```

Accumulate finished issues:
```typescript
useEffect(() => {
  if (finishedPage) {
    setAllFinished(prev => finishedOffset === 0 ? finishedPage : [...prev, ...finishedPage]);
  }
}, [finishedPage, finishedOffset]);
```

In the `byStatus` memo, replace Finished column data:
```typescript
const byStatus = useMemo(() => {
  const map = new Map<IssueStatus, Issue[]>();
  COLUMNS.forEach((s) => map.set(s, []));
  // Exclude Finished from main query results (they come from paginated query)
  filtered.filter(i => i.status !== "Finished").forEach((i) => map.get(i.status)?.push(i));
  // Use paginated finished issues
  map.set("Finished", allFinished);
  return map;
}, [filtered, allFinished]);
```

Pass new props to KanbanColumn for Finished:
```tsx
<KanbanColumn
  key="Finished"
  status="Finished"
  issues={byStatus.get("Finished") ?? []}
  ...
  onLoadMore={finishedOffset === 0 ? () => setFinishedOffset(FINISHED_PAGE_SIZE) : () => setFinishedOffset(prev => prev + FINISHED_PAGE_SIZE)}
  hasMore={finishedPage && finishedPage.length >= FINISHED_PAGE_SIZE}
  isLoadingMore={finishedLoading}
/>
```

### Step 4.3: Reset finished state when tag changes
```typescript
useEffect(() => {
  setFinishedOffset(0);
  setAllFinished([]);
}, [tag]);
```

---

## Task 5: Run, verify, commit

### Step 5.1: Apply migrations and start backend
```bash
cd backend && python -m alembic upgrade head && cd .. && python start.py
```

### Step 5.2: Verify API
```bash
curl "http://127.0.0.1:8000/api/projects/<project_id>/issues?status=Finished&limit=10&offset=0"
```
Expected: returns max 10 finished issues sorted by finished_at DESC.

### Step 5.3: Verify UI
1. Open app, go to Issues page
2. Finished column shows max 10 issues
3. Click "Load more" — next 10 load
4. Switching tag resets pagination

### Step 5.4: Commit
```bash
git add -A && git commit -m "feat: paginate finished issues in chronological order"
```
