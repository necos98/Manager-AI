# Spec: Issue not deleted on first attempt

## Problem

When user deletes issue via UI Delete button, issue reappears in list after first delete attempt. Second delete permanently removes it.

## Root Cause

Race condition in RAM-first storage (`MemoryStore` + `BackgroundWriter` + `WriteQueue`):

1. `issue_service.delete()` calls `issue_store.delete_issue()` → removes from RAM (`_core.delete`), enqueues background file delete via `WriteQueue`
2. Before `BackgroundWriter` processes the delete (up to 0.5s delay), any call to `load_issue()` for the deleted issue ID triggers disk fallback: `paths.issue_yaml().exists()` returns True → loads YAML → `_core.upsert()` re-inserts issue into RAM
3. `BackgroundWriter` eventually deletes files and rebuilds disk index, but RAM is already contaminated
4. Second delete required to clear RAM again

## Solution

Make `issue_service.delete()` delete files from disk **synchronously** immediately after removing from RAM, eliminating the race window entirely. The BackgroundWriter will still process the delete from the queue (idempotent — files already gone).

### Changes

**`backend/app/services/issue_service.py`** — `delete()` method:
- After `issue_store.delete_issue(path, issue_id)`, also call `_delete_issue_files_sync(path, issue_id)` to immediately remove from disk
- This prevents `load_issue()` disk fallback from rehydrating deleted issue

**`backend/app/storage/issue_store.py`** — expose sync deletion:
- Add `delete_issue_files(project_path, issue_id)` that removes the issue directory and rebuilds index synchronously
- Reuse `background_writer._delete_from_disk()` logic (import or inline)

**`backend/app/storage/background_writer.py`** — extract helpers:
- Make `_delete_from_disk` and `_rebuild_index_for` importable (rename to public functions)
- Issue store can call them directly for sync deletion

### Acceptance criteria

- Clicking Delete in UI removes issue from list on first attempt
- No issue reappearance after navigation
- BackgroundWriter delete processing still works (idempotent, no errors on missing files)
- Existing tests pass