# Security & Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close known security gaps (SQL injection, unenforced secret masking, orphan subprocesses, loose shell validation) and land high-impact quick wins across backend and frontend (React error boundaries, aria labels, configurable timeouts, RAG retry, API helper deduplication).

**Architecture:** Each phase is an independent, shippable improvement. No phase depends on another; execute in any order. All changes are TDD where practical (tests first for backend logic, manual verification for UI-only changes).

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async (SQLite/aiosqlite), LanceDB, pytest-asyncio (`asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`), React 19, TanStack Router, TanStack Query, Tailwind CSS 4, shadcn/radix-ui.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/rag/store.py` | Modify | Parameterized LanceDB queries |
| `backend/app/hooks/executor.py` | Modify | Subprocess lifecycle (SIGTERM on timeout) |
| `backend/app/hooks/registry.py` | Modify | Make `HOOK_TIMEOUT` read from settings |
| `backend/app/config.py` | Modify | Add `hook_timeout_seconds`, `terminal_max_buffer_bytes` |
| `backend/app/services/terminal_service.py` | Modify | Read buffer size from settings |
| `backend/app/services/project_variable_service.py` | Modify | Mask `is_secret=True` values in list responses |
| `backend/app/routers/project_variables.py` | Modify | Never return `value` for secrets on list endpoint |
| `backend/app/routers/terminals.py` | Modify | Structured condition parsing + allowlist |
| `backend/app/services/rag_service.py` | Modify | Retry + status persistence |
| `backend/app/models/project_file.py` | Modify | `embedding_status` column |
| `backend/app/models/issue.py` | Modify | `embedding_status` column |
| `backend/alembic/versions/<hash>_add_embedding_status.py` | Create | Migration for new columns |
| `backend/tests/test_rag_store.py` | Create/Modify | Tests for param-bound filters |
| `backend/tests/test_hooks_executor.py` | Modify | Test subprocess termination on timeout |
| `backend/tests/test_project_variable_service.py` | Modify | Test secret masking |
| `backend/tests/test_rag_service.py` | Modify | Test retry + status transitions |
| `frontend/src/shared/components/error-boundary.tsx` | Create | React error boundary component |
| `frontend/src/routes/__root.tsx` | Modify | Wrap children in ErrorBoundary |
| `frontend/src/shared/api/client.ts` | Modify | Expose `apiGet/apiPost/apiPatch/apiDelete` helpers |
| `frontend/src/features/projects/api*.ts` | Modify | Use new helpers (remove per-call boilerplate) |
| `frontend/src/features/issues/api.ts` | Modify | Use new helpers |
| `frontend/src/features/issues/components/kanban-board.tsx` | Modify | Add aria-label on drag handles + column regions |
| `frontend/src/features/issues/components/issue-detail.tsx` | Modify | Add aria-label on action buttons |
| `frontend/src/features/terminals/components/terminal-panel.tsx` | Modify | Add aria-label on control buttons |

---

## Phase 1: Parameterized LanceDB Filters

**Why:** `rag/store.py:54-56,68-72,103,132` use f-string interpolation for `source_id`, `project_id`, `chunk_id`. Although values are internally generated, string interpolation is a dangerous pattern — any future refactor risks exposure.

### Task 1.1: Add regression test for injection-shaped input

**Files:**
- Modify: `backend/tests/test_rag_store.py` (create if missing)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_rag_store.py
import pytest
from app.rag.store import VectorStore


@pytest.fixture
def store(tmp_path):
    return VectorStore(db_path=str(tmp_path / "lance"))


def _record(chunk_id: str, source_id: str, project_id: str, vector=None):
    return {
        "id": chunk_id,
        "project_id": project_id,
        "chunk_text": "hello",
        "vector": vector or [0.1] * 384,
        "source_type": "file",
        "source_id": source_id,
        "title": "t",
        "chunk_index": 0,
        "total_chunks": 1,
        "metadata": "{}",
        "created_at": "2026-01-01T00:00:00Z",
    }


def test_delete_by_source_ignores_injection_in_id(store):
    store.add([
        _record("c1", "safe", "p1"),
        _record("c2", "'; --", "p1"),
    ])
    store.delete_by_source("'; --")
    # Only the malicious-id row should be deleted; c1 must survive.
    all_rows = store._get_table().to_pandas()
    remaining_ids = set(all_rows["id"].tolist())
    assert "c1" in remaining_ids
    assert "c2" not in remaining_ids


def test_search_filters_by_project_literal(store):
    store.add([
        _record("c1", "s", "project-a"),
        _record("c2", "s", "project-b"),
    ])
    results = store.search([0.1] * 384, project_id="project-a")
    ids = {r["chunk_id"] for r in results}
    assert ids == {"c1"}
```

