# Implementation Plan: Regenerate index YAML files on startup

## Files

- **Modify:** `.manager_ai/.gitignore` — add three index YAML entries
- **Modify:** `backend/app/services/manager_ai_watcher.py` — add pre-watcher rebuild calls in `start_project`

## Task 1: Add index YAML files to .manager_ai/.gitignore

Add `issues.yaml`, `memories.yaml`, `files.yaml` to `.manager_ai/.gitignore` so these auto-generated index files are no longer tracked by git. Individual files in subdirectories remain the source of truth.

## Task 2: Rebuild index YAML files on startup

In `ManagerAiWatcher.start_project()`, before the observer starts, call the three existing rebuild functions:

```python
issue_store.rebuild_issues_index(project_path)
memory_store.rebuild_memories_index(project_path)
file_store.rebuild_files_index(project_path)
```

These calls go after the `root.mkdir(parents=True, exist_ok=True)` line and before the observer is created. This ensures indices are fresh before any filesystem events are captured.

### Watcher safety

The `_classify` method already skips root-level index YAML files (requires `len(parts) > 1` for subdirectory content). The rebuild writes happen before `observer.start()`, so the watcher never sees them as events. No infinite loop risk.

### Empty directory handling

All three `rebuild_*_index()` functions handle missing/empty directories gracefully — they create an index with `schema_version` and an empty list.

## Task 3: Run existing watcher tests to verify no regressions

```bash
cd backend && python -m pytest tests/test_manager_ai_watcher.py -v
```

All 3 existing tests must pass. The startup rebuild writes root-level index files before the observer starts, so `test_watcher_skips_root_index_files_but_reacts_to_content` remains valid — it tests that root index writes AFTER observer start are correctly ignored.
