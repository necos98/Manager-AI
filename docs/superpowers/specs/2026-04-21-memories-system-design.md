# Memories System (replaces RAG)

**Date:** 2026-04-21
**Status:** Design approved

## Goal

Replace the vector-search RAG subsystem with a lightweight, explicit **memories** system: a per-project DAG of titled notes that the LLM creates, links, and searches through MCP tools. The user does not use vector search today; memories give the LLM a deterministic, navigable long-term memory surface that scales to the actual needs of project brainstorming and issue work.

## Scope

Two coordinated pieces of work:

1. **Remove RAG** — delete the entire vector pipeline, embeddings, LanceDB, sentence-transformers dependency chain, `embedding_*` columns, related events and UI badges, and RAG MCP tools.
2. **Add Memories** — new domain (`memory`) with DAG semantics (single `parent_id` + lateral `memory_links`), FTS5-backed search, MCP tools for CRUD/link/search, and a read-only frontend page.

### Out of scope

- UI create/edit/delete of memories (read-only for now; only the LLM writes via MCP).
- Tags, categories, versioning, import/export, backup.
- Preserving any embedding data or migrating chunks into memories.

## Part 1 — Remove RAG

### Backend deletions
- `app/rag/` (entire package: pipeline, store, chunker, drivers, extractors).
- `app/services/rag_service.py`.
- `tests/test_rag_service.py`, `tests/test_rag_store.py`, `tests/test_rag_pipeline.py`, `tests/test_rag_drivers.py`.
- In `app/main.py`: remove RAG imports, lifespan init block, `set_rag_service` calls.
- In `app/routers/files.py`: remove `rag.embed_file` / `rag.delete_source` calls on upload/delete/retry.
- In `app/routers/issues.py` and `app/services/issue_service.py`: remove `rag.embed_issue` calls.
- In `app/mcp/server.py`: remove `rag.search` and `rag.get_chunk_details` tools.
- In `app/config.py`: remove `lancedb_path`, `embedding_driver`, `embedding_model`, `chunk_max_tokens`, `chunk_overlap_tokens`, and the validators `driver_must_be_known`, `tokens_must_be_positive`, `overlap_must_be_less_than_max`.
- In `requirements.txt`: remove `sentence-transformers`, `lancedb`, `pyarrow` (verify not used elsewhere), `torch` (verify), PDF/txt extractor deps if only used by RAG.
- In `app/services/event_service.py` / wherever emitted: remove `embedding_started|completed|failed|skipped` emissions.

### Backend migration — drop embedding columns
Alembic migration removing from both `files` and `issues`:
- `embedding_status`
- `embedding_error`
- `embedding_updated_at`

The earlier migration `8768ea9ac530_add_embedding_status_to_files_and_issues.py` stays in history; the new migration drops the columns.

### Frontend deletions
- `shared/types/index.ts`: remove `EmbeddingStatus` type and `embedding_status|error|updated_at` fields from file type.
- `shared/context/event-context.tsx`: remove cases `embedding_started`, `embedding_completed`, `embedding_failed`, `embedding_skipped`, and the codebase-invalidation branch under `embedding_completed`.
- `features/files/components/file-gallery.tsx`: delete `EmbeddingBadge` and its usages / failed-retry UI.

### Runtime cleanup
- Delete `data/lancedb/` manually (documented in changelog; no automated script).

## Part 2 — Memories System

### Database schema

```sql
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  parent_id TEXT REFERENCES memories(id) ON DELETE SET NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_memories_project ON memories(project_id);
CREATE INDEX ix_memories_parent ON memories(parent_id);

CREATE TABLE memory_links (
  from_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  to_id   TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  relation TEXT,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (from_id, to_id, relation)
);
CREATE INDEX ix_memory_links_to ON memory_links(to_id);

CREATE VIRTUAL TABLE memories_fts USING fts5(
  title, description,
  content='memories', content_rowid='rowid',
  tokenize='unicode61'
);
-- + insert/update/delete triggers on memories to keep memories_fts synchronized
```

### DAG semantics
- `parent_id` → primary hierarchy; each memory has at most one parent. Cycles forbidden; checked on create/update by walking ancestors.
- `memory_links` → many-to-many lateral references with an optional `relation` label (e.g. `see_also`, `contradicts`). Cycles allowed on lateral links (graph, not tree).
- Deletes: `projects` → cascade delete memories; memory delete → cascade `memory_links`, set children's `parent_id = NULL`.

