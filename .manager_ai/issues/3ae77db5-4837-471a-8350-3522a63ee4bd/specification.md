## Summary

`IssueService.get_by_id(issue_id)` scans all non-archived projects linearly, calling `issue_store.load_issue()` per project. With 50+ projects, each lookup does 50+ disk reads or dict lookups when only one project could contain the target issue. This is a performance bottleneck that grows with the project count.

## Scope

Add a reverse index (`issue_id → project_path`) to the in-memory store so `IssueService.get_by_id()` can look up the correct project in O(1) instead of O(N). The index must stay consistent with the source of truth through all write operations.

## Constraints

- **Zero behavioral change** — all existing callers of `get_by_id()` must return identical results for every input, including edge cases (archived projects, externally-added issues, deleted projects).
- **Disk format unchanged** — no migration, no new files on disk. Index is purely in-memory.
- **Memory overhead acceptable** — one dict entry per active issue (~100 bytes per issue).
- **Existing tests must pass** without modification.
- **Thread safety** not required — single-threaded asyncio; but no data races within async tasks.

## Acceptance Criteria

1. `get_by_id()` resolves issue to correct project in O(1) when index has the entry.
2. **Archived project**: issue in an archived project returns `None` (current behavior preserved — index hit followed by archive check, fall-through to scan on failure).
3. **Externally-added issue**: issue created outside the app (e.g., file added to disk) returns correct result — index miss triggers fallback scan which loads it and populates the index.
4. **Deleted project**: `NotFoundError` from `ProjectService.get_by_id()` is handled gracefully — returns `None`.
5. **Index stays consistent** after create, update, delete of issues. No stale entries.
6. **Project removal**: removing a project cleans up all its issues from the index.

## Non-Goals

- Fixing the same pattern in `TaskService.get_by_id()` and `TaskService.update()` — MCP tools have already moved away from task_scanner's issue_id in favor of project-scoped calls. The task pattern is lower-impact and explicitly deferred.
- Any disk or database schema changes.
- Thread safety or multiprocessing support.
- Performance metrics beyond correctness — the improvement is a structural guarantee (O(N) → O(1)), not a benchmark target.

## Files in Scope

- `backend/app/storage/memory_store_core.py` — add reverse index mapping + lifecycle hooks
- `backend/app/storage/issue_store.py` — expose lookup method
- `backend/app/services/issue_service.py` — use reverse index in `get_by_id()`
