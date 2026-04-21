# Memories System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the RAG / vector-search subsystem end-to-end and replace it with a lightweight per-project **memories** DAG (title + description, `parent_id` hierarchy + lateral `memory_links`, FTS5 search) exposed to the LLM via MCP tools, with a read-only frontend page.

**Architecture:** Two coordinated phases in one plan. **Phase A** (Tasks 1–12) strips RAG: migrations, pipeline code, MCP tools, config, dependencies, frontend badges/events. **Phase B** (Tasks 13–26) adds the memories domain: Alembic migration with FTS5 + triggers, SQLAlchemy model, Pydantic schemas, service (CRUD + cycle detection + link ops + search), REST router, MCP tools, WebSocket events, and frontend (route + tree + detail + search).

**Tech Stack:** Backend — Python 3.11+, FastAPI, SQLAlchemy 2 async, aiosqlite, Alembic, FastMCP, pytest. Frontend — React + Vite, TypeScript, TanStack Router, TanStack Query, Tailwind.

**Backend conventions:** Services take `AsyncSession` in constructor. Routers use `Depends(get_db)`. Pydantic v2 response schemas live in `app/schemas/`. MCP tools open `async with async_session() as session` and return `{"error": msg}` on `AppError`.

**Spec:** `docs/superpowers/specs/2026-04-21-memories-system-design.md`

---

## Phase A — Remove RAG

### Task 1: Alembic migration dropping `embedding_*` columns

**Files:**
- Create: `backend/alembic/versions/e7a9b1c2d3e4_drop_embedding_columns.py`

- [ ] **Step 1: Write the migration**

```python
"""drop embedding columns from files and issues

Revision ID: e7a9b1c2d3e4
Revises: a1b2c3d4e5f6
Create Date: 2026-04-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7a9b1c2d3e4'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('issues', schema=None) as batch_op:
        batch_op.drop_column('embedding_updated_at')
        batch_op.drop_column('embedding_error')
        batch_op.drop_column('embedding_status')

    with op.batch_alter_table('project_files', schema=None) as batch_op:
        batch_op.drop_column('embedding_updated_at')
        batch_op.drop_column('embedding_error')
        batch_op.drop_column('embedding_status')


def downgrade() -> None:
    with op.batch_alter_table('project_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding_status', sa.String(length=20), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('embedding_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('embedding_updated_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('issues', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding_status', sa.String(length=20), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('embedding_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('embedding_updated_at', sa.DateTime(), nullable=True))
```

> **Note:** verify `down_revision` is the current head. Run `python -m alembic heads` in `backend/` and use that value if different from `a1b2c3d4e5f6`.

- [ ] **Step 2: Verify current head and apply**

Run (in `backend/`):
```
python -m alembic heads
python -m alembic upgrade head
```
Expected: migration `e7a9b1c2d3e4` applied; `.schema issues` and `.schema project_files` in sqlite3 show no `embedding_*` columns.

- [ ] **Step 3: Commit**

```
git add backend/alembic/versions/e7a9b1c2d3e4_drop_embedding_columns.py
git commit -m "feat(db): drop embedding columns from issues and project_files"
```

---

### Task 2: Remove `embedding_*` fields from ORM models and `ProjectFile` schema

**Files:**
- Modify: `backend/app/models/project_file.py`
- Modify: `backend/app/models/issue.py`
- Modify: `backend/app/schemas/project_file.py`

- [ ] **Step 1: Edit `project_file.py` — delete the three mapped columns**

