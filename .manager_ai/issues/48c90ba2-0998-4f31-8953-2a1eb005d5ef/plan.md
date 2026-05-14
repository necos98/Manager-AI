# Implementation Plan

## Architecture
Add a `POST /api/projects/{project_id}/rebuild-index` endpoint that triggers the same directory→YAML rebuild logic used at startup. Modify `rebuild_*_index()` functions to return entry counts. Add logging and full cache invalidation to `start_project()`. Add a "Rebuild Index" button to the Health page.

## Files to modify
- `backend/app/storage/issue_store.py` — return count from `rebuild_issues_index()`
- `backend/app/storage/memory_store.py` — return count from `rebuild_memories_index()`
- `backend/app/storage/file_store.py` — return count from `rebuild_files_index()`
- `backend/app/services/manager_ai_watcher.py` — add logging + full cache invalidation in `start_project()`
- `backend/app/routers/projects.py` — add `POST /{project_id}/rebuild-index` endpoint
- `frontend/src/features/projects/api.ts` — add `rebuildIndex()` API function
- `frontend/src/features/projects/hooks.ts` — add `useRebuildIndex()` hook
- `frontend/src/features/projects/components/health-panel.tsx` — add Rebuild Index button

## Task order
1. Return counts from rebuild functions (storage layer)
2. Add logging + cache invalidation to start_project (watcher)
3. Add rebuild-index endpoint (router)
4. Add frontend API + hook
5. Add Rebuild Index button to Health page
