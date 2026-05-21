# Implementation Plan: Issue Categorization System

## Files to modify

| File | Change |
|------|--------|
| `backend/app/models/issue.py` | Add `category` column + `ALLOWED_CATEGORIES` constant |
| `backend/app/storage/issue_store.py` | Add `category` to `IssueRecord`, index, payload, disk write, rebuild |
| `backend/app/schemas/issue.py` | Add `category` to `IssueCreate`, `IssueUpdate`, `IssueResponse` |
| `backend/app/services/issue_service.py` | Pass `category` in `create()`, validate in `update_fields()` |
| `backend/alembic/versions/` | Auto-generate migration for new column |
| `frontend/src/shared/types/index.ts` | Add `category` to `Issue`, `IssueCreate`, `IssueUpdate` interfaces |
| `frontend/src/features/issues/components/new-issue-dialog.tsx` | Add category dropdown |
| `frontend/src/features/issues/components/issue-detail.tsx` | Show category badge, inline edit |
| `frontend/src/features/issues/components/issue-list.tsx` | Show category badge in table |
| `frontend/src/features/issues/components/kanban-card.tsx` | Show category badge on card |
| `frontend/src/features/issues/api.ts` | Pass `category` in create/update payload |

## Task 1: Backend model + storage layer

**Files:** `backend/app/models/issue.py`, `backend/app/storage/issue_store.py`

Add `category` field through the full backend data pipeline.

### Step 1: Add category to Issue model and ALLOWED_CATEGORIES

In `backend/app/models/issue.py`, add after priority line:
```python
ALLOWED_CATEGORIES = {
    "Bug", "Feature", "Improvement", "Documentation",
    "Refactor", "Security", "Performance", "UI/UX"
}
```

Add to `Issue` class after `priority`:
```python
category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
```

### Step 2: Add category to IssueRecord

In `backend/app/storage/issue_store.py`, add after `priority` in `IssueRecord` dataclass:
```python
category: str | None = None
```

### Step 3: Update index entry

In `_to_index_entry()`, add:
```python
"category": record.category,
```

### Step 4: Update light record

In `_index_to_light_record()`, add:
```python
category=entry.get("category"),
```

### Step 5: Update payload builder

In `_record_to_payload()`, add:
```python
"category": record.category,
```

### Step 6: Update disk writer

In `_write_issue_record()`, add to YAML payload dict:
```python
"category": payload.get("category"),
```

### Step 7: Update index rebuilder

In `rebuild_issues_index()`, add to entries dict:
```python
"category": data.get("category"),
```

### Step 8: Update create_issue for IssueRecord creation

In `create_issue()`, update `IssueRecord(...)` call to pass `category`.

In `load_issue()` disk fallback, add:
```python
category=data.get("category"),
```

### Step 9: Auto-generate migration

```bash
cd backend && python -m alembic revision --autogenerate -m "add_category_to_issues"
```

## Task 2: Backend schemas + service validation

**Files:** `backend/app/schemas/issue.py`, `backend/app/services/issue_service.py`

### Step 1: Add category to schemas

In `IssueCreate`:
```python
category: str | None = Field(None, max_length=50)
```

In `IssueUpdate`:
```python
category: str | None = Field(None, max_length=50)
```

In `IssueResponse`:
```python
category: str | None = None
```

In `IssueResponse.from_record()`, add:
```python
category=record.category,
```

### Step 2: Validate category in service

In `issue_service.py`, import `ALLOWED_CATEGORIES`.

In `update_fields()`, add before the generic loop:
```python
if "category" in kwargs and kwargs["category"] is not None:
    cat = kwargs.pop("category")
    if cat not in ALLOWED_CATEGORIES:
        raise ValidationError(f"Invalid category: {cat}. Allowed: {sorted(ALLOWED_CATEGORIES)}")
    rec.category = cat
```

In `create()`, pass `category` from args:
```python
async def create(self, project_id: str, description: str, priority: int = 3, category: str | None = None) -> IssueRecord:
    ...
    record = IssueRecord(..., category=category)
```

### Step 3: Update router to pass category

In `backend/app/routers/issues.py`, `create_issue`:
```python
record = await service.create(project_id=project_id, description=data.description, priority=data.priority, category=data.category)
```

## Task 3: Frontend types + API

**Files:** `frontend/src/shared/types/index.ts`, `frontend/src/features/issues/api.ts`

### Step 1: Update types

In `Issue` interface, add:
```typescript
category: string | null;
```

In `IssueCreate`, add:
```typescript
category?: string | null;
```

In `IssueUpdate`, add:
```typescript
category?: string | null;
```

### Step 2: Update API

In `createIssue()` function, include `category` in the request body.
In `updateIssue()` function, support `category` in the mutation variables.

## Task 4: Frontend UI - New Issue Dialog + Issue Detail

**Files:** `frontend/src/features/issues/components/new-issue-dialog.tsx`, `frontend/src/features/issues/components/issue-detail.tsx`

### Step 1: Add category dropdown to NewIssueDialog

Import `Select` components (already imported). Define `CATEGORIES` constant:
```typescript
const CATEGORIES = [
  "Bug", "Feature", "Improvement", "Documentation",
  "Refactor", "Security", "Performance", "UI/UX"
];
```

Add state: `const [category, setCategory] = useState<string | null>(null);`

Add `Select` dropdown between Priority and footer. "No category" as default option.

Update `handleSubmit` to send `category`.

Reset on dialog close: `setCategory(null)`.

### Step 2: Show category badge in IssueDetail

Import `Badge` component. Add category display next to StatusBadge showing the category with a colored badge.

Add inline edit: click badge → show Select dropdown to change category, calling `updateIssue`.

## Task 5: Frontend UI - Issue List + Kanban cards

**Files:** `frontend/src/features/issues/components/issue-list.tsx`, `frontend/src/features/issues/components/kanban-card.tsx`

### Step 1: Show category badge in issue list table

Add a small `Badge` next to the issue name in the list row.

### Step 2: Show category badge on kanban cards

Add a small category badge to `KanbanCard` component near the priority/status indicators.

## Task 6: Migration + test

**Files:** `backend/alembic/versions/`, test files

### Step 1: Run migration
```bash
cd backend && python -m alembic upgrade head
```

### Step 2: Quick backend test
```bash
cd backend && python -m pytest tests/ -x -k "issue" -v
```

### Step 3: Verify frontend builds
```bash
cd frontend && npm run build
```
