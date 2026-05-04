# Implementation Plan: Read-Through Cache Layer

## Summary

Add a per-store `_ReadCache` instance to `issue_store`, `memory_store`, and `file_store`. Reads check cache first; writes populate cache after disk flush. No async writes. Watcher gets cache-clear hooks. Tests get `clear_caches()` fixture.

---

### Task 1: Create `_ReadCache` class

**Files:**
- Create: `backend/app/storage/cache.py`

**Steps:**

- [ ] **Step 1: Write the cache class**

```python
"""In-process TTL read-through cache for storage modules."""

from __future__ import annotations

import time
from typing import Any


class ReadCache:
    """Simple TTL dict cache. Thread-safe for single-writer / multi-reader."""

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


# Per-store cache instances — imported by issue_store, memory_store, file_store
issue_cache = ReadCache()
memory_cache = ReadCache()
file_cache = ReadCache()


def clear_all_caches() -> None:
    """Reset all store caches. Called by test fixtures."""
    issue_cache.clear()
    memory_cache.clear()
    file_cache.clear()
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
cd backend && python -c "from app.storage.cache import ReadCache, issue_cache, memory_cache, file_cache, clear_all_caches; print('OK')"
```

Expected: `OK`

---

### Task 2: Integrate cache into `issue_store.py`

**Files:**
- Modify: `backend/app/storage/issue_store.py`

**Steps:**

- [ ] **Step 1: Add cache imports and wire read-through on `load_issue`**

After imports, add:
```python
from app.storage.cache import issue_cache
```

In `load_issue`, wrap the read path:
```python
def load_issue(project_path: str, issue_id: str) -> IssueRecord | None:
    cache_key = f"{project_path}:{issue_id}"
    cached = issue_cache.get(cache_key)
    if cached is not None:
        return cached

    yaml_path = paths.issue_yaml(project_path, issue_id)
    if not yaml_path.exists():
        return None
    # ... existing read logic unchanged ...
    
    # Before return, cache the result
    issue_cache.set(cache_key, record)
    return record
```

- [ ] **Step 2: Cache index list in `list_issues`**

```python
def list_issues(project_path: str) -> list[IssueRecord]:
    cache_key = f"{project_path}:__index__"
    cached = issue_cache.get(cache_key)
    if cached is not None:
        return cached

    data = atomic.read_yaml(paths.issues_index(project_path)) or {}
    entries = data.get("issues") or []
    out: list[IssueRecord] = []
    for entry in entries:
        out.append(IssueRecord(
            id=entry.get("id", ""),
            # ... existing fields ...
        ))
    issue_cache.set(cache_key, out)
    return out
```

- [ ] **Step 3: Update cache on writes**

In `create_issue`, `update_issue`: after `_write_issue_files` + `rebuild_issues_index`, add:
```python
issue_cache.set(f"{project_path}:{record.id}", record)
issue_cache.invalidate(f"{project_path}:__index__")
```

In `delete_issue`: after `shutil.rmtree` + `rebuild_issues_index`, add:
```python
issue_cache.invalidate(f"{project_path}:{issue_id}")
issue_cache.invalidate(f"{project_path}:__index__")
```

- [ ] **Step 4: Invalidate cache in `rebuild_issues_index`**

At end of `rebuild_issues_index`, add:
```python
issue_cache.invalidate(f"{project_path}:__index__")
```

- [ ] **Step 5: Expose `invalidate_issue_cache` function**

```python
def invalidate_issue_cache(project_path: str) -> None:
    """Called by watcher to clear issue cache for a project."""
    issue_cache.clear()  # coarse — watcher can't resolve individual IDs
```

- [ ] **Step 6: Run existing tests**

```bash
cd backend && python -m pytest tests/storage/test_issue_store.py tests/storage/test_issue_store_write.py -v
```

Expected: all pass

---

### Task 3: Integrate cache into `memory_store.py`

**Files:**
- Modify: `backend/app/storage/memory_store.py`

**Steps:**

- [ ] **Step 1: Add cache imports and wire read-through on `load_memory`**