### Backend modules
- `app/models/memory.py` — `Memory`, `MemoryLink` ORM.
- `app/schemas/memory.py` — Pydantic create/update/response; response includes `children_count`, `links_out_count`, `links_in_count`, and for detail endpoints the full parent/children/links payload.
- `app/services/memory_service.py` — CRUD, link/unlink, `get_related`, `search` (FTS5 `MATCH` + `bm25()` ordering + `snippet()` excerpts), cycle detection (ancestor walk). FTS sync is handled by DB triggers, not the service.
- `app/routers/memories.py` — REST endpoints for the read-only frontend:
  - `GET /projects/{project_id}/memories` — list. Query params: `parent_id` (null-root filter or specific parent), `q` (FTS query), `limit`, `offset`.
  - `GET /memories/{id}` — detail with parent, children, links_in, links_out.
- Alembic migration: create tables + FTS virtual table + triggers.
- Tests: `tests/test_memory_service.py`, `tests/test_routers_memories.py`.

### MCP tools (`app/mcp/server.py`)

```
memory.create(project_id, title, description, parent_id?) -> Memory
memory.update(memory_id, title?, description?, parent_id?) -> Memory
memory.delete(memory_id) -> {deleted: true}
memory.get(memory_id) -> Memory (with parent, children_ids, links_out, links_in)
memory.list(project_id, parent_id?, limit=50, offset=0) -> [Memory]
memory.link(from_id, to_id, relation?) -> MemoryLink
memory.unlink(from_id, to_id, relation?) -> {deleted: true}
memory.get_related(memory_id) -> {parent, children, links_out, links_in}
memory.search(project_id, query, limit=20) -> [{memory, snippet, rank}]
```

**Behavior:**
- `create` with a non-null `parent_id` verifies same `project_id` and runs cycle check.
- `update` that changes `parent_id` re-runs the cycle check.
- `delete` cascades `memory_links` and sets children's `parent_id` to NULL.
- `search` runs FTS5 `MATCH`, orders by `bm25()`, returns `snippet()` excerpts.
- All tools return structured errors for: not found, project mismatch, cycle detected, invalid parent.

Tests in `tests/test_mcp_tools.py` — replace RAG tool tests with memory tool tests.

### WebSocket events
Backend emits `memory_created`, `memory_updated`, `memory_deleted`, `memory_linked`, `memory_unlinked`, each with `project_id` and `memory_id` (plus `from_id`/`to_id` for link events). Frontend `event-context.tsx` invalidates relevant react-query keys on receipt.

### Frontend (read-only)

Route: `/projects/$projectId/memories` (TanStack Router file-route).

**Layout:**
- Left sidebar: hierarchical tree based on `parent_id`, lazy expand, click to select.
- Main pane: selected memory detail — title, description (markdown render), "Parent" link, "Children" list, "Links out" / "Links in" (with `relation` label). All references clickable.
- Top bar: debounced search input → calls `GET /projects/{pid}/memories?q=` → flat results list with snippet + rank. Selecting a result opens it in the main pane.
- Metadata: "Created / Updated" timestamps (no editor attribution; assumed LLM-authored).

**Files:**
- `frontend/src/routes/projects/$projectId/memories.tsx`
- `frontend/src/features/memories/api.ts` — `fetchMemories`, `fetchMemory`, `searchMemories`.
- `frontend/src/features/memories/hooks.ts` — `useMemories`, `useMemory`, `useMemorySearch` (react-query).
- `frontend/src/features/memories/components/memory-tree.tsx`
- `frontend/src/features/memories/components/memory-detail.tsx`
- `frontend/src/features/memories/components/memory-search.tsx`
- `shared/components/app-sidebar.tsx`: add nav link (Brain/Network icon).

## Execution order

1. Alembic migration dropping `embedding_*` columns.
2. Backend RAG removal (imports, pipeline, router calls, MCP tools, config keys, requirements).
3. Frontend RAG removal (types, badge, event cases).
4. Alembic migration creating memories tables + FTS virtual table + triggers.
5. Backend memory model / schema / service / router / tests.
6. MCP memory tools + tests.
7. Frontend memories feature + route + sidebar link.
8. Manual `data/lancedb/` cleanup (documented in changelog).

## Risks / notes

- Dropping `torch` transitively via `sentence-transformers` removal cuts install size dramatically; confirm nothing else pulls it in.
- FTS5 is built into SQLite — no new dependency.
- Cycle detection on `parent_id` runs on every create/update touching `parent_id`; cost is O(depth), negligible at expected scale (hundreds to low thousands per project).
- `memory_links` PK includes `relation`, so the same pair can carry multiple relation labels; two identical `(from, to, NULL)` rows are still rejected.
- Read-only UI means users see memories evolve in real time via WebSocket events but cannot intervene; explicit design choice until LLM usage patterns stabilize.
