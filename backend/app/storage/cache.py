"""In-process TTL read-through cache for storage modules."""

from __future__ import annotations

import time
from typing import Any


class ReadCache:
    """Simple TTL dict cache. Single-writer (event loop), multi-reader safe."""

    def __init__(self, ttl: float = 300.0) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic(), value)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in to_remove:
            del self._store[k]

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


issue_cache = ReadCache()
memory_cache = ReadCache()
file_cache = ReadCache()
resource_consistency_cache = ReadCache(ttl=300.0)  # 5 min TTL — health check scans are expensive


def clear_all_caches() -> None:
    """Reset all store caches. Called by test fixtures and watcher."""
    issue_cache.clear()
    memory_cache.clear()
    file_cache.clear()
    resource_consistency_cache.clear()
