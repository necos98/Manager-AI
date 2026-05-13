Added `ReadCache.invalidate_prefix(prefix)` method that removes all keys starting with a given prefix. Changed three invalidation functions to use per-project prefix invalidation:

- `invalidate_issue_cache(project_path)` → `issue_cache.invalidate_prefix(f"{project_path}:")`
- `invalidate_memory_cache(project_path)` → `memory_cache.invalidate_prefix(f"{project_path}:")`
- `invalidate_file_cache(project_path)` → `file_cache.invalidate_prefix(f"{project_path}:")`

Previously all three called `.clear()` which wiped cache for ALL projects. Now only keys matching the project's prefix are removed. `clear_all_caches()` (global clear) kept for test fixtures. All 103 storage + watcher tests pass.