Remove lines 23–25 (`embedding_status`, `embedding_error`, `embedding_updated_at`). Also remove the now-unused `Optional` / `Text` imports if nothing else in the file uses them (keep what's needed).

Resulting relevant block:
```python
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="files")
```

- [ ] **Step 2: Edit `issue.py` — delete the three mapped columns**

Remove lines 43–45. Keep `Text` / `Optional` imports (used elsewhere in file).

- [ ] **Step 3: Edit `schemas/project_file.py` — strip embedding fields**

Replace the file contents with:
```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProjectFileResponse(BaseModel):
    id: str
    project_id: str
    original_name: str
    stored_name: str
    file_type: str
    file_size: int
    mime_type: str
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, obj: Any) -> "ProjectFileResponse":
        return cls(
            id=obj.id,
            project_id=obj.project_id,
            original_name=obj.original_name,
            stored_name=obj.stored_name,
            file_type=obj.file_type,
            file_size=obj.file_size,
            mime_type=obj.mime_type,
            metadata=obj.file_metadata,
            created_at=obj.created_at,
        )

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run existing tests (expect transient failures since other code still imports RAG; that's OK for now)**

Run (in `backend/`): `python -m pytest tests/test_routers_issues.py -x -q`
Expected: may fail on RAG imports — next tasks fix those.

- [ ] **Step 5: Commit**

```
git add backend/app/models/project_file.py backend/app/models/issue.py backend/app/schemas/project_file.py
git commit -m "refactor: drop embedding_* fields from ProjectFile, Issue, schema"
```

---

### Task 3: Remove RAG call sites from `routers/files.py`

**Files:**
- Modify: `backend/app/routers/files.py`

- [ ] **Step 1: Rewrite the file to remove all RAG interaction and the reindex endpoint**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_file import ProjectFileResponse
from app.services.file_service import ALLOWED_EXTENSIONS, FileService
from app.services.project_service import ProjectService

formats_router = APIRouter(prefix="/api/files", tags=["files"])
router = APIRouter(prefix="/api/projects/{project_id}/files", tags=["files"])


@formats_router.get("/allowed-formats")
async def get_allowed_formats():
    extensions = sorted(ALLOWED_EXTENSIONS)
    return {
        "accept": ",".join(f".{ext}" for ext in extensions),
        "extensions": extensions,
        "label": ", ".join(ext.upper() for ext in extensions),
    }


async def _check_project(project_id: str, db: AsyncSession):
    project = await ProjectService(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=list[ProjectFileResponse], status_code=201)
async def upload_files(project_id: str, files: list[UploadFile], db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    try:
        records = await service.upload_files(project_id, files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return [ProjectFileResponse.from_model(r) for r in records]


@router.get("", response_model=list[ProjectFileResponse])
async def list_files(project_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    records = await service.list_by_project(project_id)
    return [ProjectFileResponse.from_model(r) for r in records]


@router.get("/{file_id}/download")
async def download_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    record = await service.get_by_id(project_id, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = service.get_file_path(project_id, record.stored_name)
    return FileResponse(path=file_path, filename=record.original_name, media_type=record.mime_type)


@router.delete("/{file_id}", status_code=204)
async def delete_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    deleted = await service.delete(project_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
```

- [ ] **Step 2: Commit**

```
git add backend/app/routers/files.py
git commit -m "refactor(files): remove RAG embedding hooks and /reindex endpoint"
```

---

### Task 4: Remove RAG call sites from `mcp/server.py`

**Files:**
- Modify: `backend/app/mcp/server.py`

- [ ] **Step 1: Remove the import and both RAG tools**

In `backend/app/mcp/server.py`:
- Delete line `from app.rag import get_rag_service` (around line 13).
- Delete the entire `complete_issue` `rag = get_rag_service()` + `embed_task = asyncio.create_task(...)` block (lines ~151–161 — the block beginning with the comment `# Trigger async embedding`). Keep the `await event_service.emit(...)` that follows.
- Delete the "RAG tools" section: the banner comment `# ── RAG tools …` and both `@mcp.tool`-decorated functions `search_project_context` and `get_context_chunk_details` (lines ~471–494).
- Remove the now-unused `_background_tasks: set[asyncio.Task] = set()` module global if no other code references it (grep to verify; if used elsewhere, leave it).

- [ ] **Step 2: Grep to confirm no remaining RAG references**

Run (in `backend/`): `grep -n "rag\|embed_\|search_project_context\|get_context_chunk" app/mcp/server.py`
Expected: no matches.

- [ ] **Step 3: Commit**

```
git add backend/app/mcp/server.py
git commit -m "refactor(mcp): remove rag.search and rag.get_chunk_details tools"
```

---

### Task 5: Strip RAG init from `main.py`

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Rewrite the file**

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppError
from app.hooks import hook_registry
import app.hooks.handlers  # noqa: F401 — triggers @hook decorator registration
from app.mcp.server import mcp
from app.routers import activity, events, files, issue_relations, issues, library, network, project_settings, project_skills, project_templates, project_variables, projects, settings as settings_router, tasks, terminals, terminal_commands

logger = logging.getLogger(__name__)

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    logger.info("Hook registry: %d event(s) registered", len(hook_registry._hooks))
    for event_type, hooks in hook_registry._hooks.items():
        for h in hooks:
            logger.info("  %s -> %s", event_type.value, h.name)

    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Manager AI", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(projects.dashboard_router)
app.include_router(project_settings.router)
app.include_router(project_templates.router)
app.include_router(files.formats_router)
app.include_router(files.router)
app.include_router(issues.router)
app.include_router(issue_relations.router)
app.include_router(tasks.router)
app.include_router(settings_router.router)
app.include_router(terminals.router)
app.include_router(terminal_commands.router)
app.include_router(project_variables.router)
app.include_router(events.router)
app.include_router(activity.router)
app.include_router(library.router)
app.include_router(project_skills.router)
app.include_router(network.router)

app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

> Memory router import is added later (Task 20).

- [ ] **Step 2: Commit**

```
git add backend/app/main.py
git commit -m "refactor(main): drop RAG lifespan init and imports"
```

---

### Task 6: Delete the `app/rag/` package, `rag_service`, and related tests

**Files:**
- Delete: `backend/app/rag/` (whole tree)
- Delete: `backend/app/services/rag_service.py`
- Delete: `backend/tests/test_rag_service.py`
- Delete: `backend/tests/test_rag_store.py`
- Delete: `backend/tests/test_rag_pipeline.py`
- Delete: `backend/tests/test_rag_drivers.py`

- [ ] **Step 1: Delete files and directories**

Run:
```
rm -r backend/app/rag
rm backend/app/services/rag_service.py
rm backend/tests/test_rag_service.py backend/tests/test_rag_store.py backend/tests/test_rag_pipeline.py backend/tests/test_rag_drivers.py
```

- [ ] **Step 2: Verify nothing still imports from `app.rag` or `rag_service`**

Run (in `backend/`): `grep -rn "app\.rag\|rag_service\|RagService\|get_rag_service\|set_rag_service" app/ tests/`
Expected: no matches.

- [ ] **Step 3: Run full test suite**

Run (in `backend/`): `python -m pytest -x -q`
Expected: all passing tests continue to pass (tests unrelated to RAG).

- [ ] **Step 4: Commit**

```
git add -A backend/app/rag backend/app/services/rag_service.py backend/tests/test_rag_service.py backend/tests/test_rag_store.py backend/tests/test_rag_pipeline.py backend/tests/test_rag_drivers.py
git commit -m "refactor: delete app/rag package, rag_service, and RAG tests"
```

---

### Task 7: Strip embedding config keys and validators from `config.py`

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Rewrite the file**

```python
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    recordings_path: str = str(_PROJECT_ROOT / "data" / "recordings")
    claude_library_path: str = str(_PROJECT_ROOT / "claude_library")
    backend_port: int = 8000
    hook_timeout_seconds: int = 300
    terminal_max_buffer_bytes: int = 100_000

    model_config = {"env_file": ".env"}

    @field_validator("backend_port")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"backend_port must be 1-65535, got {v}")
        return v


settings = Settings()
```

- [ ] **Step 2: Commit**

```
git add backend/app/config.py
git commit -m "refactor(config): drop embedding / lancedb / chunk settings"
```

---

### Task 8: Remove RAG tool descriptions from MCP default settings

**Files:**
- Modify: `backend/app/mcp/default_settings.json`

- [ ] **Step 1: Delete the two keys**

Remove these lines from `default_settings.json`:
- `"tool.search_project_context.description": ...`
- `"tool.get_context_chunk_details.description": ...`

Validate remaining JSON parses.

- [ ] **Step 2: Commit**

```
git add backend/app/mcp/default_settings.json
git commit -m "chore(mcp): drop RAG tool descriptions from defaults"
```

---

### Task 9: Drop RAG-related dependencies from `requirements.txt`

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Rewrite**

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy[asyncio]>=2.0.40
aiosqlite==0.21.0
alembic==1.15.2
pydantic>=2.11.0
pydantic-settings>=2.9.0
mcp[cli]==1.9.2
python-dotenv==1.1.0
httpx==0.28.1
pytest==8.3.5
pytest-asyncio==0.25.3
pywinpty>=2.0.0; sys_platform == "win32"  # Windows-only; Linux uses built-in pty module
```

- [ ] **Step 2: Verify pypdf / pyarrow not referenced elsewhere**

Run (in `backend/`): `grep -rn "import pypdf\|from pypdf\|import pyarrow\|from pyarrow" app/ tests/`
Expected: no matches. (If present, leave the lib in; it means non-RAG code uses it.)

- [ ] **Step 3: Reinstall deps in the venv**

The user runs this (show in the step): `pip install -r backend/requirements.txt`. Heavy packages (`torch`, `sentence-transformers`, `lancedb`) should be uninstalled manually or via a fresh venv — leave note in commit message.

- [ ] **Step 4: Commit**

```
git add backend/requirements.txt
git commit -m "chore(deps): drop sentence-transformers, lancedb, pypdf"
```

---

### Task 10: Remove embedding fields and RAG state from frontend types

**Files:**
- Modify: `frontend/src/shared/types/index.ts`

- [ ] **Step 1: Edit `ProjectFile` type and remove `EmbeddingStatus`**

Replace the block (lines ~192–209):
```ts
// ── Project File ──

export interface ProjectFile {
  id: string;
  project_id: string;
  original_name: string;
  stored_name: string;
  file_type: string;
  file_size: number;
  mime_type: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}
```

- [ ] **Step 2: Commit**

```
git add frontend/src/shared/types/index.ts
git commit -m "refactor(types): drop EmbeddingStatus and embedding fields from ProjectFile"
```

---

### Task 11: Strip `EmbeddingBadge` and reindex UI from `file-gallery.tsx` and hooks/api

**Files:**
- Modify: `frontend/src/features/files/components/file-gallery.tsx`
- Modify: `frontend/src/features/files/hooks.ts`
- Modify: `frontend/src/features/files/api.ts`

- [ ] **Step 1: Rewrite `file-gallery.tsx`**

```tsx
import { useRef } from "react";
import { Download, Trash2, Upload } from "lucide-react";
import { useFiles, useAllowedFormats, useUploadFiles, useDeleteFile } from "@/features/files/hooks";
import { getFileDownloadUrl } from "@/features/files/api";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

interface FileGalleryProps {
  projectId: string;
}

export function FileGallery({ projectId }: FileGalleryProps) {
  const { data: files, isLoading } = useFiles(projectId);
  const { data: formats } = useAllowedFormats();
  const uploadFiles = useUploadFiles(projectId);
  const deleteFile = useDeleteFile(projectId);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files;
    if (!selected || selected.length === 0) return;
    const formData = new FormData();
    for (const file of selected) formData.append("files", file);
    uploadFiles.mutate(formData, {
      onSettled: () => { if (inputRef.current) inputRef.current.value = ""; },
    });
  };

  const handleDelete = (fileId: string, fileName: string) => {
    if (!window.confirm(`Delete "${fileName}"?`)) return;
    deleteFile.mutate(fileId);
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (<Skeleton key={i} className="h-12" />))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <Button disabled={uploadFiles.isPending} asChild>
          <label className="cursor-pointer">
            <Upload className="size-4 mr-2" />
            {uploadFiles.isPending ? "Uploading..." : "Upload Files"}
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={formats?.accept || ""}
              onChange={handleUpload}
              disabled={uploadFiles.isPending}
              className="hidden"
            />
          </label>
        </Button>
        {formats?.label && (
          <span className="text-xs text-muted-foreground">{formats.label}</span>
        )}
      </div>

      {uploadFiles.error && (
        <p className="text-sm text-destructive mb-3">{uploadFiles.error.message}</p>
      )}

      {!files || files.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No files uploaded.</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Type</th>
              <th className="py-2 pr-4 font-medium">Size</th>
              <th className="py-2 pr-4 font-medium">Uploaded</th>
              <th className="py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id} className="border-b hover:bg-accent">
                <td className="py-2 pr-4 font-medium truncate max-w-xs" title={f.original_name}>
                  {f.original_name}
                </td>
                <td className="py-2 pr-4 text-muted-foreground uppercase">{f.file_type}</td>
                <td className="py-2 pr-4 text-muted-foreground">{formatSize(f.file_size)}</td>
                <td className="py-2 pr-4 text-muted-foreground">{formatDate(f.created_at)}</td>
                <td className="py-2 flex gap-2">
                  <Button variant="ghost" size="sm" asChild>
                    <a href={getFileDownloadUrl(projectId, f.id)} download>
                      <Download className="size-3 mr-1" />
                      Download
                    </a>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => handleDelete(f.id, f.original_name)}
                    aria-label={`Delete ${f.original_name}`}
                  >
                    <Trash2 className="size-3 mr-1" />
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Remove `useReindexFile` from `hooks.ts` and `reindexFile` from `api.ts`**

In `frontend/src/features/files/hooks.ts`: delete the `useReindexFile` export (around line 51 and its body).
In `frontend/src/features/files/api.ts`: delete the `reindexFile` function (lines 24–25 and any wider block).

- [ ] **Step 3: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/features/files/components/file-gallery.tsx frontend/src/features/files/hooks.ts frontend/src/features/files/api.ts
git commit -m "refactor(files): remove EmbeddingBadge and reindex UI"
```

---

### Task 12: Remove `embedding_*` event cases from `event-context.tsx`

**Files:**
- Modify: `frontend/src/shared/context/event-context.tsx`

- [ ] **Step 1: Delete the four `case "embedding_*"` branches inside `buildToastContent`**

Remove these four cases (and only those):
- `case "embedding_started":`
- `case "embedding_completed":` (including the codebase-specific branch)
- `case "embedding_failed":`
- `case "embedding_skipped":` (keep the sibling `case "project_updated":` — move it to a standalone case that returns the same silent toast content).

Example replacement for the `skipped`/`project_updated` pair:
```ts
    case "project_updated":
      return { title: "", message: "", variant: "default", silent: true };
```

- [ ] **Step 2: Delete the post-dispatch invalidation branch**

Remove the block:
```ts
if (data.type === "embedding_completed" && data.source_type === "codebase" && data.project_id) {
  queryClient.invalidateQueries({
    queryKey: ["projects", data.project_id, "codebase-index-status"],
  });
}
```

- [ ] **Step 3: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 4: Commit**

```
git add frontend/src/shared/context/event-context.tsx
git commit -m "refactor(events): drop embedding_* event cases from client"
```

---

## Phase B — Memories System

### Task 13: Alembic migration creating `memories`, `memory_links`, and FTS5

**Files:**
- Create: `backend/alembic/versions/f1a2b3c4d5e6_add_memories_and_fts.py`

- [ ] **Step 1: Write the migration**

```python
"""add memories, memory_links, and memories_fts

Revision ID: f1a2b3c4d5e6
Revises: e7a9b1c2d3e4
Create Date: 2026-04-21 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e7a9b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'memories',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('parent_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['memories.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_memories_project', 'memories', ['project_id'])
    op.create_index('ix_memories_parent', 'memories', ['parent_id'])

    op.create_table(
        'memory_links',
        sa.Column('from_id', sa.String(length=36), nullable=False),
        sa.Column('to_id', sa.String(length=36), nullable=False),
        sa.Column('relation', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['from_id'], ['memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_id'], ['memories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('from_id', 'to_id', 'relation'),
    )
    op.create_index('ix_memory_links_to', 'memory_links', ['to_id'])

    op.execute(
        "CREATE VIRTUAL TABLE memories_fts USING fts5("
        "title, description, "
        "content='memories', content_rowid='rowid', "
        "tokenize='unicode61')"
    )
    op.execute(
        "CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN "
        "INSERT INTO memories_fts(rowid, title, description) "
        "VALUES (new.rowid, new.title, new.description); END;"
    )
    op.execute(
        "CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN "
        "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
        "VALUES ('delete', old.rowid, old.title, old.description); END;"
    )
    op.execute(
        "CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN "
        "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
        "VALUES ('delete', old.rowid, old.title, old.description); "
        "INSERT INTO memories_fts(rowid, title, description) "
        "VALUES (new.rowid, new.title, new.description); END;"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS memories_au")
    op.execute("DROP TRIGGER IF EXISTS memories_ad")
    op.execute("DROP TRIGGER IF EXISTS memories_ai")
    op.execute("DROP TABLE IF EXISTS memories_fts")
    op.drop_index('ix_memory_links_to', table_name='memory_links')
    op.drop_table('memory_links')
    op.drop_index('ix_memories_parent', table_name='memories')
    op.drop_index('ix_memories_project', table_name='memories')
    op.drop_table('memories')
```

> Note: `relation` is stored as a non-null string with default `''` because SQLite allows multiple NULLs in a composite PK, which would let duplicate `(from, to)` rows sneak in. Using `''` for "no relation" preserves uniqueness.

- [ ] **Step 2: Apply the migration**

Run (in `backend/`): `python -m alembic upgrade head`
Expected: migration applied; `sqlite3 data/manager_ai.db ".tables"` shows `memories`, `memory_links`, `memories_fts`, `memories_fts_data`, etc.

- [ ] **Step 3: Smoke-check FTS triggers via sqlite3**

Run:
```
sqlite3 backend/../data/manager_ai.db "INSERT INTO memories(id, project_id, title, description, created_at, updated_at) SELECT 'tmp-fts-1', id, 'Test memory', 'Quick brown fox', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM projects LIMIT 1;"
sqlite3 backend/../data/manager_ai.db "SELECT rowid, title FROM memories_fts WHERE memories_fts MATCH 'brown';"
sqlite3 backend/../data/manager_ai.db "DELETE FROM memories WHERE id='tmp-fts-1';"
```
Expected: MATCH query returns one row. Second query afterwards returns none (skip if no projects exist).

- [ ] **Step 4: Commit**

```
git add backend/alembic/versions/f1a2b3c4d5e6_add_memories_and_fts.py
git commit -m "feat(db): add memories, memory_links, memories_fts"
```

---

### Task 14: `Memory` and `MemoryLink` ORM models

**Files:**
- Create: `backend/app/models/memory.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_memory_model.py`:
```python
import pytest
from sqlalchemy import select

from app.models.memory import Memory, MemoryLink
from app.models.project import Project


@pytest.mark.asyncio
async def test_memory_and_link_round_trip(db_session):
    proj = Project(id="p1", name="P", path="/tmp/p")
    db_session.add(proj)
    await db_session.flush()

    parent = Memory(id="m1", project_id="p1", title="Parent", description="root")
    child = Memory(id="m2", project_id="p1", title="Child", description="leaf", parent_id="m1")
    db_session.add_all([parent, child])
    await db_session.flush()

    link = MemoryLink(from_id="m1", to_id="m2", relation="see_also")
    db_session.add(link)
    await db_session.flush()

    rows = (await db_session.execute(select(Memory).order_by(Memory.id))).scalars().all()
    assert [m.id for m in rows] == ["m1", "m2"]
    assert rows[1].parent_id == "m1"

    link_rows = (await db_session.execute(select(MemoryLink))).scalars().all()
    assert len(link_rows) == 1
    assert link_rows[0].relation == "see_also"
```

- [ ] **Step 2: Run — expect failure ("No module named 'app.models.memory'")**

Run (in `backend/`): `python -m pytest tests/test_memory_model.py -x -q`

- [ ] **Step 3: Create `app/models/memory.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("memories.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    parent = relationship("Memory", remote_side="Memory.id", back_populates="children", foreign_keys=[parent_id])
    children = relationship("Memory", back_populates="parent", foreign_keys=[parent_id])


class MemoryLink(Base):
    __tablename__ = "memory_links"

    from_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
    to_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True, index=True)
    relation: Mapped[str] = mapped_column(String(64), primary_key=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Register the models in `app/models/__init__.py`**

Add `from app.models.memory import Memory, MemoryLink` and add `"Memory"`, `"MemoryLink"` to `__all__`.

- [ ] **Step 5: Update test conftest to import the new models**

In `backend/tests/conftest.py`, extend the import list:
```python
from app.models import (  # noqa: F401
    ActivityLog, Issue, IssueFeedback, IssueRelation, Memory, MemoryLink,
    Project, ProjectSkill, PromptTemplate, Setting, Task, TerminalCommand,
)
```

- [ ] **Step 6: Run the test**

Run: `python -m pytest tests/test_memory_model.py -x -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```
git add backend/app/models/memory.py backend/app/models/__init__.py backend/tests/conftest.py backend/tests/test_memory_model.py
git commit -m "feat(models): add Memory and MemoryLink"
```

---

### Task 15: `MemoryCreate` / `MemoryUpdate` / `MemoryResponse` schemas

**Files:**
- Create: `backend/app/schemas/memory.py`

- [ ] **Step 1: Write the schemas**

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    parent_id: str | None = None


class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    parent_id: str | None = None  # explicit None means "unchanged"; use sentinel handling in service


class MemoryResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    parent_id: str | None
    created_at: datetime
    updated_at: datetime
    children_count: int = 0
    links_out_count: int = 0
    links_in_count: int = 0

    @classmethod
    def from_model(cls, obj: Any, *, children_count: int = 0, links_out_count: int = 0, links_in_count: int = 0) -> "MemoryResponse":
        return cls(
            id=obj.id,
            project_id=obj.project_id,
            title=obj.title,
            description=obj.description,
            parent_id=obj.parent_id,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            children_count=children_count,
            links_out_count=links_out_count,
            links_in_count=links_in_count,
        )

    model_config = {"from_attributes": True}


class MemoryLinkResponse(BaseModel):
    from_id: str
    to_id: str
    relation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryDetail(MemoryResponse):
    parent: MemoryResponse | None = None
    children: list[MemoryResponse] = []
    links_out: list[MemoryLinkResponse] = []
    links_in: list[MemoryLinkResponse] = []


class MemorySearchHit(BaseModel):
    memory: MemoryResponse
    snippet: str
    rank: float
```

> `MemoryUpdate.parent_id` semantics: the service must distinguish "field missing" from "set parent to NULL". Task 16 handles this by using `model_dump(exclude_unset=True)`.

- [ ] **Step 2: Commit**

```
git add backend/app/schemas/memory.py
git commit -m "feat(schemas): add Memory schemas"
```

---

### Task 16: `MemoryService` — CRUD, cycle detection, links, search

**Files:**
- Create: `backend/app/services/memory_service.py`
- Create: `backend/tests/test_memory_service.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest

from app.exceptions import AppError
from app.models.project import Project
from app.services.memory_service import MemoryService


@pytest.fixture
def svc(db_session):
    return MemoryService(db_session)


@pytest.mark.asyncio
async def test_create_list_get(db_session, svc):
    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.flush()
    m = await svc.create(project_id="p1", title="T", description="D")
    assert m.id and m.title == "T"

    listed = await svc.list(project_id="p1")
    assert [x.id for x in listed] == [m.id]

    got = await svc.get(m.id)
    assert got.id == m.id


@pytest.mark.asyncio
async def test_parent_cycle_is_rejected(db_session, svc):
    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    b = await svc.create(project_id="p1", title="B", description="", parent_id=a.id)
    with pytest.raises(AppError):
        await svc.update(a.id, parent_id=b.id)


@pytest.mark.asyncio
async def test_parent_must_be_same_project(db_session, svc):
    db_session.add_all([Project(id="p1", name="P", path="/a"), Project(id="p2", name="Q", path="/b")])
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    with pytest.raises(AppError):
        await svc.create(project_id="p2", title="B", description="", parent_id=a.id)


@pytest.mark.asyncio
async def test_delete_sets_children_parent_to_null(db_session, svc):
    db_session.add(Project(id="p1", name="P", path="/a"))
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    b = await svc.create(project_id="p1", title="B", description="", parent_id=a.id)
    await svc.delete(a.id)
    refreshed = await svc.get(b.id)
    assert refreshed.parent_id is None


@pytest.mark.asyncio
async def test_link_and_unlink(db_session, svc):
    db_session.add(Project(id="p1", name="P", path="/a"))
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    b = await svc.create(project_id="p1", title="B", description="")
    link = await svc.link(a.id, b.id, relation="see_also")
    assert link.relation == "see_also"
    related = await svc.get_related(a.id)
    assert [l.to_id for l in related["links_out"]] == [b.id]
    await svc.unlink(a.id, b.id, relation="see_also")
    related = await svc.get_related(a.id)
    assert related["links_out"] == []


@pytest.mark.asyncio
async def test_search_fts(db_session, svc):
    db_session.add(Project(id="p1", name="P", path="/a"))
    await db_session.flush()
    await svc.create(project_id="p1", title="Alpha memory", description="about databases")
    await svc.create(project_id="p1", title="Beta", description="about painting")
    hits = await svc.search(project_id="p1", query="databases")
    assert len(hits) == 1
    assert hits[0]["memory"].title == "Alpha memory"
```

> The in-memory test DB lacks the FTS5 virtual table and triggers (they're created only by the Alembic migration). The last test will be expected to fail in-memory until we create the FTS tables manually in the test fixture. Task 17 adds FTS bootstrap to `conftest.py`.

- [ ] **Step 2: Write the service**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppError
from app.models.memory import Memory, MemoryLink


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, project_id: str, title: str, description: str = "", parent_id: str | None = None) -> Memory:
        if parent_id:
            parent = await self.session.get(Memory, parent_id)
            if parent is None:
                raise AppError("Parent memory not found", status_code=404)
            if parent.project_id != project_id:
                raise AppError("Parent memory belongs to a different project", status_code=400)
        memory = Memory(project_id=project_id, title=title, description=description, parent_id=parent_id)
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get(self, memory_id: str) -> Memory:
        memory = await self.session.get(Memory, memory_id)
        if memory is None:
            raise AppError("Memory not found", status_code=404)
        return memory

    async def list(self, *, project_id: str, parent_id: str | None = None, limit: int = 50, offset: int = 0) -> list[Memory]:
        stmt = select(Memory).where(Memory.project_id == project_id)
        if parent_id is not None:
            stmt = stmt.where(Memory.parent_id == parent_id)
        stmt = stmt.order_by(Memory.created_at).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(self, memory_id: str, *, title: str | None = None, description: str | None = None, parent_id: str | None = ..., ) -> Memory:
        memory = await self.get(memory_id)
        if title is not None:
            memory.title = title
        if description is not None:
            memory.description = description
        if parent_id is not ...:
            if parent_id is not None:
                if parent_id == memory_id:
                    raise AppError("A memory cannot be its own parent", status_code=400)
                parent = await self.session.get(Memory, parent_id)
                if parent is None:
                    raise AppError("Parent memory not found", status_code=404)
                if parent.project_id != memory.project_id:
                    raise AppError("Parent memory belongs to a different project", status_code=400)
                if await self._would_create_cycle(ancestor_id=memory_id, new_parent_id=parent_id):
                    raise AppError("Parent change would create a cycle", status_code=400)
            memory.parent_id = parent_id
        await self.session.flush()
        return memory

    async def delete(self, memory_id: str) -> None:
        memory = await self.get(memory_id)
        await self.session.delete(memory)
        await self.session.flush()

    async def link(self, from_id: str, to_id: str, relation: str = "") -> MemoryLink:
        if from_id == to_id:
            raise AppError("Cannot link a memory to itself", status_code=400)
        a = await self.get(from_id)
        b = await self.get(to_id)
        if a.project_id != b.project_id:
            raise AppError("Links must stay within one project", status_code=400)
        link = MemoryLink(from_id=from_id, to_id=to_id, relation=relation or "")
        self.session.add(link)
        await self.session.flush()
        return link

    async def unlink(self, from_id: str, to_id: str, relation: str = "") -> bool:
        stmt = select(MemoryLink).where(
            MemoryLink.from_id == from_id,
            MemoryLink.to_id == to_id,
            MemoryLink.relation == (relation or ""),
        )
        link = (await self.session.execute(stmt)).scalar_one_or_none()
        if link is None:
            return False
        await self.session.delete(link)
        await self.session.flush()
        return True

    async def get_related(self, memory_id: str) -> dict[str, Any]:
        memory = await self.get(memory_id)
        parent = await self.session.get(Memory, memory.parent_id) if memory.parent_id else None
        children = list((await self.session.execute(
            select(Memory).where(Memory.parent_id == memory_id).order_by(Memory.created_at)
        )).scalars().all())
        links_out = list((await self.session.execute(
            select(MemoryLink).where(MemoryLink.from_id == memory_id)
        )).scalars().all())
        links_in = list((await self.session.execute(
            select(MemoryLink).where(MemoryLink.to_id == memory_id)
        )).scalars().all())
        return {"memory": memory, "parent": parent, "children": children, "links_out": links_out, "links_in": links_in}

    async def counts(self, memory_id: str) -> dict[str, int]:
        children = (await self.session.execute(select(func.count()).select_from(Memory).where(Memory.parent_id == memory_id))).scalar_one()
        out = (await self.session.execute(select(func.count()).select_from(MemoryLink).where(MemoryLink.from_id == memory_id))).scalar_one()
        inn = (await self.session.execute(select(func.count()).select_from(MemoryLink).where(MemoryLink.to_id == memory_id))).scalar_one()
        return {"children_count": children, "links_out_count": out, "links_in_count": inn}

    async def search(self, *, project_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        sql = text(
            "SELECT m.id, bm25(memories_fts) AS rank, "
            "snippet(memories_fts, -1, '[', ']', '…', 10) AS snippet "
            "FROM memories_fts f JOIN memories m ON m.rowid = f.rowid "
            "WHERE memories_fts MATCH :q AND m.project_id = :pid "
            "ORDER BY rank LIMIT :lim"
        )
        rows = (await self.session.execute(sql, {"q": query, "pid": project_id, "lim": limit})).all()
        hits: list[dict[str, Any]] = []
        for row in rows:
            memory = await self.session.get(Memory, row.id)
            if memory is not None:
                hits.append({"memory": memory, "snippet": row.snippet or "", "rank": float(row.rank)})
        return hits

    async def _would_create_cycle(self, *, ancestor_id: str, new_parent_id: str) -> bool:
        current: str | None = new_parent_id
        visited: set[str] = set()
        while current is not None:
            if current == ancestor_id:
                return True
            if current in visited:
                return False
            visited.add(current)
            parent = await self.session.get(Memory, current)
            current = parent.parent_id if parent else None
        return False
```

- [ ] **Step 3: Run the non-search tests**

Run (in `backend/`): `python -m pytest tests/test_memory_service.py -k "not test_search_fts" -x -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```
git add backend/app/services/memory_service.py backend/tests/test_memory_service.py
git commit -m "feat(memory): MemoryService with CRUD, links, cycle detection"
```

---

### Task 17: Bootstrap FTS5 virtual table + triggers inside test DB

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: After `Base.metadata.create_all(connection)`, run the FTS DDL**

In `_create_tables`, after the `Base.metadata.create_all(connection)` call (around line 39), append:

```python
        connection.exec_driver_sql(
            "CREATE VIRTUAL TABLE memories_fts USING fts5("
            "title, description, "
            "content='memories', content_rowid='rowid', "
            "tokenize='unicode61')"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN "
            "INSERT INTO memories_fts(rowid, title, description) "
            "VALUES (new.rowid, new.title, new.description); END;"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN "
            "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
            "VALUES ('delete', old.rowid, old.title, old.description); END;"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN "
            "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
            "VALUES ('delete', old.rowid, old.title, old.description); "
            "INSERT INTO memories_fts(rowid, title, description) "
            "VALUES (new.rowid, new.title, new.description); END;"
        )
```

- [ ] **Step 2: Run the FTS search test**

Run: `python -m pytest tests/test_memory_service.py::test_search_fts -x -q`
Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest -x -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```
git add backend/tests/conftest.py
git commit -m "test(memory): bootstrap memories_fts in in-memory test DB"
```

---

### Task 18: Emit memory events from the service

**Files:**
- Modify: `backend/app/services/memory_service.py`

- [ ] **Step 1: Make event emission the caller's responsibility via a helper**

Event emission happens from MCP tools and the REST router so services stay synchronous with the session. Add a lightweight helper module:

Create `backend/app/services/memory_events.py`:
```python
from datetime import datetime, timezone

from app.services.event_service import event_service


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def emit_created(*, project_id: str, memory_id: str) -> None:
    await event_service.emit({"type": "memory_created", "project_id": project_id, "memory_id": memory_id, "timestamp": _now()})


async def emit_updated(*, project_id: str, memory_id: str) -> None:
    await event_service.emit({"type": "memory_updated", "project_id": project_id, "memory_id": memory_id, "timestamp": _now()})


async def emit_deleted(*, project_id: str, memory_id: str) -> None:
    await event_service.emit({"type": "memory_deleted", "project_id": project_id, "memory_id": memory_id, "timestamp": _now()})


async def emit_linked(*, project_id: str, from_id: str, to_id: str, relation: str) -> None:
    await event_service.emit({"type": "memory_linked", "project_id": project_id, "from_id": from_id, "to_id": to_id, "relation": relation, "timestamp": _now()})


async def emit_unlinked(*, project_id: str, from_id: str, to_id: str, relation: str) -> None:
    await event_service.emit({"type": "memory_unlinked", "project_id": project_id, "from_id": from_id, "to_id": to_id, "relation": relation, "timestamp": _now()})
```

- [ ] **Step 2: Commit**

```
git add backend/app/services/memory_events.py
git commit -m "feat(memory): event emission helpers"
```

---

### Task 19: REST router `/projects/{pid}/memories` and `/memories/{id}`

**Files:**
- Create: `backend/app/routers/memories.py`
- Create: `backend/tests/test_routers_memories.py`

- [ ] **Step 1: Write the failing router test**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.models.project import Project
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_list_and_detail(db_session):
    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.flush()
    svc = MemoryService(db_session)
    a = await svc.create(project_id="p1", title="Root", description="top")
    b = await svc.create(project_id="p1", title="Child", description="leaf", parent_id=a.id)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/projects/p1/memories")
        assert r.status_code == 200
        assert {m["id"] for m in r.json()} == {a.id, b.id}

        r = await client.get(f"/api/memories/{a.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == a.id
        assert [c["id"] for c in body["children"]] == [b.id]

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run — expect 404 (router not registered)**

Run: `python -m pytest tests/test_routers_memories.py -x -q`

- [ ] **Step 3: Create the router**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.memory import MemoryDetail, MemoryLinkResponse, MemoryResponse, MemorySearchHit
from app.services.memory_service import MemoryService
from app.services.project_service import ProjectService

project_scoped = APIRouter(prefix="/api/projects/{project_id}/memories", tags=["memories"])
flat = APIRouter(prefix="/api/memories", tags=["memories"])


@project_scoped.get("", response_model=list[MemoryResponse])
async def list_memories(
    project_id: str,
    parent_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    svc = MemoryService(db)
    if q:
        hits = await svc.search(project_id=project_id, query=q, limit=limit)
        out: list[MemoryResponse] = []
        for hit in hits:
            counts = await svc.counts(hit["memory"].id)
            out.append(MemoryResponse.from_model(hit["memory"], **counts))
        return out
    rows = await svc.list(project_id=project_id, parent_id=parent_id, limit=limit, offset=offset)
    results: list[MemoryResponse] = []
    for m in rows:
        counts = await svc.counts(m.id)
        results.append(MemoryResponse.from_model(m, **counts))
    return results


@project_scoped.get("/search", response_model=list[MemorySearchHit])
async def search_memories(
    project_id: str,
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = MemoryService(db)
    hits = await svc.search(project_id=project_id, query=q, limit=limit)
    return [
        MemorySearchHit(
            memory=MemoryResponse.from_model(h["memory"], **(await svc.counts(h["memory"].id))),
            snippet=h["snippet"],
            rank=h["rank"],
        )
        for h in hits
    ]


@flat.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        bundle = await svc.get_related(memory_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    memory = bundle["memory"]
    counts = await svc.counts(memory.id)
    parent = bundle["parent"]
    parent_resp = None
    if parent is not None:
        parent_counts = await svc.counts(parent.id)
        parent_resp = MemoryResponse.from_model(parent, **parent_counts)
    children_resp = []
    for c in bundle["children"]:
        ccounts = await svc.counts(c.id)
        children_resp.append(MemoryResponse.from_model(c, **ccounts))
    return MemoryDetail(
        **MemoryResponse.from_model(memory, **counts).model_dump(),
        parent=parent_resp,
        children=children_resp,
        links_out=[MemoryLinkResponse.model_validate(l, from_attributes=True) for l in bundle["links_out"]],
        links_in=[MemoryLinkResponse.model_validate(l, from_attributes=True) for l in bundle["links_in"]],
    )
```

- [ ] **Step 4: Register the routers in `app/main.py`**

Add import: `from app.routers import ..., memories` and after `app.include_router(library.router)` add:
```python
app.include_router(memories.project_scoped)
app.include_router(memories.flat)
```

- [ ] **Step 5: Run the test**

Run: `python -m pytest tests/test_routers_memories.py -x -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add backend/app/routers/memories.py backend/tests/test_routers_memories.py backend/app/main.py
git commit -m "feat(memory): REST router for list / detail / search"
```

---

### Task 20: MCP memory tools

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`
- Create: `backend/tests/test_mcp_memory_tools.py`

- [ ] **Step 1: Write failing MCP tool test**

```python
import pytest

import app.mcp.server as mcp_server
from app.database import async_session
from app.models.project import Project


@pytest.mark.asyncio
async def test_memory_create_and_search(db_session, monkeypatch):
    monkeypatch.setattr(mcp_server, "async_session", lambda: db_session_wrapper(db_session))

    # The monkeypatch target differs in real test setup; use a simpler approach:
    pytest.skip("Requires integrated DB; covered by direct tool call below")


async def _fake_async_session_cm(session):
    class _CM:
        async def __aenter__(self): return session
        async def __aexit__(self, *a): return False
    return _CM()


@pytest.mark.asyncio
async def test_memory_tools_direct(db_session, monkeypatch):
    # Patch async_session in module to yield the test session
    import contextlib
    @contextlib.asynccontextmanager
    async def _fake():
        yield db_session
    monkeypatch.setattr(mcp_server, "async_session", _fake)

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    created = await mcp_server.memory_create(project_id="p1", title="Alpha", description="quick brown fox")
    assert "id" in created and created["title"] == "Alpha"

    listed = await mcp_server.memory_list(project_id="p1")
    assert any(m["id"] == created["id"] for m in listed["memories"])

    hits = await mcp_server.memory_search(project_id="p1", query="brown")
    assert len(hits["results"]) == 1
```

- [ ] **Step 2: Add memory tool descriptions to `default_settings.json`**

Append the following keys (before the closing `}`):
```json
"tool.memory_create.description": "Create a memory (title + description, optional parent_id) scoped to a project. Memories are long-term notes the LLM manages across sessions. Use this to record decisions, patterns, constraints, and user preferences.",
"tool.memory_update.description": "Update a memory's title, description, or parent_id. Passing a new parent_id moves the memory; cycles are rejected.",
"tool.memory_delete.description": "Delete a memory. Cascades links; children's parent_id becomes null.",
"tool.memory_get.description": "Fetch a memory with its parent, children, outgoing and incoming links.",
"tool.memory_list.description": "List memories for a project. Optional parent_id filters to one branch (use empty string for root-level memories).",
"tool.memory_link.description": "Create a lateral link between two memories (same project). Optional relation label (e.g. 'see_also', 'contradicts').",
"tool.memory_unlink.description": "Remove a lateral link (matches from_id + to_id + relation).",
"tool.memory_get_related.description": "Get parent, children, and both directions of lateral links for a memory.",
"tool.memory_search.description": "Full-text search across a project's memory titles and descriptions (SQLite FTS5). Returns matches with snippet and rank."
```

- [ ] **Step 3: Add MCP tools to `mcp/server.py`**

At the bottom of the file append:
```python
from app.schemas.memory import MemoryResponse
from app.services.memory_service import MemoryService
from app.services import memory_events


def _memory_to_dict(m, counts) -> dict:
    r = MemoryResponse.from_model(m, **counts)
    return r.model_dump(mode="json")


@mcp.tool(description=_desc["tool.memory_create.description"])
async def memory_create(project_id: str, title: str, description: str = "", parent_id: str | None = None) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            m = await svc.create(project_id=project_id, title=title, description=description, parent_id=parent_id)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        counts = await svc.counts(m.id)
        await memory_events.emit_created(project_id=project_id, memory_id=m.id)
        return _memory_to_dict(m, counts)


@mcp.tool(description=_desc["tool.memory_update.description"])
async def memory_update(memory_id: str, title: str | None = None, description: str | None = None, parent_id: str | None = None, parent_id_clear: bool = False) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            if parent_id_clear:
                m = await svc.update(memory_id, title=title, description=description, parent_id=None)
            elif parent_id is not None:
                m = await svc.update(memory_id, title=title, description=description, parent_id=parent_id)
            else:
                m = await svc.update(memory_id, title=title, description=description)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        counts = await svc.counts(m.id)
        await memory_events.emit_updated(project_id=m.project_id, memory_id=m.id)
        return _memory_to_dict(m, counts)


@mcp.tool(description=_desc["tool.memory_delete.description"])
async def memory_delete(memory_id: str) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            m = await svc.get(memory_id)
            project_id = m.project_id
            await svc.delete(memory_id)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        await memory_events.emit_deleted(project_id=project_id, memory_id=memory_id)
        return {"deleted": True}


@mcp.tool(description=_desc["tool.memory_get.description"])
async def memory_get(memory_id: str) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            bundle = await svc.get_related(memory_id)
        except AppError as e:
            return {"error": e.message}
        counts = await svc.counts(memory_id)
        return {
            "memory": _memory_to_dict(bundle["memory"], counts),
            "parent": _memory_to_dict(bundle["parent"], await svc.counts(bundle["parent"].id)) if bundle["parent"] else None,
            "children": [_memory_to_dict(c, await svc.counts(c.id)) for c in bundle["children"]],
            "links_out": [{"from_id": l.from_id, "to_id": l.to_id, "relation": l.relation} for l in bundle["links_out"]],
            "links_in": [{"from_id": l.from_id, "to_id": l.to_id, "relation": l.relation} for l in bundle["links_in"]],
        }


@mcp.tool(description=_desc["tool.memory_list.description"])
async def memory_list(project_id: str, parent_id: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        effective_parent = parent_id if parent_id != "" else None
        rows = await svc.list(project_id=project_id, parent_id=effective_parent, limit=limit, offset=offset)
        out = []
        for m in rows:
            out.append(_memory_to_dict(m, await svc.counts(m.id)))
        return {"memories": out}


@mcp.tool(description=_desc["tool.memory_link.description"])
async def memory_link(from_id: str, to_id: str, relation: str = "") -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            link = await svc.link(from_id, to_id, relation=relation)
            m = await svc.get(from_id)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        await memory_events.emit_linked(project_id=m.project_id, from_id=from_id, to_id=to_id, relation=link.relation)
        return {"from_id": link.from_id, "to_id": link.to_id, "relation": link.relation}


@mcp.tool(description=_desc["tool.memory_unlink.description"])
async def memory_unlink(from_id: str, to_id: str, relation: str = "") -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            m = await svc.get(from_id)
            deleted = await svc.unlink(from_id, to_id, relation=relation)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        if deleted:
            await memory_events.emit_unlinked(project_id=m.project_id, from_id=from_id, to_id=to_id, relation=relation)
        return {"deleted": bool(deleted)}


@mcp.tool(description=_desc["tool.memory_get_related.description"])
async def memory_get_related(memory_id: str) -> dict:
    return await memory_get(memory_id)


@mcp.tool(description=_desc["tool.memory_search.description"])
async def memory_search(project_id: str, query: str, limit: int = 20) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        hits = await svc.search(project_id=project_id, query=query, limit=limit)
        results = []
        for h in hits:
            results.append({
                "memory": _memory_to_dict(h["memory"], await svc.counts(h["memory"].id)),
                "snippet": h["snippet"],
                "rank": h["rank"],
            })
        return {"results": results}
```

- [ ] **Step 4: Run the MCP test**

Run: `python -m pytest tests/test_mcp_memory_tools.py -x -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add backend/app/mcp/server.py backend/app/mcp/default_settings.json backend/tests/test_mcp_memory_tools.py
git commit -m "feat(mcp): memory CRUD + link + search tools"
```

---

### Task 21: Frontend types + API client for memories

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Create: `frontend/src/features/memories/api.ts`

- [ ] **Step 1: Extend types**

Append to `shared/types/index.ts`:
```ts
// ── Memory ──

export interface Memory {
  id: string;
  project_id: string;
  title: string;
  description: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
  children_count: number;
  links_out_count: number;
  links_in_count: number;
}

export interface MemoryLink {
  from_id: string;
  to_id: string;
  relation: string;
  created_at: string;
}

export interface MemoryDetail extends Memory {
  parent: Memory | null;
  children: Memory[];
  links_out: MemoryLink[];
  links_in: MemoryLink[];
}

export interface MemorySearchHit {
  memory: Memory;
  snippet: string;
  rank: number;
}
```

- [ ] **Step 2: Create `features/memories/api.ts`**

```ts
import { apiGet } from "@/shared/lib/api";
import type { Memory, MemoryDetail, MemorySearchHit } from "@/shared/types";

export function fetchMemories(projectId: string, parentId?: string | null): Promise<Memory[]> {
  const qs = new URLSearchParams();
  if (parentId !== undefined && parentId !== null) qs.set("parent_id", parentId);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet<Memory[]>(`/projects/${projectId}/memories${suffix}`);
}

export function fetchMemory(memoryId: string): Promise<MemoryDetail> {
  return apiGet<MemoryDetail>(`/memories/${memoryId}`);
}

export function searchMemories(projectId: string, query: string, limit = 20): Promise<MemorySearchHit[]> {
  const qs = new URLSearchParams({ q: query, limit: String(limit) });
  return apiGet<MemorySearchHit[]>(`/projects/${projectId}/memories/search?${qs.toString()}`);
}
```

> Verify the `apiGet` helper path: inspect `frontend/src/shared/lib/api.ts` and match its import / signature. Most routes use `apiGet<T>(path)`; adjust if the project uses a different helper name.

- [ ] **Step 3: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 4: Commit**

```
git add frontend/src/shared/types/index.ts frontend/src/features/memories/api.ts
git commit -m "feat(frontend): memory types and api client"
```

---

### Task 22: Memory hooks (`useMemories`, `useMemory`, `useMemorySearch`)

**Files:**
- Create: `frontend/src/features/memories/hooks.ts`

- [ ] **Step 1: Write the hooks**

```ts
import { useQuery } from "@tanstack/react-query";
import * as api from "@/features/memories/api";

export const memoryKeys = {
  all: (projectId: string) => ["projects", projectId, "memories"] as const,
  list: (projectId: string, parentId?: string | null) =>
    [...memoryKeys.all(projectId), "list", { parentId: parentId ?? null }] as const,
  detail: (memoryId: string) => ["memories", memoryId, "detail"] as const,
  search: (projectId: string, query: string) =>
    [...memoryKeys.all(projectId), "search", query] as const,
};

export function useMemories(projectId: string, parentId?: string | null) {
  return useQuery({
    queryKey: memoryKeys.list(projectId, parentId),
    queryFn: () => api.fetchMemories(projectId, parentId),
    enabled: Boolean(projectId),
  });
}

export function useMemory(memoryId: string | null | undefined) {
  return useQuery({
    queryKey: memoryId ? memoryKeys.detail(memoryId) : ["memories", "none"],
    queryFn: () => api.fetchMemory(memoryId!),
    enabled: Boolean(memoryId),
  });
}

export function useMemorySearch(projectId: string, query: string) {
  return useQuery({
    queryKey: memoryKeys.search(projectId, query),
    queryFn: () => api.searchMemories(projectId, query),
    enabled: Boolean(projectId) && query.trim().length > 0,
    staleTime: 30_000,
  });
}
```

- [ ] **Step 2: Commit**

```
git add frontend/src/features/memories/hooks.ts
git commit -m "feat(frontend): memory query hooks"
```

---

### Task 23: Tree, detail, and search components

**Files:**
- Create: `frontend/src/features/memories/components/memory-tree.tsx`
- Create: `frontend/src/features/memories/components/memory-detail.tsx`
- Create: `frontend/src/features/memories/components/memory-search.tsx`

- [ ] **Step 1: `memory-tree.tsx`**

```tsx
import { useMemories } from "@/features/memories/hooks";
import type { Memory } from "@/shared/types";
import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";
import { cn } from "@/shared/lib/utils";

interface TreeProps {
  projectId: string;
  selectedId: string | null;
  onSelect: (memoryId: string) => void;
}

export function MemoryTree({ projectId, selectedId, onSelect }: TreeProps) {
  const roots = useMemories(projectId, null);
  if (roots.isLoading) return <div className="p-3 text-xs text-muted-foreground">Loading…</div>;
  if (!roots.data || roots.data.length === 0) {
    return <div className="p-3 text-xs text-muted-foreground">No memories yet.</div>;
  }
  return (
    <ul className="text-sm">
      {roots.data.map((m) => (
        <MemoryNode key={m.id} memory={m} projectId={projectId} depth={0} selectedId={selectedId} onSelect={onSelect} />
      ))}
    </ul>
  );
}

function MemoryNode({ memory, projectId, depth, selectedId, onSelect }: { memory: Memory; projectId: string; depth: number; selectedId: string | null; onSelect: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const hasChildren = memory.children_count > 0;
  const children = useMemories(projectId, open ? memory.id : undefined);
  const isSelected = selectedId === memory.id;
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(memory.id)}
        className={cn(
          "flex w-full items-center gap-1 rounded px-2 py-1 text-left hover:bg-accent",
          isSelected && "bg-accent"
        )}
        style={{ paddingLeft: 8 + depth * 12 }}
      >
        <span
          role="button"
          tabIndex={0}
          onClick={(e) => { e.stopPropagation(); if (hasChildren) setOpen((v) => !v); }}
          onKeyDown={(e) => { if (e.key === "Enter" && hasChildren) { e.stopPropagation(); setOpen((v) => !v); } }}
          className="flex size-4 items-center justify-center"
          aria-label={hasChildren ? (open ? "Collapse" : "Expand") : undefined}
        >
          {hasChildren ? (open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />) : <Brain className="size-3 text-muted-foreground" />}
        </span>
        <span className="truncate">{memory.title}</span>
      </button>
      {open && children.data && (
        <ul>
          {children.data.map((c) => (
            <MemoryNode key={c.id} memory={c} projectId={projectId} depth={depth + 1} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </ul>
      )}
    </li>
  );
}
```

- [ ] **Step 2: `memory-detail.tsx`**

```tsx
import { useMemory } from "@/features/memories/hooks";
import type { Memory, MemoryLink } from "@/shared/types";
import ReactMarkdown from "react-markdown";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface DetailProps {
  memoryId: string | null;
  onSelect: (memoryId: string) => void;
}

export function MemoryDetail({ memoryId, onSelect }: DetailProps) {
  const { data, isLoading } = useMemory(memoryId);
  if (!memoryId) return <div className="p-6 text-sm text-muted-foreground">Select a memory.</div>;
  if (isLoading || !data) {
    return <div className="p-6 space-y-3"><Skeleton className="h-6 w-1/3" /><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-full" /></div>;
  }
  return (
    <div className="p-6 space-y-5 overflow-auto">
      <header>
        <h2 className="text-lg font-semibold">{data.title}</h2>
        <p className="text-xs text-muted-foreground">
          Created {new Date(data.created_at).toLocaleString()} · Updated {new Date(data.updated_at).toLocaleString()}
        </p>
      </header>

      <section className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{data.description || "*(no description)*"}</ReactMarkdown>
      </section>

      {data.parent && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Parent</h3>
          <MemoryPill memory={data.parent} onSelect={onSelect} />
        </section>
      )}

      {data.children.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Children</h3>
          <ul className="space-y-1">{data.children.map((c) => (<li key={c.id}><MemoryPill memory={c} onSelect={onSelect} /></li>))}</ul>
        </section>
      )}

      {data.links_out.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Links out</h3>
          <ul className="space-y-1">{data.links_out.map((l) => (<li key={`${l.from_id}-${l.to_id}-${l.relation}`}><LinkRow link={l} otherId={l.to_id} onSelect={onSelect} /></li>))}</ul>
        </section>
      )}

      {data.links_in.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Links in</h3>
          <ul className="space-y-1">{data.links_in.map((l) => (<li key={`${l.from_id}-${l.to_id}-${l.relation}`}><LinkRow link={l} otherId={l.from_id} onSelect={onSelect} /></li>))}</ul>
        </section>
      )}
    </div>
  );
}

function MemoryPill({ memory, onSelect }: { memory: Memory; onSelect: (id: string) => void }) {
  return (
    <button type="button" onClick={() => onSelect(memory.id)} className="rounded border px-2 py-1 text-sm hover:bg-accent">
      {memory.title}
    </button>
  );
}

function LinkRow({ link, otherId, onSelect }: { link: MemoryLink; otherId: string; onSelect: (id: string) => void }) {
  return (
    <button type="button" onClick={() => onSelect(otherId)} className="flex items-center gap-2 rounded border px-2 py-1 text-sm hover:bg-accent">
      <span className="font-mono text-xs text-muted-foreground">{link.relation || "—"}</span>
      <span className="font-mono text-xs">{otherId.slice(0, 8)}</span>
    </button>
  );
}
```

> If `react-markdown` is not already a dependency, use plain `<pre className="whitespace-pre-wrap">{data.description}</pre>` instead and skip the import. Verify in `frontend/package.json`.

- [ ] **Step 3: `memory-search.tsx`**

```tsx
import { useMemorySearch } from "@/features/memories/hooks";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";

interface SearchProps {
  projectId: string;
  onSelect: (memoryId: string) => void;
}

export function MemorySearch({ projectId, onSelect }: SearchProps) {
  const [input, setInput] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(input), 250);
    return () => clearTimeout(t);
  }, [input]);
  const { data } = useMemorySearch(projectId, debounced);

  return (
    <div className="relative">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Search className="size-4 text-muted-foreground" />
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search memories…"
          className="flex-1 bg-transparent text-sm outline-none"
        />
      </div>
      {debounced && data && data.length > 0 && (
        <ul className="absolute left-0 right-0 z-10 max-h-80 overflow-auto border-b bg-popover shadow">
          {data.map((hit) => (
            <li key={hit.memory.id}>
              <button
                type="button"
                onClick={() => { onSelect(hit.memory.id); setInput(""); setDebounced(""); }}
                className="flex w-full flex-col px-3 py-2 text-left hover:bg-accent"
              >
                <span className="text-sm font-medium">{hit.memory.title}</span>
                <span className="text-xs text-muted-foreground" dangerouslySetInnerHTML={{ __html: hit.snippet }} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 5: Commit**

```
git add frontend/src/features/memories/components
git commit -m "feat(frontend): memory tree, detail, and search components"
```

---

### Task 24: Memories route page

**Files:**
- Create: `frontend/src/routes/projects/$projectId/memories.tsx`

- [ ] **Step 1: Write the route**

```tsx
import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { MemoryTree } from "@/features/memories/components/memory-tree";
import { MemoryDetail } from "@/features/memories/components/memory-detail";
import { MemorySearch } from "@/features/memories/components/memory-search";

export const Route = createFileRoute("/projects/$projectId/memories")({
  component: MemoriesPage,
});

function MemoriesPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    document.title = project ? `Memories - ${project.name}` : "Memories";
  }, [project]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        {project && <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>}
        <h1 className="text-xl font-semibold">Memories</h1>
      </div>

      <div className="flex flex-1 min-h-0">
        <aside className="w-72 border-r flex flex-col min-h-0">
          <MemorySearch projectId={projectId} onSelect={setSelectedId} />
          <div className="flex-1 overflow-auto py-2">
            <MemoryTree projectId={projectId} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
        </aside>
        <main className="flex-1 min-w-0">
          <MemoryDetail memoryId={selectedId} onSelect={setSelectedId} />
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Regenerate the TanStack route tree**

Run (in `frontend/`): `npm run dev` briefly so the file-based router plugin regenerates `src/routeTree.gen.ts`, or run its generator script. If unclear, start `npm run dev`, confirm the route appears, then stop.

- [ ] **Step 3: Commit**

```
git add frontend/src/routes/projects/\$projectId/memories.tsx frontend/src/routeTree.gen.ts
git commit -m "feat(frontend): /projects/:id/memories read-only page"
```

---

### Task 25: Sidebar link + real-time invalidation

**Files:**
- Modify: `frontend/src/shared/components/app-sidebar.tsx`
- Modify: `frontend/src/shared/context/event-context.tsx`

- [ ] **Step 1: Add the sidebar entry**

Add `Brain` to the `lucide-react` import. Insert into the `projectNav` array (between "Activity" and "Ask & Brainstorming"):
```tsx
{
  label: "Memories",
  to: "/projects/$projectId/memories" as const,
  params: { projectId },
  icon: Brain,
},
```

- [ ] **Step 2: Add real-time query invalidation**

In `frontend/src/shared/context/event-context.tsx`, inside the `ws.onmessage` handler after the `terminal_created` invalidation block, add:
```ts
if (
  data.type === "memory_created" ||
  data.type === "memory_updated" ||
  data.type === "memory_deleted" ||
  data.type === "memory_linked" ||
  data.type === "memory_unlinked"
) {
  if (data.project_id) {
    queryClient.invalidateQueries({ queryKey: ["projects", data.project_id, "memories"] });
  }
  if (typeof data.memory_id === "string") {
    queryClient.invalidateQueries({ queryKey: ["memories", data.memory_id, "detail"] });
  }
}
```

And add silent toast cases inside `buildToastContent`:
```ts
case "memory_created":
case "memory_updated":
case "memory_deleted":
case "memory_linked":
case "memory_unlinked":
  return { title: "", message: "", variant: "default", silent: true };
```

Extend `WsEventData` if needed:
```ts
export type WsEventData = Record<string, unknown> & {
  type?: string;
  project_id?: string;
  issue_id?: string;
  memory_id?: string;
  from_id?: string;
  to_id?: string;
  relation?: string;
  // ...existing fields
};
```

- [ ] **Step 3: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 4: Commit**

```
git add frontend/src/shared/components/app-sidebar.tsx frontend/src/shared/context/event-context.tsx
git commit -m "feat(frontend): memories sidebar link + real-time invalidation"
```

---

### Task 26: End-to-end smoke and cleanup

**Files:**
- Modify: runtime data only (`data/lancedb/`)

- [ ] **Step 1: Full backend test suite**

Run (in `backend/`): `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Frontend lint + type-check**

Run (in `frontend/`):
```
npm run lint
npx tsc --noEmit
```
Expected: both clean.

- [ ] **Step 3: Manual smoke**

- Start the full stack: `python start.py`.
- Open a project in the UI.
- Start the Claude MCP session (in an Ask terminal or a configured project) and call the tool `memory.create` with a title and description. Confirm the memory appears in the sidebar's new Memories page in real time.
- Call `memory.link` between two memories. Confirm the detail page shows the link.
- Call `memory.search` and confirm returned snippet is highlighted in the search dropdown.

- [ ] **Step 4: Delete `data/lancedb/`**

Run: `rm -rf data/lancedb`

- [ ] **Step 5: Commit (no code, just to close the ticket cleanly)**

If nothing is staged, skip the commit step. Otherwise:
```
git status
git add -A
git commit -m "chore: drop obsolete data/lancedb after RAG removal"
```

---

## Scope coverage check (vs spec)

- Remove RAG: Tasks 1–12 cover migration, models, schema, routers, MCP, main, config, deps, tests, event cases, UI badges.
- Memories schema + FTS + triggers: Task 13.
- Memory ORM + FTS bootstrap in tests: Tasks 14, 17.
- Schemas + service + cycle + link + search: Tasks 15, 16.
- Event emission: Task 18.
- REST router: Task 19.
- MCP tools: Task 20.
- Frontend types + API + hooks + components + route + sidebar + events: Tasks 21–25.
- Smoke + runtime cleanup: Task 26.

## Risks / notes (carried from spec)

- Verify no non-RAG code pulls in `pypdf`, `pyarrow`, `torch`, `sentence-transformers`, or `lancedb` before deleting from `requirements.txt` (Task 9 step 2).
- `MemoryLink.relation` uses `''` for "no relation" so composite primary keys remain unique in SQLite.
- `MemoryUpdate.parent_id` in MCP uses an explicit `parent_id_clear: bool` to distinguish "no change" from "set to null" without clashing with FastMCP's JSON-schema exposure.
- Read-only frontend: users watch memories change via WebSocket events but cannot edit — edit/create UI is out of scope and deliberately deferred.
