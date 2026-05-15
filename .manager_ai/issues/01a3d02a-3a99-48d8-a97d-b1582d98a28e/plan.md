# Implementation Plan: Exclude Archived Projects From All Operations

## Files to modify

| File | Change |
|------|--------|
| `backend/app/services/issue_service.py:92` | `archived=None` → `archived=False` |
| `backend/app/services/memory_service.py:37` | `archived=None` → `archived=False` |
| `backend/app/services/task_service.py:31,77,85,109` | `archived=None` → `archived=False` (4 occurrences) |
| `backend/app/services/issue_relation_service.py:42,145` | `_all_paths()` uses `archived=None` → `archived=False`; `_detect_cycle()` calls `_all_paths()` so fixed transitively |
| `backend/app/mcp/server.py:389,445,476` | `archived=None` → `archived=False` (3 occurrences) |
| `backend/app/routers/projects.py:407-427` | Add archived guard before rebuild |

## Tasks

### Task 1: Fix cross-project scans in services

Change `archived=None` to `archived=False` in:
- `issue_service.py` line 92
- `memory_service.py` line 37
- `task_service.py` lines 31, 77, 85, 109
- `issue_relation_service.py` line 42

### Task 2: Fix cross-project scans in MCP server

Change `archived=None` to `archived=False` in:
- `mcp/server.py` lines 389, 445, 476

### Task 3: Add archived guard to rebuild-index endpoint

In `projects.py` `POST /{project_id}/rebuild-index`, add after `project = await service.get_by_id(project_id)`:
```python
if project.archived_at is not None:
    raise HTTPException(status_code=400, detail="Cannot rebuild index for archived project")
```

### Task 4: Add/update tests

- Verify archived projects are skipped in cross-project lookups
- Verify rebuild-index returns 400 for archived projects
- Verify unarchived projects still work normally

### Task 5: Verify with existing tests

Run full test suite to ensure no regressions.