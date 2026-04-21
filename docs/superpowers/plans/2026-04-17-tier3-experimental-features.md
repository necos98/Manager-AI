# Tier 3 — Experimental Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four exploratory capabilities that push Manager AI beyond standard PM territory: automatic context compression, smart terminal replay, project health scoring, and prompt A/B testing.

**Architecture:** Each feature is a vertical slice with its own models, service, router, and optional UI. All four are opt-in (feature flags in `Setting`) so experiments can be shipped dark and validated before becoming defaults. Services stay pure and pluggable — prompt A/B testing and context compression wrap existing executors rather than replacing them.

**Tech Stack:** FastAPI async, SQLAlchemy 2.x async, Pydantic v2, LanceDB (reuse existing embeddings for compression relevance scoring), React 19 + TanStack Router + Recharts, xterm.js for replay, tiktoken for token counting, numpy (already present via sentence-transformers) for statistical tests.

---

## File Map

| File | Responsibility | Create/Modify |
|------|----------------|---------------|
| `backend/app/models/compression.py` | `ContextSummary` model (issue_id, summary, token_count, created_at) | Create |
| `backend/app/services/context_compressor.py` | `ContextCompressor.compress(issue)` — token count, LRU trim, Claude summary call | Create |
| `backend/app/services/token_counter.py` | Wrap `tiktoken` cl100k_base | Create |
| `backend/app/routers/compression.py` | `POST /api/issues/{id}/compress`, `GET /api/issues/{id}/summaries` | Create |
| `backend/app/hooks/executor.py` | Inject compressed summary when prompt > threshold | Modify |
| `backend/app/models/terminal_recording.py` | `TerminalRecording`, `TerminalFrame` models | Create |
| `backend/app/services/terminal_recorder.py` | Record stdin/stdout frames with timestamps, anchor to `ActivityLog` ids | Create |
| `backend/app/services/terminal_service.py` | Hook recorder into PTY read loop | Modify |
| `backend/app/routers/replays.py` | `GET /api/terminals/{id}/replay`, stream frames as JSON | Create |
| `frontend/src/features/terminals/components/ReplayPlayer.tsx` | xterm.js + timeline scrubber synced to events | Create |
| `backend/app/services/health_score.py` | `HealthScoreService.compute(project_id)` → 0–100 | Create |
| `backend/app/routers/health_score.py` | `GET /api/projects/{id}/health-score` | Create |
| `frontend/src/features/dashboard/components/HealthGauge.tsx` | Radial gauge with breakdown tooltip | Create |
| `backend/app/models/prompt_experiment.py` | `PromptTemplate`, `PromptVariant`, `PromptAssignment` models | Create |
| `backend/app/services/prompt_experiments.py` | `PromptExperiments.pick_variant(name)` — weighted random, record assignment | Create |
| `backend/app/services/prompt_experiments.py` | `record_outcome(assignment_id, success: bool)` + `stats(name)` | Create |
| `backend/app/routers/experiments.py` | CRUD experiments, `GET /api/experiments/{name}/stats` | Create |
| `frontend/src/routes/experiments.tsx` | Experiments dashboard with variant table + winner highlight | Create |
| `backend/alembic/versions/xxxx_tier3.py` | Migration for all new tables | Create |
| `backend/tests/test_context_compressor.py` | Unit tests for compressor | Create |
| `backend/tests/test_terminal_recorder.py` | Unit tests for recording/replay | Create |
| `backend/tests/test_health_score.py` | Unit tests for score computation | Create |
| `backend/tests/test_prompt_experiments.py` | Unit tests for variant selection + statistics | Create |

---

## Phase 1: Foundational Migration

### Task 1.1: Alembic migration for Tier 3 tables

**Files:**
- Create: `backend/alembic/versions/20260417_tier3.py`

- [ ] **Step 1: Generate skeleton**

```bash
cd backend && python -m alembic revision -m "tier3 experimental features"
```

- [ ] **Step 2: Write migration body**

```python
"""tier3 experimental features

Revision ID: 20260417_tier3
Revises: <prev>
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260417_tier3"
down_revision = "<prev>"

def upgrade() -> None:
    op.create_table(
        "context_summaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("issue_id", sa.Integer, sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("source_frames", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_context_summaries_issue_id", "context_summaries", ["issue_id"])

    op.create_table(
        "terminal_recordings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("terminal_id", sa.String(64), nullable=False, index=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("issue_id", sa.Integer, sa.ForeignKey("issues.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "terminal_frames",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recording_id", sa.Integer, sa.ForeignKey("terminal_recordings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offset_ms", sa.Integer, nullable=False),
        sa.Column("channel", sa.String(8), nullable=False),  # "in" | "out"
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("activity_id", sa.Integer, sa.ForeignKey("activity_logs.id"), nullable=True),
    )
    op.create_index("ix_terminal_frames_recording_id", "terminal_frames", ["recording_id"])

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "prompt_variants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.UniqueConstraint("template_id", "label", name="uq_variant_label"),
    )
    op.create_table(
        "prompt_assignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("prompt_templates.id"), nullable=False),
        sa.Column("variant_id", sa.Integer, sa.ForeignKey("prompt_variants.id"), nullable=False),
        sa.Column("issue_id", sa.Integer, sa.ForeignKey("issues.id"), nullable=True),
        sa.Column("success", sa.Boolean, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prompt_assignments_template_id", "prompt_assignments", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_prompt_assignments_template_id", "prompt_assignments")
    op.drop_table("prompt_assignments")
    op.drop_table("prompt_variants")
    op.drop_table("prompt_templates")
    op.drop_index("ix_terminal_frames_recording_id", "terminal_frames")
    op.drop_table("terminal_frames")
    op.drop_table("terminal_recordings")
    op.drop_index("ix_context_summaries_issue_id", "context_summaries")
    op.drop_table("context_summaries")
```

- [ ] **Step 3: Apply migration**

Run: `cd backend && python -m alembic upgrade head`
Expected: OK, `alembic_version` advanced.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/20260417_tier3.py
git commit -m "feat(db): add tier3 tables (compression, recordings, experiments)"
```

---

## Phase 2: Context Compression

Goal: when the prompt Claude receives (project description + issue body + recent activity + RAG context) exceeds a configurable token budget, replace the oldest chunk with a summary produced by Claude itself. Summaries persist per issue and are reused.

### Task 2.1: Token counter wrapper

**Files:**
- Create: `backend/app/services/token_counter.py`
- Test: `backend/tests/test_token_counter.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_token_counter.py
from app.services.token_counter import count_tokens

def test_count_tokens_empty():
    assert count_tokens("") == 0

def test_count_tokens_stable():
    assert count_tokens("hello world") == count_tokens("hello world")

def test_count_tokens_positive_for_text():
    assert count_tokens("The quick brown fox jumps over the lazy dog") > 5
