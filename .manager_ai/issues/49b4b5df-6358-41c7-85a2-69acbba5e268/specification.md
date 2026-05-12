# Specification: Cache resource_consistency health check result

## Problem

`_check_resource_consistency()` in `backend/app/routers/projects.py:83-217` scans all `.manager_ai/` YAML/markdown files using raw `open()` + `yaml.safe_load()` to detect `project_id` mismatches. The frontend health hook polls `GET /api/projects/{id}/health` every 30 seconds (`refetchInterval: 30_000` in `hooks.ts:70` and `hooks-dashboard.ts:8`).

Even when no fixes are needed (common case), every poll reads:
- `issues.yaml` (index)
- Every `issue.yaml` under `.manager_ai/issues/<id>/`
- `memories.yaml` (index)
- Every `.manager_ai/memories/<id>.md` (with frontmatter parsing)

These reads bypass `ReadCache` (from `app/storage/cache.py`) entirely because the function uses direct file I/O instead of going through the storage layer.

## Design

### Approach: TTL result cache

Wrap `_check_resource_consistency` result in a `ReadCache` instance with a **5-minute TTL**. The `ReadCache` class already exists in `backend/app/storage/cache.py` (30s TTL, used by storage modules). A separate instance with a longer TTL is appropriate here because:

1. The consistency check result is idempotent — same files, same result
2. The watcher system already calls `cache.clear()` on file change events, providing natural invalidation
3. Longer TTL (5 min vs 30s) is safe since the consistency result rarely changes

### Changes

**1. `backend/app/storage/cache.py`** — Add `resource_consistency_cache` instance:

```python
resource_consistency_cache = ReadCache(ttl=300.0)  # 5 min TTL
```

Also add it to `clear_all_caches()` for test isolation.

**2. `backend/app/routers/projects.py`** — Apply cache in `project_health` endpoint:

- Import `resource_consistency_cache`
- Build a cache key from `project.id`
- On cache miss: call `_check_resource_consistency(project)`, store result
- On cache hit: return cached result
- Also clear the cache in `install_manager_json` endpoint (it changes `manager.json`, which changes the authority)

**3. Invalidation hooks** — The existing watcher `cache.clear()` calls will naturally invalidate the consistency cache when `.manager_ai/` files change. No additional watcher changes needed.

### What stays the same

- `_check_resource_consistency()` function is unchanged
- No changes to the frontend polling interval
- No changes to the health endpoint response shape
- No changes to the scan logic or auto-fix behavior

### Edge cases

- **Cold start**: First health call after server start always scans (cache miss). Acceptable.
- **After file changes**: Watcher clears all caches, next health call re-scans. Correct behavior.
- **After `install_manager_json`**: Explicit cache invalidation ensures new `manager.json` project_id is respected immediately.
- **Multiple projects**: Cache key includes `project.id`, so different projects don't collide.
