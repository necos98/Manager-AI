# RAG System Design — Project Context Search

## Overview

Sistema RAG (Retrieval-Augmented Generation) che permette all'LLM di cercare contesto nel progetto tramite ricerca semantica. I file caricati e le issue completate vengono embeddati in un unico indice vettoriale LanceDB, ricercabile tramite due nuovi MCP tool.

## Architettura

```
┌─────────────┐     ┌─────────────┐
│ File Upload  │     │Issue FINISHED│
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌──────────────────────────────────┐
│        Content Extractors        │  ← registry pattern, uno per tipo
│  (TxtExtractor, PdfExtractor,   │
│   IssueExtractor, ...)          │
└──────────────┬───────────────────┘
               │ testo grezzo
               ▼
┌──────────────────────────────────┐
│           Chunker                │  ← ibrido: paragrafi + split fisso
└──────────────┬───────────────────┘
               │ lista di chunk
               ▼
┌──────────────────────────────────┐
│      Embedding Driver            │  ← interfaccia astratta
│  (SentenceTransformerDriver)     │    futuri: OpenAIDriver, OllamaDriver
└──────────────┬───────────────────┘
               │ vettori
               ▼
┌──────────────────────────────────┐
│     LanceDB (unica tabella)      │
│  project_context_chunks          │
└──────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│          MCP Tools               │
│  search_project_context()        │
│  get_context_chunk_details()     │
└──────────────────────────────────┘
```

## Schema LanceDB

Tabella unica: `project_context_chunks`

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `id` | string (UUID) | ID univoco del chunk |
| `project_id` | string | Progetto di appartenenza |
| `chunk_text` | string | Testo del chunk |
| `vector` | float[384] | Embedding (MiniLM) |
| `source_type` | string | `"file"` o `"issue"` |
| `source_id` | string | `file_id` o `issue_id` |
| `title` | string | Titolo riassuntivo (nome file o titolo issue) |
| `chunk_index` | int | Posizione del chunk nella sorgente |
| `total_chunks` | int | Numero totale di chunk per questa sorgente |
| `metadata` | JSON | Extra info per display (mime_type, issue_status, ecc.). Non usato per filtering |
| `created_at` | string (ISO) | Timestamp creazione |

Re-indexing: quando un file viene sovrascritto o un'issue viene ri-completata, si eliminano tutti i chunk con quel `source_id` e si ri-generano. Per evitare race condition su re-index concorrenti dello stesso `source_id`, la pipeline usa un lock per `source_id` (asyncio.Lock per chiave).

## Content Extractors

### Interfaccia base

```python
class ContentExtractor:
    source_type: str          # "file" o "issue"
    supported_mimetypes: list  # es. ["text/plain", "application/pdf"]

    def extract(self, source) -> ExtractedContent:
        # Restituisce: title, text, metadata
```

### Registry

```python
class ExtractorRegistry:
    _extractors: dict  # mimetype → extractor instance

    def register(extractor)
    def get(mimetype) → extractor
    def supports(mimetype) → bool
```

### Extractors iniziali

| Extractor | Source type | MIME types | Libreria |
|-----------|-----------|------------|----------|
| `TxtExtractor` | file | `text/plain` | nessuna |
| `PdfExtractor` | file | `application/pdf` | `pypdf` |
| `IssueExtractor` | issue | — (non MIME) | nessuna |

`IssueExtractor` estrae e concatena i campi dell'issue:

```
## Spec
{issue.specification}

## Plan
{issue.plan}

## Recap
{issue.recap}
```

Aggiungere un nuovo extractor: creare un file, definire `supported_mimetypes`, implementare `extract()`, registrarlo nel lifespan di `main.py`.

Tipi non supportati: se un file viene caricato con un MIME type senza extractor registrato, la pipeline lo salta e broadcast un evento `"embedding_skipped"` con motivo. Il file resta salvato normalmente, solo l'embedding non avviene.

## Embedding Driver

### Interfaccia base

