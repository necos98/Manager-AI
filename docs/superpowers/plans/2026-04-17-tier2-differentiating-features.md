# Tier 2 Differentiating Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the differentiating features that move Manager AI from "issue tracker with Claude integration" to "orchestration platform for AI-assisted development": multi-agent DAG orchestration, pre-finish auto-review, knowledge graph visualisation, ML-based duration estimation, webhook integration hub, real-time presence, and project snapshot/export.

**Architecture:** Each phase extends existing subsystems. Multi-agent builds on the hook registry. Auto-review plugs into the state machine. Knowledge graph re-uses the ReactFlow infrastructure. Estimation uses `scikit-learn` on `ActivityLog` data. Webhooks become a new outbound channel next to SSE. Presence is a WebSocket enhancement. Snapshot is a new router + tar/zip pipeline.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async (SQLite/aiosqlite), scikit-learn, httpx, React 19, ReactFlow, dagre, TanStack Router, TanStack Query, pytest-asyncio (`asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/agent_run.py` | Create | DAG node state |
| `backend/app/models/agent_dag.py` | Create | DAG definition per issue |
| `backend/app/services/orchestrator.py` | Create | DAG execution engine |
| `backend/app/routers/orchestrator.py` | Create | `/api/issues/{id}/orchestrate` |
| `backend/app/hooks/handlers/auto_review.py` | Create | `ISSUE_BEFORE_FINISH` handler |
| `backend/app/hooks/registry.py` | Modify | Add `ISSUE_BEFORE_FINISH` event + blocking firing mode |
| `backend/app/services/issue_service.py` | Modify | Call `before_finish` hooks with abort semantics |
| `backend/app/routers/knowledge_graph.py` | Create | Graph assembly endpoint |
| `backend/app/models/issue_estimate.py` | Create | Saved estimates + ground truth |
| `backend/app/services/estimation_service.py` | Create | Train + predict |
| `backend/app/routers/estimation.py` | Create | Predict endpoint |
| `backend/app/models/webhook.py` | Create | Outbound webhook configuration |
| `backend/app/services/webhook_dispatcher.py` | Create | SSE listener → HTTP POST |
| `backend/app/routers/webhooks.py` | Create | Webhook CRUD |
| `backend/app/services/presence_service.py` | Create | In-memory WebSocket presence registry |
| `backend/app/routers/presence.py` | Create | Presence WS endpoint |
| `backend/app/services/snapshot_service.py` | Create | Export + import |
| `backend/app/routers/snapshots.py` | Create | Snapshot endpoints |
| `frontend/src/features/orchestrator/` | Create | DAG editor + runner UI |
| `frontend/src/features/knowledge-graph/` | Create | Graph view |
| `frontend/src/features/estimation/components/estimation-badge.tsx` | Create | Display on issue cards |
| `frontend/src/features/webhooks/` | Create | Webhook CRUD UI |
| `frontend/src/features/presence/components/presence-avatars.tsx` | Create | Avatar stack per issue |
| `frontend/src/features/snapshots/` | Create | Export/import UI |
| `backend/requirements.txt` | Modify | Add `scikit-learn`, `joblib` |

---

## Phase 1: Multi-Agent DAG Orchestration

**Why:** A single Claude invocation per hook is rigid. For large issues, parallel specialised agents (frontend, backend, tests) + a reviewer are vastly more efficient. Model the workflow as a DAG and let the orchestrator run nodes in topological order.

### Task 1.1: DAG model

**Files:**
- Create: `backend/app/models/agent_dag.py`
- Create: `backend/app/models/agent_run.py`

- [ ] **Step 1: Models**

```python
# backend/app/models/agent_dag.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AgentDag(Base):
    __tablename__ = "agent_dags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    nodes: Mapped[dict] = mapped_column(JSON, nullable=False)  # [{id, prompt, tools, depends_on}]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

```python
# backend/app/models/agent_run.py
class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dag_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_dags.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed, skipped
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### Task 1.2: Orchestrator

**Files:**
- Create: `backend/app/services/orchestrator.py`

- [ ] **Step 1: Topological runner**

```python
# backend/app/services/orchestrator.py
from __future__ import annotations
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.hooks.executor import ClaudeCodeExecutor
from app.models import AgentDag, AgentRun, Project, Issue


class Orchestrator:
    def __init__(self, db: AsyncSession, dag: AgentDag):
        self.db = db
        self.dag = dag
        self.runs: dict[str, AgentRun] = {}

    async def run(self) -> None:
        nodes_by_id = {n["id"]: n for n in self.dag.nodes}
        in_degree: dict[str, int] = defaultdict(int)
        downstream: dict[str, list[str]] = defaultdict(list)
        for n in self.dag.nodes:
            for dep in n.get("depends_on", []):
                in_degree[n["id"]] += 1
                downstream[dep].append(n["id"])

        ready = [n["id"] for n in self.dag.nodes if in_degree[n["id"]] == 0]
        running: dict[str, asyncio.Task] = {}
        done: set[str] = set()

        issue = await self.db.get(Issue, self.dag.issue_id)
        project = await self.db.get(Project, issue.project_id)

        for nid in ready:
            running[nid] = asyncio.create_task(self._run_node(nodes_by_id[nid], project.path))

        while running:
            done_tasks, _ = await asyncio.wait(running.values(), return_when=asyncio.FIRST_COMPLETED)
            completed_ids = [nid for nid, t in running.items() if t in done_tasks]
            for nid in completed_ids:
                task = running.pop(nid)
                run = self.runs[nid]
                if task.exception() or run.status == "failed":
                    # Skip all downstream nodes
                    for d in downstream[nid]:
                        self.runs[d] = AgentRun(dag_id=self.dag.id, node_id=d, status="skipped")
                        self.db.add(self.runs[d])
                        done.add(d)
                    continue
                done.add(nid)
                for d in downstream[nid]:
                    in_degree[d] -= 1
                    if in_degree[d] == 0 and d not in done and d not in running:
                        running[d] = asyncio.create_task(self._run_node(nodes_by_id[d], project.path))

        await self.db.commit()

    async def _run_node(self, node: dict, project_path: str) -> None:
        run = AgentRun(dag_id=self.dag.id, node_id=node["id"], status="running",
                       started_at=datetime.now(timezone.utc))
        self.runs[node["id"]] = run
        self.db.add(run)
        await self.db.commit()

        result = await ClaudeCodeExecutor().run(
            prompt=node["prompt"], project_path=project_path,
            tool_guidance=node.get("tool_guidance", ""),
            timeout=node.get("timeout", 300),
        )

        run.status = "completed" if result.success else "failed"
        run.output = result.output
        run.error = result.error
        run.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
```

### Task 1.3: Router + UI

**Files:**
- Create: `backend/app/routers/orchestrator.py`
- Create: `frontend/src/features/orchestrator/components/dag-editor.tsx`
- Create: `frontend/src/features/orchestrator/components/dag-runner.tsx`

- [ ] **Step 1: Endpoints**

```python
# backend/app/routers/orchestrator.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.database import get_session
from app.models import AgentDag, AgentRun
from app.services.orchestrator import Orchestrator

router = APIRouter(prefix="/api/issues/{issue_id}/orchestrate", tags=["orchestrator"])


@router.post("")
async def start_orchestration(issue_id: str, payload: dict, db=Depends(get_session)) -> dict:
    dag = AgentDag(issue_id=issue_id, nodes=payload["nodes"])
    db.add(dag)
    await db.commit()
    import asyncio
    asyncio.create_task(Orchestrator(db, dag).run())
    return {"dag_id": dag.id, "status": "running"}


@router.get("/{dag_id}/runs")
async def list_runs(issue_id: str, dag_id: str, db=Depends(get_session)):
    return (await db.execute(select(AgentRun).where(AgentRun.dag_id == dag_id))).scalars().all()
```

- [ ] **Step 2: Preset DAGs**

Ship three presets accessible from `DagEditor`:
- **frontend-backend-test-review**: 3 parallel nodes (frontend, backend, tests) → 1 reviewer node depending on all three.
- **spec-plan-implement**: sequential chain matching the standard issue workflow.
- **hotfix**: single `implement + test` node.

- [ ] **Step 3: UI** — ReactFlow canvas to visualise the DAG; each node shows live status via events.

- [ ] **Step 4: Commit**

```bash
git add backend/ frontend/src/features/orchestrator/
git commit -m "feat(orchestrator): multi-agent DAG runner with live status"
```

---

## Phase 2: Auto-Review Before FINISHED

**Why:** Today an issue moves to FINISHED on user command (or `complete_issue` MCP tool). A pre-finish review hook that spawns Claude to inspect the git diff catches regressions before they are marked done.

### Task 2.1: New hook event + blocking mode

**Files:**
- Modify: `backend/app/hooks/registry.py`
- Modify: `backend/app/services/issue_service.py`

- [ ] **Step 1: Add event type**

```python
# backend/app/hooks/registry.py
class HookEvent(str, Enum):
    ISSUE_COMPLETED = "issue_completed"
    ISSUE_ACCEPTED = "issue_accepted"
    ISSUE_CANCELLED = "issue_cancelled"
    ISSUE_CREATED = "issue_created"
    ALL_TASKS_COMPLETED = "all_tasks_completed"
    ISSUE_BEFORE_FINISH = "issue_before_finish"  # new — blocking
```

- [ ] **Step 2: Add blocking `fire_and_wait` method**

```python
# backend/app/hooks/registry.py  (append)
async def fire_and_wait(self, event: HookEvent, context: HookContext) -> list[HookResult]:
    """Fire hooks synchronously; return their results. Used for gate events."""
    results: list[HookResult] = []
    for hook_class in self._hooks.get(event, []):
        hook = hook_class()
        try:
            result = await asyncio.wait_for(
                hook.execute(context), timeout=settings.hook_timeout_seconds
            )
        except Exception as exc:
            result = HookResult(success=False, error=str(exc))
        results.append(result)
    return results
```

- [ ] **Step 3: Gate `complete_issue`**

```python
# backend/app/services/issue_service.py  (inside complete_issue, before setting status)
results = await hook_registry.fire_and_wait(
    HookEvent.ISSUE_BEFORE_FINISH,
    HookContext(project_id=issue.project_id, issue_id=issue.id,
                event=HookEvent.ISSUE_BEFORE_FINISH,
                metadata={"issue_name": issue.name or "",
                          "project_path": project.path or "",
                          "recap": recap}),
)
if any(not r.success for r in results):
    errors = "; ".join((r.error or "review failed") for r in results if not r.success)
    raise ValidationError(f"auto-review blocked completion: {errors}")
```

### Task 2.2: Auto-review handler

**Files:**
- Create: `backend/app/hooks/handlers/auto_review.py`

- [ ] **Step 1: Implementation**

```python
# backend/app/hooks/handlers/auto_review.py
from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook


@hook(event=HookEvent.ISSUE_BEFORE_FINISH)
class AutoReviewHook(BaseHook):
    name = "auto_review"
    description = "Runs Claude over the git diff; vetoes completion on critical findings."

    async def execute(self, ctx: HookContext) -> HookResult:
        if not ctx.metadata.get("project_path"):
            return HookResult(success=True, output="skipped: no project path")
        prompt = (
            "Review the current git diff for the issue below. "
            "Reply with one line beginning 'APPROVE' if the change is safe to finish, "
            "or 'BLOCK: <reason>' if you find a critical issue (regression, missing test, "
            "unsafe shell, leaked secret, broken migration).\n\n"
            f"Issue: {ctx.metadata.get('issue_name')}\n"
            f"Recap draft: {ctx.metadata.get('recap')}\n"
        )
        result = await ClaudeCodeExecutor().run(
            prompt=prompt, project_path=ctx.metadata["project_path"],
            timeout=180,
        )
        output = (result.output or "").strip()
        if output.upper().startswith("BLOCK"):
            return HookResult(success=False, error=output)
        return HookResult(success=True, output=output)
```

- [ ] **Step 2: Register handler + make it opt-in per project** (setting `auto_review_enabled: bool = False`). The hook exits early with `success=True` when disabled.

- [ ] **Step 3: Test the blocking path**

```python
# backend/tests/test_auto_review.py
async def test_block_response_aborts_completion(...):
    # Monkeypatch ClaudeCodeExecutor.run to return a BLOCK line;
    # call IssueService.complete_issue; expect ValidationError.
```

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat(hooks): blocking ISSUE_BEFORE_FINISH auto-review gate"
```

---

## Phase 3: Knowledge Graph

**Why:** `IssueRelation` graph already ships for issue-to-issue links. A broader graph that also shows file → issue (via RAG), skill → project, and terminal → issue gives a single bird's-eye view of the project.

### Task 3.1: Graph endpoint

**Files:**
- Create: `backend/app/routers/knowledge_graph.py`

- [ ] **Step 1: Assembler**

```python
# backend/app/routers/knowledge_graph.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.database import get_session
from app.models import Issue, IssueRelation, ProjectFile, ProjectSkill

router = APIRouter(prefix="/api/projects/{project_id}/knowledge-graph", tags=["knowledge-graph"])


@router.get("")
async def knowledge_graph(project_id: str, db=Depends(get_session)) -> dict:
    issues = (await db.execute(select(Issue).where(Issue.project_id == project_id))).scalars().all()
    relations = (await db.execute(
        select(IssueRelation).join(Issue, IssueRelation.source_id == Issue.id)
        .where(Issue.project_id == project_id)
    )).scalars().all()
    files = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id))).scalars().all()
    skills = (await db.execute(select(ProjectSkill).where(ProjectSkill.project_id == project_id))).scalars().all()

    nodes = (
        [{"id": f"issue:{i.id}", "type": "issue", "label": i.name or i.id, "status": i.status.value} for i in issues]
        + [{"id": f"file:{f.id}", "type": "file", "label": f.original_name} for f in files]
        + [{"id": f"skill:{s.id}", "type": "skill", "label": s.name} for s in skills]
    )
    edges = (
        [{"source": f"issue:{r.source_id}", "target": f"issue:{r.target_id}", "kind": r.relation_type.value}
         for r in relations]
    )
    # File ↔ issue links: search RAG for completed issue chunks mentioning a file's title.
    # (Pragmatic approach: skip the RAG step in v1 and add it in a follow-up — pure UI graph already valuable.)
    return {"nodes": nodes, "edges": edges}
