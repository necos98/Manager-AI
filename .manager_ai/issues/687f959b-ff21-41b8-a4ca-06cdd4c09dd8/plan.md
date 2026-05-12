## Implementation Plan

One-line change in `backend/app/services/project_service.py`.

### Task 1: Verify current behavior
Run existing dashboard tests to confirm they pass before the change.

### Task 2: Replace `list_issues_full` with `list_issues`
In `get_dashboard_data()`, line 77, change:
```python
for r in issue_store.list_issues_full(project.path)
```
to:
```python
for r in issue_store.list_issues(project.path)
```

### Task 3: Verify tests still pass
Run dashboard tests again to confirm no regression.