"""Test utilities for the RAM-first architecture.

MemoryStore.reset() clears all in-memory data.
flush_pending_writes() drains the write queue to disk (for tests).
"""

from app.storage.memory_store_core import memory_store

# Global write queue reference for test flushing
_write_queue_ref: object = None


def clear_all_caches() -> None:
    """Reset all in-memory data. Called by test fixtures."""
    memory_store.reset()


def set_write_queue(queue: object) -> None:
    global _write_queue_ref
    _write_queue_ref = queue


def flush_pending_writes() -> int:
    """Flush all pending writes to disk. For tests that check disk state."""
    if _write_queue_ref is None:
        return 0
    from app.storage.background_writer import flush_all_pending
    return flush_all_pending(_write_queue_ref)