```

### Task 3.2: UI

**Files:**
- Create: `frontend/src/features/knowledge-graph/components/graph-view.tsx`
- Create: `frontend/src/routes/projects/$projectId/graph.tsx`

- [ ] **Step 1: ReactFlow + dagre layout**

```tsx
// frontend/src/features/knowledge-graph/components/graph-view.tsx
import ReactFlow, { Background, Controls } from "reactflow";
import dagre from "dagre";
import { useMemo } from "react";

export function GraphView({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const laid = useMemo(() => layout(nodes, edges), [nodes, edges]);
  return (
    <div className="h-[80vh]">
      <ReactFlow nodes={laid.nodes} edges={laid.edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function layout(nodes: GraphNode[], edges: GraphEdge[]) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 40, ranksep: 60 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: 180, height: 40 }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      data: { label: n.label },
      position: { x: g.node(n.id).x, y: g.node(n.id).y },
      style: nodeStyle(n.type),
    })),
    edges: edges.map((e, i) => ({ id: `${i}`, source: e.source, target: e.target })),
  };
}

function nodeStyle(t: string) {
  const palette: Record<string, string> = { issue: "#3b82f6", file: "#10b981", skill: "#a855f7" };
  return { background: palette[t] || "#888", color: "white", borderRadius: 6, padding: 4 };
}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/knowledge_graph.py frontend/src/features/knowledge-graph/ frontend/src/routes/projects/$projectId/graph.tsx
git commit -m "feat(graph): unified knowledge graph with issues, files, skills"
```

---

## Phase 4: Auto-Estimation

**Why:** Velocity planning requires estimates. Train a simple regression on historical data (description length, priority, tech_stack token count) to predict issue duration.

### Task 4.1: Data pipeline + model

**Files:**
- Modify: `backend/requirements.txt` (add `scikit-learn`, `joblib`)
- Create: `backend/app/services/estimation_service.py`
- Create: `backend/app/models/issue_estimate.py`

- [ ] **Step 1: Install deps**

```bash
cd backend && pip install scikit-learn joblib && echo "scikit-learn>=1.5" >> requirements.txt && echo "joblib>=1.4" >> requirements.txt
```

- [ ] **Step 2: Model**

```python
# backend/app/models/issue_estimate.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IssueEstimate(Base):
    __tablename__ = "issue_estimates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_hours: Mapped[float] = mapped_column(Float, nullable=False)
    actual_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    features: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Service**

