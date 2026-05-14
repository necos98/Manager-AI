## Changes

### `.manager_ai/.gitignore`
Added `issues.yaml`, `memories.yaml`, `files.yaml` — these index YAML files are now excluded from git tracking. Individual files in subdirectories (`issues/<id>/`, `memories/<id>.md`, `files/<id>.txt`) remain the source of truth.

### `backend/app/services/manager_ai_watcher.py`
Added three `rebuild_*_index()` calls in `ManagerAiWatcher.start_project()`, before the observer starts:
- `issue_store.rebuild_issues_index(project_path)`
- `memory_store.rebuild_memories_index(project_path)`
- `file_store.rebuild_files_index(project_path)`

This ensures indices are regenerated from directory files on every server startup. The rebuild happens before `observer.start()`, so the watcher never sees these writes — no infinite loop risk. The `_classify` method already correctly skips root-level index YAML files as a secondary safeguard.

## Verification

All 3 existing watcher tests pass with no regressions. The startup rebuild writes happen before observer init, so `test_watcher_skips_root_index_files_but_reacts_to_content` continues to validate the watcher's correct classification behavior.
