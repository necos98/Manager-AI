# Finish Half-Built Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the partially implemented features surfaced in the project audit: complete the codebase indexing backend (UI button already ships), finalise the mobile sidebar QR pairing flow, expose a real `/api/health` endpoint, add structured logging, and populate empty hook handler slots.

**Architecture:** Five independent initiatives. Each can land in its own PR. Order flexible; some phases depend only on Alembic migrations.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async (SQLite/aiosqlite), LanceDB, pathspec, `structlog`, React 19, TanStack Router, TanStack Query, `react-qr-code`, pytest-asyncio (`asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/rag/extractors/codebase_extractor.py` | Create | `FileEntry` + `CodebaseWalker` |
| `backend/app/models/codebase_file.py` | Create | `CodebaseFile` SQLAlchemy model |
| `backend/alembic/versions/<hash>_codebase_files.py` | Create | Migration |
| `backend/app/services/rag_service.py` | Modify | `embed_codebase` |
| `backend/app/routers/projects.py` | Modify | Trigger on path update |
| `backend/app/mcp/server.py` | Modify | `index_codebase` tool + trigger in `complete_issue` |
| `backend/app/mcp/default_settings.json` | Modify | Tool description |
| `backend/app/hooks/handlers/on_issue_created.py` | Create | Starter hook for `ISSUE_CREATED` |
| `backend/app/hooks/handlers/on_all_tasks_completed.py` | Create | Starter hook for `ALL_TASKS_COMPLETED` |
| `backend/app/hooks/handlers/__init__.py` | Modify | Import new handlers |
| `backend/app/routers/health.py` | Create | `/api/health` with subsystem probes |
| `backend/app/main.py` | Modify | Register health router + `structlog` |
| `backend/app/logging_config.py` | Create | `structlog` setup |
| `backend/requirements.txt` | Modify | Add `structlog`, `pathspec` |
| `frontend/src/features/projects/components/mobile-sidebar-dialog.tsx` | Modify/Create | QR pairing flow |
| `frontend/src/routes/mobile/$token.tsx` | Create | Mobile companion view |
| `backend/app/routers/mobile.py` | Create | Token-gated mobile payload |
| `backend/app/models/mobile_pairing.py` | Create | Token + expiry model |
| `backend/alembic/versions/<hash>_mobile_pairings.py` | Create | Migration |
| `backend/tests/test_rag_codebase_extractor.py` | Create | Walker unit tests |
| `backend/tests/test_rag_service_codebase.py` | Create | `embed_codebase` tests |
| `backend/tests/test_health_router.py` | Create | Health probe tests |
| `backend/tests/test_mobile_router.py` | Create | Pairing tests |

---

## Phase 1: Complete Codebase Indexing Backend

**Why:** UI button in `project-settings-dialog.tsx` already calls `useTriggerCodebaseIndex`, but the backend walker + `embed_codebase` service method + MCP tool are missing. The design is in `docs/superpowers/specs/2026-04-02-codebase-indexing-design.md`; this phase completes the implementation side.

### Task 1.1: `CodebaseFile` model + migration

**Files:**
- Create: `backend/app/models/codebase_file.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Create model**

```python
# backend/app/models/codebase_file.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CodebaseFile(Base):
    __tablename__ = "codebase_files"
    __table_args__ = (UniqueConstraint("project_id", "file_path", name="uq_codebase_file"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Register in `__init__.py` + `alembic/env.py` + `tests/conftest.py`**

Add `CodebaseFile` to the import list in all three files (see `docs/superpowers/plans/2026-04-02-codebase-indexing.md` Task 1 for exact patterns).

- [ ] **Step 3: Autogenerate + apply migration**

```bash
cd backend && python -m alembic revision --autogenerate -m "add codebase_files table"
cd backend && python -m alembic upgrade head
```

### Task 1.2: `CodebaseWalker`

**Files:**
- Create: `backend/app/rag/extractors/codebase_extractor.py`
- Modify: `backend/requirements.txt` (add `pathspec`)

- [ ] **Step 1: Install dep**

```bash
cd backend && pip install pathspec && echo "pathspec>=0.12" >> requirements.txt
```

- [ ] **Step 2: Failing test**

```python
# backend/tests/test_rag_codebase_extractor.py
import hashlib
from pathlib import Path
from app.rag.extractors.codebase_extractor import CodebaseWalker, FileEntry


def test_walker_yields_text_files(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('hi')")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("x")
    (tmp_path / ".gitignore").write_text("node_modules/\n")

    files = list(CodebaseWalker(str(tmp_path)).walk())
    paths = {f.relative_path for f in files}
    assert "a.py" in paths
    assert "node_modules/ignored.js" not in paths


def test_walker_hashes_content(tmp_path: Path):
    content = "hello world"
    (tmp_path / "a.txt").write_text(content)
    entry: FileEntry = next(CodebaseWalker(str(tmp_path)).walk())
    assert entry.file_hash == hashlib.md5(content.encode()).hexdigest()


def test_walker_skips_binary(tmp_path: Path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    (tmp_path / "code.py").write_text("x = 1")
    files = list(CodebaseWalker(str(tmp_path)).walk())
    assert {f.relative_path for f in files} == {"code.py"}
```

- [ ] **Step 3: Implementation**

```python
# backend/app/rag/extractors/codebase_extractor.py
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pathspec

TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
    ".md", ".txt", ".toml", ".ini", ".cfg", ".html", ".css", ".scss",
    ".sh", ".bash", ".rs", ".go", ".java", ".kt", ".rb", ".php", ".sql",
    ".vue", ".svelte", ".lua", ".c", ".cpp", ".h", ".hpp", ".cs",
}
MAX_FILE_BYTES = 512 * 1024  # 512 KB
DEFAULT_IGNORE = [
    ".git/", "node_modules/", "__pycache__/", ".venv/", "venv/",
    "dist/", "build/", ".next/", "target/", "*.pyc", "*.lock",
    "data/", ".claude/",
]


@dataclass
class FileEntry:
    relative_path: str
    content: str
    file_hash: str


class CodebaseWalker:
    def __init__(self, root: str):
        self.root = Path(root)
        self._spec = self._load_gitignore()

    def _load_gitignore(self) -> pathspec.PathSpec:
        patterns = list(DEFAULT_IGNORE)
        gi = self.root / ".gitignore"
        if gi.is_file():
            patterns.extend(gi.read_text(encoding="utf-8", errors="ignore").splitlines())
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def walk(self) -> Iterator[FileEntry]:
        if not self.root.is_dir():
            return
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(self.root).as_posix()
            if self._spec.match_file(rel):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            yield FileEntry(
                relative_path=rel,
                content=content,
                file_hash=hashlib.md5(content.encode()).hexdigest(),
            )
```

- [ ] **Step 4: Tests green**

```bash
cd backend && python -m pytest tests/test_rag_codebase_extractor.py -v
```

### Task 1.3: `RagService.embed_codebase`

**Files:**
- Modify: `backend/app/services/rag_service.py`
- Modify: `backend/app/rag/store.py:58` (extend `VALID_SOURCE_TYPES`)

- [ ] **Step 1: Extend allowed source types**

```python
# backend/app/rag/store.py
VALID_SOURCE_TYPES = {"file", "issue", "codebase_file"}
```

- [ ] **Step 2: Failing test**

```python
# backend/tests/test_rag_service_codebase.py
async def test_embed_codebase_indexes_new_files(db_session, tmp_path, rag_service):
    project = await _create_project(db_session, path=str(tmp_path))
    (tmp_path / "a.py").write_text("x = 1")

    await rag_service.embed_codebase(project_id=project.id)

    from app.models import CodebaseFile
    rows = (await db_session.execute(__import__("sqlalchemy").select(CodebaseFile))).scalars().all()
    assert {r.file_path for r in rows} == {"a.py"}


async def test_embed_codebase_skips_unchanged_files(db_session, tmp_path, rag_service):
    project = await _create_project(db_session, path=str(tmp_path))
    (tmp_path / "a.py").write_text("x = 1")
    await rag_service.embed_codebase(project_id=project.id)
    # second run — no change
    calls_before = rag_service._pipeline.embed_file_content.call_count
    await rag_service.embed_codebase(project_id=project.id)
    assert rag_service._pipeline.embed_file_content.call_count == calls_before


async def test_embed_codebase_removes_deleted_files(db_session, tmp_path, rag_service):
    project = await _create_project(db_session, path=str(tmp_path))
    f = tmp_path / "a.py"
    f.write_text("x = 1")
    await rag_service.embed_codebase(project_id=project.id)
    f.unlink()
    await rag_service.embed_codebase(project_id=project.id)

    from app.models import CodebaseFile
    rows = (await db_session.execute(__import__("sqlalchemy").select(CodebaseFile))).scalars().all()
    assert rows == []
```

- [ ] **Step 3: Implement**

```python
# backend/app/services/rag_service.py  (append method)
from sqlalchemy import select, delete as sa_delete
from app.models import CodebaseFile, Project
from app.rag.extractors.codebase_extractor import CodebaseWalker, FileEntry

async def embed_codebase(self, project_id: str) -> dict:
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if project is None or not project.path:
            return {"indexed": 0, "skipped": 0, "removed": 0, "reason": "no_path"}

    await event_service.emit({
        "type": "embedding_started",
        "project_id": project_id,
        "source_type": "codebase",
        "source_id": project_id,
    })

    walker = CodebaseWalker(project.path)
    seen: dict[str, str] = {}
    indexed = skipped = 0

    async with async_session() as session:
        existing = {
            r.file_path: r
            for r in (await session.execute(
                select(CodebaseFile).where(CodebaseFile.project_id == project_id)
            )).scalars().all()
        }

        for entry in walker.walk():
            seen[entry.relative_path] = entry.file_hash
            prior = existing.get(entry.relative_path)
            if prior and prior.file_hash == entry.file_hash:
                skipped += 1
                continue
            # re-index: drop old vectors for this source_id, embed new
            source_id = f"{project_id}:{entry.relative_path}"
            await asyncio.to_thread(
                self._pipeline.embed_file_content,
                content=entry.content,
                project_id=project_id,
                source_type="codebase_file",
                source_id=source_id,
                title=entry.relative_path,
            )
            if prior:
                prior.file_hash = entry.file_hash
            else:
                session.add(CodebaseFile(
                    project_id=project_id,
                    file_path=entry.relative_path,
                    file_hash=entry.file_hash,
                ))
            indexed += 1

        removed = 0
        for path, row in existing.items():
            if path not in seen:
                await asyncio.to_thread(
                    self._pipeline.delete_source,
                    source_id=f"{project_id}:{path}",
                )
                await session.delete(row)
                removed += 1

        await session.commit()

    await event_service.emit({
        "type": "embedding_completed",
        "project_id": project_id,
        "source_type": "codebase",
        "source_id": project_id,
    })
    return {"indexed": indexed, "skipped": skipped, "removed": removed}
```

> `embed_file_content` and `delete_source` are thin passthroughs to pipeline + store; add them if not present.

- [ ] **Step 4: Tests green**

```bash
cd backend && python -m pytest tests/test_rag_service_codebase.py -v
```

### Task 1.4: MCP tool + trigger

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`
- Modify: `backend/app/routers/projects.py`

- [ ] **Step 1: Add `index_codebase` MCP tool**

```python
# backend/app/mcp/server.py
@mcp.tool(description=_tool_descriptions.get("index_codebase", "Index the project codebase."))
async def index_codebase(project_id: str) -> dict:
    task = asyncio.create_task(rag_service.embed_codebase(project_id=project_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "accepted", "project_id": project_id}
```

- [ ] **Step 2: Add description**

```json
// backend/app/mcp/default_settings.json (tool_descriptions block)
"index_codebase": "Re-index the project's source code into the semantic search index. Returns immediately; progress emitted via WebSocket events."
```

- [ ] **Step 3: Trigger in `complete_issue` MCP tool**

```python
# backend/app/mcp/server.py  (inside complete_issue, after the issue embedding task is spawned)
codebase_task = asyncio.create_task(rag_service.embed_codebase(project_id=project_id))
_background_tasks.add(codebase_task)
codebase_task.add_done_callback(_background_tasks.discard)
```

- [ ] **Step 4: Trigger on project path update**

```python
# backend/app/routers/projects.py  (inside update_project, after commit, if path changed)
if payload.path and payload.path != old_path:
    task = asyncio.create_task(rag_service.embed_codebase(project_id=project_id))
    # fire-and-forget; errors logged inside embed_codebase
```

- [ ] **Step 5: Commit**

```bash
git add backend/ 
git commit -m "feat(rag): complete codebase indexing backend + MCP tool"
```

---

## Phase 2: `/api/health` Endpoint

**Why:** `/health` returns a static "ok"; ops need real subsystem probes.

### Task 2.1: Probe router

**Files:**
- Create: `backend/app/routers/health.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_health_router.py
async def test_health_returns_subsystem_status(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"ok", "degraded"}
    assert set(data["checks"].keys()) >= {"database", "lancedb", "claude_cli"}

async def test_health_marks_db_failure(monkeypatch, client):
    async def fail(_self, _q):
        raise RuntimeError("db down")
    monkeypatch.setattr("sqlalchemy.ext.asyncio.AsyncSession.execute", fail)
    resp = await client.get("/api/health")
    assert resp.status_code == 503
```

- [ ] **Step 2: Implementation**

```python
# backend/app/routers/health.py
from __future__ import annotations
import shutil
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.config import settings

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health(response: Response, db: AsyncSession = Depends(get_session)) -> dict:
    checks: dict[str, dict] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as exc:
        checks["database"] = {"ok": False, "error": str(exc)}

    try:
        import lancedb
        lancedb.connect(settings.lancedb_path)
        checks["lancedb"] = {"ok": True}
    except Exception as exc:
        checks["lancedb"] = {"ok": False, "error": str(exc)}

    claude = shutil.which("claude")
    checks["claude_cli"] = {"ok": claude is not None, "path": claude}

    overall_ok = all(c.get("ok") for c in checks.values())
    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if overall_ok else "degraded", "checks": checks}
```

- [ ] **Step 3: Register router**

```python
# backend/app/main.py
from app.routers.health import router as health_router
app.include_router(health_router)
```

- [ ] **Step 4: Tests green**

```bash
cd backend && python -m pytest tests/test_health_router.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/health.py backend/app/main.py backend/tests/test_health_router.py
git commit -m "feat(health): /api/health with database, lancedb, claude CLI probes"
```

---

## Phase 3: Structured Logging

**Why:** Current `logger.info(...)` / `logger.error(...)` calls emit free-form text. `structlog` gives JSON output suitable for log aggregation without changing call sites significantly.

### Task 3.1: Configure `structlog`

**Files:**
- Create: `backend/app/logging_config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Install**

```bash
cd backend && pip install structlog && echo "structlog>=24.1.0" >> requirements.txt
```

- [ ] **Step 2: Config**

```python
# backend/app/logging_config.py
import logging
import sys
import structlog
from app.config import settings


def configure_logging() -> None:
    level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging through structlog (so existing logger.X calls benefit)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(handlers=[handler], level=level, force=True)
```

- [ ] **Step 3: Add settings**

```python
# backend/app/config.py
log_level: str = "INFO"
log_format: str = "console"  # or "json"
```

- [ ] **Step 4: Call at startup**

```python
# backend/app/main.py  (top of lifespan, before anything else)
from app.logging_config import configure_logging
configure_logging()
```

### Task 3.2: Request/response middleware

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Middleware**

```python
# backend/app/main.py
import time, uuid
import structlog
from fastapi import Request

log = structlog.get_logger("http")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    structlog.contextvars.bind_contextvars(request_id=req_id, path=request.url.path, method=request.method)
    start = time.monotonic()
    try:
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000)
        log.info("http_response", status=response.status_code, duration_ms=duration_ms)
        response.headers["x-request-id"] = req_id
        return response
    finally:
        structlog.contextvars.clear_contextvars()
```

- [ ] **Step 2: Manual verify**

```bash
cd backend && LOG_FORMAT=json python -m uvicorn app.main:app --reload
curl http://localhost:8000/api/health
```
Confirm JSON log lines in stdout.

- [ ] **Step 3: Commit**

```bash
git add backend/app/logging_config.py backend/app/main.py backend/app/config.py backend/requirements.txt
git commit -m "feat(logging): structlog with request-id context and JSON mode"
```

---

## Phase 4: Populate Empty Hook Handlers

**Why:** Only `EnrichProjectContext` is registered. Shipping starter handlers for `ISSUE_CREATED` (auto-generate a spec skeleton) and `ALL_TASKS_COMPLETED` (send a desktop notification) unlocks the hook system's usefulness.

### Task 4.1: `on_issue_created` handler

**Files:**
- Create: `backend/app/hooks/handlers/on_issue_created.py`

- [ ] **Step 1: Implement**

```python
# backend/app/hooks/handlers/on_issue_created.py
from __future__ import annotations
from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook


@hook(event=HookEvent.ISSUE_CREATED)
class DraftSpecSkeletonHook(BaseHook):
    name = "draft_spec_skeleton"
    description = "Generate a draft specification skeleton from the issue description."

    async def execute(self, ctx: HookContext) -> HookResult:
        project_path = ctx.metadata.get("project_path") or ""
        issue_description = ctx.metadata.get("issue_description") or ""
        prompt = (
            "A new issue was just created in Manager AI. "
            "Write a concise draft specification (3-6 bullet points) outlining scope, "
            "approach, and unknowns, then call mcp__ManagerAi__create_issue_spec with it.\n\n"
            f"Issue: {issue_description}\n"
            f"Project ID: {ctx.project_id}\n"
            f"Issue ID: {ctx.issue_id}\n"
        )
        result = await ClaudeCodeExecutor().run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": ctx.project_id,
                "MANAGER_AI_ISSUE_ID": ctx.issue_id,
            },
            timeout=180,
            tool_guidance="[Tool guidance] Only use mcp__ManagerAi__create_issue_spec.",
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
```

> The hook is **opt-in** per project via a setting (`auto_draft_spec: bool = False`). Guard with an early return in `execute` if disabled.

### Task 4.2: `on_all_tasks_completed` handler

**Files:**
- Create: `backend/app/hooks/handlers/on_all_tasks_completed.py`

- [ ] **Step 1: Implement**

```python
# backend/app/hooks/handlers/on_all_tasks_completed.py
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.event_service import event_service


@hook(event=HookEvent.ALL_TASKS_COMPLETED)
class NotifyAllTasksCompleteHook(BaseHook):
    name = "notify_all_tasks_complete"
    description = "Emit a notification when the final task of an issue is marked Completed."

    async def execute(self, ctx: HookContext) -> HookResult:
        await event_service.emit({
            "type": "notification",
            "project_id": ctx.project_id,
            "issue_id": ctx.issue_id,
            "title": "All tasks completed",
            "message": f"Issue {ctx.metadata.get('issue_name', '')} is ready for completion.",
        })
        return HookResult(success=True)
```

### Task 4.3: Register handlers

**Files:**
- Modify: `backend/app/hooks/handlers/__init__.py`

- [ ] **Step 1: Import for registration**

```python
# backend/app/hooks/handlers/__init__.py
from app.hooks.handlers import enrich_context  # noqa: F401
from app.hooks.handlers import on_issue_created  # noqa: F401
from app.hooks.handlers import on_all_tasks_completed  # noqa: F401
```

- [ ] **Step 2: Add test**

```python
# backend/tests/test_hooks_handlers.py
async def test_all_tasks_completed_emits_notification(monkeypatch):
    from app.hooks.handlers.on_all_tasks_completed import NotifyAllTasksCompleteHook
    from app.hooks.registry import HookContext, HookEvent

    events = []
    monkeypatch.setattr("app.services.event_service.event_service.emit", lambda e: events.append(e))

    result = await NotifyAllTasksCompleteHook().execute(HookContext(
        project_id="p", issue_id="i", event=HookEvent.ALL_TASKS_COMPLETED,
        metadata={"issue_name": "Ship it"},
    ))
    assert result.success
    assert events[0]["type"] == "notification"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/hooks/handlers/ backend/tests/test_hooks_handlers.py
git commit -m "feat(hooks): starter handlers for issue_created and all_tasks_completed"
```

---

## Phase 5: Mobile Sidebar QR Pairing (Finish)

**Why:** `smartphone-qr-dialog.tsx` exists but the backend pairing endpoint + mobile companion route are incomplete. This phase closes the loop.

### Task 5.1: Pairing model + router

**Files:**
- Create: `backend/app/models/mobile_pairing.py`
- Create: `backend/app/routers/mobile.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Model**

```python
# backend/app/models/mobile_pairing.py
from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MobilePairing(Base):
    __tablename__ = "mobile_pairings"

    token: Mapped[str] = mapped_column(String(64), primary_key=True,
                                        default=lambda: secrets.token_urlsafe(32))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=6))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
```

Register in `models/__init__.py`, `alembic/env.py`, `conftest.py`. Autogenerate migration.

- [ ] **Step 2: Router**

```python
# backend/app/routers/mobile.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import MobilePairing, Project, Issue

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


@router.post("/pair")
async def create_pairing(project_id: str, db: AsyncSession = Depends(get_session)) -> dict:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")
    pairing = MobilePairing(project_id=project_id)
    db.add(pairing)
    await db.commit()
    return {"token": pairing.token, "expires_at": pairing.expires_at.isoformat()}


@router.get("/view/{token}")
async def mobile_view(token: str, db: AsyncSession = Depends(get_session)) -> dict:
    pairing = await db.get(MobilePairing, token)
    if not pairing or pairing.expires_at < datetime.now(timezone.utc):
        raise HTTPException(404, "pairing expired or not found")
    project = await db.get(Project, pairing.project_id)
    issues = (await db.execute(
        select(Issue).where(Issue.project_id == pairing.project_id).order_by(Issue.updated_at.desc()).limit(50)
    )).scalars().all()
    return {
        "project": {"id": project.id, "name": project.name},
        "issues": [
            {"id": i.id, "name": i.name, "status": i.status.value, "priority": i.priority}
            for i in issues
        ],
    }
```

### Task 5.2: Mobile view route

**Files:**
- Create: `frontend/src/routes/mobile/$token.tsx`

- [ ] **Step 1: Read-only mobile UI**

```tsx
// frontend/src/routes/mobile/$token.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/shared/api/client";

export const Route = createFileRoute("/mobile/$token")({
  component: MobileView,
});

function MobileView() {
  const { token } = Route.useParams();
  const { data, isLoading, error } = useQuery({
    queryKey: ["mobile", token],
    queryFn: () => apiGet<{ project: { id: string; name: string }; issues: Array<{ id: string; name: string; status: string; priority: number }> }>(`/api/mobile/view/${token}`),
    refetchInterval: 10_000,
  });

  if (isLoading) return <div className="p-4">Loading…</div>;
  if (error) return <div className="p-4 text-destructive">Link expired or invalid.</div>;
  if (!data) return null;

  return (
    <div className="min-h-screen bg-background p-4">
      <h1 className="text-xl font-semibold">{data.project.name}</h1>
      <ul className="mt-4 space-y-2">
        {data.issues.map((i) => (
          <li key={i.id} className="rounded-md border p-3">
            <div className="text-sm font-medium">{i.name || i.id}</div>
            <div className="text-xs text-muted-foreground">{i.status} · priority {i.priority}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Task 5.3: Wire QR dialog

**Files:**
- Modify: `frontend/src/shared/components/smartphone-qr-dialog.tsx`

- [ ] **Step 1: Call `/api/mobile/pair` and render QR**

```tsx
// Inside the dialog component
const { data: pairing, refetch } = useQuery({
  queryKey: ["mobile-pair", projectId],
  queryFn: () => apiPost<{ token: string; expires_at: string }>("/api/mobile/pair", { project_id: projectId }),
  enabled: open,
  staleTime: 5 * 60 * 1000,
});

const pairingUrl = pairing
  ? `${window.location.origin}/mobile/${pairing.token}`
  : null;

// Render QRCode component with value={pairingUrl}
```

- [ ] **Step 2: Manual verify** — open dialog, scan QR with phone (or open URL directly), confirm mobile view loads and auto-refreshes.

- [ ] **Step 3: Commit**

```bash
git add backend/ frontend/src/routes/mobile/ frontend/src/shared/components/smartphone-qr-dialog.tsx
git commit -m "feat(mobile): finish QR pairing with token-gated mobile view"
```

---

## Self-Review Checklist

- [ ] Codebase indexing: UI button triggers real backend work; deleting a file causes removal on next index.
- [ ] Health probe returns 503 when LanceDB path is unreachable.
- [ ] JSON log output contains `request_id`, `path`, `status`, `duration_ms`.
- [ ] Hook handlers fire on the right events (tested with monkeypatched `event_service`).
- [ ] Mobile pairing link expires after 6 h; polling view handles expiry gracefully.

---

## Execution

Estimated effort:
1. Phase 1 (codebase indexing) — 12 h
2. Phase 2 (/api/health) — 2 h
3. Phase 3 (structlog) — 4 h
4. Phase 4 (hook handlers) — 3 h
5. Phase 5 (mobile QR) — 6 h

Total: ~27 hours.
