# Tier 1 Natural Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship six high-value features that extend the existing architecture in natural directions without introducing new paradigms: token/cost tracking per issue, Git integration (branch/PR linking + auto-complete on merge), reusable issue templates, an analytics dashboard, prompt replay/debug, and spec/plan/recap version history.

**Architecture:** Every phase leans on existing subsystems — the `ActivityLog` for analytics, the `ClaudeCodeExecutor` for prompt capture, `PromptTemplate` for templates, a new `IssueRevision` table for versioning, a new `ExecutorRun` table for prompt replay, a new `IssueMetric` table for tokens/cost, and optional Git CLI hooks. All six phases are independent.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async (SQLite/aiosqlite), Pydantic v2, React 19, TanStack Router, TanStack Query, Recharts, `gh` / `git` CLIs, pytest-asyncio (`asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/issue_metric.py` | Create | Per-issue token usage + cost rollup |
| `backend/app/models/executor_run.py` | Create | Full prompt/response capture |
| `backend/app/models/issue_revision.py` | Create | Spec/plan/recap version history |
| `backend/app/models/issue_template.py` | Create | Named templates for issue creation |
| `backend/app/models/git_link.py` | Create | Issue ↔ branch/PR linkage |
| `backend/alembic/versions/<hash>_tier1.py` | Create | Single migration for the new tables |
| `backend/app/hooks/executor.py` | Modify | Capture stdout/usage into `ExecutorRun`, emit `IssueMetric` |
| `backend/app/services/issue_service.py` | Modify | Snapshot revision on spec/plan/recap writes |
| `backend/app/services/git_service.py` | Create | `git` + `gh` wrappers |
| `backend/app/routers/metrics.py` | Create | `/api/projects/{id}/metrics` |
| `backend/app/routers/executor_runs.py` | Create | `/api/executor-runs` list + detail + replay |
| `backend/app/routers/revisions.py` | Create | `/api/issues/{id}/revisions` |
| `backend/app/routers/templates.py` | Create | CRUD for issue templates |
| `backend/app/routers/git.py` | Create | `/api/projects/{id}/git/*` |
| `backend/app/routers/analytics.py` | Create | Derived metrics (velocity, hook success rate) |
| `backend/app/mcp/server.py` | Modify | New tools: `use_issue_template`, `link_git_branch`, `record_token_usage` |
| `frontend/src/features/metrics/` | Create | Cost dashboard components |
| `frontend/src/features/analytics/` | Create | Charts + project health |
| `frontend/src/features/issues/components/issue-revisions-panel.tsx` | Create | Diff viewer |
| `frontend/src/features/issues/components/issue-templates-dialog.tsx` | Create | Pick template on create |
| `frontend/src/features/issues/components/git-link-panel.tsx` | Create | Branch + PR link UI |
| `frontend/src/features/executor/` | Create | Prompt replay UI |
| `frontend/src/routes/projects/$projectId/analytics.tsx` | Create | Analytics route |
| `frontend/src/routes/projects/$projectId/metrics.tsx` | Create | Cost route |

---

## Phase 1: Token/Cost Tracking per Issue

**Why:** Claude is the app's most expensive dependency. Teams need per-issue visibility so they can justify spend and spot runaway loops.

**Approach:** Run Claude Code with `--output-format stream-json`. The executor parses the final JSON line, which includes token counts. Persist each run on `ExecutorRun`, then roll up into `IssueMetric`.

### Task 1.1: Migration for `IssueMetric` + `ExecutorRun`

**Files:**
- Create: `backend/app/models/issue_metric.py`
- Create: `backend/app/models/executor_run.py`

- [ ] **Step 1: Models**

```python
# backend/app/models/issue_metric.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IssueMetric(Base):
    __tablename__ = "issue_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    runs: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

```python
# backend/app/models/executor_run.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ExecutorRun(Base):
    __tablename__ = "executor_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    issue_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True, index=True)
    hook_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tool_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Register + migrate**

```bash
cd backend && python -m alembic revision --autogenerate -m "add issue_metrics and executor_runs"
cd backend && python -m alembic upgrade head
```

### Task 1.2: Capture usage in `ClaudeCodeExecutor`

**Files:**
- Modify: `backend/app/hooks/executor.py`
- Create: `backend/app/services/metrics_service.py`

- [ ] **Step 1: Use `--output-format stream-json`**

```python
# backend/app/hooks/executor.py  (cmd list)
cmd = ["claude", "-p", "--output-format", "stream-json", "--allowedTools", "mcp__ManagerAi__*"]
```

- [ ] **Step 2: Parse the final `result` line**

```python
# backend/app/hooks/executor.py  (after successful run)
import json

def _parse_usage(stdout: str) -> dict:
    usage = {"input_tokens": 0, "output_tokens": 0,
             "cache_creation_tokens": 0, "cache_read_tokens": 0,
             "cost_usd": 0.0, "model": None}
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result":
            u = obj.get("usage", {})
            usage["input_tokens"] = u.get("input_tokens", 0)
            usage["output_tokens"] = u.get("output_tokens", 0)
            usage["cache_creation_tokens"] = u.get("cache_creation_input_tokens", 0)
            usage["cache_read_tokens"] = u.get("cache_read_input_tokens", 0)
            usage["cost_usd"] = obj.get("total_cost_usd", 0.0)
            usage["model"] = obj.get("model")
            break
    return usage
```

Attach to `ExecutorResult` via a new `usage: dict` field; hooks pass it through to `MetricsService.record_run`.

- [ ] **Step 3: Metrics service**

```python
# backend/app/services/metrics_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ExecutorRun, IssueMetric


class MetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_run(self, *, project_id: str, issue_id: str | None, hook_name: str | None,
                          prompt: str, tool_guidance: str | None,
                          stdout: str | None, stderr: str | None,
                          success: bool, duration_ms: int, usage: dict) -> ExecutorRun:
        run = ExecutorRun(
            project_id=project_id, issue_id=issue_id, hook_name=hook_name,
            prompt=prompt, tool_guidance=tool_guidance,
            stdout=stdout, stderr=stderr, success=success, duration_ms=duration_ms,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_creation_tokens=usage.get("cache_creation_tokens", 0),
            cache_read_tokens=usage.get("cache_read_tokens", 0),
            cost_usd=usage.get("cost_usd", 0.0),
            model=usage.get("model"),
        )
        self.db.add(run)
        if issue_id:
            await self._roll_up(project_id, issue_id, usage)
        await self.db.commit()
        return run

    async def _roll_up(self, project_id: str, issue_id: str, usage: dict) -> None:
        row = (await self.db.execute(
            select(IssueMetric).where(IssueMetric.issue_id == issue_id)
        )).scalar_one_or_none()
        if row is None:
            row = IssueMetric(project_id=project_id, issue_id=issue_id)
            self.db.add(row)
        row.input_tokens += usage.get("input_tokens", 0)
        row.output_tokens += usage.get("output_tokens", 0)
        row.cache_creation_tokens += usage.get("cache_creation_tokens", 0)
        row.cache_read_tokens += usage.get("cache_read_tokens", 0)
        row.cost_usd += usage.get("cost_usd", 0.0)
        row.runs += 1
```

- [ ] **Step 4: Test with a captured stream-json fixture**

```python
# backend/tests/test_metrics_service.py
async def test_record_run_rolls_up_into_issue_metric(db_session):
    svc = MetricsService(db_session)
    await svc.record_run(project_id="p", issue_id="i", hook_name="h",
                         prompt="hi", tool_guidance=None, stdout="ok", stderr=None,
                         success=True, duration_ms=500,
                         usage={"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.001})
    await svc.record_run(project_id="p", issue_id="i", hook_name="h",
                         prompt="hi", tool_guidance=None, stdout="ok", stderr=None,
                         success=True, duration_ms=500,
                         usage={"input_tokens": 200, "output_tokens": 80, "cost_usd": 0.003})
    from app.models import IssueMetric
    row = (await db_session.execute(__import__("sqlalchemy").select(IssueMetric))).scalar_one()
    assert row.input_tokens == 300
    assert row.output_tokens == 130
    assert round(row.cost_usd, 4) == 0.004
    assert row.runs == 2
```

### Task 1.3: Metrics router + UI

**Files:**
- Create: `backend/app/routers/metrics.py`
- Create: `frontend/src/features/metrics/` (page + hook + api)
- Create: `frontend/src/routes/projects/$projectId/metrics.tsx`

- [ ] **Step 1: Router**

```python
# backend/app/routers/metrics.py
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.database import get_session
from app.models import IssueMetric

router = APIRouter(prefix="/api/projects/{project_id}/metrics", tags=["metrics"])


@router.get("")
async def project_metrics(project_id: str, db=Depends(get_session)) -> dict:
    rows = (await db.execute(
        select(IssueMetric).where(IssueMetric.project_id == project_id)
    )).scalars().all()
    total_cost = sum(r.cost_usd for r in rows)
    total_tokens = sum(r.input_tokens + r.output_tokens for r in rows)
    per_issue = [
        {"issue_id": r.issue_id, "cost_usd": r.cost_usd,
         "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
         "runs": r.runs}
        for r in rows
    ]
    return {"total_cost_usd": total_cost, "total_tokens": total_tokens, "per_issue": per_issue}
```

- [ ] **Step 2: UI page**

```tsx
// frontend/src/routes/projects/$projectId/metrics.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/shared/api/client";

export const Route = createFileRoute("/projects/$projectId/metrics")({
  component: MetricsPage,
});

function MetricsPage() {
  const { projectId } = Route.useParams();
  const { data } = useQuery({
    queryKey: ["projects", projectId, "metrics"],
    queryFn: () => apiGet<{ total_cost_usd: number; total_tokens: number; per_issue: Array<{ issue_id: string; cost_usd: number; input_tokens: number; output_tokens: number; runs: number }> }>(`/api/projects/${projectId}/metrics`),
    refetchInterval: 30_000,
  });
  if (!data) return null;

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold">Cost & Tokens</h1>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-md border p-4">
          <div className="text-xs text-muted-foreground">Total cost</div>
          <div className="text-2xl font-semibold">${data.total_cost_usd.toFixed(4)}</div>
        </div>
        <div className="rounded-md border p-4">
          <div className="text-xs text-muted-foreground">Total tokens</div>
          <div className="text-2xl font-semibold">{data.total_tokens.toLocaleString()}</div>
        </div>
      </div>
      <table className="mt-6 w-full text-sm">
        <thead><tr><th className="text-left p-2">Issue</th><th>Runs</th><th>Input</th><th>Output</th><th>Cost</th></tr></thead>
        <tbody>
          {data.per_issue.map((m) => (
            <tr key={m.issue_id} className="border-t">
              <td className="p-2 font-mono text-xs">{m.issue_id}</td>
              <td className="text-center">{m.runs}</td>
              <td className="text-right">{m.input_tokens}</td>
              <td className="text-right">{m.output_tokens}</td>
              <td className="text-right">${m.cost_usd.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add backend/ frontend/
git commit -m "feat(metrics): per-issue token/cost tracking with project dashboard"
```

---

## Phase 2: Git Integration

**Why:** Issues and Git work are currently disconnected. Linking an issue to a branch/PR and auto-completing on merge removes a major source of manual status updates.

### Task 2.1: `GitLink` model + service

**Files:**
- Create: `backend/app/models/git_link.py`
- Create: `backend/app/services/git_service.py`

- [ ] **Step 1: Model**

```python
# backend/app/models/git_link.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class GitLink(Base):
    __tablename__ = "git_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    branch: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pr_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Git service wraps the CLIs**

```python
# backend/app/services/git_service.py
from __future__ import annotations
import asyncio
import json
import re
from dataclasses import dataclass


@dataclass
class PrInfo:
    number: int
    url: str
    state: str  # "open", "merged", "closed"


class GitService:
    @staticmethod
    async def current_branch(project_path: str) -> str | None:
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--abbrev-ref", "HEAD",
            cwd=project_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        return out.decode().strip()

    @staticmethod
    async def create_branch(project_path: str, name: str) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "git", "checkout", "-b", name,
            cwd=project_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    @staticmethod
    async def pr_for_branch(project_path: str, branch: str) -> PrInfo | None:
        proc = await asyncio.create_subprocess_exec(
            "gh", "pr", "list", "--head", branch, "--state", "all",
            "--json", "number,url,state",
            cwd=project_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        try:
            rows = json.loads(out.decode() or "[]")
        except json.JSONDecodeError:
            return None
        if not rows:
            return None
        row = rows[0]
        return PrInfo(number=row["number"], url=row["url"], state=row["state"].lower())

    @staticmethod
    def sanitize_branch_name(name: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9\-_/]+", "-", name.strip().lower())
        return s.strip("-")[:80] or "issue"
```

### Task 2.2: Poll PR status

**Files:**
- Modify: `backend/app/main.py` (add periodic task)

- [ ] **Step 1: Periodic PR sync**

```python
# backend/app/main.py  (inside lifespan — alongside activity purge)
from app.services.git_service import GitService
from app.models import GitLink, Issue, IssueStatus, Project

async def _pr_sync_loop():
    while True:
        await asyncio.sleep(60)
        try:
            async with async_session() as session:
                links = (await session.execute(select(GitLink).where(GitLink.pr_state != "merged"))).scalars().all()
                for link in links:
                    issue = await session.get(Issue, link.issue_id)
                    if not issue:
                        continue
                    project = await session.get(Project, issue.project_id)
                    if not project or not project.path or not link.branch:
                        continue
                    info = await GitService.pr_for_branch(project.path, link.branch)
                    if info:
                        link.pr_url = info.url
                        link.pr_state = info.state
                        link.pr_number = info.number
                        if info.state == "merged" and issue.status == IssueStatus.ACCEPTED:
                            from app.services.issue_service import IssueService
                            svc = IssueService(session)
                            try:
                                await svc.complete_issue(issue.id, recap=f"Auto-completed: PR #{info.number} merged.")
                            except Exception:
                                pass
                await session.commit()
        except Exception as exc:
            logger.error("PR sync failed: %s", exc)
```

### Task 2.3: Router + MCP tool + UI panel

**Files:**
- Create: `backend/app/routers/git.py`
- Modify: `backend/app/mcp/server.py`
- Create: `frontend/src/features/issues/components/git-link-panel.tsx`

- [ ] **Step 1: Router endpoints**

```python
# backend/app/routers/git.py
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_session
from app.models import GitLink, Issue, Project
from app.services.git_service import GitService

router = APIRouter(prefix="/api/issues/{issue_id}/git", tags=["git"])


@router.post("/link")
async def link_branch(issue_id: str, branch: str, db=Depends(get_session)) -> GitLink:
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "issue not found")
    link = GitLink(issue_id=issue_id, branch=branch)
    db.add(link)
    await db.commit()
    return link


@router.post("/branch")
async def create_branch(issue_id: str, db=Depends(get_session)) -> dict:
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "issue not found")
    project = await db.get(Project, issue.project_id)
    name = GitService.sanitize_branch_name(f"{issue.name or issue.id}")
    ok = await GitService.create_branch(project.path, name)
    if not ok:
        raise HTTPException(400, "git checkout failed")
    db.add(GitLink(issue_id=issue_id, branch=name))
    await db.commit()
    return {"branch": name}