```

- [ ] **Step 2: Run — expect FAIL (module missing)**

Run: `cd backend && python -m pytest tests/test_token_counter.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/services/token_counter.py
from functools import lru_cache
import tiktoken

@lru_cache(maxsize=1)
def _encoder():
    return tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_encoder().encode(text))
```

- [ ] **Step 4: Add tiktoken dep**

Modify `backend/pyproject.toml` dependencies: add `"tiktoken>=0.7.0"`.
Run: `cd backend && pip install tiktoken`

- [ ] **Step 5: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_token_counter.py -v`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/token_counter.py backend/tests/test_token_counter.py backend/pyproject.toml
git commit -m "feat(tokens): wrap tiktoken cl100k_base counter"
```

### Task 2.2: ContextSummary model

**Files:**
- Create: `backend/app/models/compression.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Model file**

```python
# backend/app/models/compression.py
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class ContextSummary(Base):
    __tablename__ = "context_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    source_frames: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    issue = relationship("Issue")
```

- [ ] **Step 2: Register in package**

Edit `backend/app/models/__init__.py` — add `from .compression import ContextSummary`.

- [ ] **Step 3: Verify import**

Run: `cd backend && python -c "from app.models import ContextSummary; print(ContextSummary.__tablename__)"`
Expected: `context_summaries`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/compression.py backend/app/models/__init__.py
git commit -m "feat(models): add ContextSummary"
```

### Task 2.3: Compressor service

**Files:**
- Create: `backend/app/services/context_compressor.py`
- Test: `backend/tests/test_context_compressor.py`

Strategy: caller passes a list of `ContextChunk(text, kind, created_at)`. Compressor:
1. Counts tokens per chunk.
2. If sum < budget → returns input.
3. Otherwise trims oldest chunks until under budget, sends a summarization prompt to Claude for the trimmed portion, persists as `ContextSummary`, and returns `[ContextSummary(...)] + kept_chunks`.

- [ ] **Step 1: Failing test with fake summarizer**

```python
# backend/tests/test_context_compressor.py
import pytest
from app.services.context_compressor import ContextCompressor, ContextChunk

class FakeSummarizer:
    async def summarize(self, text: str) -> str:
        return f"SUMMARY({len(text)})"

async def test_below_budget_returns_input(db_session):
    comp = ContextCompressor(db=db_session, summarizer=FakeSummarizer(), budget_tokens=10_000)
    chunks = [ContextChunk("hello", "activity", None)]
    kept = await comp.maybe_compress(issue_id=1, chunks=chunks)
    assert kept == chunks

async def test_above_budget_compresses_oldest(db_session, monkeypatch):
    monkeypatch.setattr("app.services.context_compressor.count_tokens", lambda t: len(t))
    comp = ContextCompressor(db=db_session, summarizer=FakeSummarizer(), budget_tokens=12)
    chunks = [
        ContextChunk("a" * 10, "activity", None),
        ContextChunk("b" * 10, "activity", None),
    ]
    kept = await comp.maybe_compress(issue_id=1, chunks=chunks)
    assert len(kept) == 2
    assert kept[0].kind == "summary"
    assert "SUMMARY" in kept[0].text
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_context_compressor.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/services/context_compressor.py
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.compression import ContextSummary
from app.services.token_counter import count_tokens

@dataclass
class ContextChunk:
    text: str
    kind: str  # "activity" | "rag" | "summary" | "base"
    created_at: datetime | None

class Summarizer(Protocol):
    async def summarize(self, text: str) -> str: ...

SYSTEM_PROMPT = (
    "You compress project management context for an AI assistant. "
    "Preserve decisions, blockers, and anchor facts. Drop greetings and filler. "
    "Return a compact paragraph."
)

class ClaudeSummarizer:
    def __init__(self, executor):
        self._executor = executor

    async def summarize(self, text: str) -> str:
        prompt = f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{text}\n\nSUMMARY:"
        return await self._executor.run_once(prompt=prompt, allow_tools=False)

class ContextCompressor:
    def __init__(self, db: AsyncSession, summarizer: Summarizer, budget_tokens: int = 12_000):
        self._db = db
        self._summarizer = summarizer
        self._budget = budget_tokens

    async def maybe_compress(self, issue_id: int, chunks: list[ContextChunk]) -> list[ContextChunk]:
        total = sum(count_tokens(c.text) for c in chunks)
        if total <= self._budget:
            return chunks
        # Trim oldest until <= 60% of budget, then summarize.
        target = int(self._budget * 0.6)
        kept: list[ContextChunk] = []
        running = 0
        for chunk in reversed(chunks):
            t = count_tokens(chunk.text)
            if running + t > target:
                break
            kept.append(chunk)
            running += t
        kept.reverse()
        trimmed = chunks[: len(chunks) - len(kept)]
        if not trimmed:
            return kept
        raw = "\n\n".join(f"[{c.kind}] {c.text}" for c in trimmed)
        summary_text = await self._summarizer.summarize(raw)
        summary = ContextSummary(
            issue_id=issue_id,
            summary=summary_text,
            token_count=count_tokens(summary_text),
            source_frames=[c.kind for c in trimmed],
        )
        self._db.add(summary)
        await self._db.flush()
        return [ContextChunk(text=summary_text, kind="summary", created_at=summary.created_at), *kept]
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_context_compressor.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/context_compressor.py backend/tests/test_context_compressor.py
git commit -m "feat(compression): context compressor with token-budget LRU trim"
```

### Task 2.4: Wire into ClaudeCodeExecutor

**Files:**
- Modify: `backend/app/hooks/executor.py`
- Test: `backend/tests/test_executor_compression.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_executor_compression.py
from app.hooks.executor import build_prompt_chunks

async def test_build_prompt_chunks_pulls_activity(db_session, seed_issue_with_activity):
    chunks = await build_prompt_chunks(db_session, issue_id=seed_issue_with_activity.id)
    kinds = [c.kind for c in chunks]
    assert "base" in kinds
    assert "activity" in kinds
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_executor_compression.py -v`

- [ ] **Step 3: Add `build_prompt_chunks` helper**

Add to `backend/app/hooks/executor.py`:

```python
from app.services.context_compressor import ContextChunk
from app.models import Issue, ActivityLog
from sqlalchemy import select

