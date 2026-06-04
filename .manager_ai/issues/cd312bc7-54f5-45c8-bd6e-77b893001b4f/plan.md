## Implementation Plan: Fix N+1 query in issue relations loading

### Overview

Replace N parallel `GET /api/issues/{id}/relations` calls with a single `POST /api/issues/relations/batch` call. Backend: single-pass scan returns `{blocked_ids: string[]}`. Frontend: `useBlockedIssueIds` hook switches from `useQueries` to one `useQuery`.

### Files to change

| File | Change |
|------|--------|
| `backend/app/schemas/issue_relation.py` | Add `BlockedIdsRequest` + `BlockedIdsResponse` schemas |
| `backend/app/services/issue_relation_service.py` | Add `get_blocked_issue_ids()` — single-pass scan, returns only blocked IDs |
| `backend/app/routers/issue_relations.py` | Add `batch_router` with `POST /api/issues/relations/batch` |
| `backend/app/main.py` | Register `batch_router` |
| `frontend/src/features/issues/api-relations.ts` | Add `fetchBlockedIssueIds(issueIds)` calling batch endpoint |
| `frontend/src/features/issues/hooks-relations.ts` | Replace `useQueries` in `useBlockedIssueIds` with single `useQuery` |

### Step 1: Backend schemas (`schemas/issue_relation.py`)

Add two models:

```python
class BlockedIdsRequest(BaseModel):
    issue_ids: list[str]

class BlockedIdsResponse(BaseModel):
    blocked_ids: list[str]
```

### Step 2: Backend service method (`services/issue_relation_service.py`)

Add `get_blocked_issue_ids(self, issue_ids: list[str]) -> list[str]`:

```python
async def get_blocked_issue_ids(self, issue_ids: set[str]) -> list[str]:
    blocked: set[str] = set()
    for path in await self._all_paths():
        for issue in issue_store.list_issues_full(path):
            if issue is None:  # filter None sentinels from memory fallback path
                continue
            for rel in issue.relations:
                if rel.type == RelationType.BLOCKS.value and rel.target_id in issue_ids:
                    blocked.add(rel.target_id)
    return sorted(blocked)
```

Design notes:
- Accept `set[str]` for O(1) membership check (caller converts list→set)
- Single scan of all projects — same as `get_blockers()` but filtered by requested IDs
- Filter None sentinels from `list_issues_full` (see memory: `list_issues_full` returns None values from memory fallback path)
- Return sorted for deterministic ordering
- MemoryStore is RAM-first, so a single pass is fast regardless of issue count

### Step 3: Backend batch router (`routers/issue_relations.py`)

New `batch_router` (separate from the `{issue_id}`-prefixed router):

```python
batch_router = APIRouter(prefix="/api/issues/relations", tags=["issue-relations"])

@batch_router.post("/batch", response_model=BlockedIdsResponse)
async def get_blocked_ids(data: BlockedIdsRequest, db: AsyncSession = Depends(get_db)):
    svc = IssueRelationService(db)
    blocked_ids = await svc.get_blocked_issue_ids(set(data.issue_ids))
    return BlockedIdsResponse(blocked_ids=blocked_ids)
```

Register in `main.py`:
```python
app.include_router(issue_relations.batch_router)
```

### Step 4: Frontend API function (`api-relations.ts`)

```typescript
export function fetchBlockedIssueIds(issueIds: string[]): Promise<string[]> {
  return apiPost<{ blocked_ids: string[] }>("/issues/relations/batch", { issue_ids: issueIds })
    .then(r => r.blocked_ids);
}
```

Note: the URL path is `/issues/relations/batch` — Vite dev proxy prepends `/api`.

### Step 5: Frontend hook rewrite (`hooks-relations.ts`)

Replace `useBlockedIssueIds`:

```typescript
export function useBlockedIssueIds(issues: Issue[]) {
  const issueIds = issues.map(i => i.id);
  const { data } = useQuery({
    queryKey: ["relations", "batch", ...issueIds],
    queryFn: () => fetchBlockedIssueIds(issueIds),
    enabled: issueIds.length > 0,
  });
  return new Set(data ?? []);
}
```

Changes:
- Remove `useQueries` import (keep `useQuery`)
- Remove `fetchRelations` import (add `fetchBlockedIssueIds`)
- Single `useQuery` with composite key `["relations", "batch", ...ids]` — React Query serializes this for cache key, and issue IDs change → refetch
- `enabled` guard prevents request when issues list is empty
- Consumer interface unchanged: returns `Set<string>`
- The old per-issue relation caches (`["relations", id]`) become unreferenced — React Query garbage collects them

### Data flow

```
Frontend: issues[] -> useBlockedIssueIds(issues)
  -> POST /api/issues/relations/batch { issue_ids: [...] }
    -> get_blocked_issue_ids(set(issue_ids))  # single scan
      -> return { blocked_ids: [...] }
  -> new Set(blocked_ids)  ->  kanban: blockedIssueIds.has(id)
```

### Dependencies (task order)

1. Backend schemas (no deps)
2. Backend service method (depends on 1)
3. Backend batch router + registration (depends on 1, 2)
4. Frontend API function (depends on 3 — could parallelize with 2)
5. Frontend hook rewrite (depends on 4)
6. Verify: run existing tests, manual check

Tasks 1+2 are strongly ordered. Tasks 4+5 are frontend-only, parallelizable with backend after the API contract is agreed.