```

- [ ] **Step 2: MCP tool**

```python
# backend/app/mcp/server.py
@mcp.tool(description=_tool_descriptions.get("link_git_branch", "Associate a git branch with an issue."))
async def link_git_branch(issue_id: str, branch: str) -> dict:
    async with async_session() as session:
        link = GitLink(issue_id=issue_id, branch=branch)
        session.add(link)
        await session.commit()
        return {"linked": True, "branch": branch}
```

- [ ] **Step 3: UI panel** — input field + "Create branch" button + "PR: #42 · open / merged" badge. Goes inside the `IssueActions` component.

- [ ] **Step 4: Commit**

```bash
git add backend/ frontend/
git commit -m "feat(git): issue-branch linking with auto-complete on PR merge"
```

---

## Phase 3: Issue Templates

**Why:** `PromptTemplate` already exists but is not wired into issue creation. Extending it with a dedicated `IssueTemplate` model (with default spec + plan + tech_stack hints) lets users start from known-good shells.

### Task 3.1: Model + router

**Files:**
- Create: `backend/app/models/issue_template.py`
- Create: `backend/app/routers/templates.py`

- [ ] **Step 1: Model**

```python
# backend/app/models/issue_template.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IssueTemplate(Base):
    __tablename__ = "issue_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="generic")  # bug, feature, refactor, chore
    default_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_spec: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_priority: Mapped[int] = mapped_column(default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Router**

```python
# backend/app/routers/templates.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.database import get_session
from app.models import IssueTemplate
from app.schemas.issue_template import IssueTemplateCreate, IssueTemplateRead

router = APIRouter(prefix="/api/issue-templates", tags=["templates"])


@router.get("", response_model=list[IssueTemplateRead])
async def list_templates(project_id: str | None = None, db=Depends(get_session)):
    q = select(IssueTemplate)
    if project_id:
        q = q.where((IssueTemplate.project_id == project_id) | (IssueTemplate.project_id.is_(None)))
    return (await db.execute(q)).scalars().all()


@router.post("", response_model=IssueTemplateRead)
async def create_template(payload: IssueTemplateCreate, db=Depends(get_session)):
    t = IssueTemplate(**payload.model_dump())
    db.add(t)
    await db.commit()
    return t


@router.delete("/{template_id}")
async def delete_template(template_id: str, db=Depends(get_session)):
    t = await db.get(IssueTemplate, template_id)
    if not t:
        raise HTTPException(404, "not found")
    await db.delete(t)
    await db.commit()
    return {"deleted": True}
```

### Task 3.2: Apply on issue create

**Files:**
- Modify: `backend/app/routers/issues.py`

- [ ] **Step 1: Accept `template_id` on create**

```python
# backend/app/schemas/issue.py
class IssueCreate(BaseModel):
    name: str | None = None
    description: str = Field(..., min_length=1)
    priority: int = 3
    template_id: str | None = None
```

- [ ] **Step 2: Service hydrates from template**

```python
# backend/app/services/issue_service.py  (in create)
if payload.template_id:
    template = await self.db.get(IssueTemplate, payload.template_id)
    if template:
        description = payload.description or template.default_description or ""
        # Write draft spec/plan straight into the issue
        issue.specification = template.default_spec
        issue.plan = template.default_plan
        if not payload.priority:
            issue.priority = template.default_priority
```

### Task 3.3: UI picker

**Files:**
- Create: `frontend/src/features/issues/components/issue-templates-dialog.tsx`
- Modify: `frontend/src/routes/projects/$projectId/issues/new.tsx`

- [ ] **Step 1: Picker dialog** — list templates (global + project-scoped), preview spec/plan, "Use template" button sets form fields.

- [ ] **Step 2: Manual verify** — create a template "bug report" with spec/plan skeleton, pick it on new issue, confirm fields prefilled.

- [ ] **Step 3: Commit**

```bash
git add backend/ frontend/
git commit -m "feat(templates): reusable issue templates with spec/plan skeletons"
```

---

## Phase 4: Analytics Dashboard

**Why:** The data is there (`ActivityLog`, `IssueMetric`, `ExecutorRun`) but not surfaced. A single analytics page turns operational telemetry into decision-making input.

### Task 4.1: Analytics router

**Files:**
- Create: `backend/app/routers/analytics.py`

- [ ] **Step 1: Endpoint returning aggregated metrics**

```python
# backend/app/routers/analytics.py
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.database import get_session
from app.models import ActivityLog, Issue, IssueStatus, ExecutorRun

router = APIRouter(prefix="/api/projects/{project_id}/analytics", tags=["analytics"])


@router.get("")
async def project_analytics(project_id: str, db=Depends(get_session)) -> dict:
    # Velocity: issues finished per week for the last 8 weeks
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=8)
    finished_rows = (await db.execute(
        select(ActivityLog.created_at)
        .where(ActivityLog.project_id == project_id)
        .where(ActivityLog.event_type == "issue_completed")
        .where(ActivityLog.created_at >= cutoff)
    )).scalars().all()
    weekly: dict[str, int] = {}
    for ts in finished_rows:
        week = ts.strftime("%G-W%V")
        weekly[week] = weekly.get(week, 0) + 1

    # Average time per transition
    avg_times = await _avg_transition_times(db, project_id, cutoff)

    # Hook success rate
    hook_runs = (await db.execute(
        select(ActivityLog.event_type)
        .where(ActivityLog.project_id == project_id)
        .where(ActivityLog.event_type.in_(["hook_completed", "hook_failed"]))
        .where(ActivityLog.created_at >= cutoff)
    )).scalars().all()
    completed = sum(1 for e in hook_runs if e == "hook_completed")
    failed = sum(1 for e in hook_runs if e == "hook_failed")
    hook_success_rate = completed / (completed + failed) if (completed + failed) else None

    # Bottleneck: issues stuck > 3 days in a non-terminal state
    stuck_cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    stuck = (await db.execute(
        select(Issue).where(Issue.project_id == project_id)
        .where(Issue.status.in_([IssueStatus.NEW, IssueStatus.REASONING, IssueStatus.PLANNED, IssueStatus.ACCEPTED]))
        .where(Issue.updated_at < stuck_cutoff)
    )).scalars().all()

    return {
        "velocity_per_week": weekly,
        "avg_transition_seconds": avg_times,
        "hook_success_rate": hook_success_rate,
        "stuck_issues": [{"id": i.id, "name": i.name, "status": i.status.value, "updated_at": i.updated_at.isoformat()} for i in stuck],
    }


async def _avg_transition_times(db, project_id: str, cutoff) -> dict[str, float]:
    # For each issue completed after cutoff, measure time between consecutive ActivityLog rows.
    # Implementation detail: group by issue, order by created_at, compute deltas per event sequence.
    # ...
    return {}  # keep empty in first pass; wire the pipeline, fill in a follow-up task
```

### Task 4.2: Analytics UI page

**Files:**
- Create: `frontend/src/routes/projects/$projectId/analytics.tsx`

- [ ] **Step 1: Page with Recharts**

```tsx
// frontend/src/routes/projects/$projectId/analytics.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { apiGet } from "@/shared/api/client";

export const Route = createFileRoute("/projects/$projectId/analytics")({
  component: AnalyticsPage,
});

function AnalyticsPage() {
  const { projectId } = Route.useParams();
  const { data } = useQuery({
    queryKey: ["projects", projectId, "analytics"],
    queryFn: () => apiGet<AnalyticsResponse>(`/api/projects/${projectId}/analytics`),
    refetchInterval: 60_000,
  });
  if (!data) return null;

  const velocity = Object.entries(data.velocity_per_week).map(([week, count]) => ({ week, count }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Analytics</h1>

      <section>
        <h2 className="text-sm font-medium mb-2">Velocity (issues finished / week)</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={velocity}>
              <XAxis dataKey="week" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="hsl(var(--primary))" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-md border p-4">
          <div className="text-xs text-muted-foreground">Hook success rate</div>
          <div className="text-2xl font-semibold">
            {data.hook_success_rate != null ? `${(data.hook_success_rate * 100).toFixed(0)}%` : "—"}
          </div>
        </div>
        <div className="rounded-md border p-4">
          <div className="text-xs text-muted-foreground">Stuck issues</div>
          <div className="text-2xl font-semibold">{data.stuck_issues.length}</div>
          <ul className="mt-2 space-y-1 text-sm">
            {data.stuck_issues.map((i) => (
              <li key={i.id} className="text-muted-foreground">{i.name || i.id} · {i.status}</li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}

interface AnalyticsResponse {
  velocity_per_week: Record<string, number>;
  avg_transition_seconds: Record<string, number>;
  hook_success_rate: number | null;
  stuck_issues: Array<{ id: string; name: string; status: string; updated_at: string }>;
}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/analytics.py frontend/src/routes/projects/$projectId/analytics.tsx
git commit -m "feat(analytics): velocity, hook success rate, stuck issue dashboard"
```

---

## Phase 5: Prompt Replay / Debug

**Why:** When Claude misbehaves (e.g., fails a hook or produces the wrong spec), engineers today have no way to inspect what exactly was sent. `ExecutorRun` already captures everything from Phase 1; surface it.

### Task 5.1: Router

**Files:**
- Create: `backend/app/routers/executor_runs.py`

- [ ] **Step 1: List + detail + replay**

```python
# backend/app/routers/executor_runs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from app.database import get_session
from app.models import ExecutorRun
from app.hooks.executor import ClaudeCodeExecutor

router = APIRouter(prefix="/api/executor-runs", tags=["executor-runs"])


@router.get("")
async def list_runs(project_id: str | None = None, issue_id: str | None = None,
                     limit: int = 50, db=Depends(get_session)):
    q = select(ExecutorRun).order_by(desc(ExecutorRun.created_at)).limit(limit)
    if project_id: q = q.where(ExecutorRun.project_id == project_id)
    if issue_id: q = q.where(ExecutorRun.issue_id == issue_id)
    return (await db.execute(q)).scalars().all()


@router.get("/{run_id}")
async def get_run(run_id: str, db=Depends(get_session)) -> ExecutorRun:
    run = await db.get(ExecutorRun, run_id)
    if not run:
        raise HTTPException(404, "not found")
    return run


@router.post("/{run_id}/replay")
async def replay_run(run_id: str, db=Depends(get_session)) -> dict:
    run = await db.get(ExecutorRun, run_id)
    if not run:
        raise HTTPException(404, "not found")
    # Replay in-place: re-use original prompt and tool guidance; do not touch hooks.
    from app.models import Project
    project = await db.get(Project, run.project_id)
    result = await ClaudeCodeExecutor().run(
        prompt=run.prompt, project_path=project.path if project else "",
        tool_guidance=run.tool_guidance or "",
    )
    return {"success": result.success, "output": result.output, "error": result.error}
```

### Task 5.2: UI

**Files:**
- Create: `frontend/src/features/executor/components/executor-runs-list.tsx`
- Create: `frontend/src/features/executor/components/executor-run-detail.tsx`
- Create: `frontend/src/routes/projects/$projectId/runs.tsx`

- [ ] **Step 1: List + detail split view**

Left pane: list of runs (hook_name, issue_id, cost, success, timestamp). Right pane: selected run with tabs `Prompt / Stdout / Stderr`, plus a "Replay" button.

```tsx
<Button aria-label="Replay this run" onClick={() => replay(run.id)}>
  <Play className="mr-2 h-4 w-4" />Replay
</Button>
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/executor_runs.py frontend/src/features/executor/ frontend/src/routes/projects/$projectId/runs.tsx
git commit -m "feat(executor): prompt replay and debug browser"
```

---

## Phase 6: Version History for Spec/Plan/Recap

**Why:** Every round of iteration on spec/plan overwrites the previous version. `IssueRevision` captures the history so users can diff and roll back.

### Task 6.1: Model + snapshotting

**Files:**
- Create: `backend/app/models/issue_revision.py`
- Modify: `backend/app/services/issue_service.py`

- [ ] **Step 1: Model**

```python
# backend/app/models/issue_revision.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IssueRevision(Base):
    __tablename__ = "issue_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(32), nullable=False)  # specification, plan, recap, description
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(64), default="claude")  # "claude" or "user"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Snapshot before each write**

```python
# backend/app/services/issue_service.py  (extract helper)
async def _snapshot(self, issue: Issue, field: str, new_value: str | None, author: str) -> None:
    previous = getattr(issue, field, None)
    if previous == new_value:
        return
    self.db.add(IssueRevision(issue_id=issue.id, field=field,
                              previous_value=previous, new_value=new_value, author=author))

# Call inside create_spec / edit_spec / create_plan / edit_plan / complete_issue / update (description) before assigning.
```

### Task 6.2: Router + UI diff

**Files:**
- Create: `backend/app/routers/revisions.py`
- Create: `frontend/src/features/issues/components/issue-revisions-panel.tsx`

- [ ] **Step 1: Router**

```python
# backend/app/routers/revisions.py
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from app.database import get_session
from app.models import IssueRevision

router = APIRouter(prefix="/api/issues/{issue_id}/revisions", tags=["revisions"])


@router.get("")
async def list_revisions(issue_id: str, db=Depends(get_session)):
    return (await db.execute(
        select(IssueRevision).where(IssueRevision.issue_id == issue_id).order_by(desc(IssueRevision.created_at))
    )).scalars().all()
```

- [ ] **Step 2: UI diff panel**

Use `diff` (npm package) to render inline additions/deletions between `previous_value` and `new_value`.

```bash
cd frontend && npm install diff
```

```tsx
// frontend/src/features/issues/components/issue-revisions-panel.tsx
import { diffLines } from "diff";

function RevisionDiff({ previous, next }: { previous: string; next: string }) {
  const parts = diffLines(previous || "", next || "");
  return (
    <pre className="rounded-md border bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
      {parts.map((part, i) => (
        <span key={i} className={
          part.added ? "bg-green-500/20 text-green-900" :
          part.removed ? "bg-red-500/20 text-red-900 line-through" : ""
        }>{part.value}</span>
      ))}
    </pre>
  );
}
```

- [ ] **Step 3: Add "Restore this version" button** — calls `PATCH /api/projects/{pid}/issues/{iid}` with the `previous_value`, creating a new revision in the process.

- [ ] **Step 4: Commit**

```bash
git add backend/ frontend/
git commit -m "feat(revisions): version history with diff viewer and restore"
```

---

## Self-Review Checklist

- [ ] `ExecutorRun` row created for every claude subprocess invocation (hook + MCP replay).
- [ ] Cost dashboard matches sum of individual run costs.
- [ ] PR sync loop does not flake under offline conditions (swallows CLI errors).
- [ ] Applying a template pre-fills description/spec/plan; leaving it out still works.
- [ ] Analytics page renders with empty data (no division by zero).
- [ ] Revision snapshot skipped when field value unchanged.

---

## Execution

Estimated effort:
1. Phase 1 (cost tracking) — 10 h
2. Phase 2 (git integration) — 12 h
3. Phase 3 (templates) — 4 h
4. Phase 4 (analytics) — 6 h
5. Phase 5 (prompt replay) — 6 h
6. Phase 6 (version history) — 5 h

Total: ~43 hours. Ship phase-by-phase; each is user-visible on its own.
