## Problem

`invalidate_issue_cache()`, `invalidate_memory_cache()`, `invalidate_file_cache()` all accept a `project_path` parameter but call `.clear()` on their respective global `ReadCache` instance. This wipes cached data for ALL projects when a single file changes in one project.

## Root Cause

`ReadCache` has `invalidate(key)` for single-key removal and `clear()` for global wipe. No method exists for prefix-based invalidation (remove all keys starting with `{project_path}:`).

## Solution

### 1. Add `ReadCache.invalidate_prefix(prefix: str)` to `backend/app/storage/cache.py`

```python
def invalidate_prefix(self, prefix: str) -> None:
    to_remove = [k for k in self._store if k.startswith(prefix)]
    for k in to_remove:
        del self._store[k]
```

### 2. Fix three invalidation functions

**`issue_store.py:325-327`** — Replace `issue_cache.clear()` with `issue_cache.invalidate_prefix(f"{project_path}:")`

**`memory_store.py:182-184`** — Replace `memory_cache.clear()` with `memory_cache.invalidate_prefix(f"{project_path}:")`

**`file_store.py:102-104`** — Replace `file_cache.clear()` with `file_cache.invalidate_prefix(f"{project_path}:")`

### What stays unchanged

- `clear_all_caches()` — used by test fixtures (`conftest.py`), must continue to clear everything globally
- `ReadCache.clear()` — kept as-is for `clear_all_caches()`
- All individual write operations — already use precise `cache.invalidate(f"{project_path}:...")` keys correctly
- `ReadCache.invalidate(key)` — unchanged, single-key removal

### Key design constraint

All cache keys already follow `{project_path}:{suffix}` format consistently across all three stores. The `:` separator is unambiguous — `project_path` itself is a filesystem path and won't contain `:` on Windows (drive letter `C:` appears, but paths passed as project_path use `/` separators and the colon only appears in the key prefix we control).

### No watcher changes needed

Watcher already calls `rebuild_*_index()` immediately before `invalidate_*_cache()`. The rebuild invalidates `__index__` precisely. The `invalidate_*_cache` call is a safety net — making it per-project suffices.