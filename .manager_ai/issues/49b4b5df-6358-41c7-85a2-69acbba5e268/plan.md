# Cache resource_consistency Health Check — Implementation Plan

**Goal:** Add a 5-minute TTL cache on `_check_resource_consistency()` results so repeated health polls don't rescan all YAML files.

**Architecture:** Reuse existing `ReadCache` class. Add a module-level `resource_consistency_cache` instance with 300s TTL. Wrap the health endpoint call. Invalidate on watcher events (free via existing `clear_all_caches()`) and on `install_manager_json`.

**Files touched:**
- `backend/app/storage/cache.py` — new cache instance
- `backend/app/routers/projects.py` — cache usage in health + explicit clear in install_manager_json
- `backend/tests/test_routers_projects.py` — test cache behavior
