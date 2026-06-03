## Bug: `list_issues_full` returns `None` values causing 500 errors

### Error

```
AttributeError: 'NoneType' object has no attribute 'relations'
```
at `backend/app/services/issue_relation_service.py:86` in `get_relations_for_issue`.

### Root Cause

**`backend/app/storage/issue_store.py:165`** — In `list_issues()` fallback path, `None` is stored as the cached record:

```python
_core.upsert(project_path, "issues", e.get("id", ""), None, e)
```

This is intentional: the fallback path loads the light index from disk and stores `None` as the record so individual `load_issue()` calls hit the disk-fallback path instead. However, `list_issues_full()` at line 170-172 reads all cached records and returns them unfiltered:

```python
all_records = _core.list_all(project_path, "issues")
if all_records:
    return list(all_records)  # includes None
```

Since `[None]` is a non-empty (truthy) list, the fallback is skipped and `None` values propagate to callers.

### Affected Callers

Three methods in `issue_relation_service.py` iterate `list_issues_full` results and crash:
1. `get_relations_for_issue()` — line 86 — `GET /api/issues/{id}/relations`
2. `get_blockers()` — line 102
3. `delete_relation()` — line 122

### Fix

**Single change** in `backend/app/storage/issue_store.py:172`:

```python
# Before:
return list(all_records)
# After:
return [r for r in all_records if r is not None]
```

This matches what the fallback path already does at line 178 (`if full is not None`). The `relations` field on `IssueRecord` defaults to `[]`, so an issue with no relations iterates safely — only `None` causes the crash.

No other callers of `list_issues_full` need changes since the type signature already says `list[IssueRecord]` and filtering `None` makes it correct.