async def build_prompt_chunks(db, issue_id: int) -> list[ContextChunk]:
    issue = (await db.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
    chunks = [ContextChunk(text=f"Issue: {issue.title}\n{issue.description or ''}", kind="base", created_at=issue.created_at)]
    rows = (await db.execute(
        select(ActivityLog).where(ActivityLog.issue_id == issue_id).order_by(ActivityLog.created_at.asc())
    )).scalars().all()
    for r in rows:
        chunks.append(ContextChunk(text=r.message or "", kind="activity", created_at=r.created_at))
    return chunks
```

- [ ] **Step 4: Thread compressor into `ClaudeCodeExecutor.run_hook`**

Inside `run_hook`, before building the subprocess command:

```python
from app.services.context_compressor import ContextCompressor, ClaudeSummarizer
from app.services.settings_service import get_int_setting

budget = await get_int_setting(self._db, "context.budget_tokens", default=12_000)
if budget > 0 and ctx.issue_id:
    comp = ContextCompressor(self._db, ClaudeSummarizer(self), budget_tokens=budget)
    chunks = await build_prompt_chunks(self._db, ctx.issue_id)
    chunks = await comp.maybe_compress(ctx.issue_id, chunks)
    ctx.extra_context = "\n\n".join(c.text for c in chunks)
```

- [ ] **Step 5: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_executor_compression.py -v`

- [ ] **Step 6: Commit**

```bash
git add backend/app/hooks/executor.py backend/tests/test_executor_compression.py
git commit -m "feat(executor): compress prompt context when over budget"
```

### Task 2.5: Compression router

**Files:**
- Create: `backend/app/routers/compression.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_routers_compression.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_routers_compression.py
async def test_list_summaries_empty(client, seed_issue):
    r = await client.get(f"/api/issues/{seed_issue.id}/summaries")
    assert r.status_code == 200
    assert r.json() == []

async def test_manual_compress(client, seed_issue_with_activity, monkeypatch):
    async def fake_summarize(self, text): return "SHORT"
    from app.services.context_compressor import ClaudeSummarizer
    monkeypatch.setattr(ClaudeSummarizer, "summarize", fake_summarize)
    r = await client.post(f"/api/issues/{seed_issue_with_activity.id}/compress", json={"budget_tokens": 1})
    assert r.status_code == 200
    assert r.json()["summary"] == "SHORT"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_routers_compression.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/routers/compression.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models.compression import ContextSummary
from app.services.context_compressor import ContextCompressor, ClaudeSummarizer
from app.hooks.executor import ClaudeCodeExecutor, build_prompt_chunks

router = APIRouter(prefix="/api/issues", tags=["compression"])

class CompressRequest(BaseModel):
    budget_tokens: int = Field(gt=0, le=50_000)

class SummaryOut(BaseModel):
    id: int
    summary: str
    token_count: int
    source_frames: list
    class Config: from_attributes = True

@router.get("/{issue_id}/summaries", response_model=list[SummaryOut])
async def list_summaries(issue_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ContextSummary).where(ContextSummary.issue_id == issue_id).order_by(ContextSummary.created_at.desc())
    )).scalars().all()
    return rows

@router.post("/{issue_id}/compress", response_model=SummaryOut)
async def compress_now(issue_id: int, body: CompressRequest, db: AsyncSession = Depends(get_db)):
    executor = ClaudeCodeExecutor(db=db)
    comp = ContextCompressor(db, ClaudeSummarizer(executor), budget_tokens=body.budget_tokens)
    chunks = await build_prompt_chunks(db, issue_id)
    kept = await comp.maybe_compress(issue_id, chunks)
    summaries = [c for c in kept if c.kind == "summary"]
    if not summaries:
        raise HTTPException(status_code=400, detail="nothing to compress under budget")
    await db.commit()
    row = (await db.execute(
        select(ContextSummary).where(ContextSummary.issue_id == issue_id).order_by(ContextSummary.created_at.desc())
    )).scalars().first()
    return row
```

Register in `backend/app/main.py`:

```python
from app.routers import compression
app.include_router(compression.router)
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_routers_compression.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/compression.py backend/app/main.py backend/tests/test_routers_compression.py
git commit -m "feat(api): compression router (list + manual compress)"
```

### Task 2.6: Setting toggle + docs

**Files:**
- Modify: `backend/app/services/settings_service.py` (if defaults exist) or seed via migration

- [ ] **Step 1: Insert default rows**

Add to migration `downgrade` side (or a small data-migration) or simply document defaults. Create `backend/app/services/settings_defaults.py` if absent:

```python
DEFAULT_SETTINGS = {
    "context.budget_tokens": "12000",
    "context.compression_enabled": "false",
}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/settings_defaults.py
git commit -m "feat(settings): defaults for compression budget"
```

---

## Phase 3: Smart Terminal Replay

Goal: record every PTY session to disk, then replay it in-browser with a timeline synced to `ActivityLog` entries (hook fires, status transitions).

### Task 3.1: Terminal recording models

**Files:**
- Create: `backend/app/models/terminal_recording.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Model**

```python
# backend/app/models/terminal_recording.py
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, DateTime, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class TerminalRecording(Base):
    __tablename__ = "terminal_recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    terminal_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    frames = relationship("TerminalFrame", back_populates="recording", cascade="all, delete-orphan")

class TerminalFrame(Base):
    __tablename__ = "terminal_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("terminal_recordings.id", ondelete="CASCADE"), index=True)
    offset_ms: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(8))  # "in" | "out"
    data: Mapped[bytes] = mapped_column(LargeBinary)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activity_logs.id"), nullable=True)

    recording = relationship("TerminalRecording", back_populates="frames")
```

- [ ] **Step 2: Register**

Add imports in `backend/app/models/__init__.py`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/terminal_recording.py backend/app/models/__init__.py
git commit -m "feat(models): TerminalRecording + TerminalFrame"
```

### Task 3.2: Recorder service

**Files:**
- Create: `backend/app/services/terminal_recorder.py`
- Test: `backend/tests/test_terminal_recorder.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_terminal_recorder.py
import asyncio
from app.services.terminal_recorder import TerminalRecorder

async def test_records_frames(db_session):
    rec = TerminalRecorder(db=db_session, terminal_id="t1", project_id=None, issue_id=None)
    await rec.start()
    await rec.write("in", b"ls\n")
    await asyncio.sleep(0.01)
    await rec.write("out", b"file.txt\n")
    await rec.stop()
    assert rec.recording.finished_at is not None
    assert len(rec.recording.frames) == 2
    assert rec.recording.frames[0].channel == "in"
    assert rec.recording.frames[1].offset_ms >= rec.recording.frames[0].offset_ms
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_terminal_recorder.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/services/terminal_recorder.py
from __future__ import annotations
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.terminal_recording import TerminalRecording, TerminalFrame
from datetime import datetime

class TerminalRecorder:
    def __init__(self, db: AsyncSession, terminal_id: str, project_id: int | None, issue_id: int | None):
        self._db = db
        self._terminal_id = terminal_id
        self._project_id = project_id
        self._issue_id = issue_id
        self._start_monotonic: float | None = None
        self.recording: TerminalRecording | None = None

    async def start(self) -> None:
        self.recording = TerminalRecording(
            terminal_id=self._terminal_id,
            project_id=self._project_id,
            issue_id=self._issue_id,
        )
        self._db.add(self.recording)
        await self._db.flush()
        self._start_monotonic = time.monotonic()

    async def write(self, channel: str, data: bytes, activity_id: int | None = None) -> None:
        assert self.recording is not None and self._start_monotonic is not None
        offset = int((time.monotonic() - self._start_monotonic) * 1000)
        frame = TerminalFrame(
            recording_id=self.recording.id,
            offset_ms=offset,
            channel=channel,
            data=data,
            activity_id=activity_id,
        )
        self._db.add(frame)
        self.recording.frames.append(frame)
        await self._db.flush()

    async def stop(self) -> None:
        if self.recording is None:
            return
        self.recording.finished_at = datetime.utcnow()
        await self._db.flush()
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_terminal_recorder.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/terminal_recorder.py backend/tests/test_terminal_recorder.py
git commit -m "feat(terminal): recorder service with frame offsets"
```

