## Changes Made

### Backend
1. **`app/storage/issue_store.py`**: `rebuild_issues_index()` now returns `int` (entry count)
2. **`app/storage/memory_store.py`**: `rebuild_memories_index()` now returns `int`
3. **`app/storage/file_store.py`**: `rebuild_files_index()` now returns `int`
4. **`app/services/manager_ai_watcher.py`**: `start_project()` now logs rebuild start/completion with entry counts and calls full cache invalidation (`invalidate_*_cache`) after each rebuild, not just index key invalidation
5. **`app/routers/projects.py`**: Added `POST /api/projects/{project_id}/rebuild-index` endpoint that rebuilds all three indexes from directory files, fully invalidates caches, and returns `{issues, memories, files}` counts

### Frontend
6. **`features/projects/api.ts`**: Added `RebuildIndexResponse` type and `rebuildIndex()` API function
7. **`features/projects/hooks.ts`**: Added `useRebuildIndex()` mutation hook with toast on success
8. **`features/projects/components/health-panel.tsx`**: Added "Maintenance" section with "Rebuild Index" button showing spinner during rebuild

### Key decisions
- Endpoint placed in projects router (not a new router) following existing pattern
- Full prefix cache invalidation used everywhere (not just index key) for correctness
- Rebuild button grouped under new "Maintenance" section in Health page to distinguish from install checks