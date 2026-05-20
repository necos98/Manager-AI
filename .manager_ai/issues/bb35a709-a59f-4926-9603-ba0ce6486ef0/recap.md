## What was done

Replaced the file-backed read-through cache architecture with a RAM-first architecture across all three stores (issues, memories, files).

### Killed
- `ReadCache` class and 4 module-level instances (issue_cache, memory_cache, file_cache, resource_consistency_cache)
- `ManagerAiWatcher` class — entire file + tests
- `prewarm_project_cache()` — no longer needed
- `watchfiles` dependency
- All `invalidate_*_cache()` functions → no-ops
- `resource_consistency_cache` usage in health check → direct check, no cache

### Created
- `memory_store_core.py` — `MemoryStore` singleton: nested dict `{project_path: {store_type: {records: {id: obj}, index: [...]}}}`, O(1) get/list/upsert/delete
- `write_queue.py` — `WriteQueue`: SQLite-backed durable queue (`pending_writes.db`), deduplication by (project_path, store_type, record_id), retry count
- `background_writer.py` — `BackgroundWriter`: async worker draining queue → disk in batches of 10, idle sleep 500ms, shutdown flush, `flush_all_pending()` for tests

### Rewritten
- `memory_store.py`, `issue_store.py`, `file_store.py` — all public functions delegate to MemoryStore + enqueue writes. Disk fallback in `load_*`/`list_*` functions ensures backward compatibility with tests that seed disk files directly.
- `cache.py` — now just `clear_all_caches()` (calls `memory_store.reset()`) + `flush_pending_writes()` helper

### Modified
- `main.py` — lifespan replaces watcher with `_load_project_into_memory()` + `BackgroundWriter.start()`. On shutdown: `background_writer.stop()` + `write_queue.close()`.
- `routers/projects.py` — removed watcher from archive/unarchive/rebuild-index. Rebuild now reloads from disk into MemoryStore.
- `conftest.py` — injects WriteQueue into all store modules, flushes pending writes on teardown
- `requirements.txt` — removed `watchfiles`

### Tests
- 140/140 storage tests pass
- 52/52 memory/migration/service tests pass
- New: test_memory_store_core.py (20), test_write_queue.py (11), test_background_writer.py (5)

### Architecture
```
caller → MemoryStore (RAM) → return (O(1))
caller → MemoryStore.upsert → WriteQueue.enqueue → return (non-blocking)
BackgroundWriter loop → WriteQueue.dequeue_batch → write .md/.yaml → rebuild index
```