```python
# backend/app/services/estimation_service.py
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Issue, ActivityLog

MODEL_PATH = Path("data/models/estimator.joblib")


class EstimationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _features(self, issue: Issue) -> list[float]:
        return [
            len(issue.description or ""),
            issue.priority or 3,
            len((issue.specification or "")) / 10,
            len((issue.plan or "")) / 10,
        ]

    async def train(self, project_id: str | None = None) -> dict:
        q = select(Issue).where(Issue.status == "Finished")
        if project_id:
            q = q.where(Issue.project_id == project_id)
        finished = (await self.db.execute(q)).scalars().all()

        xs: list[list[float]] = []
        ys: list[float] = []
        for issue in finished:
            duration = await self._measure_duration(issue)
            if duration is None:
                continue
            xs.append(self._features(issue))
            ys.append(duration)

        if len(xs) < 5:
            return {"trained": False, "reason": "insufficient_data", "samples": len(xs)}

        model = LinearRegression()
        model.fit(np.array(xs), np.array(ys))
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        return {"trained": True, "samples": len(xs), "r2": float(model.score(np.array(xs), np.array(ys)))}

    async def predict(self, issue: Issue) -> float | None:
        if not MODEL_PATH.exists():
            return None
        model = joblib.load(MODEL_PATH)
        return float(model.predict(np.array([self._features(issue)]))[0])

    async def _measure_duration(self, issue: Issue) -> float | None:
        rows = (await self.db.execute(
            select(ActivityLog).where(ActivityLog.issue_id == issue.id).order_by(ActivityLog.created_at)
        )).scalars().all()
        created = next((r for r in rows if r.event_type == "issue_created"), None)
        finished = next((r for r in rows if r.event_type == "issue_completed"), None)
        if not created or not finished:
            return None
        return (finished.created_at - created.created_at).total_seconds() / 3600.0
```

