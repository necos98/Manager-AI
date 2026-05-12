## Architecture

Add `invalidate_prefix(prefix)` to `ReadCache` (single class, `cache.py`). Change three `invalidate_*_cache` functions to use it instead of `.clear()`. No new files, no watcher changes, no API changes.

## Files

- **Modify:** `backend/app/storage/cache.py` — add `invalidate_prefix` method
- **Modify:** `backend/app/storage/issue_store.py:325-327` — use `invalidate_prefix`
- **Modify:** `backend/app/storage/memory_store.py:182-184` — use `invalidate_prefix`
- **Modify:** `backend/app/storage/file_store.py:102-104` — use `invalidate_prefix`

## Tasks