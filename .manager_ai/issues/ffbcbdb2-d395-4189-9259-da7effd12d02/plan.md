# Implementation Plan: Extract `_find_task_issue` Utility

## File Changed
`backend/app/mcp/server.py` — sole file affected (acceptance criterion #6)

## Tech Stack
Python 3.x + FastMCP. File uses `_`-prefixed module-level helpers, `@mcp_tool_wrapper` decorator pattern.

## Steps

### Step 1: Add `Any` to typing imports
**Location:** top of file, near line 4 (`from pathlib import Path`)
**Action:** Add `Any` to existing typing import if not present. Check if `from typing import Any` is already present — if not, add it.
**Why:** `_find_task_issue` return type uses `Any` for the issue record. SpecReviewer confirmed this is needed (acceptance criterion #5 says no NEW module-level imports for the storage lazy import, but typing imports are separate).

### Step 2: Insert `_find_task_issue` helper function
**Location:** Between `_serialize_pipeline` (ends line 65) and `mcp_tool_wrapper` decorator (line 68) → insert at line 66-67.
**Signature:**
```python
async def _find_task_issue(session, task_id: str) -> tuple[Any | None, str]:
    """Scan all active projects to find which issue owns a task.
    Returns (issue_record, issue_id). Both are None/"" if not found.
    """
    from app.storage import issue_store as _is
    for project in await ProjectService(session).list_all(archived=False):
        found = _is.find_task(project.path, task_id)
        if found is not None:
            issue_rec, _ = found
            return issue_rec, issue_rec.id
    return None, ""
```
**Key details:**
- Lazy import `from app.storage import issue_store as _is` inside function body (matches existing pattern)
- `ProjectService` already imported at line 20 — no new import needed
- `Any` from typing (added in Step 1)
- Uses `issue_rec` internally (like `update_task_status` call site) — return tuple general
- Returns early on first match (preserves existing `break` behavior)

### Step 3: Replace duplicate in `update_task_status` (lines 424-432)
**Before (9 lines):**
```python
            issue_rec = None
            task_issue_id = ""
            for project in await ProjectService(session).list_all(archived=False):
                from app.storage import issue_store as _is
                found = _is.find_task(project.path, task_id)
                if found is not None:
                    issue_rec, _ = found
                    task_issue_id = issue_rec.id
                    break
```
**After (1 line):**
```python
            issue_rec, task_issue_id = await _find_task_issue(session, task_id)
```
**Note:** Destructures into `issue_rec` and `task_issue_id` — matches existing variable names used later in this function.

### Step 4: Replace duplicate in `update_task_name` (lines 480-488)
**Before (9 lines):**
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
**After (1 line):**
```python
            issue, task_issue_id = await _find_task_issue(session, task_id)
```
**Note:** Destructures into `issue` and `task_issue_id` — matches existing variable names used later.

### Step 5: Replace duplicate in `delete_task` (lines 510-519)
**Before (10 lines):**
```python
            # Find owning issue before deletion
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
**After (1 line):**
```python
            issue, task_issue_id = await _find_task_issue(session, task_id)
```
**Note:** Remove `# Find owning issue before deletion` comment — helper name is self-documenting. Destructures into `issue` and `task_issue_id`.

### Step 6: Verify and run tests
**Action:** Run backend test suite to confirm no regressions:
```bash
cd backend && python -m pytest
```
All tests must pass (acceptance criterion #4).

## Verification Checklist
- [ ] `_find_task_issue` exists between `_serialize_pipeline` and `mcp_tool_wrapper` (lines 66-67)
- [ ] All 3 functions call the helper instead of inline scan
- [ ] Each function's return dict matches pre-refactor:
  - `update_task_status`: `{"id": str, "name": str, "status": str}`
  - `update_task_name`: `{"id": str, "name": str}`
  - `delete_task`: `{"deleted": true}`
- [ ] All existing tests pass
- [ ] No new module-level imports (lazy import stays inside helper)
- [ ] No changes outside `server.py`
