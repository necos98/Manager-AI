## Recap: Issue not deleted on first attempt

### Root cause
Race condition in RAM-first storage: `issue_service.delete()` removed issue from RAM (`MemoryStore`) but files persisted until `BackgroundWriter` async-processed the write queue (up to 0.5s delay). If `load_issue()` was called during this window, the issue was reloaded from disk (`issue.yaml` still existed) and reinserted into RAM via `_core.upsert()`, undoing the delete. Required second delete to clear RAM again.

### Changes made

**`backend/app/storage/background_writer.py`**
- Renamed `_delete_from_disk` → `delete_from_disk` (made public/importable)
- Renamed `_rebuild_index_for` → `rebuild_index_for` (made public/importable)
- Updated all internal references

**`backend/app/storage/issue_store.py`**
- Added `delete_issue_files(project_path, issue_id)` — imports `delete_from_disk` and `rebuild_index_for` from background_writer and calls them synchronously to immediately remove issue files from disk and rebuild the index

**`backend/app/services/issue_service.py`**
- `delete()` now calls `issue_store.delete_issue_files(path, issue_id)` immediately after `issue_store.delete_issue(path, issue_id)`, closing the race window

### Verification
- 177/177 issue service + storage tests pass
- BackgroundWriter delete processing remains idempotent (files already gone by the time it runs)
- No new test failures introduced