### Task 3.3: Wire recorder into TerminalService

**Files:**
- Modify: `backend/app/services/terminal_service.py`

- [ ] **Step 1: Inject recorder on session start**

Find the `spawn` or `start_session` method. After PTY is created:

```python
self._recorder = TerminalRecorder(db=self._db, terminal_id=term_id, project_id=project_id, issue_id=issue_id)
await self._recorder.start()
```

- [ ] **Step 2: Capture stdin path**

Inside the WebSocket message handler where user input reaches PTY:

```python
await self._recorder.write("in", data_bytes)
pty.write(data_bytes)
```

- [ ] **Step 3: Capture stdout path**

Inside the PTY read loop (thread or asyncio task that pushes output to client):

```python
chunk = pty.read(4096)
if chunk:
    asyncio.run_coroutine_threadsafe(self._recorder.write("out", chunk), loop)
    await ws.send_bytes(chunk)
```

- [ ] **Step 4: Stop on close**

Add to cleanup:

```python
try:
    await self._recorder.stop()
except Exception:
    logger.exception("failed to stop recorder")
```

- [ ] **Step 5: Smoke test**

Run: `cd backend && python -m pytest tests/test_routers_terminals.py -v` (ensure existing tests still pass).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/terminal_service.py
git commit -m "feat(terminal): record every PTY session"
```

### Task 3.4: Anchor frames to ActivityLog

**Files:**
- Modify: `backend/app/services/activity_service.py`
- Modify: `backend/app/services/terminal_service.py`

- [ ] **Step 1: Expose latest activity id**

In `activity_service.py`, ensure the `log` function returns the created row id.

- [ ] **Step 2: Bridge via hook listener**

In `terminal_service.py`, when an `ActivityLog` is created that references this terminal's `issue_id`, emit a zero-length anchor frame:

```python
async def on_activity(self, activity_id: int):
    await self._recorder.write("out", b"", activity_id=activity_id)
```

Register via `HookRegistry` on `HookEvent.ACTIVITY_CREATED` (add event if missing in `hooks/events.py`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/activity_service.py backend/app/services/terminal_service.py backend/app/hooks/events.py
git commit -m "feat(terminal): anchor frames to activity log ids"
```

### Task 3.5: Replay router

**Files:**
- Create: `backend/app/routers/replays.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_routers_replays.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_routers_replays.py
async def test_replay_returns_frames(client, seed_recording):
    r = await client.get(f"/api/recordings/{seed_recording.id}/replay")
    assert r.status_code == 200
    payload = r.json()
    assert payload["terminal_id"] == seed_recording.terminal_id
    assert len(payload["frames"]) > 0
    assert payload["frames"][0]["channel"] in {"in", "out"}
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_routers_replays.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/routers/replays.py
import base64
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models.terminal_recording import TerminalRecording

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

@router.get("/{recording_id}/replay")
async def replay(recording_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(TerminalRecording).options(selectinload(TerminalRecording.frames)).where(TerminalRecording.id == recording_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404)
    frames = sorted(row.frames, key=lambda f: f.offset_ms)
    return {
        "id": row.id,
        "terminal_id": row.terminal_id,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "frames": [
            {
                "offset_ms": f.offset_ms,
                "channel": f.channel,
                "data_b64": base64.b64encode(f.data).decode("ascii"),
                "activity_id": f.activity_id,
            }
            for f in frames
        ],
    }
```

Register in `main.py`:

```python
from app.routers import replays
app.include_router(replays.router)
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_routers_replays.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/replays.py backend/app/main.py backend/tests/test_routers_replays.py
git commit -m "feat(api): recording replay endpoint"
```

### Task 3.6: Replay player UI

**Files:**
- Create: `frontend/src/features/terminals/components/ReplayPlayer.tsx`
- Create: `frontend/src/features/terminals/api/replays.ts`
- Create: `frontend/src/routes/recordings.$id.tsx`

- [ ] **Step 1: API client**

```typescript
// frontend/src/features/terminals/api/replays.ts
import { apiGet } from "@/shared/api/client";

export type ReplayFrame = {
  offset_ms: number;
  channel: "in" | "out";
  data_b64: string;
  activity_id: number | null;
};
export type Replay = {
  id: number;
  terminal_id: string;
  started_at: string | null;
  finished_at: string | null;
  frames: ReplayFrame[];
};
export const getReplay = (id: number) => apiGet<Replay>(`/api/recordings/${id}/replay`);
```

- [ ] **Step 2: Player component**

```tsx
// frontend/src/features/terminals/components/ReplayPlayer.tsx
import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import type { Replay, ReplayFrame } from "../api/replays";

function decode(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export function ReplayPlayer({ replay }: { replay: Replay }) {
  const ref = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const [position, setPosition] = useState(0);
  const [playing, setPlaying] = useState(false);
  const duration = replay.frames.at(-1)?.offset_ms ?? 0;

  useEffect(() => {
    if (!ref.current) return;
    const term = new Terminal({ convertEol: true, theme: { background: "#111" } });
    term.open(ref.current);
    termRef.current = term;
    return () => term.dispose();
  }, []);

  useEffect(() => {
    if (!termRef.current) return;
    termRef.current.clear();
    for (const f of replay.frames) {
      if (f.offset_ms > position) break;
      if (f.channel === "out") termRef.current.write(decode(f.data_b64));
    }
  }, [position, replay.frames]);

  useEffect(() => {
    if (!playing) return;
    const start = performance.now() - position;
    let raf = 0;
    const tick = () => {
      const next = performance.now() - start;
      setPosition(next);
      if (next >= duration) {
        setPlaying(false);
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, duration, position]);

  return (
    <div className="flex flex-col gap-2">
      <div ref={ref} className="h-[400px] w-full" />
      <div className="flex items-center gap-2">
        <button onClick={() => setPlaying(p => !p)} className="px-2 py-1 rounded bg-zinc-800 text-white">
          {playing ? "Pause" : "Play"}
        </button>
        <input
          type="range"
          min={0}
          max={duration}
          value={position}
          onChange={e => setPosition(Number(e.target.value))}
          className="flex-1"
        />
        <span className="tabular-nums text-xs text-zinc-400">{Math.floor(position / 1000)}s / {Math.floor(duration / 1000)}s</span>
      </div>
      <ActivityMarkers frames={replay.frames} position={position} />
    </div>
  );
}

function ActivityMarkers({ frames, position }: { frames: ReplayFrame[]; position: number }) {
  const markers = frames.filter(f => f.activity_id !== null);
  return (
    <ul className="text-xs">
      {markers.map(m => (
        <li key={`${m.offset_ms}-${m.activity_id}`} className={m.offset_ms <= position ? "text-emerald-400" : "text-zinc-500"}>
          @ {Math.floor(m.offset_ms / 1000)}s — activity #{m.activity_id}
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: Route**

```tsx
// frontend/src/routes/recordings.$id.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { getReplay } from "@/features/terminals/api/replays";
import { ReplayPlayer } from "@/features/terminals/components/ReplayPlayer";

