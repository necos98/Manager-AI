# Plan: Issue not deleted on first attempt

## Summary

Make `issue_service.delete()` synchronously delete files from disk immediately after RAM removal, eliminating race condition with BackgroundWriter.

## Files to modify

- `backend/app/storage/background_writer.py` — rename `_delete_from_disk` → `delete_from_disk`, `_rebuild_index_for` → `rebuild_index_for` (make public/importable)
- `backend/app/storage/issue_store.py` — add `delete_issue_files()` that calls `delete_from_disk` + `rebuild_index_for` synchronously
- `backend/app/services/issue_service.py` — `delete()` calls the new sync deletion after RAM removal

---

### Task 1: Make background_writer helpers importable

**Files:**
- Modify: `backend/app/storage/background_writer.py`

Rename `_delete_from_disk` → `delete_from_disk` and `_rebuild_index_for` → `rebuild_index_for` so they can be imported by `issue_store.py`.

Update internal callers in `_process`, `_flush_remaining`, `flush_all_pending`.

- [ ] **Step 1: Rename functions**

Rename `_delete_from_disk` to `delete_from_disk` (line 146).
Rename `_rebuild_index_for` to `rebuild_index_for` (line 184).
Update all internal references in the file.

- [ ] **Step 2: Verify existing tests pass**

Command: `cd backend && python -m pytest tests/ -x -q`
Expected: all tests pass

- [ ] **Step 3: Commit**

---

### Task 2: Add sync deletion to issue_store

**Files:**
- Modify: `backend/app/storage/issue_store.py`

Add `delete_issue_files(project_path, issue_id)` that:
1. Calls `delete_from_disk(project_path, "issues", issue_id)` from background_writer
2. Calls `rebuild_index_for(project_path, "issues")` from background_writer

This gives callers a single function to synchronously delete issue files + rebuild the disk index.

- [ ] **Step 1: Add function and import**

```python
def delete_issue_files(project_path: str, issue_id: str) -> None:
    from app.storage.background_writer import delete_from_disk, rebuild_index_for
    delete_from_disk(project_path, "issues", issue_id)
    rebuild_index_for(project_path, "issues")
```

- [ ] **Step 2: Verify tests pass**

Command: `cd backend && python -m pytest tests/ -x -q`
Expected: all tests pass

- [ ] **Step 3: Commit**

---

### Task 3: Call sync deletion in issue_service.delete()

**Files:**
- Modify: `backend/app/services/issue_service.py`

Update `delete()` method to call `issue_store.delete_issue_files()` immediately after `issue_store.delete_issue()`. This closes the race window between RAM deletion and disk cleanup.

- [ ] **Step 1: Add sync deletion call**

In `issue_service.py`, `delete()` method, after `issue_store.delete_issue(path, issue_id)`:
```python
issue_store.delete_issue_files(path, issue_id)
```

- [ ] **Step 2: Verify tests pass**

Command: `cd backend && python -m pytest tests/ -x -q`
Expected: all tests pass

- [ ] **Step 3: Commit**