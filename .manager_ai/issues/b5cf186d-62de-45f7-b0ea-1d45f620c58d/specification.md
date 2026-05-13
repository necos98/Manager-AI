## Scope

Add request-scoped caching to `IssueService._resolve_path()` to avoid duplicate `ProjectService.get_by_id()` SQL queries when multiple methods in the same HTTP request resolve the same `project_id`.

## Design

Add a `dict[str, str]` cache on `IssueService` instance. Since `IssueService` is created per-request (one `AsyncSession` → one `IssueService`), the cache lifetime matches exactly one request.

```python
class IssueService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._path_cache: dict[str, str] = {}

    async def _resolve_path(self, project_id: str) -> str:
        if project_id not in self._path_cache:
            project = await ProjectService(self.session).get_by_id(project_id)
            self._path_cache[project_id] = project.path
        return self._path_cache[project_id]
```

## Constraints

- No TTL needed — request-scoped lifetime is correct.
- No invalidation needed — cache dies with the instance.
- No change to any callers or method signatures.

## Files touched

- `backend/app/services/issue_service.py` — add cache dict to `__init__` and check in `_resolve_path`.