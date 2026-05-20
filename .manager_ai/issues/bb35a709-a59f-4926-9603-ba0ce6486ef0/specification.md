# RAM-First Memory Layer

## Problem

Il sistema storage file-backed con read-through cache (TTL 300s) causa blocchi quando la cache scade o il watcher invalida. Ogni cache miss = I/O disco bloccante. Ogni write = rebuild index sincrono che scansiona tutti i file.

## Soluzione

Architettura RAM-first: la RAM e source of truth, il disco e output asincrono.

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

Inizializzazione startup: itera i file individuali (`.md`, `.yaml`) in `memories/`, `issues/`, `files/`. Parsa frontmatter, crea Record, popola MemoryStore. Costruisce index leggero (id, title, status, date — no body). File corrotti: logga warning, skippa.

### WriteQueue (SQLite)

Tabella `pending_writes` con colonne: id, project_path, store_type, record_id, action, payload_json, created_at, retry_count. Deduplica per (project_path, store_type, record_id). Dopo 3 retry falliti: logga errore, emette evento `write_failed`, butta la riga. File DB: `data/pending_writes.db`.

### BackgroundWriter

Un `asyncio.Task` per processo, avviato nel lifespan FastAPI. Loop: SELECT batch da 10 righe, processa (scrive .md/.yaml, rebuild index), DELETE righe completate. Coda vuota: sleep 500ms. Shutdown: flush finale.

### Startup

Sostituisce `ManagerAiWatcher.start_project`:
1. `_load_all_from_disk()` per issues, memories, files
2. `memory_store.init_project()` popola RAM
3. `background_writer.ensure_running()`

### Eventi realtime

Il service layer emette `issue_updated`/`memory_updated`/`file_updated` subito dopo la modifica RAM. BackgroundWriter emette `write_failed` in caso di errore disco.

### Resilienza

- Crash durante write: atomic write (temp+rename), riga resta in coda, riprocessata al restart
- File corrotti a startup: try/except, skippa, logga warning
- Disco pieno: retry_count, dopo 3 → write_failed, butta riga, RAM intatta
- Scrittura concorrente: deduplica collassa in unica write con ultimo stato

### Cosa muore

ManagerAiWatcher, ReadCache (tutte le istanze), prewarm_project_cache(), watchfiles.

### Cosa nasce

`memory_store_core.py` (MemoryStore), `write_queue.py` (coda SQLite), `background_writer.py` (worker).

### File da modificare

main.py (lifespan), routers/projects.py, storage/__init__.py, pyproject.toml (rimuovere watchfiles), event_service.py (aggiungere write_failed). memory_store.py, issue_store.py, file_store.py riscritti per delegare a MemoryStore + coda. Service layer invariati nelle API.