### Task 4.2: Router + UI badge

**Files:**
- Create: `backend/app/routers/estimation.py`
- Create: `frontend/src/features/estimation/components/estimation-badge.tsx`

- [ ] **Step 1: Endpoints**

```python
# backend/app/routers/estimation.py
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_session
from app.models import Issue
from app.services.estimation_service import EstimationService

router = APIRouter(prefix="/api/estimation", tags=["estimation"])


@router.post("/train")
async def train(project_id: str | None = None, db=Depends(get_session)) -> dict:
    return await EstimationService(db).train(project_id=project_id)


@router.get("/predict/{issue_id}")
async def predict(issue_id: str, db=Depends(get_session)) -> dict:
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "not found")
    hours = await EstimationService(db).predict(issue)
    return {"predicted_hours": hours}
```

- [ ] **Step 2: Badge**

```tsx
// frontend/src/features/estimation/components/estimation-badge.tsx
export function EstimationBadge({ hours }: { hours: number | null }) {
  if (hours == null) return null;
  return (
    <Badge variant="outline" aria-label={`Estimated duration ${hours.toFixed(1)} hours`}>
      ~{hours.toFixed(1)} h
    </Badge>
  );
}
```

Display on issue cards in the kanban + issue list.

- [ ] **Step 3: Nightly retraining** — add a task to the `main.py` lifespan loop (like activity purge): once per 24 h, call `EstimationService(session).train()` for all projects.

