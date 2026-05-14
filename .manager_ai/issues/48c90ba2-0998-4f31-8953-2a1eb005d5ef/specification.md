# Fix cache invalidation and rebuild gaps after index regeneration

## Background

Index YAML files (`issues.yaml`, `memories.yaml`, `files.yaml`) are auto-generated from individual directory files on startup via `ManagerAiWatcher.start_project()`. The watcher handles runtime file changes. However, there's no way to trigger a full rebuild without restarting the server, and cache invalidation after rebuild could be more robust.

## Requirements

### R1: Add diagnostic logging to `start_project()` rebuilds
Log when rebuild starts and completes, with entry counts per area (issues/memories/files). This confirms rebuilds actually execute and reveals how many entries were recovered.

### R2: Add force-rebuild API endpoint
`POST /api/projects/{project_id}/rebuild-index` that triggers the same rebuild logic as `start_project()`:
- Rebuilds `issues.yaml`, `memories.yaml`, `files.yaml` from directory files
- Full cache invalidation (prefix-based) for all three stores
- Returns counts of rebuilt entries per area
- Useful for recovery without restart and for debugging

### R3: Fix `start_project()` cache invalidation completeness
Currently `start_project()` calls `rebuild_*_index()` which only invalidates the index cache key (`__index__`). At startup the cache is empty, so this is harmless, but for consistency and correctness, also call `invalidate_*_cache()` (prefix invalidation) after each rebuild.

### R4: Add "Rebuild Index" button to Health page
Add a button in the frontend Health panel that:
- Calls `POST /api/projects/{project_id}/rebuild-index`
- Shows spinner while request is in flight
- Displays result counts on success
- Shows error message on failure

## Non-requirements
- No changes to cache TTL values
- No changes to watcher event classification logic
- No changes to how individual files are written (atomic write pattern stays)

## Success criteria
- Rebuild endpoint returns correct entry counts for existing directories
- Health page button triggers rebuild and shows results
- Log output confirms rebuild execution with counts
- Cache is fully invalidated after both startup rebuild and manual rebuild