export const Route = createFileRoute("/recordings/$id")({
  component: Page,
});

function Page() {
  const { id } = Route.useParams();
  const { data, isLoading } = useQuery({
    queryKey: ["replay", id],
    queryFn: () => getReplay(Number(id)),
  });
  if (isLoading || !data) return <div className="p-6">Loading replay…</div>;
  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold mb-2">Replay #{data.id} — {data.terminal_id}</h1>
      <ReplayPlayer replay={data} />
    </div>
  );
}
```

- [ ] **Step 4: Smoke check**

Run `npm run dev`, open `/recordings/<id>` for a recorded session. Verify playback, scrubbing, activity markers turning green in sync.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/terminals/api/replays.ts frontend/src/features/terminals/components/ReplayPlayer.tsx frontend/src/routes/recordings.$id.tsx
git commit -m "feat(ui): terminal replay player with activity markers"
```

---

## Phase 4: Project Health Score

Goal: compute a 0–100 score for a project combining four weighted signals: velocity, hook success rate, stuck-issue penalty, and test coverage (from optional `coverage.xml`).

### Task 4.1: Health score service

**Files:**
- Create: `backend/app/services/health_score.py`
- Test: `backend/tests/test_health_score.py`

Signal weights (total = 1.0):
- velocity (issues finished / week, normalized to [0,1] at 10/week) — 0.35
- hook success rate (successful runs / total) — 0.25
- stuck penalty — 0.25 (1.0 if none > 3 days; linearly decays to 0 if any > 14 days)
- coverage — 0.15 (0.0 if unknown/<50%, 1.0 at >=90%)

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_health_score.py
from app.services.health_score import HealthScoreService

async def test_all_green(db_session, seed_finished_issues_this_week):
    svc = HealthScoreService(db_session)
    score = await svc.compute(project_id=1)
    assert score["total"] >= 80
    assert "velocity" in score["signals"]

async def test_stuck_issue_penalizes(db_session, seed_stuck_issue):
    svc = HealthScoreService(db_session)
    score = await svc.compute(project_id=1)
    assert score["signals"]["stuck"] < 0.5

async def test_no_data_not_crash(db_session):
    svc = HealthScoreService(db_session)
    score = await svc.compute(project_id=99)
    assert 0 <= score["total"] <= 100
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_health_score.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/services/health_score.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Issue, ActivityLog
from app.models.issue import IssueStatus

WEIGHTS = {"velocity": 0.35, "hook_success": 0.25, "stuck": 0.25, "coverage": 0.15}

class HealthScoreService:
    def __init__(self, db: AsyncSession, coverage_path: Path | None = None):
        self._db = db
        self._coverage_path = coverage_path

    async def compute(self, project_id: int) -> dict:
        v = await self._velocity(project_id)
        h = await self._hook_success(project_id)
        s = await self._stuck(project_id)
        c = self._coverage()
        total = 100 * (WEIGHTS["velocity"] * v + WEIGHTS["hook_success"] * h + WEIGHTS["stuck"] * s + WEIGHTS["coverage"] * c)
        return {
            "total": round(total, 1),
            "signals": {"velocity": round(v, 3), "hook_success": round(h, 3), "stuck": round(s, 3), "coverage": round(c, 3)},
            "weights": WEIGHTS,
        }

    async def _velocity(self, project_id: int) -> float:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        q = select(func.count()).select_from(Issue).where(
            Issue.project_id == project_id,
            Issue.status == IssueStatus.FINISHED,
            Issue.updated_at >= since,
        )
        n = (await self._db.execute(q)).scalar_one()
        return min(1.0, n / 10.0)

    async def _hook_success(self, project_id: int) -> float:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        q = select(ActivityLog.kind, func.count()).where(
            ActivityLog.project_id == project_id,
            ActivityLog.created_at >= since,
            ActivityLog.kind.in_(["hook_success", "hook_failure"]),
        ).group_by(ActivityLog.kind)
        rows = (await self._db.execute(q)).all()
        counts = dict(rows)
        total = counts.get("hook_success", 0) + counts.get("hook_failure", 0)
        if total == 0:
            return 1.0
        return counts.get("hook_success", 0) / total

    async def _stuck(self, project_id: int) -> float:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=3)
        max_allowed = now - timedelta(days=14)
        q = select(Issue.updated_at).where(
            Issue.project_id == project_id,
            Issue.status.in_([IssueStatus.NEW, IssueStatus.REASONING, IssueStatus.PLANNED, IssueStatus.ACCEPTED]),
            Issue.updated_at < threshold,
        )
        rows = (await self._db.execute(q)).scalars().all()
        if not rows:
            return 1.0
        oldest = min(rows)
        if oldest <= max_allowed:
            return 0.0
        span = (threshold - max_allowed).total_seconds()
        frac = (oldest - max_allowed).total_seconds() / span
        return max(0.0, min(1.0, frac))

    def _coverage(self) -> float:
        if not self._coverage_path or not self._coverage_path.exists():
            return 0.0
        try:
            import xml.etree.ElementTree as ET
            root = ET.parse(self._coverage_path).getroot()
            rate = float(root.attrib.get("line-rate", "0"))
            if rate >= 0.9:
                return 1.0
            if rate <= 0.5:
                return 0.0
            return (rate - 0.5) / 0.4
        except Exception:
            return 0.0
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_health_score.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/health_score.py backend/tests/test_health_score.py
git commit -m "feat(health): weighted project health score service"
```

### Task 4.2: Health score router

**Files:**
- Create: `backend/app/routers/health_score.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_routers_health_score.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_routers_health_score.py
async def test_health_score_endpoint(client, seed_project):
    r = await client.get(f"/api/projects/{seed_project.id}/health-score")
    assert r.status_code == 200
    body = r.json()
    assert "total" in body and "signals" in body and "weights" in body
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_routers_health_score.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/routers/health_score.py
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.health_score import HealthScoreService
from app.core.config import settings

