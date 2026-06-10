## Implementation Plan

1. Open `backend/app/routers/issues.py`
2. Replace `event_service.notify(` → `event_service.emit(` on both line 133 (inside `complete_issue()`) and line 159 (inside `force_finish_issue_endpoint()`)
3. Verify syntax with `python -c "import ast; ast.parse(open('backend/app/routers/issues.py').read())"`