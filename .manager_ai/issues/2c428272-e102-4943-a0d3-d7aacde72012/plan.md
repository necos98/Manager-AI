# Implementation Plan: Issue Tagging & Grouping

## Files to modify

| File | Change |
|------|--------|
| `backend/app/storage/issue_store.py` | Add `tags` to IssueRecord, serialization |
| `backend/app/schemas/issue.py` | Add `tags` to IssueCreate, IssueUpdate, IssueResponse |
| `backend/app/services/issue_service.py` | Tag normalization, aggregation, filter logic |
| `backend/app/routers/issues.py` | New `/tags` endpoint, `?tag=` query param |
| `frontend/src/shared/types/index.ts` | Add `tags` to TS interfaces |
| `frontend/src/features/issues/api.ts` | `fetchProjectTags`, `tag` param in fetchIssues |
| `frontend/src/features/issues/hooks.ts` | `useProjectTags`, tag in useIssues |
| `frontend/src/features/issues/components/new-issue-dialog.tsx` | Tag input with autocomplete |
| `frontend/src/features/issues/components/issue-detail.tsx` | Tag chips + inline add |
| `frontend/src/features/issues/components/issue-list.tsx` | Tag filter dropdown |

## Task 1: Backend — Data layer (issue_store.py + schemas)

### Step 1: Add tags to IssueRecord

In `backend/app/storage/issue_store.py`, add to IssueRecord dataclass:
```python
tags: list[str] = field(default_factory=list)
```

### Step 2: Add tags to serialization

In `_record_to_payload`:
```python
"tags": record.tags,
```

In `load_issue`, extract tags from YAML:
```python
tags=data.get("tags") or [],
```

### Step 3: Add tags to Pydantic schemas

In `backend/app/schemas/issue.py`:

`IssueCreate`:
```python
tags: list[str] | None = None
```

`IssueUpdate`:
```python
tags: list[str] | None = None
```

`IssueResponse`:
```python
tags: list[str] = []
```

Update `from_record`:
```python
tags=record.tags if hasattr(record, 'tags') else [],
```

## Task 2: Backend — Service layer (issue_service.py)

### Step 1: Tag normalization helper
```python
TAG_MAX_LEN = 50
TAG_MAX_COUNT = 20

def _normalize_tags(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    out = []
    for t in raw[:TAG_MAX_COUNT]:
        t = t.strip().lower()
        if t and len(t) <= TAG_MAX_LEN:
            if t not in out:
                out.append(t)
    return out
```

### Step 2: Handle tags in create()
After creating the record, if tags provided:
```python
if tags:
    record.tags = _normalize_tags(tags)
```

### Step 3: Handle tags in update_fields()
Allow setting tags via update:
```python
# In update_fields, tags key already works via setattr
# But normalize before setting
if "tags" in kwargs and kwargs["tags"] is not None:
    kwargs["tags"] = _normalize_tags(kwargs["tags"])
```

### Step 4: Tag aggregation method
```python
async def get_project_tags(self, project_id: str) -> list[str]:
    path = await self._resolve_path(project_id)
    records = issue_store.list_issues_full(path)
    tags = set()
    for r in records:
        for t in getattr(r, 'tags', []) or []:
            tags.add(t)
    return sorted(tags)
```

### Step 5: Tag filtering in list_by_project()
Add `tag: str | None = None` parameter. After status/search filtering:
```python
if tag:
    tag_lower = tag.strip().lower()
    records = [r for r in records if tag_lower in (getattr(r, 'tags', []) or [])]
```

## Task 3: Backend — Router layer (issues.py)

### Step 1: New /tags endpoint
```python
@router.get("/tags", response_model=list[str])
async def list_project_tags(project_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    return await service.get_project_tags(project_id)
```

Note: route must be registered BEFORE `/{issue_id}` to avoid path collision.

### Step 2: Tag filter in list_issues
Add `tag: str | None = Query(None)` parameter and pass to service.

## Task 4: Frontend — Types + API + Hooks

### Step 1: Update TypeScript types

In `frontend/src/shared/types/index.ts`:

`Issue`:
```typescript
tags: string[];
```

`IssueCreate`:
```typescript
tags?: string[];
```

