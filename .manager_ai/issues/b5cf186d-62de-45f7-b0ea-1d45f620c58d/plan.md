## Architecture

Add instance-level dict cache to `IssueService` for `project_id → path` lookups. Since IssueService is created per-request, the cache is naturally request-scoped and needs no TTL or invalidation.

## Files

- **Modify:** `backend/app/services/issue_service.py` — add `_path_cache` dict and cache check in `_resolve_path`

## Implementation

1. Add `self._path_cache: dict[str, str] = {}` to `__init__`
2. In `_resolve_path`, check cache before querying DB
3. No tests needed — existing tests cover `_resolve_path` behavior; cache is transparent to callers