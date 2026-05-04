"""In-process TTL read-through cache for storage modules."""

from __future__ import annotations

import time
from typing import Any


class ReadCache:
    """Simple TTL dict cache. Single-writer (event loop), multi-reader safe."""

    def __init__(self, ttl: float = 30.0) -> None:
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

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


issue_cache = ReadCache()
memory_cache = ReadCache()
file_cache = ReadCache()


def clear_all_caches() -> None:
    """Reset all store caches. Called by test fixtures."""
    issue_cache.clear()
    memory_cache.clear()
    file_cache.clear()