- [ ] **Step 4: Commit**

```bash
git add backend/ frontend/src/features/estimation/
git commit -m "feat(estimation): linear-regression duration predictor + UI badge"
```

---

## Phase 5: Integration Hub (Outbound Webhooks)

**Why:** Teams already live in Slack/Discord/Linear. Emitting the existing SSE events as outbound HTTPS POSTs to user-configured URLs lets the app participate in existing pipelines.

### Task 5.1: Model + dispatcher

**Files:**
- Create: `backend/app/models/webhook.py`
- Create: `backend/app/services/webhook_dispatcher.py`

- [ ] **Step 1: Model**

```python
# backend/app/models/webhook.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Webhook(Base):
    __tablename__ = "webhooks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    events: Mapped[dict] = mapped_column(JSON, nullable=False)  # list[str]
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Dispatcher**

```python
# backend/app/services/webhook_dispatcher.py
from __future__ import annotations
import hashlib, hmac, json
from typing import Any
import httpx
from sqlalchemy import select
from app.models import Webhook


async def dispatch(event: dict, session_factory) -> None:
    project_id = event.get("project_id")
    if not project_id:
        return
    event_type = event.get("type")
    async with session_factory() as db:
        hooks = (await db.execute(
            select(Webhook).where(Webhook.project_id == project_id, Webhook.active == True)
        )).scalars().all()
    eligible = [h for h in hooks if event_type in (h.events or [])]
    if not eligible:
        return

    body = json.dumps(event).encode()
    async with httpx.AsyncClient(timeout=10) as client:
        for h in eligible:
            headers = {"content-type": "application/json"}
            if h.secret:
                sig = hmac.new(h.secret.encode(), body, hashlib.sha256).hexdigest()
                headers["x-manager-ai-signature"] = f"sha256={sig}"
            try:
                await client.post(h.url, content=body, headers=headers)
            except Exception:
                pass  # webhook failures never block the main flow
