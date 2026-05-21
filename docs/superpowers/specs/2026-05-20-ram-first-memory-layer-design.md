# RAM-First Memory Layer

**Date:** 2026-05-20
**Issue:** bb35a709-a59f-4926-9603-ba0ce6486ef0
**Status:** Draft

## Problem

Il sistema storage file-backed con read-through cache (TTL 300s) causa blocchi quando la cache scade o il watcher invalida. Ogni cache miss = I/O disco bloccante. Ogni write = rebuild index sincrono che scansiona tutti i file.

## Soluzione

Architettura RAM-first: la RAM è source of truth, il disco è output asincrono.

### Architettura

```
MCP tools / REST API
       ↓
Service layer (business logic, invariato)
       ↓
MemoryStore (RAM) ← source of truth, O(1) dict lookup
       ↓
WriteQueue (SQLite) ← coda durabile
       ↓
BackgroundWriter ← worker asincrono
       ↓
File system (.md + .yaml) ← output only
```

**Flusso read:** `caller → MemoryStore[id] → return` (zero I/O, zero cache check)

**Flusso write:** `caller → MemoryStore[id] = record → INSERT pending_writes → return` (non bloccante)

### MemoryStore

Dizionario annidato: `MemoryStore._projects[project_path] = {"records": {id: Record}, "index": [IndexEntry]}`.

- `init_project(path, store_type, records)` — popola a startup da disco
- `get(path, id)` — O(1)
- `list(path)` — ritorna index pre-costruito
- `upsert(path, record)` — RAM + coda
- `delete(path, id)` — RAM + coda

Inizializzazione startup:
1. `start_project()` itera i file individuali (`.md`, `.yaml`) in `memories/`, `issues/`, `files/`
2. Parsa frontmatter, crea Record, popola MemoryStore
3. Costruisce index leggero (id, title, status, date — no body)
4. File corrotti: logga warning, skippa

Thread safety: single-threaded event loop, nessun lock.

### WriteQueue (SQLite)

Tabella `pending_writes`:

```sql
CREATE TABLE pending_writes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT NOT NULL,
    store_type TEXT NOT NULL,    -- 'issues', 'memories', 'files'
    record_id TEXT NOT NULL,
    action TEXT NOT NULL,        -- 'upsert', 'delete'
    payload_json TEXT,           -- record serializzato (null per delete)
    created_at TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0
);
```

- Deduplica: DELETE righe esistenti per `(project_path, store_type, record_id)` prima di INSERT
- Dopo 3 retry falliti: logga errore, emette evento `write_failed`, butta la riga
- File DB: `data/pending_writes.db`

### BackgroundWriter

Un `asyncio.Task` per processo, avviato nel lifespan FastAPI.

- Loop: `SELECT * FROM pending_writes ORDER BY id LIMIT 10`
- Coda vuota: `await asyncio.sleep(0.5)`
- Processa batch: per ogni riga → scrive .md/.yaml → rebuild index → DELETE riga
- Shutdown: `running = False`, cancel task, flush finale della coda

### Startup (sostituisce ManagerAiWatcher.start_project)

```python
async def start_project(project_id, project_path):
    for store_type in ["issues", "memories", "files"]:
        records = _load_all_from_disk(project_path, store_type)
        memory_store.init_project(project_path, store_type, records)
    background_writer.ensure_running()
```

### Resilienza

- **Crash durante write disco:** atomic write (temp+rename) garantisce file integro o assente. Riga rimane in coda → riprocessata al restart.
- **File corrotti a startup:** try/except per file, skippa, logga warning. Server parte comunque.
- **Disco pieno:** OSError → retry_count += 1. Dopo 3 retry → evento `write_failed`, butta riga. RAM intatta.
- **Scrittura concorrente stesso record:** deduplica collassa in unica write disco con ultimo stato.

### Cosa muore

- `ManagerAiWatcher` — intera classe
- `ReadCache` — tutte le istanze module-level
- `prewarm_project_cache()`
- `watchfiles` da dipendenze
- `_is_archived` — archiviazione gestita a livello service

### Cosa resta

- `memory_store.py`, `issue_store.py`, `file_store.py` — riscritti per delegare a MemoryStore + coda
- `memory_service.py`, `issue_service.py` — API invariate
- Index YAML su disco — output del BackgroundWriter
- `atomic.py`, `paths.py` — invariati

### Cosa nasce

- `backend/app/storage/memory_store_core.py` — classe MemoryStore
- `backend/app/storage/write_queue.py` — coda SQLite + funzioni helper
- `backend/app/storage/background_writer.py` — worker asincrono

### File aggiuntivi da modificare

- `backend/app/main.py` — lifespan: init MemoryStore + BackgroundWriter, rimuovere watcher
- `backend/app/routers/projects.py` — rimuovere rebuild-index endpoint watcher-dependent
- `backend/app/storage/__init__.py` — esportare nuovi moduli
- `backend/pyproject.toml` — rimuovere `watchfiles`
- `backend/app/services/event_service.py` — aggiungere tipo evento `write_failed`

### Eventi realtime

Il watcher emetteva `issue_updated`/`memory_updated`/`file_updated` dopo il rebuild index. Con RAM-first:
- Il **service layer** emette l'evento subito dopo la modifica RAM (prima della coda)
- Il BackgroundWriter emette `write_failed` solo in caso di errore disco
- I consumer frontend vedono aggiornamenti immediati, non dipendenti dal flush disco

### Health check resource_consistency

Il check `resource_consistency` usava `resource_consistency_cache` (ReadCache). Con MemoryStore, il check interroga direttamente MemoryStore — zero I/O, zero cache. La logica di scansione `_check_resource_consistency` viene riscritta per leggere da MemoryStore invece che dai file YAML.

### Testing

- `test_memory_store_core.py` — init, get, list, upsert, delete, deduplica
- `test_write_queue.py` — enqueue, dequeue, dedup, retry, limite retry
- `test_background_writer.py` — process batch, idle, shutdown flush
- `test_startup_cold.py` — load da disco, file corrotti, avvio garantito
- Test esistenti adattati alle nuove firme