- [ ] **Step 2: Run test to verify it fails or passes (baseline)**

```bash
cd backend && python -m pytest tests/test_rag_store.py -v
```
Expected: passes today (LanceDB tolerates the input). This test pins behaviour so refactoring to parameterized queries cannot regress it.

- [ ] **Step 3: Commit baseline test**

```bash
git add backend/tests/test_rag_store.py
git commit -m "test(rag): pin VectorStore filter semantics against injection-shaped input"
```

### Task 1.2: Refactor to parameter binding

**Files:**
- Modify: `backend/app/rag/store.py:54-56,60-83,98-135`

- [ ] **Step 1: Replace f-string in `delete_by_source`**

```python
# backend/app/rag/store.py
def delete_by_source(self, source_id: str):
    table = self._get_table()
    # LanceDB supports parameter binding via the `?` placeholder.
    table.delete("source_id = ?", [source_id])
```

- [ ] **Step 2: Replace f-string in `search`**

```python
# backend/app/rag/store.py
def search(
    self,
    query_vector: list[float],
    project_id: str,
    source_type: str | None = None,
    limit: int = 5,
) -> list[dict]:
    table = self._get_table()
    where = "project_id = ?"
    params: list[str] = [project_id]
    if source_type:
        if source_type not in self.VALID_SOURCE_TYPES:
            return []
        where += " AND source_type = ?"
        params.append(source_type)

    try:
        results = (
            table.search(query_vector)
            .where(where, params)
            .metric("cosine")
            .limit(limit)
            .to_list()
        )
    except Exception:
        return []
    # ... (return block unchanged)
```

> If the installed LanceDB version does not expose parameter binding via `.where(sql, params)`, fall back to a **strict allowlist**: validate `project_id` and `source_id` against `^[A-Za-z0-9_\-]{1,64}$` before interpolating, and raise `ValueError` on mismatch. Keep the test from Task 1.1 — both implementations must pass it.

- [ ] **Step 3: Replace f-string in `get_chunk`**

```python
# backend/app/rag/store.py  — same pattern for the `id = ? AND project_id = ?` query
results = (
    table.search()
    .where("id = ? AND project_id = ?", [chunk_id, project_id])
    .limit(1)
    .to_list()
)
# ... siblings query:
siblings = (
    table.search()
    .where("source_id = ?", [source_id])
    .limit(1000)
    .to_list()
)
```

- [ ] **Step 4: Run full RAG test suite**

```bash
cd backend && python -m pytest tests/test_rag_store.py tests/test_rag_service.py tests/test_rag_pipeline.py -v
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/store.py
git commit -m "security(rag): parameter-bind LanceDB filter predicates"
```

---

## Phase 2: Subprocess Lifecycle on Hook Timeout

**Why:** `hooks/executor.py:100-106` catches `TimeoutExpired` but the underlying `claude` process may still be alive and holding file handles / MCP connections. `subprocess.run(timeout=…)` in a thread already tries to kill the child, but the parent `asyncio.wait_for` in `registry.py:94` can also trip, in which case the subprocess is never reaped. Add explicit process-group termination and assert it in tests.

### Task 2.1: Use `Popen` with explicit termination

**Files:**
- Modify: `backend/app/hooks/executor.py:25-122`

- [ ] **Step 1: Rewrite `_run` to use `Popen`**

