Code review complete. Reviewed all 5 changed files (models/issue.py, issue_service.py, test_issue_model.py, test_issue_service.py, test_routers_issues.py).

**Verdict: PASS — no issues found.**

All changes correct:
1. ✅ `VALID_TRANSITIONS` dict removed from `models/issue.py`
2. ✅ `update_status()` simplified — accepts any IssueStatus, CANCELED special case removed
3. ✅ Import cleaned up in `issue_service.py`
4. ✅ All lifecycle guards untouched (create_spec, edit_spec, create_plan, edit_plan, accept_issue, complete_issue, cancel_issue still enforce status checks)
5. ✅ Tests removed — 3 model tests, 2 service tests, 1 router test; docstring fixed
6. ✅ Zero VALID_TRANSITIONS references remain in backend
7. ✅ Scope boundary respected — no lifecycle or frontend changes