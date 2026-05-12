Changed `ReadCache.__init__` default `ttl` from 30.0 to 300.0 in `backend/app/storage/cache.py:12`.

This raises TTL for `issue_cache`, `memory_cache`, and `file_cache` from 30s to 5 minutes. `resource_consistency_cache` unchanged (already passes `ttl=300.0` explicitly).

Watcher-based invalidation (`clear_all_caches()` on file changes) is unaffected. All 103 storage and watcher tests pass.