```python
# backend/app/hooks/executor.py  (replace the _run function and try block)
import signal
import sys

def _run() -> tuple[int, bytes, bytes]:
    kwargs: dict = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "cwd": cwd,
        "env": env,
    }
    if sys.platform == "win32":
        # CREATE_NEW_PROCESS_GROUP lets us send CTRL_BREAK_EVENT to the whole tree.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True  # new POSIX process group

    proc = subprocess.Popen(cmd, **kwargs)
    try:
        stdout, stderr = proc.communicate(input=prompt_bytes, timeout=timeout)
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        _terminate_tree(proc)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        raise  # re-raise so the outer handler returns the timeout error


def _terminate_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        return
    # Escalate to SIGKILL if the tree ignores SIGTERM.
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if sys.platform == "win32":
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
```

- [ ] **Step 2: Update the outer try/except to use the new return shape**

```python
try:
    returncode, stdout_b, stderr_b = await asyncio.to_thread(_run)
    duration = time.monotonic() - start
    stdout = stdout_b.decode(errors="replace").strip()
    stderr = stderr_b.decode(errors="replace").strip()

    if returncode == 0:
        return ExecutorResult(success=True, output=stdout or None, duration=duration)
    return ExecutorResult(
        success=False,
        output=stdout or None,
        error=stderr or f"Process exited with code {returncode}",
        duration=duration,
    )
except subprocess.TimeoutExpired:
    # _run already terminated the tree before re-raising.
    duration = time.monotonic() - start
    return ExecutorResult(
        success=False,
        error=f"Claude Code process timed out after {timeout}s",
        duration=duration,
    )
# ... (FileNotFoundError and generic except unchanged)
```

- [ ] **Step 3: Add test covering termination behaviour**

```python
# backend/tests/test_hooks_executor.py  (append)
import sys
import pytest
from app.hooks.executor import ClaudeCodeExecutor


async def test_executor_times_out_and_reports_error(monkeypatch, tmp_path):
    # Replace the `claude` command with a shell that sleeps longer than the timeout.
    script = tmp_path / ("claude.bat" if sys.platform == "win32" else "claude")
    if sys.platform == "win32":
        script.write_text("@echo off\r\nping 127.0.0.1 -n 10 > nul\r\n")
    else:
        script.write_text("#!/bin/sh\nsleep 10\n")
        script.chmod(0o755)

    monkeypatch.setenv("PATH", str(tmp_path) + ("";" if sys.platform == "win32" else ":") + __import__("os").environ["PATH"])

    exec_ = ClaudeCodeExecutor()
    result = await exec_.run(prompt="hi", project_path=str(tmp_path), timeout=1)
    assert result.success is False
    assert "timed out" in (result.error or "")
```

- [ ] **Step 4: Run test**

```bash
cd backend && python -m pytest tests/test_hooks_executor.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/hooks/executor.py backend/tests/test_hooks_executor.py
git commit -m "security(hooks): SIGTERM claude subprocess tree on timeout"
```

---

## Phase 3: Configurable Timeouts & Buffer Sizes

**Why:** `HOOK_TIMEOUT = 300` (`registry.py:16`) and `MAX_BUFFER_SIZE = 100 * 1024` (`terminal_service.py:96`) are hardcoded. Long-running refactor hooks and high-throughput terminals need these configurable without a code change.

### Task 3.1: Add settings

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add fields**

```python
# backend/app/config.py  (inside Settings class)
hook_timeout_seconds: int = 300
terminal_max_buffer_bytes: int = 100 * 1024
```

### Task 3.2: Wire `HOOK_TIMEOUT` to settings

**Files:**
- Modify: `backend/app/hooks/registry.py:16,94`

- [ ] **Step 1: Replace constant with settings read**

```python
# backend/app/hooks/registry.py  (top of file)
from app.config import settings

# Remove: HOOK_TIMEOUT = 300
# Replace the asyncio.wait_for call:
result = await asyncio.wait_for(
    hook.execute(context), timeout=settings.hook_timeout_seconds
)
```

- [ ] **Step 2: Update the timeout-error message to include the actual value**

```python
error_msg = f"Hook timed out after {settings.hook_timeout_seconds}s"
```

- [ ] **Step 3: Update any test that imports `HOOK_TIMEOUT`**

```bash
cd backend && grep -rn "HOOK_TIMEOUT" tests/
```