```

- [ ] **Step 3: Subscribe to the event bus**

```python
# backend/app/main.py  (inside lifespan)
from app.services.event_service import event_service
from app.services.webhook_dispatcher import dispatch

async def _webhook_listener():
    async def relay(e: dict):
        await dispatch(e, async_session)
    event_service.subscribe(relay)
    # keep the task alive
    while True:
        await asyncio.sleep(3600)

wh_task = asyncio.create_task(_webhook_listener())
```

Assumes `event_service` exposes `subscribe(callback)`. If not, add a simple in-process broker.

### Task 5.2: CRUD + UI

**Files:**
- Create: `backend/app/routers/webhooks.py`
- Create: `frontend/src/features/webhooks/` (list, create, delete)

- [ ] **Step 1: Standard CRUD router + form UI**

- [ ] **Step 2: Test with https://webhook.site** — create a hook, trigger an issue event, confirm payload lands.

- [ ] **Step 3: Commit**

```bash
git add backend/ frontend/src/features/webhooks/
git commit -m "feat(webhooks): outbound integration hub with HMAC-signed payloads"
```

---

## Phase 6: Presence

**Why:** Even in single-user mode, seeing "I have issue X open in another tab" avoids editing collisions. For future multi-user, presence is the foundation.

### Task 6.1: Presence registry

**Files:**
- Create: `backend/app/services/presence_service.py`
- Create: `backend/app/routers/presence.py`
- Create: `frontend/src/features/presence/components/presence-avatars.tsx`

- [ ] **Step 1: In-memory registry**

```python
# backend/app/services/presence_service.py
from __future__ import annotations
import asyncio
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Viewer:
    session_id: str
    name: str
    color: str


