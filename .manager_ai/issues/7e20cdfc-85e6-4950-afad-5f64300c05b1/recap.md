## Summary

Added a read-through TTL cache layer to the flat-file storage system. Every `load_*` and `list_*` function in `issue_store`, `memory_store`, and `file_store` now checks an in-memory dict cache before hitting disk. Writes update the cache synchronously after disk flush, with no change to write ordering (index rebuilds still see latest data).

## Changes

- **New file:** `backend/app/storage/cache.py` — `ReadCache` class (TTL dict) + per-store instances (`issue_cache`, `memory_cache`, `file_cache`) + `clear_all_caches()`
- **Modified:** `backend/app/storage/issue_store.py` — cache wrap on `load_issue`, `list_issues`, `create_issue`, `update_issue`, `delete_issue`, `rebuild_issues_index`; added `invalidate_issue_cache()`
- **Modified:** `backend/app/storage/memory_store.py` — same pattern; tracks affected IDs in `delete_memory` for precise child invalidation
- **Modified:** `backend/app/storage/file_store.py` — same pattern + cache on `read_extracted_text`, `write_extracted_text`
- **Modified:** `backend/app/services/manager_ai_watcher.py` — calls `invalidate_*_cache()` after each area flush
- **Modified:** `backend/tests/conftest.py` — autouse `_clear_store_caches` fixture

## Test results

- 100/100 storage tests pass
- Pre-existing router/dashboard failures (unrelated `KeyError: 'id'` in fixtures) confirmed via git stash — not caused by this change
- Zero new regressions

## Design decisions

- Read-through only, no async writes — avoids write-ordering hazards with index rebuilds
- 30s TTL as safety net for external file modifications
- Watcher clears full store cache (coarse but correct — watcher only tracks area, not individual IDs)
- Cache keys include project_path to isolate projects
- `_clear_store_caches()` autouse fixture ensures test isolation