Replace patches like `monkeypatch.setattr("app.hooks.registry.HOOK_TIMEOUT", 1)` with `monkeypatch.setattr(settings, "hook_timeout_seconds", 1)`.

- [ ] **Step 4: Run hook tests**

```bash
cd backend && python -m pytest tests/test_hook_registry.py -v
```
Expected: green.

### Task 3.3: Wire terminal buffer to settings

**Files:**
- Modify: `backend/app/services/terminal_service.py:96` (and every use of `MAX_BUFFER_SIZE`)

- [ ] **Step 1: Replace constant read**

```python
from app.config import settings

# Where MAX_BUFFER_SIZE was referenced:
max_buffer = settings.terminal_max_buffer_bytes
if len(buffer) > max_buffer:
    del buffer[: len(buffer) - max_buffer]
```

- [ ] **Step 2: Run terminal tests**

```bash
cd backend && python -m pytest tests/test_terminal_service.py -v
```
Expected: green.

- [ ] **Step 3: Commit both changes**

```bash
git add backend/app/config.py backend/app/hooks/registry.py backend/app/services/terminal_service.py backend/tests/
git commit -m "feat(config): make hook timeout and terminal buffer configurable"
```

---

## Phase 4: `is_secret` Enforcement

**Why:** `ProjectVariable.is_secret` exists but is not respected anywhere. Secrets leak via list endpoints, logs, and subprocess env inspection.

### Task 4.1: Mask on list response

**Files:**
- Modify: `backend/app/routers/project_variables.py` (list endpoint)
- Modify: `backend/app/schemas/project_variable.py` (if present — otherwise inline the response model)

- [ ] **Step 1: Add failing test**

```python
# backend/tests/test_project_variables_router.py  (append)
async def test_list_masks_secret_values(client, project):
    await client.post(f"/api/projects/{project.id}/variables", json={
        "name": "API_KEY", "value": "super-secret", "is_secret": True
    })
    resp = await client.get(f"/api/projects/{project.id}/variables")
    data = resp.json()
    secret = next(v for v in data if v["name"] == "API_KEY")
    assert secret["value"] == ""
    assert secret["has_value"] is True
    assert secret["is_secret"] is True
```

- [ ] **Step 2: Update router to mask**

```python
# backend/app/routers/project_variables.py
from app.schemas.project_variable import ProjectVariableRead

@router.get("", response_model=list[ProjectVariableRead])
async def list_variables(project_id: str, db: AsyncSession = Depends(get_session)):
    rows = await ProjectVariableService(db).list_for_project(project_id)
    return [
        ProjectVariableRead(
            id=r.id,
            name=r.name,
            value="" if r.is_secret else r.value,
            has_value=bool(r.value),
            is_secret=r.is_secret,
            sort_order=r.sort_order,
        )
        for r in rows
    ]
```

- [ ] **Step 3: Add `has_value: bool` to the schema if not already present**

```python
# backend/app/schemas/project_variable.py
class ProjectVariableRead(BaseModel):
    id: int
    name: str
    value: str
    has_value: bool
    is_secret: bool
    sort_order: int
```

- [ ] **Step 4: Add a secret-revealing endpoint for in-place edits**

```python
@router.get("/{variable_id}/reveal", response_model=ProjectVariableRead)
async def reveal_variable(project_id: str, variable_id: int, db: AsyncSession = Depends(get_session)):
    row = await ProjectVariableService(db).get(project_id, variable_id)
    if not row:
        raise HTTPException(404, "Not found")
    return ProjectVariableRead(
        id=row.id, name=row.name, value=row.value,
        has_value=bool(row.value), is_secret=row.is_secret, sort_order=row.sort_order,
    )
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_project_variables_router.py -v
```
Expected: green.

### Task 4.2: Mask in logs

**Files:**
- Modify: `backend/app/hooks/executor.py`
- Modify: anywhere that logs env vars (grep for `env_vars` usage)

- [ ] **Step 1: Add a redaction helper**

```python
# backend/app/hooks/executor.py  (top-level function)
def _redact_env(env_vars: dict | None, secret_names: set[str]) -> dict:
    if not env_vars:
        return {}
    return {k: ("***" if k in secret_names else v) for k, v in env_vars.items()}
```

