# Codebase Indexing Design — Incremental Semantic Search

## Overview

Indicizzazione semantica incrementale della codebase del progetto gestito (`project.path`) per permettere a Claude Code di cercare nel codice sorgente via `search_project_context` invece di leggere file interi, riducendo il consumo di token.

I file sorgente vengono chunked e indicizzati in LanceDB con `source_type: "codebase_file"`, riutilizzando pipeline, store e MCP tool già esistenti. Un tracking degli hash su SQLite garantisce che i re-index successivi siano incrementali (solo file nuovi/modificati).

## Architettura

```
project.path impostato/aggiornato
issue → FINISHED
MCP tool index_codebase()
         │
         ▼
  RagService.embed_codebase(project_id, project_path)   [background task]
         │
         ▼
  CodebaseWalker                    ← walk del filesystem, skip patterns + .gitignore
         │ lista FileEntry (path, content, hash)
         ▼
  Incremental check                 ← confronta hash con tabella codebase_files (SQLite)
         │ solo file nuovi/modificati
         ▼
  TextChunker (esistente)           ← CODEBASE_CHUNK_MAX_TOKENS=200, overlap=20
         │ chunk di testo
         ▼
  EmbeddingDriver (esistente)       ← SentenceTransformerDriver
         │ vettori float[384]
         ▼
  LanceDB project_context_chunks    ← source_type: "codebase_file"
         │
         ▼
  MCP tool search_project_context() ← zero modifiche, già funzionante
```

## Nuova tabella SQLite: `codebase_files`

SQLAlchemy model `CodebaseFile`:

| Campo | Tipo | Descrizione |
|---|---|---|
| `id` | UUID | Primary key |
| `project_id` | str | FK progetto |
| `file_path` | str | Path relativo al project root |
| `file_hash` | str | MD5 del contenuto del file |
| `indexed_at` | datetime | Timestamp ultimo index riuscito |

Unique constraint su `(project_id, file_path)`. Fonte di verità per l'incrementalità: prima di re-indicizzare un file si verifica se l'hash è cambiato.

Il `source_id` usato in LanceDB per i chunk di un file codebase è `f"{project_id}:{relative_path}"` (es. `"abc-123:src/auth/login.py"`). Questo garantisce unicità cross-project e permette `store.delete_source(source_id)` per cleanup preciso.

## CodebaseWalker

```python
class CodebaseWalker:
    DEFAULT_IGNORE_DIRS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache"
    }
    DEFAULT_IGNORE_EXTENSIONS = {".pyc", ".pyo", ".lock", ".map"}
    MAX_FILE_SIZE_BYTES = 500_000  # skip file generati/binari grandi

    TEXT_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
        ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".sh", ".bash", ".sql", ".graphql",
        ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp", ".h"
    }
```

- Rispetta `.gitignore` se presente nel root del progetto (via libreria `pathspec`)
- Restituisce `FileEntry` (dataclass): `path: str` (relativo al root), `content: str`, `hash: str` (MD5)
- Il `title` del chunk in LanceDB è il path relativo del file (es. `"src/auth/login.py"`)

## Chunking per codice

Riusa `TextChunker` esistente con parametri ridotti rispetto ai file di testo normali:

```env
CODEBASE_CHUNK_MAX_TOKENS=200    # vs 500 per file/issue
CODEBASE_CHUNK_OVERLAP_TOKENS=20
```

Il chunker per paragrafi (`\n\n`) funziona bene per codice: funzioni e classi sono naturalmente separati da righe vuote.

## Trigger

### Trigger 1 — `project.path` impostato/aggiornato

In `project_service.py`, dopo `update()` se il campo `path` è cambiato:

```python
asyncio.create_task(rag_service.embed_codebase(project_id, new_path))
```

### Trigger 2 — Issue → FINISHED

In `mcp/server.py`, nel tool `complete_issue`, dopo l'embed dell'issue:

```python
if project.path:
    asyncio.create_task(rag_service.embed_codebase(project_id, project.path))
```

Grazie all'incrementalità, questo trigger è leggero: re-indicizza solo i file modificati dall'ultima issue completata.

### Trigger 3 — MCP tool manuale

```python
@mcp.tool(description=_desc["tool.index_codebase.description"])
async def index_codebase(project_id: str) -> dict:
    project = await project_service.get(project_id)
    if not project.path:
        return {"error": "Project path not set"}
    asyncio.create_task(rag_service.embed_codebase(project_id, project.path))
    return {"status": "started", "project_id": project_id}
```

Ritorna immediatamente. Il lavoro avviene in background. Al completamento viene emesso evento WebSocket `"embedding_completed"` con `source_type: "codebase"`.

## Cleanup file eliminati

Durante ogni walk, la pipeline confronta i file trovati con quelli registrati in `codebase_files` per quel `project_id`. I file presenti in DB ma non più sul filesystem vengono:
1. Eliminati da LanceDB (`store.delete_source(source_id)`)
2. Rimossi da `codebase_files`

## Struttura file

**Nuovi file:**

```
backend/app/
├── rag/
│   └── extractors/
│       └── codebase_extractor.py   ← CodebaseWalker + FileEntry
├── models/
│   └── codebase_file.py            ← SQLAlchemy model CodebaseFile
└── alembic/
    └── versions/xxxx_add_codebase_files.py
```

**Modifiche a file esistenti:**

| File | Modifica |
|---|---|
| `rag/pipeline.py` | Aggiunge `embed_codebase(project_id, root_path, db_session)` — riceve la session SQLAlchemy per leggere/scrivere `codebase_files` |
| `services/rag_service.py` | Aggiunge `embed_codebase(project_id, path)` — apre una propria `async_session` e la passa alla pipeline (stesso pattern delle altre operazioni async del servizio) |
| `services/project_service.py` | Triggera `embed_codebase` dopo update del path |
| `mcp/server.py` | Trigger in `complete_issue` + nuovo tool `index_codebase` |
| `mcp/default_settings.json` | Aggiunge `tool.index_codebase.description` |
| `models/__init__.py` | Registra `CodebaseFile` |
| `requirements.txt` | `+pathspec` |

## Configurazione

```env
CODEBASE_CHUNK_MAX_TOKENS=200     # default
CODEBASE_CHUNK_OVERLAP_TOKENS=20  # default
```

Aggiunti alla classe `Settings` in `config.py` con i valori di default.

## Testing

- `CodebaseWalker` testabile in isolamento con una directory temporanea (`tmp_path`)
- Incremental check testato: primo index → modifica file → secondo index verifica che solo il file modificato venga re-indicizzato
- Cleanup testato: file rimosso dal filesystem → chunks eliminati da LanceDB
- Il `SentenceTransformerDriver` viene mockato come negli altri test RAG
- `index_codebase` MCP tool testato con mock di `project.path`

## Nuove dipendenze

```
pathspec    # parsing .gitignore (leggero, ~30KB, zero dipendenze)
```
