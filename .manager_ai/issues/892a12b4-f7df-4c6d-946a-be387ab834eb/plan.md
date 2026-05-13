# Raise ReadCache TTL — Implementation Plan

**Goal:** Change default TTL in `ReadCache.__init__` from 30s to 300s.

**Architecture:** Single-line parameter change. No logic, no new tests needed. Existing watcher-based invalidation unchanged.

## Files
- **Modify:** `backend/app/storage/cache.py:12` — change default `ttl` value

### Task 1: Change default TTL

- Modify `ReadCache.__init__` signature: `ttl: float = 30.0` → `ttl: float = 300.0`
- Run existing tests: `cd backend && python -m pytest tests/ -x -q`
- Verify `resource_consistency_cache` still passes `ttl=300.0` explicitly (no regression)