Callers that want to log the env must pass `secret_names` (the set of `name`s of variables with `is_secret=True`). Any log statement that currently dumps `env_vars` directly — update it.

- [ ] **Step 2: Grep for env logging**

```bash
cd backend && grep -rn "env_vars\|environment" app/ | grep -iE "log|print"
```
Patch every match to use `_redact_env`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/project_variables.py backend/app/schemas/ backend/app/hooks/executor.py backend/tests/test_project_variables_router.py
git commit -m "security(variables): mask is_secret values in API responses and logs"
```

### Task 4.3: Frontend — show masked UI

**Files:**
- Modify: `frontend/src/features/projects/components/variables-table.tsx` (or equivalent)

- [ ] **Step 1: Render secrets as `••••••••` with a "Reveal" button**

```tsx
// frontend/src/features/projects/components/variables-table.tsx (excerpt)
{variable.is_secret && !revealed[variable.id] ? (
  <div className="flex items-center gap-2">
    <span className="font-mono tracking-wider">••••••••</span>
    <Button size="sm" variant="ghost" aria-label={`Reveal secret ${variable.name}`}
            onClick={() => revealSecret(variable.id)}>
      <Eye className="h-3.5 w-3.5" />
    </Button>
  </div>
) : (
  <span className="font-mono">{variable.value || "(empty)"}</span>
)}
```

- [ ] **Step 2: Fetch revealed value on demand via the new endpoint**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/projects/components/variables-table.tsx
git commit -m "feat(ui): mask secret project variables with reveal button"
```

---

## Phase 5: Shell Command Condition Parser

**Why:** `routers/terminals.py:24-32` currently matches condition strings with naive substring checks. Unknown syntax defaults to "execute", which is permissive. Replace with an explicit parser that rejects unknown forms.

### Task 5.1: Structured condition evaluator

**Files:**
- Create: `backend/app/services/terminal_condition.py`
- Modify: `backend/app/routers/terminals.py`

- [ ] **Step 1: Write failing tests first**

```python
# backend/tests/test_terminal_condition.py
import pytest
from app.services.terminal_condition import evaluate_condition, UnknownConditionError


def test_eq_true():
    assert evaluate_condition("$issue_status == Accepted", {"issue_status": "Accepted"}) is True

def test_eq_false():
    assert evaluate_condition("$issue_status == Accepted", {"issue_status": "New"}) is False

def test_ne():
    assert evaluate_condition("$issue_status != Canceled", {"issue_status": "New"}) is True

def test_empty_condition_passes():
    assert evaluate_condition("", {}) is True
    assert evaluate_condition(None, {}) is True

def test_unknown_variable_is_false():
    assert evaluate_condition("$nope == x", {}) is False

def test_unknown_operator_raises():
    with pytest.raises(UnknownConditionError):
        evaluate_condition("$issue_status matches Accepted", {"issue_status": "Accepted"})
```

- [ ] **Step 2: Run (expect fail — module missing)**

```bash
cd backend && python -m pytest tests/test_terminal_condition.py -v
```

- [ ] **Step 3: Implement**

```python
# backend/app/services/terminal_condition.py
from __future__ import annotations
import re

_CONDITION_RE = re.compile(r"^\s*\$(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<op>==|!=)\s*(?P<value>.+?)\s*$")


class UnknownConditionError(ValueError):
    """Raised when the condition cannot be parsed."""


def evaluate_condition(condition: str | None, variables: dict[str, str]) -> bool:
    if not condition or not condition.strip():
        return True
    match = _CONDITION_RE.match(condition)
    if not match:
        raise UnknownConditionError(f"Unparseable condition: {condition!r}")
    var = match.group("var")
    op = match.group("op")
    expected = match.group("value").strip().strip('"').strip("'")
    actual = variables.get(var)
    if actual is None:
        return False
    if op == "==":
        return actual == expected
    return actual != expected
```

- [ ] **Step 4: Run tests — all green**

```bash
cd backend && python -m pytest tests/test_terminal_condition.py -v
```

- [ ] **Step 5: Swap old parser in router**

