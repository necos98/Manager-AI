# Codebase Indexing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incrementally index a project's source code into LanceDB so Claude Code can search the codebase semantically via `search_project_context` instead of reading entire files.

**Architecture:** A `CodebaseWalker` walks the managed project's filesystem, computing MD5 hashes per file. A `codebase_files` SQLite table tracks which files are indexed at which hash. On each trigger, only new/modified files are re-embedded (`source_type: "codebase_file"`); deleted files are cleaned up. Triggers: project path set/updated (REST router), issue FINISHED (MCP tool), and a new `index_codebase` MCP tool for manual re-index.

**Tech Stack:** Python, FastAPI, SQLAlchemy async (SQLite/aiosqlite), LanceDB, pathspec, pytest-asyncio (`asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/codebase_file.py` | Create | `CodebaseFile` SQLAlchemy model |
| `backend/app/models/__init__.py` | Modify | Register `CodebaseFile` |
| `backend/alembic/env.py` | Modify | Import `CodebaseFile` so Alembic sees it |
| `backend/alembic/versions/<hash>_add_codebase_files.py` | Create (autogenerate) | Migration for `codebase_files` table |
| `backend/app/config.py` | Modify | Add `codebase_chunk_max_tokens`, `codebase_chunk_overlap_tokens` |
| `backend/app/rag/extractors/codebase_extractor.py` | Create | `FileEntry` dataclass + `CodebaseWalker` |
| `backend/app/rag/pipeline.py` | Modify | Add optional `chunker` param to `_process`; add `embed_codebase_batch`; accept `codebase_chunker` in `__init__` |
| `backend/app/rag/store.py` | Modify | Add `"codebase_file"` to `VALID_SOURCE_TYPES` |
| `backend/app/services/rag_service.py` | Modify | Add `embed_codebase` method |
| `backend/app/routers/projects.py` | Modify | Trigger `embed_codebase` on project create/update if path set |
| `backend/app/mcp/server.py` | Modify | Trigger in `complete_issue` + new `index_codebase` tool |
| `backend/app/mcp/default_settings.json` | Modify | Add `tool.index_codebase.description` |
| `backend/app/main.py` | Modify | Pass `codebase_chunker` to `EmbeddingPipeline` |
| `backend/requirements.txt` | Modify | Add `pathspec` |
| `backend/tests/test_rag_codebase_extractor.py` | Create | Tests for `CodebaseWalker` |
| `backend/tests/test_rag_pipeline.py` | Modify | Add `test_pipeline_embed_codebase_batch` |
| `backend/tests/test_rag_service.py` | Modify | Add `test_embed_codebase_*` |

---

## Task 1: `CodebaseFile` model + migration

**Files:**
- Create: `backend/app/models/codebase_file.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/alembic/env.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Create the model**

```python
# backend/app/models/codebase_file.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CodebaseFile(Base):
    __tablename__ = "codebase_files"
    __table_args__ = (
        UniqueConstraint("project_id", "file_path", name="uq_codebase_file"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Register in `models/__init__.py`**

Add `from app.models.codebase_file import CodebaseFile` and add `"CodebaseFile"` to `__all__`:

```python
# backend/app/models/__init__.py
from app.database import Base
from app.models.activity_log import ActivityLog
from app.models.codebase_file import CodebaseFile
from app.models.issue import Issue
from app.models.issue_feedback import IssueFeedback
from app.models.issue_relation import IssueRelation
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.project_skill import ProjectSkill
from app.models.project_variable import ProjectVariable
from app.models.prompt_template import PromptTemplate
from app.models.setting import Setting
from app.models.task import Task
from app.models.terminal_command import TerminalCommand

__all__ = [
    "ActivityLog", "Base", "CodebaseFile", "Issue", "IssueFeedback", "IssueRelation",
    "Project", "ProjectFile", "ProjectSkill", "ProjectVariable", "PromptTemplate",
    "Setting", "Task", "TerminalCommand",
]
```

- [ ] **Step 3: Register in `alembic/env.py`**

The import in `env.py` currently imports some models to ensure Alembic sees them. Add `CodebaseFile`:

```python
# backend/alembic/env.py  (line 9 — existing line)
from app.models import Project, Task  # noqa: F401 — ensure models are registered
```

Replace with:

```python
from app.models import CodebaseFile, Project, Task  # noqa: F401 — ensure models are registered
```

- [ ] **Step 4: Register in `tests/conftest.py`**

The conftest imports models so the in-memory DB creates all tables. Add `CodebaseFile`:

```python
# backend/tests/conftest.py  — existing import block (lines 6-9)
from app.models import (  # noqa: F401
    ActivityLog, Issue, IssueFeedback, IssueRelation, Project, ProjectSkill,
    PromptTemplate, Setting, Task, TerminalCommand,
)
```

Replace with:

```python
from app.models import (  # noqa: F401
    ActivityLog, CodebaseFile, Issue, IssueFeedback, IssueRelation, Project, ProjectSkill,
    PromptTemplate, Setting, Task, TerminalCommand,
)
```

- [ ] **Step 5: Generate and verify migration**

```bash
cd backend && python -m alembic revision --autogenerate -m "add codebase_files table"
```

Open the generated file in `alembic/versions/`. It must contain `op.create_table('codebase_files', ...)` with columns `id`, `project_id`, `file_path`, `file_hash`, `indexed_at` and the unique constraint. If it doesn't, the model was not registered — re-check steps 2-3.

- [ ] **Step 6: Apply and verify migration**

```bash
cd backend && python -m alembic upgrade head
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/codebase_file.py backend/app/models/__init__.py backend/alembic/env.py backend/tests/conftest.py backend/alembic/versions/
git commit -m "feat: add CodebaseFile model and migration for codebase indexing"
```

---

## Task 2: Config settings for codebase chunking

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add settings**

In `backend/app/config.py`, add two fields to `Settings` after the existing `chunk_overlap_tokens` field:

```python
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50
    codebase_chunk_max_tokens: int = 200
    codebase_chunk_overlap_tokens: int = 20
```

- [ ] **Step 2: Add validator for new fields**

The existing `tokens_must_be_positive` validator uses `@field_validator("chunk_max_tokens", "chunk_overlap_tokens")`. Extend it to cover the new fields:

```python
    @field_validator("chunk_max_tokens", "chunk_overlap_tokens", "codebase_chunk_max_tokens", "codebase_chunk_overlap_tokens")
    @classmethod
    def tokens_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("token counts must be >= 1")
        return v
```

Also extend the `overlap_must_be_less_than_max` validator to check the new pair:

```python
    @model_validator(mode="after")
    def overlap_must_be_less_than_max(self) -> "Settings":
        if self.chunk_overlap_tokens >= self.chunk_max_tokens:
            raise ValueError(
                f"chunk_overlap_tokens ({self.chunk_overlap_tokens}) must be "
                f"less than chunk_max_tokens ({self.chunk_max_tokens})"
            )
        if self.codebase_chunk_overlap_tokens >= self.codebase_chunk_max_tokens:
            raise ValueError(
                f"codebase_chunk_overlap_tokens ({self.codebase_chunk_overlap_tokens}) must be "
                f"less than codebase_chunk_max_tokens ({self.codebase_chunk_max_tokens})"
            )
        return self
```

- [ ] **Step 3: Verify settings load**

```bash
cd backend && python -c "from app.config import settings; print(settings.codebase_chunk_max_tokens, settings.codebase_chunk_overlap_tokens)"
```

Expected output: `200 20`

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add codebase chunking config settings"
```

---

## Task 3: `CodebaseWalker`

**Files:**
- Create: `backend/app/rag/extractors/codebase_extractor.py`
- Create: `backend/tests/test_rag_codebase_extractor.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add `pathspec` to requirements**

```
# backend/requirements.txt — add after pypdf line
pathspec>=0.12.0
```

- [ ] **Step 2: Install dependency**

```bash
cd backend && pip install pathspec
```

- [ ] **Step 3: Write the failing tests**

```python
# backend/tests/test_rag_codebase_extractor.py
import hashlib

import pytest

from app.rag.extractors.codebase_extractor import CodebaseWalker, FileEntry


def test_walker_finds_text_files(tmp_path):
    (tmp_path / "main.py").write_text("def hello(): pass", encoding="utf-8")
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")

    walker = CodebaseWalker()
    entries = walker.walk(str(tmp_path))
    paths = [e.path for e in entries]

    assert "main.py" in paths
    assert "README.md" in paths


def test_walker_ignores_default_dirs(tmp_path):
    (tmp_path / "main.py").write_text("code", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("ignored", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.cpython-311.pyc").write_text("bytecode", encoding="utf-8")

    walker = CodebaseWalker()
    entries = walker.walk(str(tmp_path))
    paths = [e.path for e in entries]

    assert "main.py" in paths
    assert not any("node_modules" in p for p in paths)
    assert not any("__pycache__" in p for p in paths)


def test_walker_skips_unsupported_extensions(tmp_path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG")
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
    (tmp_path / "script.py").write_text("pass", encoding="utf-8")

    walker = CodebaseWalker()
    entries = walker.walk(str(tmp_path))
    paths = [e.path for e in entries]

    assert "script.py" in paths
    assert "image.png" not in paths
    assert "data.bin" not in paths


def test_walker_skips_large_files(tmp_path):
    large = tmp_path / "big.py"
    large.write_bytes(b"x" * 500_001)

    walker = CodebaseWalker()
    entries = walker.walk(str(tmp_path))

    assert entries == []


def test_walker_computes_md5_hash(tmp_path):
    content = b"def main(): pass\n"
    (tmp_path / "app.py").write_bytes(content)

    walker = CodebaseWalker()
    entries = walker.walk(str(tmp_path))

    assert len(entries) == 1
    assert entries[0].hash == hashlib.md5(content).hexdigest()


def test_walker_returns_relative_paths(tmp_path):
    sub = tmp_path / "src" / "auth"
    sub.mkdir(parents=True)
    (sub / "login.py").write_text("# login", encoding="utf-8")

    walker = CodebaseWalker()
    entries = walker.walk(str(tmp_path))

    assert entries[0].path == "src/auth/login.py"


def test_walker_respects_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\nbuild/\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("code", encoding="utf-8")
    (tmp_path / "debug.log").write_text("log content", encoding="utf-8")
    build = tmp_path / "build"
    build.mkdir()
    (build / "output.js").write_text("built", encoding="utf-8")

    walker = CodebaseWalker()
    entries = walker.walk(str(tmp_path))
    paths = [e.path for e in entries]

    assert "main.py" in paths
    assert "debug.log" not in paths
    assert not any("build" in p for p in paths)
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_rag_codebase_extractor.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.rag.extractors.codebase_extractor'`

- [ ] **Step 5: Implement `codebase_extractor.py`**

```python
# backend/app/rag/extractors/codebase_extractor.py
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    path: str    # relative to project root, forward-slash separated
    content: str
    hash: str    # MD5 of raw file bytes


class CodebaseWalker:
    DEFAULT_IGNORE_DIRS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", ".tox", "htmlcov",
    }
    DEFAULT_IGNORE_EXTENSIONS = {".pyc", ".pyo", ".map"}
    MAX_FILE_SIZE_BYTES = 500_000  # 500 KB

    TEXT_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
        ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".sh", ".bash", ".sql", ".graphql",
        ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp", ".h",
        ".txt", ".rst", ".xml", ".env",
    }

    def walk(self, root_path: str) -> list[FileEntry]:
        """Walk root_path and return FileEntry for each indexable source file."""
        root = Path(root_path)
        if not root.is_dir():
            logger.warning("CodebaseWalker: root path is not a directory: %s", root_path)
            return []

        spec = self._load_gitignore(root)
        entries: list[FileEntry] = []

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            rel = file_path.relative_to(root)
            parts = rel.parts

            # Skip ignored directories (any ancestor)
            if any(p in self.DEFAULT_IGNORE_DIRS for p in parts[:-1]):
                continue

            suffix = file_path.suffix.lower()
            if suffix not in self.TEXT_EXTENSIONS:
                continue
            if suffix in self.DEFAULT_IGNORE_EXTENSIONS:
                continue

            # Check gitignore
            rel_posix = rel.as_posix()
            if spec and spec.match_file(rel_posix):
                continue

            try:
                raw = file_path.read_bytes()
            except OSError:
                continue

            if len(raw) > self.MAX_FILE_SIZE_BYTES:
                continue

            content = raw.decode("utf-8", errors="replace")
            file_hash = hashlib.md5(raw).hexdigest()
            entries.append(FileEntry(path=rel_posix, content=content, hash=file_hash))

        return entries

    def _load_gitignore(self, root: Path):
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            return None
        try:
            import pathspec
            return pathspec.PathSpec.from_lines("gitwildmatch", gitignore.read_text(encoding="utf-8").splitlines())
        except Exception:
            return None
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_rag_codebase_extractor.py -v
```

Expected: all 7 PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/rag/extractors/codebase_extractor.py backend/tests/test_rag_codebase_extractor.py backend/requirements.txt
git commit -m "feat: add CodebaseWalker for incremental codebase file discovery"
```

---

## Task 4: Pipeline — `embed_codebase_batch` + store update

**Files:**
- Modify: `backend/app/rag/pipeline.py`
- Modify: `backend/app/rag/store.py`
- Modify: `backend/tests/test_rag_pipeline.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_rag_pipeline.py`:

```python
def test_pipeline_embed_codebase_batch():
    from app.rag.extractors.codebase_extractor import FileEntry

    registry = ExtractorRegistry()
    driver = _mock_driver()
    store = _mock_store()
    chunker = TextChunker(max_tokens=200, overlap_tokens=20)
    pipeline = EmbeddingPipeline(
        registry=registry, chunker=chunker, driver=driver, store=store,
        codebase_chunker=chunker,
    )

    entries = [
        FileEntry(path="src/main.py", content="def main():\n    pass\n\ndef helper():\n    return 1", hash="abc123"),
        FileEntry(path="src/utils.py", content="def util(): return True", hash="def456"),
    ]
    pipeline.embed_codebase_batch(project_id="proj-1", entries=entries)

    assert driver.embed.call_count >= 1
    assert store.delete_by_source.call_count == 2
    assert store.add.call_count == 2

    # Verify source_id format and source_type
    first_call_records = store.add.call_args_list[0][0][0]
    assert first_call_records[0]["source_type"] == "codebase_file"
    assert first_call_records[0]["source_id"] == "proj-1:src/main.py"
    assert first_call_records[0]["title"] == "src/main.py"
    assert first_call_records[0]["project_id"] == "proj-1"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_rag_pipeline.py::test_pipeline_embed_codebase_batch -v
```

Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'codebase_chunker'`

- [ ] **Step 3: Update `pipeline.py`**

**3a.** Add `codebase_chunker` to `__init__`:

```python
# backend/app/rag/pipeline.py

class EmbeddingPipeline:
    """Orchestrates: extract → chunk → embed → store."""

    def __init__(
        self,
        registry: ExtractorRegistry,
        chunker: TextChunker,
        driver: EmbeddingDriver,
        store: VectorStore,
        codebase_chunker: TextChunker | None = None,
    ):
        self.registry = registry
        self.chunker = chunker
        self.driver = driver
        self.store = store
        self.codebase_chunker = codebase_chunker or chunker
```

**3b.** Add optional `chunker` parameter to `_process`:

```python
    def _process(self, project_id: str, source_id: str, content, source_type: str, chunker: TextChunker | None = None):
        """Core pipeline: chunk → embed → delete old → store new."""
        actual_chunker = chunker if chunker is not None else self.chunker
        chunks = actual_chunker.chunk(content.text)
        if not chunks:
            logger.info("No chunks produced for %s/%s", source_type, source_id)
            return

        texts = [c.text for c in chunks]
        vectors = self.driver.embed(texts)
        total = len(chunks)
        now = datetime.now(timezone.utc).isoformat()

        records = [
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "chunk_text": chunk.text,
                "vector": vector,
                "source_type": source_type,
                "source_id": source_id,
                "title": content.title,
                "chunk_index": chunk.index,
                "total_chunks": total,
                "metadata": json.dumps(content.metadata),
                "created_at": now,
            }
            for chunk, vector in zip(chunks, vectors)
        ]

        self.store.delete_by_source(source_id)
        self.store.add(records)
        logger.info("Embedded %d chunks for %s/%s", total, source_type, source_id)
```

**3c.** Add `embed_codebase_batch` method (insert after `embed_issue`):

```python
    def embed_codebase_batch(self, project_id: str, entries: list) -> None:
        """Embed a list of FileEntry objects. source_type='codebase_file'."""
        from app.rag.extractors.base import ExtractedContent
        for entry in entries:
            source_id = f"{project_id}:{entry.path}"
            content = ExtractedContent(title=entry.path, text=entry.content, metadata={})
            self._process(project_id, source_id, content, "codebase_file", self.codebase_chunker)
```

- [ ] **Step 4: Update `VALID_SOURCE_TYPES` in `store.py`**

```python
# backend/app/rag/store.py  — line 58
VALID_SOURCE_TYPES = {"file", "issue"}
```

Replace with:

```python
    VALID_SOURCE_TYPES = {"file", "issue", "codebase_file"}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_rag_pipeline.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/rag/pipeline.py backend/app/rag/store.py backend/tests/test_rag_pipeline.py
git commit -m "feat: add embed_codebase_batch to pipeline and codebase_file source type"
```

---

## Task 5: `RagService.embed_codebase`

**Files:**
- Modify: `backend/app/services/rag_service.py`
- Modify: `backend/tests/test_rag_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_rag_service.py`:

```python
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock


def _make_session_factory(mock_session):
    """Helper: make a mock async_session that yields mock_session."""
    class MockSessionMaker:
        def __call__(self):
            @asynccontextmanager
            async def _cm():
                yield mock_session
            return _cm()
    return MockSessionMaker()


async def test_embed_codebase_fresh_index(mock_pipeline, mock_event_service, tmp_path):
    """First-time index: all files are embedded, DB gets new records."""
    from app.services.rag_service import RagService
    from app.rag.extractors.codebase_extractor import FileEntry

    fake_entries = [
        FileEntry(path="main.py", content="def main(): pass", hash="abc123"),
    ]

    mock_session = AsyncMock()
    # Empty existing records (fresh project)
    mock_session.execute.return_value.scalars.return_value.__iter__ = MagicMock(return_value=iter([]))
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    mock_pipeline.embed_codebase_batch.return_value = None

    with patch("app.services.rag_service.CodebaseWalker") as MockWalker, \
         patch("app.services.rag_service.async_session", _make_session_factory(mock_session)), \
         patch("asyncio.to_thread", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
        MockWalker.return_value.walk.return_value = fake_entries
        svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
        await svc.embed_codebase(project_id="p1", path=str(tmp_path), project_name="Test")

    mock_pipeline.embed_codebase_batch.assert_called_once_with("p1", fake_entries)
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_completed"
    assert event["source_type"] == "codebase"
    assert event["project_id"] == "p1"


async def test_embed_codebase_incremental_skips_unchanged(mock_pipeline, mock_event_service, tmp_path):
    """File with unchanged hash is NOT re-embedded."""
    from app.services.rag_service import RagService
    from app.rag.extractors.codebase_extractor import FileEntry
    from app.models.codebase_file import CodebaseFile

    fake_entries = [
        FileEntry(path="main.py", content="def main(): pass", hash="abc123"),
    ]

    # Existing record with same hash
    existing_record = MagicMock(spec=CodebaseFile)
    existing_record.file_path = "main.py"
    existing_record.file_hash = "abc123"

    mock_session = AsyncMock()
    mock_session.execute.return_value.scalars.return_value.__iter__ = MagicMock(
        return_value=iter([existing_record])
    )
    mock_session.commit = AsyncMock()

    with patch("app.services.rag_service.CodebaseWalker") as MockWalker, \
         patch("app.services.rag_service.async_session", _make_session_factory(mock_session)), \
         patch("asyncio.to_thread", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
        MockWalker.return_value.walk.return_value = fake_entries
        svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
        await svc.embed_codebase(project_id="p1", path=str(tmp_path))

    mock_pipeline.embed_codebase_batch.assert_not_called()


async def test_embed_codebase_cleanup_deleted_files(mock_pipeline, mock_event_service, tmp_path):
    """File no longer on disk gets chunks deleted from LanceDB and DB."""
    from app.services.rag_service import RagService
    from app.models.codebase_file import CodebaseFile

    # Walker returns empty (no files on disk)
    # But DB has one old record
    old_record = MagicMock(spec=CodebaseFile)
    old_record.file_path = "deleted.py"
    old_record.file_hash = "old_hash"

    mock_session = AsyncMock()
    mock_session.execute.return_value.scalars.return_value.__iter__ = MagicMock(
        return_value=iter([old_record])
    )
    mock_session.commit = AsyncMock()

    mock_pipeline.store.delete_by_source = MagicMock()

    with patch("app.services.rag_service.CodebaseWalker") as MockWalker, \
         patch("app.services.rag_service.async_session", _make_session_factory(mock_session)), \
         patch("asyncio.to_thread", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
        MockWalker.return_value.walk.return_value = []
        svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
        await svc.embed_codebase(project_id="p1", path=str(tmp_path))

    mock_pipeline.store.delete_by_source.assert_called_once_with("p1:deleted.py")


async def test_embed_codebase_failure_broadcasts_event(mock_pipeline, mock_event_service, tmp_path):
    """Exception during embedding broadcasts embedding_failed."""
    from app.services.rag_service import RagService

    with patch("app.services.rag_service.CodebaseWalker") as MockWalker:
        MockWalker.return_value.walk.side_effect = RuntimeError("disk error")
        svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
        await svc.embed_codebase(project_id="p1", path=str(tmp_path), project_name="Test")

    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_failed"
    assert event["source_type"] == "codebase"
    assert "disk error" in event["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_rag_service.py -k "codebase" -v
```

Expected: all 4 FAIL (AttributeError: `RagService` has no `embed_codebase`)

- [ ] **Step 3: Implement `embed_codebase` in `rag_service.py`**

Add these imports at the top of `rag_service.py` (after existing imports):

```python
from datetime import datetime, timezone

from app.database import async_session
from app.rag.extractors.codebase_extractor import CodebaseWalker
```

Then add the method to `RagService` (after `delete_source`):

```python
    async def embed_codebase(self, project_id: str, path: str, project_name: str = "") -> None:
        """Incrementally index the project codebase. Only re-embeds new/modified files."""
        async with _source_lock(f"codebase:{project_id}"):
            try:
                from sqlalchemy import delete, select
                from app.models.codebase_file import CodebaseFile

                # 1. Walk filesystem (IO-bound)
                entries = await asyncio.to_thread(CodebaseWalker().walk, path)
                entries_map = {e.path: e for e in entries}

                async with async_session() as session:
                    # 2. Fetch existing hash records
                    result = await session.execute(
                        select(CodebaseFile).where(CodebaseFile.project_id == project_id)
                    )
                    existing_records = {cf.file_path: cf.file_hash for cf in result.scalars()}

                    # 3. Compute diff
                    to_embed = [e for e in entries if existing_records.get(e.path) != e.hash]
                    to_delete_paths = [fp for fp in existing_records if fp not in entries_map]

                    # 4. Delete removed files from LanceDB
                    for fp in to_delete_paths:
                        source_id = f"{project_id}:{fp}"
                        await asyncio.to_thread(self.pipeline.store.delete_by_source, source_id)

                    # 5. Delete removed files from DB
                    if to_delete_paths:
                        await session.execute(
                            delete(CodebaseFile).where(
                                CodebaseFile.project_id == project_id,
                                CodebaseFile.file_path.in_(to_delete_paths),
                            )
                        )

                    # 6. Embed new/modified files (CPU-bound)
                    if to_embed:
                        await asyncio.to_thread(self.pipeline.embed_codebase_batch, project_id, to_embed)

                        # 7. Upsert codebase_files
                        now = datetime.now(timezone.utc)
                        for entry in to_embed:
                            row_result = await session.execute(
                                select(CodebaseFile).where(
                                    CodebaseFile.project_id == project_id,
                                    CodebaseFile.file_path == entry.path,
                                )
                            )
                            existing = row_result.scalar_one_or_none()
                            if existing:
                                existing.file_hash = entry.hash
                                existing.indexed_at = now
                            else:
                                session.add(CodebaseFile(
                                    project_id=project_id,
                                    file_path=entry.path,
                                    file_hash=entry.hash,
                                    indexed_at=now,
                                ))

                    await session.commit()

                await self.event_service.emit({
                    "type": "embedding_completed",
                    "source_type": "codebase",
                    "project_id": project_id,
                    "project_name": project_name,
                    "files_indexed": len(to_embed),
                    "files_deleted": len(to_delete_paths),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            except Exception as e:
                logger.exception("Codebase embedding failed for project %s", project_id)
                await self.event_service.emit({
                    "type": "embedding_failed",
                    "source_type": "codebase",
                    "project_id": project_id,
                    "project_name": project_name,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_rag_service.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rag_service.py backend/tests/test_rag_service.py
git commit -m "feat: add embed_codebase to RagService with incremental hash-based diffing"
```

---

## Task 6: Update `main.py` to pass `codebase_chunker`

**Files:**
- Modify: `backend/app/main.py`

This is a one-step change — no test needed since the integration is covered by the existing RAG startup test (the app boots without error).

- [ ] **Step 1: Update `main.py` lifespan**

In `backend/app/main.py`, inside the `lifespan` function, replace the pipeline construction:

```python
    # existing code
    driver = SentenceTransformerDriver(model_name=settings.embedding_model)
    chunker = TextChunker(
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    store = VectorStore(db_path=settings.lancedb_path)
    pipeline = EmbeddingPipeline(
        registry=registry, chunker=chunker, driver=driver, store=store
    )
```

With:

```python
    driver = SentenceTransformerDriver(model_name=settings.embedding_model)
    chunker = TextChunker(
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    codebase_chunker = TextChunker(
        max_tokens=settings.codebase_chunk_max_tokens,
        overlap_tokens=settings.codebase_chunk_overlap_tokens,
    )
    store = VectorStore(db_path=settings.lancedb_path)
    pipeline = EmbeddingPipeline(
        registry=registry, chunker=chunker, driver=driver, store=store,
        codebase_chunker=codebase_chunker,
    )
```

- [ ] **Step 2: Verify app starts**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: pass codebase_chunker to EmbeddingPipeline in app lifespan"
```

---

## Task 7: Triggers + `index_codebase` MCP tool

**Files:**
- Modify: `backend/app/routers/projects.py`
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`

### Sub-task 7a: Trigger on project create/update

- [ ] **Step 1: Add `asyncio` import and `_background_tasks` set to `projects.py`**

At the top of `backend/app/routers/projects.py`, add:

```python
import asyncio
```

After the `router = APIRouter(...)` line, add:

```python
_background_tasks: set[asyncio.Task] = set()
```

- [ ] **Step 2: Update `create_project` endpoint**

Replace the existing `create_project` handler:

```python
@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description,
        tech_stack=data.tech_stack, shell=data.shell
    )
    await db.commit()

    if project.path:
        from app.rag import get_rag_service
        rag = get_rag_service()
        t = asyncio.create_task(rag.embed_codebase(project.id, project.path, project.name))
        _background_tasks.add(t)
        t.add_done_callback(_background_tasks.discard)

    return await _enrich_project(service, project)
```

- [ ] **Step 3: Update `update_project` endpoint**

Replace the existing `update_project` handler:

```python
@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    old_project = await service.get_by_id(project_id)
    old_path = old_project.path

    project = await service.update(project_id, **data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(project)

    new_path = data.path if data.path is not None else None
    if new_path is not None and new_path != old_path and project.path:
        from app.rag import get_rag_service
        rag = get_rag_service()
        t = asyncio.create_task(rag.embed_codebase(project.id, project.path, project.name))
        _background_tasks.add(t)
        t.add_done_callback(_background_tasks.discard)

    return await _enrich_project(service, project)
```

- [ ] **Step 4: Verify existing project router tests pass**

```bash
cd backend && python -m pytest tests/test_routers_projects.py -v 2>/dev/null || python -m pytest tests/ -k "project" -v
```

Expected: all PASS (or no project tests found — that's fine).

### Sub-task 7b: `index_codebase` MCP tool + trigger in `complete_issue`

- [ ] **Step 5: Add `tool.index_codebase.description` to `default_settings.json`**

In `backend/app/mcp/default_settings.json`, add before the closing `}`:

```json
  "tool.index_codebase.description": "Trigger incremental re-indexing of the project codebase for semantic search. Returns immediately; indexing runs in the background. A 'embedding_completed' event is broadcast when done."
```

- [ ] **Step 6: Add `index_codebase` tool and codebase trigger in `complete_issue`**

In `backend/app/mcp/server.py`:

**6a.** After the last `@mcp.tool` decorated function, add the new tool:

```python
@mcp.tool(description=_desc["tool.index_codebase.description"])
async def index_codebase(project_id: str) -> dict:
    async with async_session() as session:
        project_service = ProjectService(session)
        try:
            project = await project_service.get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
        if not project.path:
            return {"error": "Project path not set"}
        project_path = project.path
        project_name = project.name

    rag = get_rag_service()
    t = asyncio.create_task(rag.embed_codebase(project_id, project_path, project_name))
    _background_tasks.add(t)
    t.add_done_callback(_background_tasks.discard)
    return {"status": "started", "project_id": project_id}
```

**6b.** In `complete_issue`, extract `project_path` alongside `project_name`. The existing code (lines ~144-148) already fetches the project:

```python
            try:
                project = await ProjectService(session).get_by_id(project_id)
                project_name = project.name
            except AppError:
                project_name = ""
```

Replace with:

```python
            try:
                project = await ProjectService(session).get_by_id(project_id)
                project_name = project.name
                project_path = project.path
            except AppError:
                project_name = ""
                project_path = ""
```

**6c.** After the existing `embed_task` block (the `embed_issue` task), add the codebase trigger:

```python
            _background_tasks.add(embed_task)
            embed_task.add_done_callback(_background_tasks.discard)
            logger.debug("embed_issue task started for issue %s", issue_id_val)

            # Trigger incremental codebase re-index after issue completion
            if project_path:
                codebase_task = asyncio.create_task(rag.embed_codebase(
                    project_id=project_id,
                    path=project_path,
                    project_name=project_name,
                ))
                _background_tasks.add(codebase_task)
                codebase_task.add_done_callback(_background_tasks.discard)
```

- [ ] **Step 7: Verify MCP server loads without errors**

```bash
cd backend && python -c "from app.mcp.server import mcp; print('MCP tools:', len(mcp._tool_manager._tools))"
```

Expected: prints `MCP tools: <number>` without error. The number should be one higher than before (new `index_codebase` tool).

- [ ] **Step 8: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/routers/projects.py backend/app/mcp/server.py backend/app/mcp/default_settings.json
git commit -m "feat: add index_codebase MCP tool and codebase re-index triggers"
```

---

## Self-Review Notes

- `source_id` format `"{project_id}:{file_path}"` is consistent across pipeline, service, and store
- `VALID_SOURCE_TYPES` in store updated in Task 4 — `search_project_context` filter for `"codebase_file"` now works
- `embed_codebase_batch` uses `self.codebase_chunker` (200 tokens) not the default chunker (500 tokens)
- `_source_lock(f"codebase:{project_id}")` prevents concurrent re-index of the same project
- `project_path` is extracted before `session.commit()` in `complete_issue` to avoid session expiry issues
- `conftest.py` updated in Task 1 so the in-memory test DB creates the `codebase_files` table