```python
class EmbeddingDriver:
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Batch embedding — metodo sincrono (CPU-bound)
```

**Nota async:** `embed()` e tutte le operazioni LanceDB sono sincrone/CPU-bound. La pipeline le wrappa con `asyncio.to_thread()` per non bloccare l'event loop.

### Driver iniziale: SentenceTransformerDriver

- Modello: `all-MiniLM-L6-v2` (384 dim, ~80MB, download al primo utilizzo)
- Caricamento lazy al primo utilizzo (non all'avvio dell'app)
- Batch nativo con batch size massimo di 32 chunk per chiamata
- Singleton in memoria

### Configurazione

```env
EMBEDDING_DRIVER=sentence_transformer
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Cambiare driver richiede re-indicizzare tutto (vettori con dimensioni/spazi diversi).

## Chunker

### Algoritmo ibrido

```python
class TextChunker:
    max_tokens: int = 500
    overlap_tokens: int = 50

    def chunk(self, text: str) -> list[Chunk]:
```

Tre step:
1. **Split per paragrafi** — separa su `\n\n`
2. **Merge piccoli** — paragrafi sotto ~100 token uniti al successivo
3. **Split grandi** — paragrafi oltre `max_tokens` spezzati per frasi (`. `) con overlap

Il conteggio token usa `len(text.split())` come approssimazione (word count). Sufficiente per il chunking, non serve un tokenizer specifico.

Per le issue, spec/plan/recap sono chunk logici naturali. Split interviene solo se superano `max_tokens`.

### Configurazione

```env
CHUNK_MAX_TOKENS=500
CHUNK_OVERLAP_TOKENS=50
```

## Pipeline e Trigger

### Trigger 1: Upload file

```
File upload API
  → salva file su disco (esistente)
  → salva record in DB (esistente)
  → asyncio.create_task(embed_pipeline(...))
  → risponde 201 subito

  Background:
    → ExtractorRegistry.get(mime_type)
    → extractor.extract(file_path)
    → TextChunker.chunk(text)
    → EmbeddingDriver.embed(chunks)
    → LanceDB.add(records)
    → EventService.broadcast("embedding_completed", {source_type, source_id})
```

### Trigger 2: Issue completata (FINISHED)

```
complete_issue (MCP tool)
  → status → FINISHED (esistente)
  → fire hooks (esistente)
  → estrai dati issue (title, spec, plan, recap) PRIMA di creare il task
  → asyncio.create_task(embed_pipeline(extracted_data))

  Background:
    → IssueExtractor.extract(extracted_data)  # riceve dati già estratti, non l'ORM object
    → TextChunker.chunk(text)
    → EmbeddingDriver.embed(chunks)           # via asyncio.to_thread
    → LanceDB.add(records)                    # via asyncio.to_thread
    → EventService.broadcast("embedding_completed", {source_type, source_id})
```

**Nota:** i dati dell'issue vengono estratti nel contesto della session attiva e passati al background task come dict/dataclass, non come ORM object. Questo evita problemi di session lifecycle (la session si chiude prima che il task in background esegua).

### Re-indexing e cleanup

- File eliminato → cancella chunk con quel `source_id`
- File sovrascritto → delete + re-embed
- Issue ri-completata → delete vecchi chunk + re-embed

### Errori

- Embedding fallito non blocca il file/issue — solo la parte vettoriale manca
- Broadcast `"embedding_failed"` con payload: `{source_type, source_id, title, error: str}`
- Broadcast `"embedding_skipped"` quando il MIME type non ha un extractor registrato
- Nessun retry automatico

## MCP Tools

### search_project_context

```
Input:
  - query: str            # testo di ricerca libero
  - project_id: str       # progetto in cui cercare
  - source_type: str?     # filtro opzionale: "file", "issue", o null per tutti
  - limit: int = 5        # numero massimo risultati

Output:
  - results: [
      {
        chunk_id: "abc-123",
        title: "auth-requirements.pdf (chunk 3/7)",
        source_type: "file",
        score: 0.87,
        preview: "primi 200 caratteri del chunk..."
      }
    ]
