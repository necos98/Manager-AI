# Cache Layer for Flat-File System Performance

## Problem

After migrating to the flat-file system (YAML+markdown under `.manager_ai/`), every read hits the filesystem directly via `atomic.read_yaml()` / `atomic.read_text()` → `path.read_text()`. For a full issue list with N issues, this means 1 index read + N × (issue.yaml + description.md) = 2N+1 file reads per request. Same pattern for memories and files. Users perceive lag when navigating between issues or switching projects — every navigation triggers fresh disk I/O.

## Solution

Add a **read-through TTL cache** inside the storage modules (`issue_store`, `memory_store`, `file_store`). Reads hit memory after first warm-up. Writes remain synchronous (update cache + disk atomically from caller's perspective). No background flush, no async write helpers — keeps the existing write-then-rebuild-index ordering intact.

## Design

### Cached entities

| Store | Cached type | Cache key |
|-------|------------|-----------|
| `issue_store` | Individual `IssueRecord` | `issue_id` |
| `issue_store` | Index list (light listing) | `__index__` |
| `memory_store` | Individual `MemoryRecord` | `memory_id` |
| `memory_store` | Index list (light listing) | `__index__` |
| `file_store` | Index list of `FileRecord` | `__index__` |
| `file_store` | Individual `FileRecord` (with text) | `file_id` |
| `file_store` | Extracted text strings | `text:{file_id}` |

### Cache structure

Per-store module-level dict with a simple wrapper class to centralize logic:

```python
class _ReadCache:
    def __init__(self, ttl: float = 30.0): ...
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...
    def invalidate(self, key: str) -> None: ...
    def clear(self) -> None: ...
```

Only the read path checks the cache. Writes call `cache.set()` after writing to disk, keeping cache and disk in sync.

### Read path

```
load(key):
    cached = cache.get(key)
    if cached is not None:
        return cached
    record = read_from_disk(key)
    cache.set(key, record)
    return record
```

### Write path (synchronous — no fire-and-forget)

```
save(key, record):
    write_to_disk(record)          # sync
    rebuild_index_if_needed()      # sync — reads from disk, which now has new data
    cache.set(key, record)         # sync
```

Writes stay synchronous so index rebuilds always see the latest data on disk. No write-ordering hazard.

### Invalidation

Two mechanisms:

1. **Local writes**: cache updated immediately after disk write (`cache.set`). No stale window
2. **TTL expiry (30s)**: safety net for external file changes (git, editor). Watcher events also trigger `cache.clear()` on the relevant store when the area is flushed

Since the watcher currently only tracks area ("issues"/"memories"/"files") and not individual IDs, invalidation on watcher events clears the full store cache (`cache.clear()`). This is coarse but correct — the next read will repopulate from disk. The 30s TTL provides a finer-grained fallback for individual entries.

### Thread safety

The cache is only mutated from the async event loop thread (service → store calls). Watcher timer threads do NOT access the cache directly — they call `rebuild_*_index()` which writes to disk and can optionally clear the cache via a separate entry point. This avoids shared-mutable-state across threads. If watcher integration is needed, a simple `invalidate_index(store_name)` function called from the event loop (via `asyncio.run_coroutine_threadsafe`) clears the relevant store's index cache entry.

### Test isolation

Add a `clear_caches()` function that resets all store caches. Called in test fixtures (conftest.py or individual test setup). Each test starts with a clean cache.

## Files to modify

- `backend/app/storage/atomic.py` — no changes needed (no async helpers)
- `backend/app/storage/issue_store.py` — add `_cache` and wrap `load_issue`, `list_issues` read paths; add `cache.set` after writes in `create_issue`, `update_issue`, `delete_issue`; expose `invalidate_cache()` 
- `backend/app/storage/memory_store.py` — same pattern for memory reads/writes
- `backend/app/storage/file_store.py` — same pattern for file reads/writes
- `backend/tests/conftest.py` — add `clear_caches()` call in fixture setup

No service layer changes needed. No frontend changes.

## Non-goals

- No async/background disk writes
- No Redis or external cache server
- No inter-process cache sharing
- No disk-based cache persistence (rebuilds on restart, takes <100ms)
- No fine-grained watcher-based per-ID invalidation (clear full store cache on watcher event)