Same pattern as issue_store:
```python
from app.storage.cache import memory_cache

def load_memory(project_path: str, memory_id: str) -> MemoryRecord | None:
    cache_key = f"{project_path}:{memory_id}"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return cached
    # ... existing read ...
    memory_cache.set(cache_key, record)
    return record
```

- [ ] **Step 2: Cache index list in `list_memories`**

```python
def list_memories(project_path: str) -> list[MemoryRecord]:
    cache_key = f"{project_path}:__index__"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return cached
    # ... existing read ...
    memory_cache.set(cache_key, out)
    return out
```

- [ ] **Step 3: Update cache on writes**

`create_memory`, `update_memory`: after `_write_memory_file` + `rebuild_memories_index`:
```python
memory_cache.set(f"{project_path}:{record.id}", record)
memory_cache.invalidate(f"{project_path}:__index__")
```

`delete_memory`: after unlinking + `rebuild_memories_index`:
```python
memory_cache.invalidate(f"{project_path}:{memory_id}")
memory_cache.invalidate(f"{project_path}:__index__")
```

- [ ] **Step 4: Invalidate cache in `rebuild_memories_index`**

```python
memory_cache.invalidate(f"{project_path}:__index__")
```

- [ ] **Step 5: Expose `invalidate_memory_cache`**

```python
def invalidate_memory_cache(project_path: str) -> None:
    memory_cache.clear()
```

- [ ] **Step 6: Run existing tests**

```bash
cd backend && python -m pytest tests/storage/test_memory_store.py -v
```

Expected: all pass

---

### Task 4: Integrate cache into `file_store.py`

**Files:**
- Modify: `backend/app/storage/file_store.py`

**Steps:**

- [ ] **Step 1: Add cache imports and wire read-through**

Same patterns. `load_file` checks cache key `f"{project_path}:{file_id}"`. `list_files` checks `f"{project_path}:__index__"`. `read_extracted_text` checks `f"{project_path}:text:{file_id}"`.

- [ ] **Step 2: Update cache on writes**

`create_file`, `update_file`: set individual + invalidate index.
`delete_file`: invalidate individual + index.

- [ ] **Step 3: Invalidate in `rebuild_files_index` and expose `invalidate_file_cache`**

- [ ] **Step 4: Run existing tests**

```bash
cd backend && python -m pytest tests/storage/test_file_store.py -v
```

Expected: all pass

---

### Task 5: Add watcher cache invalidation

**Files:**
- Modify: `backend/app/services/manager_ai_watcher.py`

**Steps:**

- [ ] **Step 1: Call cache invalidation in `_flush`**

After each `rebuild_*_index` call in `_flush`, add the corresponding cache clear:

```python
def _flush(self, area: str) -> None:
    try:
        if area == "issues":
            issue_store.rebuild_issues_index(self.project_path)
            issue_store.invalidate_issue_cache(self.project_path)
            event_type = "issue_updated"
        elif area == "memories":
            memory_store.rebuild_memories_index(self.project_path)
            memory_store.invalidate_memory_cache(self.project_path)
            event_type = "memory_updated"
        elif area == "files":
            file_store.rebuild_files_index(self.project_path)
            file_store.invalidate_file_cache(self.project_path)
            event_type = "file_updated"
        else:
            return
    except Exception:
        logger.exception(...)
        return
    # ... emit event ...
```

- [ ] **Step 2: Verify import**

```bash
cd backend && python -c "from app.services.manager_ai_watcher import ManagerAiWatcher; print('OK')"
```

---

### Task 6: Add cache clearing to test fixtures

**Files:**
- Modify: `backend/tests/conftest.py`

**Steps:**

- [ ] **Step 1: Add `clear_all_caches` call in a fixture**

Add an autouse fixture that clears caches before each test:

```python
@pytest.fixture(autouse=True)
def _clear_store_caches():
    from app.storage.cache import clear_all_caches
    clear_all_caches()
    yield
    clear_all_caches()
```

- [ ] **Step 2: Run all storage tests**

```bash
cd backend && python -m pytest tests/storage/ -v
```

Expected: all pass

---

### Task 7: Full test suite

**Steps:**

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: all pass, no regressions
