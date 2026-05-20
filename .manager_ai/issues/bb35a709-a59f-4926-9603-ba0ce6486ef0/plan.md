## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| CREATE | `backend/app/storage/memory_store_core.py` | RAM dict store: init from disk, get, list, upsert, delete |
| CREATE | `backend/app/storage/write_queue.py` | SQLite coda durabile: enqueue, dequeue_batch, dedup, retry |
| CREATE | `backend/app/storage/background_writer.py` | Async worker: processa coda, scrive disco, rebuild index |
| REWRITE | `backend/app/storage/memory_store.py` | Delega a MemoryStore + WriteQueue, firma API invariata |
| REWRITE | `backend/app/storage/issue_store.py` | Delega a MemoryStore + WriteQueue, firma API invariata |
| REWRITE | `backend/app/storage/file_store.py` | Delega a MemoryStore + WriteQueue, firma API invariata |
| MODIFY | `backend/app/main.py` | Lifespan: init MemoryStore + BackgroundWriter, rimuovi watcher |
| MODIFY | `backend/app/routers/projects.py` | Rimuovi watcher da archive/unarchive/rebuild-index |
| MODIFY | `backend/app/services/event_service.py` | Aggiungi tipo evento `write_failed` |
| MODIFY | `backend/app/storage/cache.py` | Rimuovi ReadCache e istanze, tieni `clear_all_caches` stub |
| MODIFY | `backend/app/storage/__init__.py` | Esporta nuovi moduli |
| DELETE | `backend/app/services/manager_ai_watcher.py` | Non piu necessario |
| MODIFY | `backend/pyproject.toml` | Rimuovi `watchfiles` |
| MODIFY | `backend/tests/conftest.py` | Sostituisci clear_all_caches con memory_store.reset |
| DELETE | `backend/tests/test_manager_ai_watcher.py` | Non piu necessario |
| MODIFY | `backend/tests/storage/test_issue_store.py` | Adatta a nuovo MemoryStore (niente cache imports) |
| CREATE | `backend/tests/storage/test_memory_store_core.py` | Test per MemoryStore |
| CREATE | `backend/tests/storage/test_write_queue.py` | Test per WriteQueue |
| CREATE | `backend/tests/storage/test_background_writer.py` | Test per BackgroundWriter |

## Implementation Order

### Task 1: MemoryStore core

**Files:** CREATE `backend/app/storage/memory_store_core.py`

Implementa la classe `MemoryStore` — dizionario annidato RAM-first.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


class MemoryStore:
    """RAM-first store. Source of truth per tutti i record in esecuzione.

    _projects: dict[project_path, dict[store_type, StoreData]]
    StoreData = {"records": dict[id, Record], "index": list[IndexEntry]}
    """

    def __init__(self) -> None:
        self._projects: dict[str, dict[str, dict[str, Any]]] = {}

    # --- project lifecycle ---

    def has_project(self, project_path: str) -> bool:
        return project_path in self._projects

    def init_project(
        self,
        project_path: str,
        store_type: str,
        records: dict[str, Any],
        index: list[dict[str, Any]],
    ) -> None:
        if project_path not in self._projects:
            self._projects[project_path] = {}
        self._projects[project_path][store_type] = {
            "records": records,
            "index": index,
        }

    def remove_project(self, project_path: str) -> None:
        self._projects.pop(project_path, None)

    def _ensure(self, project_path: str, store_type: str) -> dict:
        p = self._projects.setdefault(project_path, {})
        return p.setdefault(store_type, {"records": {}, "index": []})

    # --- CRUD ---

    def get(self, project_path: str, store_type: str, record_id: str) -> Any | None:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return None
        return store["records"].get(record_id)

    def list(self, project_path: str, store_type: str) -> list[dict[str, Any]]:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return []
        return list(store["index"])

    def list_all(self, project_path: str, store_type: str) -> list[Any]:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return []
        return list(store["records"].values())

    def upsert(self, project_path: str, store_type: str, record_id: str, record: Any, index_entry: dict[str, Any]) -> None:
        store = self._ensure(project_path, store_type)
        store["records"][record_id] = record
        # replace or append index entry
        idx = store["index"]
        for i, e in enumerate(idx):
            if e.get("id") == record_id:
                idx[i] = index_entry
                break
        else:
            idx.append(index_entry)
        idx.sort(key=lambda e: (e.get("created_at", ""), e.get("id", "")))

    def delete(self, project_path: str, store_type: str, record_id: str) -> None:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return
        store["records"].pop(record_id, None)
        store["index"] = [e for e in store["index"] if e.get("id") != record_id]

    def reset(self) -> None:
        self._projects.clear()


