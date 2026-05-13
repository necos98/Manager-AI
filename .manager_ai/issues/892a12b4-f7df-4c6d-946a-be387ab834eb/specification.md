# Specification: Raise ReadCache TTL from 30s to 300s

## Problem

`ReadCache` in `backend/app/storage/cache.py` defaults to 30s TTL. This causes frequent cache misses during normal navigation. The watcher system already calls `.clear()` on file change events, making the TTL a secondary safety net, not the primary invalidation mechanism.

## Solution

Change the default `ttl` parameter in `ReadCache.__init__` from `30.0` to `300.0` (5 minutes).

## Why this is safe

1. **Watcher is primary invalidation** — `manager_ai_watcher` calls `clear_all_caches()` on any `.manager_ai/` file change, which calls `.clear()` on all cache instances. The TTL only matters for external modifications the watcher misses.
2. **Coarse-grained invalidation** — since stores use `.clear()` (wipe everything), not targeted `.invalidate(key)`, a longer TTL doesn't cause stale individual entries to persist.
3. **In-process, single-writer** — no shared memory concerns. Cache is per-process with single event loop writer.
4. **Precedent** — `resource_consistency_cache` already uses 300s TTL successfully.

## Change

**File:** `backend/app/storage/cache.py`, line 12

```python
# Before
def __init__(self, ttl: float = 30.0) -> None:

# After
def __init__(self, ttl: float = 300.0) -> None:
```

## Impact

- `issue_cache`, `memory_cache`, `file_cache` — pick up new 300s default (currently 30s)
- `resource_consistency_cache` — unchanged (already passes `ttl=300.0` explicitly)
- No test changes needed — tests use `clear_all_caches()` in fixtures, no test depends on 30s expiry