router = APIRouter(prefix="/api/projects", tags=["health"])

@router.get("/{project_id}/health-score")
async def health_score(project_id: int, db: AsyncSession = Depends(get_db)):
    coverage = Path(settings.data_dir) / "coverage.xml"
    svc = HealthScoreService(db, coverage_path=coverage)
    return await svc.compute(project_id)
```

Register in `main.py`:

```python
from app.routers import health_score
app.include_router(health_score.router)
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_routers_health_score.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/health_score.py backend/app/main.py backend/tests/test_routers_health_score.py
git commit -m "feat(api): project health score endpoint"
```

### Task 4.3: Health gauge UI

**Files:**
- Create: `frontend/src/features/dashboard/api/health.ts`
- Create: `frontend/src/features/dashboard/components/HealthGauge.tsx`
- Modify: `frontend/src/routes/projects.$id.tsx` (or wherever dashboard lives)

- [ ] **Step 1: API client**

```typescript
// frontend/src/features/dashboard/api/health.ts
import { apiGet } from "@/shared/api/client";

export type HealthScore = {
  total: number;
  signals: { velocity: number; hook_success: number; stuck: number; coverage: number };
  weights: Record<string, number>;
};
export const getHealthScore = (projectId: number) =>
  apiGet<HealthScore>(`/api/projects/${projectId}/health-score`);
```

- [ ] **Step 2: Gauge component**

```tsx
// frontend/src/features/dashboard/components/HealthGauge.tsx
import { useQuery } from "@tanstack/react-query";
import { getHealthScore } from "../api/health";
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from "recharts";