# Singleton
memory_store = MemoryStore()
```

### Task 2: WriteQueue

**Files:** CREATE `backend/app/storage/write_queue.py`

Coda durabile SQLite per pending writes.

```python
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class WriteQueue:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS pending_writes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT NOT NULL,
                    store_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0
                )"""
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pending_sort ON pending_writes(id)"
            )
            self._conn.commit()
        return self._conn

    def enqueue(
        self,
        project_path: str,
        store_type: str,
        record_id: str,
        action: str,
        payload: Any,
        now: str,
    ) -> None:
        conn = self._ensure_conn()
        payload_json = json.dumps(payload, default=str) if payload is not None else None
        # deduplica: rimuovi write pendenti per lo stesso record
        conn.execute(
            "DELETE FROM pending_writes WHERE project_path=? AND store_type=? AND record_id=?",
            (project_path, store_type, record_id),
        )
        conn.execute(
            "INSERT INTO pending_writes (project_path, store_type, record_id, action, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_path, store_type, record_id, action, payload_json, now),
        )
        conn.commit()

    def dequeue_batch(self, limit: int = 10) -> list[dict[str, Any]]:
        conn = self._ensure_conn()
        rows = conn.execute(
            "SELECT * FROM pending_writes ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def remove(self, row_id: int) -> None:
        conn = self._ensure_conn()
        conn.execute("DELETE FROM pending_writes WHERE id=?", (row_id,))
        conn.commit()

    def increment_retry(self, row_id: int) -> int:
        conn = self._ensure_conn()
        conn.execute(
            "UPDATE pending_writes SET retry_count = retry_count + 1 WHERE id=?",
            (row_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT retry_count FROM pending_writes WHERE id=?", (row_id,)
        ).fetchone()
        return row[0] if row else 0

    def count_pending(self) -> int:
        conn = self._ensure_conn()
        row = conn.execute("SELECT COUNT(*) FROM pending_writes").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
```

### Task 3: BackgroundWriter

**Files:** CREATE `backend/app/storage/background_writer.py`

Worker asincrono che processa la coda e scrive su disco.

```python
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.storage import atomic, paths
from app.storage.write_queue import WriteQueue
from app.storage.memory_store_core import memory_store as global_memory_store
from app.services.event_service import event_service
from app.storage import issue_store, memory_store, file_store as file_store_module

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class BackgroundWriter:
    def __init__(self, write_queue: WriteQueue) -> None:
        self._queue = write_queue
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Flush finale
        await self._flush_remaining()

    def ensure_running(self) -> None:
        if not self._running:
            asyncio.create_task(self.start())

    async def _loop(self) -> None:
        while self._running:
            batch = self._queue.dequeue_batch(limit=10)
            if not batch:
                await asyncio.sleep(0.5)
                continue
            for row in batch:
                try:
                    await self._process(row)
                    self._queue.remove(row["id"])
                except Exception:
                    retries = self._queue.increment_retry(row["id"])
                    if retries >= MAX_RETRIES:
                        logger.error(
                            "Write failed after %d retries: %s/%s/%s",
                            MAX_RETRIES, row["store_type"], row["record_id"], row["action"],
                        )
                        self._queue.remove(row["id"])
                        try:
                            await event_service.emit({
                                "type": "write_failed",
                                "project_id": row.get("project_path", ""),
                                "store_type": row.get("store_type", ""),
                                "record_id": row.get("record_id", ""),
                                "source": "background_writer",
                            })
                        except Exception:
                            pass
                    else:
                        logger.warning(
                            "Write retry %d for %s/%s", retries, row["store_type"], row["record_id"],
                        )

    async def _process(self, row: dict[str, Any]) -> None:
        project_path = row["project_path"]
        store_type = row["store_type"]
        record_id = row["record_id"]
        action = row["action"]

        if action == "delete":
            _delete_file(project_path, store_type, record_id)
        elif action == "upsert":
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
            _write_file(project_path, store_type, record_id, payload)

        _rebuild_index(project_path, store_type)

    async def _flush_remaining(self) -> None:
        batch = self._queue.dequeue_batch(limit=100)
        for row in batch:
            try:
                await self._process(row)
                self._queue.remove(row["id"])
            except Exception:
                logger.exception("Flush failed for %s/%s", row["store_type"], row["record_id"])
```

Le funzioni `_delete_file`, `_write_file`, `_rebuild_index` sono helper che chiamano le funzioni esistenti di write disco da `memory_store`, `issue_store`, `file_store` (che verranno mantenute come funzioni private di write disco).

### Task 4: Rewrite memory_store.py

**Files:** REWRITE `backend/app/storage/memory_store.py`

Ogni funzione pubblica delega a MemoryStore + WriteQueue. Le funzioni di write disco diventano private (chiamate solo dal BackgroundWriter).

Per ogni funzione pubblica:
- `create_memory(path, record)` → `memory_store.upsert(path, "memories", record.id, record, _to_index_entry(record))` + `write_queue.enqueue(...)` + `event_service.emit("memory_updated")`
- `update_memory(path, record)` → stesso pattern
- `load_memory(path, id)` → `memory_store.get(path, "memories", id)`
- `delete_memory(path, id)` → memory_store.delete + write_queue.enqueue(delete) + event
- `list_memories(path)` → `memory_store.list(path, "memories")`
- `list_memories_full(path)` → `memory_store.list_all(path, "memories")`
- `add_link(path, from_id, link)` → modifica record in memory_store + enqueue
- `remove_link(path, from_id, to_id, relation)` → modifica record in memory_store + enqueue
- `rebuild_memories_index(path)` → mantenuta come funzione privata `_rebuild_index` chiamata dal BackgroundWriter
- `invalidate_memory_cache` → no-op (non serve piu)

### Task 5: Rewrite issue_store.py

**Files:** REWRITE `backend/app/storage/issue_store.py`

Stesso pattern di memory_store.py. Ogni funzione pubblica delega a MemoryStore + WriteQueue.

- `load_issue`, `list_issues`, `list_issues_full` → MemoryStore read
- `create_issue`, `update_issue`, `delete_issue` → MemoryStore + WriteQueue + event
- `upsert_task`, `remove_task`, `replace_tasks` → MemoryStore + WriteQueue + event
- `rebuild_issues_index` → privata `_rebuild_index`
- `invalidate_issue_cache` → no-op
- `prewarm_project_cache` → no-op (rimossa)
- `find_task` → MemoryStore scan

### Task 6: Rewrite file_store.py

**Files:** REWRITE `backend/app/storage/file_store.py`

Stesso pattern. Le funzioni di read/scrittura testo estratto restano su disco (i file estratti sono grandi). Solo l'index e i metadati vanno in MemoryStore.

### Task 7: Update main.py lifespan

**Files:** MODIFY `backend/app/main.py`

```python
# Rimuovi: from app.services.manager_ai_watcher import manager_ai_watcher
# Aggiungi:
from app.storage.memory_store_core import memory_store
from app.storage.write_queue import WriteQueue
from app.storage.background_writer import BackgroundWriter

# Nel lifespan, sostituisci il blocco watcher con:
write_queue = WriteQueue("data/pending_writes.db")
background_writer = BackgroundWriter(write_queue)

for p in rows:
    # Load all da disco
    _load_project_into_memory(p.path, memory_store)
await background_writer.start()

# Nello shutdown:
await background_writer.stop()
write_queue.close()
```

### Task 8: Update routers/projects.py

**Files:** MODIFY `backend/app/routers/projects.py`

- Rimuovi import `manager_ai_watcher`
- `archive_project`: rimuovi `stop_project`, tieni solo `stop_plugins_for_project`
- `unarchive_project`: rimuovi `start_project`, tieni solo `start_plugins_for_project`
- `rebuild_index`: riscrivi per usare MemoryStore (o rimuovi endpoint, non piu necessario)

### Task 9: Clean up

**Files:**
- MODIFY `backend/app/storage/cache.py`: rimuovi `ReadCache` e istanze, tieni `clear_all_caches()` come stub vuoto
- MODIFY `backend/app/services/event_service.py`: nessuna modifica necessaria (l'event service e generico)
- MODIFY `backend/app/storage/__init__.py`: esporta `memory_store`, `write_queue`, `background_writer`
- MODIFY `backend/pyproject.toml`: rimuovi `watchfiles` da dependencies

### Task 10: Remove watcher, update tests

**Files:**
- DELETE `backend/app/services/manager_ai_watcher.py`
- DELETE `backend/tests/test_manager_ai_watcher.py`
- MODIFY `backend/tests/conftest.py`: `clear_all_caches()` → `memory_store.reset()`
- MODIFY `backend/tests/storage/test_issue_store.py`: adatta import cache

### Task 11: New tests

**Files:**
- CREATE `backend/tests/storage/test_memory_store_core.py`: test init, get, list, upsert, delete, reset, multi-project
- CREATE `backend/tests/storage/test_write_queue.py`: test enqueue, dequeue_batch, dedup, retry, remove
- CREATE `backend/tests/storage/test_background_writer.py`: test process batch, idle, flush, retry limit