class PresenceService:
    def __init__(self) -> None:
        self._viewers: dict[tuple[str, str], dict[str, Viewer]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def join(self, project_id: str, issue_id: str, viewer: Viewer) -> None:
        async with self._lock:
            self._viewers[(project_id, issue_id)][viewer.session_id] = viewer

    async def leave(self, project_id: str, issue_id: str, session_id: str) -> None:
        async with self._lock:
            self._viewers[(project_id, issue_id)].pop(session_id, None)

    def list(self, project_id: str, issue_id: str) -> list[Viewer]:
        return list(self._viewers.get((project_id, issue_id), {}).values())


presence_service = PresenceService()
```

- [ ] **Step 2: WebSocket endpoint**

```python
# backend/app/routers/presence.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.presence_service import presence_service, Viewer
from app.services.event_service import event_service

router = APIRouter(prefix="/api/presence", tags=["presence"])


@router.websocket("/ws/{project_id}/{issue_id}")
async def presence_ws(ws: WebSocket, project_id: str, issue_id: str,
                      session_id: str, name: str = "guest", color: str = "#3b82f6"):
    await ws.accept()
    viewer = Viewer(session_id=session_id, name=name, color=color)
    await presence_service.join(project_id, issue_id, viewer)
    await event_service.emit({"type": "presence_update", "project_id": project_id, "issue_id": issue_id,
                               "viewers": [v.__dict__ for v in presence_service.list(project_id, issue_id)]})
    try:
        while True:
            await ws.receive_text()  # heartbeats ignored
    except WebSocketDisconnect:
        await presence_service.leave(project_id, issue_id, session_id)
        await event_service.emit({"type": "presence_update", "project_id": project_id, "issue_id": issue_id,
                                   "viewers": [v.__dict__ for v in presence_service.list(project_id, issue_id)]})
```

- [ ] **Step 3: Client avatars**

```tsx
// frontend/src/features/presence/components/presence-avatars.tsx
export function PresenceAvatars({ viewers }: { viewers: Array<{ session_id: string; name: string; color: string }> }) {
  if (!viewers.length) return null;
  return (
    <div className="flex -space-x-2">
      {viewers.map((v) => (
        <div key={v.session_id}
             style={{ background: v.color }}
             title={v.name}
             aria-label={`${v.name} viewing this issue`}
             className="h-6 w-6 rounded-full border-2 border-background flex items-center justify-center text-[10px] font-medium text-white">
          {v.name.slice(0, 1).toUpperCase()}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add backend/ frontend/src/features/presence/
git commit -m "feat(presence): WebSocket presence with avatar stack on issue detail"
```

---

## Phase 7: Snapshot / Export

**Why:** A single zip containing the SQLite slice + LanceDB chunks + uploaded files makes backups trivial and lets users move projects between machines.

### Task 7.1: Export

**Files:**
- Create: `backend/app/services/snapshot_service.py`
- Create: `backend/app/routers/snapshots.py`

- [ ] **Step 1: Service**

```python
# backend/app/services/snapshot_service.py
from __future__ import annotations
import io
import json
import tempfile
import zipfile
from pathlib import Path
from sqlalchemy import select
from app.models import (ActivityLog, Issue, IssueRelation, IssueFeedback,
                         Project, ProjectFile, ProjectSkill, ProjectVariable,
                         PromptTemplate, Task, TerminalCommand)


class SnapshotService:
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings

    async def export(self, project_id: str) -> bytes:
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError("project not found")

        manifest = {"schema_version": 1, "project_id": project_id,
                    "project": _serialize(project)}
        manifest["issues"] = [_serialize(i) for i in (await self._q(Issue, project_id))]
        manifest["tasks"] = [_serialize(t) for t in (await self._tasks(project_id))]
        manifest["relations"] = [_serialize(r) for r in (await self._relations(project_id))]
        manifest["feedback"] = [_serialize(f) for f in (await self._feedback(project_id))]
        manifest["variables"] = [_serialize(v) for v in (await self._q(ProjectVariable, project_id))]
        manifest["skills"] = [_serialize(s) for s in (await self._q(ProjectSkill, project_id))]
        manifest["templates"] = [_serialize(t) for t in (await self._q(PromptTemplate, project_id))]
        manifest["activity"] = [_serialize(a) for a in (await self._q(ActivityLog, project_id))]
        manifest["terminal_commands"] = [_serialize(tc) for tc in (await self._terminal_commands(project_id))]
        manifest["files"] = [_serialize(f) for f in (await self._q(ProjectFile, project_id))]

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, default=str, indent=2))
            for pf in (await self._q(ProjectFile, project_id)):
                fpath = Path(self.settings.uploads_path) / pf.stored_name
                if fpath.is_file():
                    zf.write(fpath, arcname=f"files/{pf.stored_name}")
            # LanceDB chunks for this project
            chunks = _collect_lancedb_chunks(self.settings.lancedb_path, project_id)
            zf.writestr("vectors.json", json.dumps(chunks, default=str))
        return buffer.getvalue()

    async def import_(self, data: bytes) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            buffer = io.BytesIO(data)
            with zipfile.ZipFile(buffer) as zf:
                zf.extractall(tmp)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text())
            # Rehydrate rows, remapping project_id to a new UUID if desired.
            # (Left as an exercise per record type — follow the order of creation:
            # Project → ProjectFile → Issue → Task → IssueRelation → IssueFeedback → ActivityLog → etc.)
            # Restore files/ directory, then restore vectors.json into LanceDB.
            return manifest["project_id"]


def _serialize(row) -> dict:
    from sqlalchemy.inspection import inspect as sa_inspect
    cols = sa_inspect(row.__class__).columns
    return {c.name: getattr(row, c.name) for c in cols}
```

- [ ] **Step 2: Router**

```python
# backend/app/routers/snapshots.py
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from app.database import get_session
from app.services.snapshot_service import SnapshotService
from app.config import settings

router = APIRouter(prefix="/api/projects/{project_id}/snapshot", tags=["snapshots"])


@router.get("/export")
async def export_snapshot(project_id: str, db=Depends(get_session)):
    data = await SnapshotService(db, settings).export(project_id)
    return StreamingResponse(
        iter([data]), media_type="application/zip",
        headers={"content-disposition": f'attachment; filename="{project_id}.snapshot.zip"'},
    )


@router.post("/import")
async def import_snapshot(file: UploadFile = File(...), db=Depends(get_session)) -> dict:
    data = await file.read()
    project_id = await SnapshotService(db, settings).import_(data)
    return {"project_id": project_id}
```

- [ ] **Step 3: UI buttons** — Export / Import in project settings dialog.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/snapshot_service.py backend/app/routers/snapshots.py frontend/
git commit -m "feat(snapshot): project export/import zip bundle"
```

---

## Self-Review Checklist

- [ ] Orchestrator aborts downstream nodes when a dependency fails — tested with a forced failure in the middle of a 3-node DAG.
- [ ] Auto-review BLOCK response surfaces to the caller with 4xx + readable error.
- [ ] Knowledge graph renders without errors on a project with zero files/skills.
- [ ] Estimation service refuses to predict (returns `null`) when the model file is missing.
- [ ] Webhook dispatcher never throws into the main event pipeline — errors swallowed.
- [ ] Presence avatars disappear within 2 s of tab close.
- [ ] Snapshot round-trip: export → wipe DB → import → every issue/task/activity row intact.

---

## Execution

Estimated effort:
1. Phase 1 (orchestrator) — 20 h
2. Phase 2 (auto-review) — 6 h
3. Phase 3 (knowledge graph) — 6 h
4. Phase 4 (auto-estimation) — 12 h
5. Phase 5 (webhooks) — 8 h
6. Phase 6 (presence) — 6 h
7. Phase 7 (snapshot) — 12 h

Total: ~70 hours. Ship phase 1 and 2 together (they unlock the "AI orchestration platform" positioning); others in follow-ups.