`IssueUpdate`:
```typescript
tags?: string[];
```

### Step 2: Update API layer

In `frontend/src/features/issues/api.ts`:

`fetchIssues`:
```typescript
export function fetchIssues(projectId: string, status?: IssueStatus, search?: string, tag?: string): Promise<Issue[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search) params.set("search", search);
  if (tag) params.set("tag", tag);
  const qs = params.toString();
  return apiGet<Issue[]>(`/projects/${projectId}/issues${qs ? `?${qs}` : ""}`);
}
```

New function:
```typescript
export function fetchProjectTags(projectId: string): Promise<string[]> {
  return apiGet<string[]>(`/projects/${projectId}/issues/tags`);
}
```

### Step 3: Update hooks

In `frontend/src/features/issues/hooks.ts`:

`useIssues` — add tag param:
```typescript
export function useIssues(projectId: string, status?: IssueStatus, search?: string, tag?: string) {
  return useQuery({
    queryKey: [...issueKeys.all(projectId), "list", { status, search, tag }],
    queryFn: () => api.fetchIssues(projectId, status, search, tag),
  });
}
```

New hook:
```typescript
export function useProjectTags(projectId: string) {
  return useQuery({
    queryKey: [...issueKeys.all(projectId), "tags"],
    queryFn: () => api.fetchProjectTags(projectId),
    staleTime: 60_000,
  });
}
```

## Task 5: Frontend — TagInput component

Create `frontend/src/features/issues/components/tag-input.tsx`:

Autocomplete input component:
- Text input that filters existing tags
- Dropdown showing matching tags + "Create 'xyz'" for non-matching text
- Selected tags shown as removable chips (Badge + X button)
- Props: `tags: string[]`, `onChange: (tags: string[]) => void`, `availableTags: string[]`, `disabled?: boolean`
- Enter or comma to add tag
- Backspace on empty input removes last tag

## Task 6: Frontend — NewIssueDialog (add tag input)

In `new-issue-dialog.tsx`:
- Import TagInput, useProjectTags
- Add `const [tags, setTags] = useState<string[]>([])`
- Add `const { data: availableTags } = useProjectTags(projectId)`
- Add TagInput component below Priority dropdown
- Pass tags in create mutation: `createIssue.mutate({ description, priority, tags })`

## Task 7: Frontend — IssueDetail (tag chips + inline add)

In `issue-detail.tsx`:
- Import TagInput, useProjectTags
- After StatusBadge, render tag chips:
```tsx
{issue.tags?.map(tag => (
  <Link key={tag} to="/projects/$projectId/issues" params={{ projectId }} search={{ tag }}>
    <Badge variant="secondary" className="cursor-pointer">{tag}</Badge>
  </Link>
))}
```
- Add a `+` button that toggles inline TagInput for adding tags
- On tag add: `updateIssue.mutate({ tags: [...(issue.tags || []), newTag] })`
- On tag remove: `updateIssue.mutate({ tags: issue.tags.filter(t => t !== removedTag) })`

## Task 8: Frontend — IssueList (tag filter dropdown)

In `issue-list.tsx`:
- Import useProjectTags, Select
- Read current tag filter from route search params
- Add Select dropdown above issue list:
  - "All tags" (default, clears filter)
  - Each unique tag as option
- Pass selected tag to parent/route as search param
- Parent page passes `tag` to `useIssues(projectId, status, search, tag)`

### Step also: Update issues route page

In `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`:
- Read `tag` from route search params
- Pass to `useIssues` hook

Also need to check how the index route works in the issues page.

Check `frontend/src/routes/projects/$projectId/issues/` for the index route that renders IssueList.

## Execution order

Tasks 1→2→3 (backend) must be sequential. Tasks 4→5 (frontend infrastructure) must follow. Tasks 6,7,8 can be parallelized.

1. Task 1: Backend data layer
2. Task 2: Backend service layer
3. Task 3: Backend router layer
4. Task 4: Frontend types + API + hooks
5. Task 5: Frontend TagInput component
6. Task 6: Frontend NewIssueDialog
7. Task 7: Frontend IssueDetail
8. Task 8: Frontend IssueList + route
