Added `self._path_cache: dict[str, str] = {}` to `IssueService.__init__` and a cache check in `_resolve_path` to avoid duplicate `ProjectService.get_by_id()` SQL queries when multiple methods in the same HTTP request resolve the same `project_id`.

Changed 3 lines in `backend/app/services/issue_service.py`:
- `__init__`: added `self._path_cache: dict[str, str] = {}`
- `_resolve_path`: cache check before DB query, store result in cache, return from cache

Cache is naturally request-scoped (IssueService lives per-request). No TTL or invalidation needed. All 57 issue-related tests pass.