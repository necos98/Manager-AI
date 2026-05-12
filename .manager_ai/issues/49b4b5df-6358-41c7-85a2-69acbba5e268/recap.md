## What changed

Added a 5-minute TTL result cache to `_check_resource_consistency()` health check to prevent redundant YAML file I/O on every 30s health poll.

### Changes

1. **`backend/app/storage/cache.py`** — Added `resource_consistency_cache = ReadCache(ttl=300.0)` module-level instance. Included it in `clear_all_caches()` for test isolation and watcher invalidation.

2. **`backend/app/routers/projects.py`** — 
   - Imported `resource_consistency_cache`
   - Modified `project_health` endpoint to check cache before calling `_check_resource_consistency()`. Cache key: `f"health:{project.id}"`
   - Added `resource_consistency_cache.clear()` in `install_manager_json` endpoint after writing new `manager.json`

### Key decisions

- Reused existing `ReadCache` class (same as storage layer) rather than introducing a new cache mechanism
- 5-minute TTL chosen because the consistency check result is idempotent and rarely changes
- Cache invalidation via watcher is free — `clear_all_caches()` already called on file system events
- Frontend polling interval left at 30s — the backend cache absorbs the cost, so reducing the frontend frequency wasn't necessary