```python
# backend/app/routers/terminals.py
from app.services.terminal_condition import evaluate_condition, UnknownConditionError

# Replace the old inline branch with:
try:
    passes = evaluate_condition(cmd.condition, variables)
except UnknownConditionError as exc:
    logger.warning("Skipping terminal command %s: %s", cmd.id, exc)
    continue
if not passes:
    continue
```

- [ ] **Step 6: Run terminal router tests**

```bash
cd backend && python -m pytest tests/test_terminal_router.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/terminal_condition.py backend/app/routers/terminals.py backend/tests/test_terminal_condition.py
git commit -m "security(terminals): strict parser for startup-command conditions"
```

---

## Phase 6: RAG Embedding Retry + Persistent Status

**Why:** `rag_service.py:84-95` logs failures but the client never sees them. Add an `embedding_status` column to both `project_files` and `issues`, persist transitions (`pending` → `running` → `completed` / `failed`), and add a single retry with exponential backoff.

### Task 6.1: Migration for new columns

**Files:**
- Modify: `backend/app/models/project_file.py`
- Modify: `backend/app/models/issue.py`
- Create: `backend/alembic/versions/<hash>_add_embedding_status.py` (via `--autogenerate`)

- [ ] **Step 1: Add column on both models**

```python
# backend/app/models/project_file.py  (inside ProjectFile)
embedding_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)
embedding_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

Repeat on `Issue`.

- [ ] **Step 2: Autogenerate migration**

```bash
cd backend && python -m alembic revision --autogenerate -m "add embedding_status to files and issues"
cd backend && python -m alembic upgrade head
```

Verify migration includes both `ALTER TABLE` statements.

### Task 6.2: Retry wrapper in RagService

**Files:**
- Modify: `backend/app/services/rag_service.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_rag_service.py  (append)
async def test_embed_file_retries_once_on_failure(db_session, monkeypatch):
    svc = RagService(...)
    calls = {"n": 0}

    def flaky(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return None

    monkeypatch.setattr(svc._pipeline, "embed_file", flaky)
    await svc.embed_file(project_file_id="f1", ...)
    assert calls["n"] == 2
    # Status should reflect success.
    file_row = await db_session.get(ProjectFile, "f1")
    assert file_row.embedding_status == "completed"


async def test_embed_file_marks_failed_after_exhausting_retries(db_session, monkeypatch):
    svc = RagService(...)
    monkeypatch.setattr(svc._pipeline, "embed_file", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("always fails")))
    await svc.embed_file(project_file_id="f1", ...)
    file_row = await db_session.get(ProjectFile, "f1")
    assert file_row.embedding_status == "failed"
    assert "always fails" in (file_row.embedding_error or "")
```

- [ ] **Step 2: Implement retry**

```python
# backend/app/services/rag_service.py  (inside embed_file)
from datetime import datetime, timezone
import asyncio

async def _set_status(self, session, model, pk, status: str, error: str | None = None):
    row = await session.get(model, pk)
    if row is None:
        return
    row.embedding_status = status
    row.embedding_error = error
    row.embedding_updated_at = datetime.now(timezone.utc)
    await session.commit()


async def embed_file(self, project_file_id: str, ...):
    async with async_session() as session:
        await self._set_status(session, ProjectFile, project_file_id, "running")

    last_error: str | None = None
    for attempt in (0, 1):  # one retry
        try:
            await asyncio.to_thread(self._pipeline.embed_file, ...)
            async with async_session() as session:
                await self._set_status(session, ProjectFile, project_file_id, "completed")
            await event_service.emit({"type": "embedding_completed", ...})
            return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc) or type(exc).__name__
            if attempt == 0:
                await asyncio.sleep(1.5)  # simple backoff

    async with async_session() as session:
        await self._set_status(session, ProjectFile, project_file_id, "failed", last_error)
    await event_service.emit({"type": "embedding_failed", "error": last_error, ...})
