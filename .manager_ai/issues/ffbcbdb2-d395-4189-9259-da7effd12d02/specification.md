# Extract `_find_task_issue` Utility from Duplicated Code

## Scope

Extract the duplicated project-scan pattern in `backend/app/mcp/server.py` into a shared `_find_task_issue(session, task_id)` helper function. Replace the 3 inline copies with calls to the helper.

No behavioral changes. No performance optimization. Pure extraction.

## Affected Code

**File:** `backend/app/mcp/server.py`

**3 functions contain identical project-scan logic:**

| Function | Lines | Variable name | Notes |
|----------|-------|---------------|-------|
| `update_task_status` | 424-432 | `issue_rec` | Uses `issue_rec` + `task_issue_id` independently |
| `update_task_name` | 480-488 | `issue` | Uses `issue` + `task_issue_id` |
| `delete_task` | 510-519 | `issue` | Has comment `# Find owning issue before deletion` |

**The duplicated block (exact):**
```python
issue = None
task_issue_id = ""
for project in await ProjectService(session).list_all(archived=False):
    from app.storage import issue_store as _is
    found = _is.find_task(project.path, task_id)
    if found is not None:
        issue, _ = found
        task_issue_id = issue.id
        break
```

Variation between copies: `update_task_status` renames the first variable to `issue_rec`. All 3 produce identical `(issue_record, issue_id)` output.

## Requirements

### 1. New helper function

Insert a module-level async helper near line 66 (after `_serialize_pipeline`, before `mcp_tool_wrapper` decorator):

```python
async def _find_task_issue(session, task_id: str) -> tuple[Any | None, str]:
    """Scan all active projects to find which issue owns a task.
    Returns (issue_record, issue_id). Both are None/"" if not found.
    """
```

- Use `Any` import from `typing` (or `typing.Optional` — follow existing import style).
- Move the `from app.storage import issue_store as _is` import inside the function body (preserve lazy import pattern).
- `ProjectService(session).list_all(archived=False)` via existing `ProjectService` import at top of file (already imported line 20).

### 2. Replace in `update_task_status` (lines 424-432)

Replace lines 424-432 with:
```python
issue_rec, task_issue_id = await _find_task_issue(session, task_id)
```

Local variables `issue_rec` and `task_issue_id` already exist in this function's scope — result destructures into them directly.

### 3. Replace in `update_task_name` (lines 480-488)

Replace lines 480-488 with:
```python
issue, task_issue_id = await _find_task_issue(session, task_id)
```

Local variables `issue` and `task_issue_id` already exist in this function's scope.

### 4. Replace in `delete_task` (lines 510-519)

Replace lines 510-519 with:
```python
issue, task_issue_id = await _find_task_issue(session, task_id)
```

Preserve the current variable names `issue` and `task_issue_id`. The comment `# Find owning issue before deletion` can be removed — the helper name is self-documenting.

## Constraints

- **Return signatures must not change** — all 3 MCP tools must return identical dict shapes:
  - `update_task_status`: `{"id": str, "name": str, "status": str}`
  - `update_task_name`: `{"id": str, "name": str}`
  - `delete_task`: `{"deleted": true}`
- **Timestamp format**: `str()` not `.isoformat()` — preserve existing format (`str(agent.created_at)` pattern, not `agent.created_at.isoformat()`).
- **No `@mcp_tool_wrapper` migration** — the 3 functions manage sessions/errors inline. Extracting the scan loop does not change this.
- **Insert position**: after `_serialize_pipeline` (line 65), before `mcp_tool_wrapper` (line 68). Preserves grouping: serializers first, then utilities, then decorator, then MCP tool implementations.
- **Lazy import**: keep `from app.storage import issue_store as _is` inside the helper body (not module-level). Matches existing pattern.

## Out of Scope

- Migrating `update_task_status`, `update_task_name`, or `delete_task` to use `@mcp_tool_wrapper`
- Performance optimization (still O(n) projects × O(1) scan per call)
- Renaming variables across the 3 callers beyond the replacement above
- Adding tests (existing tests must still pass as-is)
- Any changes outside `backend/app/mcp/server.py`

## Acceptance Criteria

1. `_find_task_issue(session, task_id)` exists as module-level helper between `_serialize_pipeline` and `mcp_tool_wrapper`
2. All 3 functions call the helper instead of inline scan
3. Each function's return dict is identical to pre-refactor
4. All existing tests pass
5. No new imports at module level (lazy import stays inside helper)
6. No changes outside `server.py`
