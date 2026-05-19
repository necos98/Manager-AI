## Summary

Changed all cross-project scan locations from `archived=None` (return all projects) to `archived=False` (return only active). Added a guard on the rebuild-index endpoint to reject archived projects with HTTP 400.

## Files changed

- `app/services/issue_service.py:92` — `archived=None` → `archived=False`
- `app/services/memory_service.py:37` — `archived=None` → `archived=False`
- `app/services/task_service.py:31,77,85,109` — `archived=None` → `archived=False`
- `app/services/issue_relation_service.py:42` — `archived=None` → `archived=False`
- `app/mcp/server.py:389,445,476` — `archived=None` → `archived=False`
- `app/routers/projects.py` — added archived guard on `POST /{project_id}/rebuild-index`

## Test results

- 8 new tests in `test_archived_exclusion.py` — all pass
- 6 existing archive tests in `test_project_service_archive.py` — all pass
- `test_rebuild_index_archived_project_returns_400` — passes
- Full suite: 513 passed, 32 pre-existing failures (router test infrastructure, unrelated), 13 pre-existing errors

## No regressions