```

Apply the same shape to `embed_issue`.

- [ ] **Step 3: Run RAG tests**

```bash
cd backend && python -m pytest tests/test_rag_service.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/project_file.py backend/app/models/issue.py backend/alembic/versions/ backend/app/services/rag_service.py backend/tests/test_rag_service.py
git commit -m "feat(rag): persist embedding status with one automatic retry"
```

### Task 6.3: Frontend — show status badge

**Files:**
- Modify: `frontend/src/features/files/components/file-card.tsx`
- Modify: `frontend/src/features/issues/components/issue-list-item.tsx`

- [ ] **Step 1: Render a `Badge` for non-completed states**

```tsx
{file.embedding_status === "failed" && (
  <Badge variant="destructive" aria-label="Indicizzazione fallita">Indexing failed</Badge>
)}
{file.embedding_status === "running" && (
  <Badge variant="secondary">Indexing…</Badge>
)}
```

- [ ] **Step 2: Add retry button on failed rows** — posts to a new `POST /api/projects/{id}/files/{fid}/reindex` endpoint that sets status back to `pending` and re-spawns the embed task.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/files/components/file-card.tsx frontend/src/features/issues/components/issue-list-item.tsx
git commit -m "feat(ui): surface embedding status + retry on failed rows"
```

---

## Phase 7: React Error Boundary

**Why:** A runtime error in `issue-detail.tsx` (complex tab machinery) or `kanban-board.tsx` (drag-drop) currently crashes the whole app.

### Task 7.1: ErrorBoundary component

**Files:**
- Create: `frontend/src/shared/components/error-boundary.tsx`

- [ ] **Step 1: Implement**

```tsx
// frontend/src/shared/components/error-boundary.tsx
import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/shared/components/ui/button";

type Props = { children: ReactNode; fallback?: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;
    if (this.props.fallback) return this.props.fallback;
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 p-6">
        <h2 className="text-lg font-semibold">Something went wrong</h2>
        <p className="max-w-md text-center text-sm text-muted-foreground">
          {this.state.error.message}
        </p>
        <Button onClick={this.reset} aria-label="Retry rendering">Try again</Button>
      </div>
    );
  }
}
```

### Task 7.2: Wrap every route

**Files:**
- Modify: `frontend/src/routes/__root.tsx`

- [ ] **Step 1: Wrap `<Outlet />`**

```tsx
import { ErrorBoundary } from "@/shared/components/error-boundary";
// inside the route component:
<ErrorBoundary>
  <Outlet />
</ErrorBoundary>
```

- [ ] **Step 2: Wrap `IssueDetail` and `KanbanBoard` separately**

These two components are the most likely to throw. A local boundary isolates the blast radius so the sidebar keeps rendering.

- [ ] **Step 3: Manual verification**

```bash
cd frontend && npm run dev
```
Introduce a temporary `throw new Error("boom")` in `issue-detail.tsx`, open an issue, confirm only that pane shows the fallback UI. Remove the test throw before committing.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/components/error-boundary.tsx frontend/src/routes/__root.tsx frontend/src/features/issues/components/
git commit -m "feat(ui): wrap root outlet and heavy components in ErrorBoundary"
```

---

## Phase 8: ARIA Labels on Critical Controls

**Why:** The frontend audit found zero `aria-*` attributes. Start with the highest-leverage controls: action buttons on issues, kanban drag handles, terminal toolbar.

### Task 8.1: Issue action buttons

**Files:**
- Modify: `frontend/src/features/issues/components/issue-detail.tsx`

- [ ] **Step 1: Add `aria-label` to every `<Button>` that ships only an icon or terse text**

Examples — patch each button that is currently unlabelled:

```tsx
<Button aria-label="Accept issue" onClick={accept} ...>Accept</Button>
<Button aria-label="Cancel issue" onClick={cancel} ...>Cancel</Button>
<Button aria-label="Mark issue as finished" onClick={complete} ...>Complete</Button>
<Button aria-label="Delete issue" variant="destructive" onClick={deleteIssue} ...><Trash /></Button>
```

### Task 8.2: Kanban columns and cards

**Files:**
- Modify: `frontend/src/features/issues/components/kanban-board.tsx`

- [ ] **Step 1: Add `role="region"` + `aria-label` to each column**

```tsx
<div role="region" aria-label={`${status} column, ${items.length} issues`} ...>
```

- [ ] **Step 2: Add `aria-grabbed` / `aria-label` to the draggable card**

```tsx
<div role="article" aria-label={`Issue ${issue.name || issue.id}, status ${issue.status}`} ...>
```

### Task 8.3: Terminal controls

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx`