```

La ricerca usa distanza coseno (cosine similarity). Score normalizzato 0-1, dove 1 = identico. LanceDB inizialmente usa flat search (brute-force); indici ANN (IVF_PQ) sono un'ottimizzazione futura per dataset grandi.

### get_context_chunk_details

```
Input:
  - chunk_id: str
  - project_id: str       # validazione che il chunk appartenga al progetto

Output:
  {
    chunk_id: "abc-123",
    chunk_text: "testo completo del chunk...",
    source_type: "file",
    source_id: "file-uuid",
    title: "auth-requirements.pdf",
    chunk_index: 3,
    total_chunks: 7,
    metadata: { mime_type: "application/pdf", ... },
    adjacent_chunks: {
      previous: "def-456",
      next: "ghi-789"
    }
  }
```

### Flusso tipico

```
1. LLM riceve un task: "implementa il login OAuth"
2. LLM → search_project_context("OAuth login autenticazione")
3. ← risultati con preview e score
4. LLM → get_context_chunk_details(chunk più rilevante)
5. ← testo completo + metadata + chunk adiacenti
6. LLM procede con il contesto recuperato
```

## Struttura file

```
backend/app/
├── rag/
│   ├── __init__.py
│   ├── pipeline.py               # orchestratore: extract → chunk → embed → store
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py               # ContentExtractor + ExtractorRegistry
│   │   ├── txt_extractor.py
│   │   ├── pdf_extractor.py
│   │   └── issue_extractor.py
│   ├── chunker.py                # TextChunker
│   ├── drivers/
│   │   ├── __init__.py
│   │   ├── base.py               # EmbeddingDriver interfaccia
│   │   └── sentence_transformer.py
│   └── store.py                  # LanceDB wrapper: add, delete, search, get_chunk
├── services/
│   └── rag_service.py            # business logic: embed_file, embed_issue, search, delete
└── mcp/
    └── server.py                 # +2 tool: search_project_context, get_context_chunk_details
```

### Modifiche a file esistenti

| File | Modifica |
|------|----------|
| `services/file_service.py` | Dopo upload chiama `rag_service.embed_file()`, dopo delete chiama `rag_service.delete_source()` |
| `mcp/server.py` | Aggiunge 2 nuovi tool. In `complete_issue` chiama `rag_service.embed_issue()` |
| `config.py` | Nuove settings: `embedding_driver`, `embedding_model`, `chunk_max_tokens`, `chunk_overlap` |
| `main.py` | Registra extractors nel lifespan |
| `requirements.txt` | `+sentence-transformers`, `+pypdf` |
| `lancedb_store.py` | Rimosso, sostituito da `rag/store.py` |

Nessun nuovo router REST. L'embedding e' asincrono, i MCP tool sono l'unica interfaccia di ricerca. Il frontend riceve notifiche WebSocket di completamento.

## Configurazione completa

```env
# Embedding
EMBEDDING_DRIVER=sentence_transformer    # default
EMBEDDING_MODEL=all-MiniLM-L6-v2        # default

# Chunking
CHUNK_MAX_TOKENS=500                     # default
CHUNK_OVERLAP_TOKENS=50                  # default
```

Tutti i valori hanno default nella classe `Settings` di `config.py`.

## Testing

- I componenti `rag/` (extractors, chunker, driver) sono testabili in isolamento senza FastAPI
- LanceDB usa una directory temporanea (`tmp_path` di pytest) nei test
- Il `SentenceTransformerDriver` nei test viene mockato per evitare il download del modello in CI
- I test di integrazione della pipeline verificano il flusso extract → chunk → embed → store → search con un driver mock che restituisce vettori random

## Nuove dipendenze

```
sentence-transformers   # embedding locale (include torch, ~2GB totali con dipendenze)
pypdf                   # estrazione testo da PDF
```

Nota: `sentence-transformers` include PyTorch come dipendenza. Il modello (~80MB) viene scaricato al primo utilizzo, non all'installazione.