export function HealthGauge({ projectId }: { projectId: number }) {
  const { data } = useQuery({ queryKey: ["health", projectId], queryFn: () => getHealthScore(projectId) });
  if (!data) return null;
  const color = data.total >= 75 ? "#10b981" : data.total >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex flex-col items-center">
      <div className="h-[200px] w-[200px] relative">
        <ResponsiveContainer>
          <RadialBarChart innerRadius="70%" outerRadius="90%" data={[{ v: data.total, fill: color }]} startAngle={90} endAngle={-270}>
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar background dataKey="v" cornerRadius={10} />
          </RadialBarChart>
        </ResponsiveContainer>
        <span className="absolute inset-0 grid place-items-center text-3xl font-semibold tabular-nums">
          {data.total.toFixed(0)}
        </span>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 text-xs text-zinc-500">
        {Object.entries(data.signals).map(([k, v]) => (
          <div key={k} className="flex gap-1">
            <dt className="capitalize">{k.replace("_", " ")}</dt>
            <dd className="tabular-nums">{(v * 100).toFixed(0)}%</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
```

- [ ] **Step 3: Mount on dashboard**

Insert `<HealthGauge projectId={project.id} />` on the project dashboard route.

- [ ] **Step 4: Smoke check**

Run `npm run dev`, verify gauge shows and breakdown renders.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/dashboard/api/health.ts frontend/src/features/dashboard/components/HealthGauge.tsx frontend/src/routes/projects.$id.tsx
git commit -m "feat(ui): health score gauge + signal breakdown"
```

---

## Phase 5: Prompt A/B Testing

Goal: version-control hook prompt templates, randomly assign variants per execution, record outcome (success/latency), then surface winner via statistics.

### Task 5.1: Models

**Files:**
- Create: `backend/app/models/prompt_experiment.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Model**

```python
# backend/app/models/prompt_experiment.py
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, Float, Boolean, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    variants = relationship("PromptVariant", back_populates="template", cascade="all, delete-orphan")

class PromptVariant(Base):
    __tablename__ = "prompt_variants"
    __table_args__ = (UniqueConstraint("template_id", "label", name="uq_variant_label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("prompt_templates.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(64))
    body: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    template = relationship("PromptTemplate", back_populates="variants")

class PromptAssignment(Base):
    __tablename__ = "prompt_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("prompt_templates.id"), index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("prompt_variants.id"))
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Register in `__init__.py`, commit**

```bash
git add backend/app/models/prompt_experiment.py backend/app/models/__init__.py
git commit -m "feat(models): prompt experiments (template/variant/assignment)"
```

### Task 5.2: Experiments service — variant picker

**Files:**
- Create: `backend/app/services/prompt_experiments.py`
- Test: `backend/tests/test_prompt_experiments.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_prompt_experiments.py
import pytest
from app.services.prompt_experiments import PromptExperiments

async def test_pick_variant_respects_weights(db_session, seed_template_with_variants, monkeypatch):
    monkeypatch.setattr("app.services.prompt_experiments.random.random", lambda: 0.1)
    svc = PromptExperiments(db_session)
    variant, assignment = await svc.pick_variant("reasoning", issue_id=1)
    assert variant.label == "A"  # 0.1 < weight_A / total
    assert assignment.variant_id == variant.id

async def test_pick_variant_missing_template_raises(db_session):
    svc = PromptExperiments(db_session)
    with pytest.raises(LookupError):
        await svc.pick_variant("does-not-exist", issue_id=None)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_prompt_experiments.py -v`

- [ ] **Step 3: Implement picker**

```python
# backend/app/services/prompt_experiments.py
from __future__ import annotations
import random
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prompt_experiment import PromptTemplate, PromptVariant, PromptAssignment

class PromptExperiments:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def pick_variant(self, name: str, issue_id: int | None) -> tuple[PromptVariant, PromptAssignment]:
        row = (await self._db.execute(
            select(PromptTemplate).options(selectinload(PromptTemplate.variants)).where(PromptTemplate.name == name, PromptTemplate.active.is_(True))
        )).scalar_one_or_none()
        if row is None or not row.variants:
            raise LookupError(f"no active template named {name!r}")
        total = sum(v.weight for v in row.variants)
        if total <= 0:
            raise ValueError("variant weights sum to 0")
        r = random.random() * total
        acc = 0.0
        pick = row.variants[0]
        for v in row.variants:
            acc += v.weight
            if r <= acc:
                pick = v
                break
        assignment = PromptAssignment(template_id=row.id, variant_id=pick.id, issue_id=issue_id)
        self._db.add(assignment)
        await self._db.flush()
        return pick, assignment

    async def record_outcome(self, assignment_id: int, success: bool, latency_ms: int | None = None) -> None:
        row = (await self._db.execute(
            select(PromptAssignment).where(PromptAssignment.id == assignment_id)
        )).scalar_one()
        row.success = success
        row.latency_ms = latency_ms
        await self._db.flush()

    async def stats(self, name: str) -> dict:
        tpl = (await self._db.execute(
            select(PromptTemplate).options(selectinload(PromptTemplate.variants)).where(PromptTemplate.name == name)
        )).scalar_one_or_none()
        if tpl is None:
            raise LookupError(name)
        assigns = (await self._db.execute(
            select(PromptAssignment).where(PromptAssignment.template_id == tpl.id)
        )).scalars().all()
        by_variant: dict[int, list[PromptAssignment]] = {v.id: [] for v in tpl.variants}
        for a in assigns:
            by_variant.setdefault(a.variant_id, []).append(a)
        report = []
        for v in tpl.variants:
            rows = by_variant.get(v.id, [])
            n = len(rows)
            scored = [r for r in rows if r.success is not None]
            successes = sum(1 for r in scored if r.success)
            rate = successes / len(scored) if scored else 0.0
            latencies = [r.latency_ms for r in scored if r.latency_ms is not None]
            mean_latency = sum(latencies) / len(latencies) if latencies else None
            report.append({
                "variant_id": v.id,
                "label": v.label,
                "n": n,
                "scored": len(scored),
                "success_rate": round(rate, 3),
                "mean_latency_ms": int(mean_latency) if mean_latency is not None else None,
            })
        winner = max((r for r in report if r["scored"] >= 20), key=lambda r: r["success_rate"], default=None)
        return {"template": name, "variants": report, "winner_label": winner["label"] if winner else None}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_prompt_experiments.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/prompt_experiments.py backend/tests/test_prompt_experiments.py
git commit -m "feat(experiments): variant picker + outcome + stats"
```

### Task 5.3: Outcome recording + stats tests

**Files:**
- Modify: `backend/tests/test_prompt_experiments.py`

- [ ] **Step 1: Add tests**

```python
async def test_record_outcome_and_stats(db_session, seed_template_with_variants):
    svc = PromptExperiments(db_session)
    v, a = await svc.pick_variant("reasoning", issue_id=None)
    await svc.record_outcome(a.id, success=True, latency_ms=1200)
    stats = await svc.stats("reasoning")
    assert any(r["scored"] == 1 and r["success_rate"] == 1.0 for r in stats["variants"])
```

- [ ] **Step 2: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_prompt_experiments.py -v`

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_prompt_experiments.py
git commit -m "test(experiments): outcome recording + stats shape"
```

### Task 5.4: Wire experiments into ClaudeCodeExecutor

**Files:**
- Modify: `backend/app/hooks/executor.py`

- [ ] **Step 1: Swap template source**

Inside the run path where a hook constructs its system prompt, look up the template name (existing hook registration should carry `prompt_template: str | None`):

```python
from app.services.prompt_experiments import PromptExperiments

assignment_id: int | None = None
if hook.prompt_template:
    try:
        svc = PromptExperiments(self._db)
        variant, assignment = await svc.pick_variant(hook.prompt_template, issue_id=ctx.issue_id)
        prompt_body = variant.body.format(**ctx.template_vars())
        assignment_id = assignment.id
    except LookupError:
        prompt_body = hook.default_prompt
else:
    prompt_body = hook.default_prompt
```

- [ ] **Step 2: Record outcome after subprocess returns**

```python
import time
started = time.monotonic()
try:
    result = await self._run_subprocess(prompt_body, ctx)
    success = result.returncode == 0
finally:
    latency_ms = int((time.monotonic() - started) * 1000)
    if assignment_id is not None:
        try:
            await PromptExperiments(self._db).record_outcome(assignment_id, success=success, latency_ms=latency_ms)
        except Exception:
            logger.exception("failed to record experiment outcome")
```

- [ ] **Step 3: Extend `HookContext.template_vars()`**

Add to `app/hooks/context.py`:

```python
def template_vars(self) -> dict[str, str]:
    return {
        "issue_title": self.issue.title if self.issue else "",
        "issue_description": self.issue.description if self.issue else "",
        "issue_id": str(self.issue.id) if self.issue else "",
        "project_name": self.project.name if self.project else "",
    }
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/hooks/executor.py backend/app/hooks/context.py
git commit -m "feat(executor): route hook prompts through experiment picker"
```

### Task 5.5: Experiments router

**Files:**
- Create: `backend/app/routers/experiments.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_routers_experiments.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_routers_experiments.py
async def test_list_and_stats(client, seed_template_with_variants):
    r = await client.get("/api/experiments")
    assert r.status_code == 200
    assert any(t["name"] == "reasoning" for t in r.json())

    r = await client.get("/api/experiments/reasoning/stats")
    assert r.status_code == 200
    assert "variants" in r.json()

async def test_create_variant(client, seed_template_with_variants):
    r = await client.post("/api/experiments/reasoning/variants", json={"label": "C", "body": "v3", "weight": 0.5})
    assert r.status_code == 201
    assert r.json()["label"] == "C"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && python -m pytest tests/test_routers_experiments.py -v`

- [ ] **Step 3: Implement**

```python
# backend/app/routers/experiments.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models.prompt_experiment import PromptTemplate, PromptVariant
from app.services.prompt_experiments import PromptExperiments

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

class VariantIn(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    body: str = Field(min_length=1)
    weight: float = Field(gt=0)

class VariantOut(BaseModel):
    id: int
    label: str
    body: str
    weight: float
    class Config: from_attributes = True

class TemplateOut(BaseModel):
    id: int
    name: str
    description: str | None
    active: bool
    variants: list[VariantOut]
    class Config: from_attributes = True

@router.get("", response_model=list[TemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(PromptTemplate).options(selectinload(PromptTemplate.variants))
    )).scalars().all()
    return rows

@router.post("/{name}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED)
async def create_variant(name: str, body: VariantIn, db: AsyncSession = Depends(get_db)):
    tpl = (await db.execute(select(PromptTemplate).where(PromptTemplate.name == name))).scalar_one_or_none()
    if tpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    v = PromptVariant(template_id=tpl.id, label=body.label, body=body.body, weight=body.weight)
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v

@router.get("/{name}/stats")
async def stats(name: str, db: AsyncSession = Depends(get_db)):
    try:
        return await PromptExperiments(db).stats(name)
    except LookupError:
        raise HTTPException(status_code=404)
```

Register in `main.py`.

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && python -m pytest tests/test_routers_experiments.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/experiments.py backend/app/main.py backend/tests/test_routers_experiments.py
git commit -m "feat(api): experiments router (list, create variant, stats)"
```

### Task 5.6: Experiments UI

**Files:**
- Create: `frontend/src/features/experiments/api/experiments.ts`
- Create: `frontend/src/routes/experiments.tsx`

- [ ] **Step 1: API client**

```typescript
// frontend/src/features/experiments/api/experiments.ts
import { apiGet, apiPost } from "@/shared/api/client";

export type Variant = { id: number; label: string; body: string; weight: number };
export type Template = { id: number; name: string; description: string | null; active: boolean; variants: Variant[] };
export type Stats = {
  template: string;
  variants: { variant_id: number; label: string; n: number; scored: number; success_rate: number; mean_latency_ms: number | null }[];
  winner_label: string | null;
};

export const listTemplates = () => apiGet<Template[]>("/api/experiments");
export const getStats = (name: string) => apiGet<Stats>(`/api/experiments/${encodeURIComponent(name)}/stats`);
export const createVariant = (name: string, body: Omit<Variant, "id">) =>
  apiPost<Variant>(`/api/experiments/${encodeURIComponent(name)}/variants`, body);
```

- [ ] **Step 2: Route + page**

```tsx
// frontend/src/routes/experiments.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { listTemplates, getStats } from "@/features/experiments/api/experiments";

export const Route = createFileRoute("/experiments")({ component: Page });

function Page() {
  const { data: templates } = useQuery({ queryKey: ["experiments"], queryFn: listTemplates });
  return (
    <div className="p-6 space-y-8">
      <h1 className="text-xl font-semibold">Prompt Experiments</h1>
      {templates?.map(t => <TemplateBlock key={t.id} name={t.name} />)}
    </div>
  );
}

function TemplateBlock({ name }: { name: string }) {
  const { data } = useQuery({ queryKey: ["experiments", name], queryFn: () => getStats(name) });
  if (!data) return null;
  return (
    <section>
      <h2 className="font-medium mb-2">{name} {data.winner_label && <span className="text-emerald-500 text-xs">winner: {data.winner_label}</span>}</h2>
      <table className="w-full text-sm">
        <thead className="text-zinc-500">
          <tr><th className="text-left">Variant</th><th>n</th><th>scored</th><th>success</th><th>avg latency</th></tr>
        </thead>
        <tbody>
          {data.variants.map(v => (
            <tr key={v.variant_id} className={v.label === data.winner_label ? "bg-emerald-950/30" : ""}>
              <td>{v.label}</td>
              <td className="text-center tabular-nums">{v.n}</td>
              <td className="text-center tabular-nums">{v.scored}</td>
              <td className="text-center tabular-nums">{(v.success_rate * 100).toFixed(0)}%</td>
              <td className="text-center tabular-nums">{v.mean_latency_ms ?? "—"} ms</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 3: Smoke check**

Run `npm run dev`, open `/experiments`. Verify table renders for each template.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/experiments/api/experiments.ts frontend/src/routes/experiments.tsx
git commit -m "feat(ui): experiments dashboard with winner highlighting"
```

---

## Phase 6: Observability + Feature Flags

### Task 6.1: Feature flags via settings

**Files:**
- Modify: `backend/app/services/settings_defaults.py`

- [ ] **Step 1: Add flags**

```python
DEFAULT_SETTINGS.update({
    "feature.context_compression": "false",
    "feature.terminal_recording": "true",
    "feature.health_score": "true",
    "feature.prompt_experiments": "false",
})
```

- [ ] **Step 2: Guard each feature at its entry point**

- Compressor: skip when `feature.context_compression == "false"`
- Recorder: skip `start()` when `feature.terminal_recording == "false"`
- Health score endpoint: return 404 when flag off
- Experiments picker: fall back to `hook.default_prompt` when flag off

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/settings_defaults.py backend/app/hooks/executor.py backend/app/services/terminal_service.py backend/app/routers/health_score.py
git commit -m "feat(tier3): feature flags for all experimental features"
```

### Task 6.2: Expose flags to frontend

**Files:**
- Modify: `backend/app/routers/settings.py` (or equivalent config route)
- Modify: `frontend/src/shared/api/features.ts` (create if missing)

- [ ] **Step 1: GET /api/features**

```python
@router.get("/api/features")
async def features(db: AsyncSession = Depends(get_db)):
    keys = [
        "feature.context_compression", "feature.terminal_recording",
        "feature.health_score", "feature.prompt_experiments",
    ]
    out = {}
    for k in keys:
        out[k.replace("feature.", "")] = (await get_bool_setting(db, k, default=False))
    return out
```

- [ ] **Step 2: `useFeatures()` hook frontend**

```tsx
// frontend/src/shared/api/features.ts
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";

export type Features = {
  context_compression: boolean;
  terminal_recording: boolean;
  health_score: boolean;
  prompt_experiments: boolean;
};
export const useFeatures = () => useQuery({ queryKey: ["features"], queryFn: () => apiGet<Features>("/api/features") });
```

Wrap Tier 3 UI entries with `features?.xxx` checks.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/settings.py frontend/src/shared/api/features.ts
git commit -m "feat(features): expose feature flags endpoint + hook"
```

---

## Self-Review Checklist

After finishing all phases, walk through the list and confirm.

- [ ] Migration applies and rolls back cleanly on a fresh DB
- [ ] `context_compression` flag OFF → `ClaudeCodeExecutor` path unchanged (no compressor allocation, no DB write)
- [ ] `terminal_recording` flag OFF → no rows added to `terminal_recordings` during a 10s PTY session
- [ ] Replay player scrubs backwards without duplicating output (term is cleared before re-applying frames up to `position`)
- [ ] Health score never throws on a fresh project with zero activity
- [ ] Experiments weights honored when `random.random()` is mocked to boundary values (0.0, just above A weight, 1.0)
- [ ] Stats endpoint returns `winner_label: null` until variants have ≥20 scored assignments
- [ ] All new routers registered in `main.py` and show up in `GET /docs`
- [ ] Feature flag OFF → corresponding router returns 404 (not 500)
- [ ] No new N+1 queries — `selectinload` used on relationship access
- [ ] No SQL string interpolation anywhere new — parameterized via SQLAlchemy only
- [ ] Recording capture does not block PTY read loop (write scheduled on event loop via `run_coroutine_threadsafe`)
- [ ] `ContextCompressor` persists summary + source_frames so audit is possible
- [ ] Typescript: `frontend` compiles (`npm run lint` passes) and features guard conditionally render

---

## Execution

Estimated effort:
- Phase 1 (migration): 30 min
- Phase 2 (compression): 3–4 h
- Phase 3 (terminal replay): 4–5 h
- Phase 4 (health score): 2–3 h
- Phase 5 (experiments): 4–5 h
- Phase 6 (flags): 1 h

**Total: ~15–18 hours.** Phases 2–5 are independent and can be parallelized across subagents. Phase 6 depends on 2–5 landing first.

Recommended execution path: Phase 1 → ship Phase 4 first (smallest, validates the flag pattern) → then 3 → 5 → 2 → 6.