- [ ] **Step 1: Label icon buttons**

```tsx
<Button aria-label="Copy terminal selection" ...><Copy /></Button>
<Button aria-label="Search in terminal" ...><Search /></Button>
<Button aria-label="Download session recording" ...><Download /></Button>
```

- [ ] **Step 2: Commit all three tasks together**

```bash
git add frontend/src/features/issues/components/issue-detail.tsx frontend/src/features/issues/components/kanban-board.tsx frontend/src/features/terminals/components/terminal-panel.tsx
git commit -m "a11y: aria-label critical controls in issue, kanban, terminal"
```

---

## Phase 9: API Helper Deduplication

**Why:** Six `api-*.ts` files for projects repeat the same fetch boilerplate. Extract one helper per verb; call sites become one line.

### Task 9.1: Extract helpers

**Files:**
- Modify: `frontend/src/shared/api/client.ts`

- [ ] **Step 1: Add verb-specific helpers**

```ts
// frontend/src/shared/api/client.ts  (append)
export const apiGet = <T>(path: string, signal?: AbortSignal) =>
  request<T>(path, { method: "GET", signal });

export const apiPost = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body), signal });

export const apiPatch = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body), signal });

export const apiPut = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: "PUT", body: JSON.stringify(body), signal });

export const apiDelete = (path: string, signal?: AbortSignal) =>
  request<void>(path, { method: "DELETE", signal });
```

### Task 9.2: Migrate feature APIs

**Files:**
- Modify: `frontend/src/features/issues/api.ts`
- Modify: `frontend/src/features/projects/api*.ts`
- Modify: `frontend/src/features/terminals/api.ts`
- Modify: `frontend/src/features/files/api.ts`
- Modify: `frontend/src/features/activity/api.ts`
- Modify: `frontend/src/features/settings/api.ts`
- Modify: `frontend/src/features/library/api.ts`

- [ ] **Step 1: Grep call sites**

```bash
cd frontend && grep -rn "request<" src/features/
```

- [ ] **Step 2: Replace each call site**

Example transformation:

```ts
// before
export const fetchIssues = (projectId: string) =>
  request<Issue[]>(`/api/projects/${projectId}/issues`, { method: "GET" });

// after
import { apiGet } from "@/shared/api/client";
export const fetchIssues = (projectId: string) =>
  apiGet<Issue[]>(`/api/projects/${projectId}/issues`);
```

- [ ] **Step 3: Run full type check + lint**

```bash
cd frontend && npm run lint
```

- [ ] **Step 4: Manual verify** — open each feature page in dev (`npm run dev`), confirm list/detail/create still work.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/api/client.ts frontend/src/features/
git commit -m "refactor(ui): extract verb helpers, remove per-feature fetch boilerplate"
```

---

## Self-Review Checklist

- [ ] Every phase has at least one failing test before implementation (except UI-only changes where manual verification is called out).
- [ ] `config.py` constants wired to runtime reads — no lingering `HOOK_TIMEOUT = 300` references (grep confirms).
- [ ] All LanceDB `.where(` callsites use parameter binding or pass the allowlist validator.
- [ ] Secret masking verified by test and by UI screenshot.
- [ ] Error boundary manually tested with a forced throw.
- [ ] `grep -rn "request<" frontend/src/features/` returns empty after Phase 9.

---

## Execution

Each phase is independent. Recommended order by impact-per-hour:
1. Phase 1 (SQL injection) — 1 h
2. Phase 3 (configurable constants) — 1 h
3. Phase 7 (error boundary) — 1 h
4. Phase 2 (subprocess cleanup) — 2 h
5. Phase 4 (`is_secret`) — 3 h
6. Phase 5 (condition parser) — 2 h
7. Phase 8 (aria labels) — 1 h
8. Phase 9 (API helpers) — 3 h
9. Phase 6 (RAG retry + status) — 4 h

Total: ~18 hours for a single engineer.
