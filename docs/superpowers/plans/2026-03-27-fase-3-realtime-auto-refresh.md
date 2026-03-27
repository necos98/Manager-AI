# Fase 3 — Real-Time & Auto-Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the frontend auto-refresh when Claude writes specs/plans, updates tasks, or changes issue status via MCP tools, while adding typed toast notifications, a sound toggle, and a persistent activity log.

**Architecture:** Event emission is added to MCP tool functions (after DB commit) so the frontend receives WebSocket events and invalidates the right TanStack Query caches. Activity logs are persisted to a new `activity_logs` DB table populated from the service layer. The frontend gets a new per-project Activity page with a scrollable timeline.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic (backend); React, TanStack Query, TanStack Router, Sonner toasts, localStorage (frontend)

---

## File Map

**Backend — new files:**
- `backend/app/models/activity_log.py` — SQLAlchemy model
- `backend/app/services/activity_service.py` — log creation and querying
- `backend/app/schemas/activity.py` — Pydantic response schema
- `backend/app/routers/activity.py` — `GET /api/projects/{project_id}/activity`
- `backend/alembic/versions/XXXX_add_activity_log_table.py` — migration

**Backend — modified files:**
- `backend/app/mcp/server.py` — add event emission to all 14 MCP tools after commit
- `backend/app/models/__init__.py` — export `ActivityLog`
- `backend/app/main.py` — register activity router
- `backend/app/services/issue_service.py` — call `ActivityService.log()` in state transitions
- `backend/app/hooks/registry.py` — call `ActivityService.log()` in `_run_hook`
- `backend/tests/conftest.py` — import `ActivityLog` so table is created in test DB

**Frontend — new files:**
- `frontend/src/features/activity/api.ts`
- `frontend/src/features/activity/hooks.ts`
- `frontend/src/features/activity/components/activity-timeline.tsx`
- `frontend/src/routes/projects/$projectId/activity.tsx`

**Frontend — modified files:**
- `frontend/src/shared/context/event-context.tsx` — typed toasts based on `event.type`
- `frontend/src/shared/components/app-sidebar.tsx` — add Activity nav item
- `frontend/src/shared/types/index.ts` — add `ActivityLog` type
- `frontend/src/routes/settings.tsx` — add Preferences tab with sound toggle

---

## Task 1: Emit events from MCP issue tools (3.1)

**Files:**
- Modify: `backend/app/mcp/server.py`
- Test: `backend/tests/test_mcp_events.py` (new)

The root cause of stale UI: MCP tools call `session.commit()` but never call `event_service.emit()`. The frontend EventContext already invalidates TanStack Query caches when it receives a WebSocket event with `project_id` + `issue_id`. We just need to emit after each commit.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_mcp_events.py`:

```python
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

import app.mcp.server as mcp_server
from app.services.project_service import ProjectService
from app.services.issue_service import IssueService


@pytest_asyncio.fixture
async def project(db_session):
    svc = ProjectService(db_session)
    return await svc.create(name="MCP Events", path="/tmp/mcp_events", description="")


@pytest_asyncio.fixture
async def issue(db_session, project):
    svc = IssueService(db_session)
    return await svc.create(project_id=project.id, description="Test issue", priority=1)


def make_session_patcher(db_session):
    @asynccontextmanager
    async def _fake():
        yield db_session
    return _fake


@pytest.mark.asyncio
async def test_create_issue_spec_emits_event(db_session, project, issue):
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.create_issue_spec(
            project_id=project.id, issue_id=issue.id, spec="# Spec"
        )
    assert result["status"] == "Reasoning"
    emit_mock.assert_called_once()
    event = emit_mock.call_args[0][0]
    assert event["type"] == "issue_status_changed"
    assert event["project_id"] == project.id
    assert event["issue_id"] == issue.id


@pytest.mark.asyncio
async def test_create_issue_plan_emits_event(db_session, project, issue):
    svc = IssueService(db_session)
    await svc.create_spec(issue.id, project.id, "# Spec")
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.create_issue_plan(
            project_id=project.id, issue_id=issue.id, plan="# Plan"
        )
    assert result["status"] == "Planned"
    event = emit_mock.call_args[0][0]
    assert event["type"] == "issue_status_changed"


@pytest.mark.asyncio
async def test_set_issue_name_emits_event(db_session, project, issue):
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.set_issue_name(
            project_id=project.id, issue_id=issue.id, name="My Issue Name"
        )
    assert result["name"] == "My Issue Name"
    event = emit_mock.call_args[0][0]
    assert event["type"] == "issue_content_updated"
    assert event["content_type"] == "name"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_mcp_events.py -v
```

Expected: FAIL — `emit_mock.assert_called_once()` fails (emit is not called yet)

- [ ] **Step 3: Add `from app.models.issue import Issue` import and emit calls to MCP server**

At the top of `backend/app/mcp/server.py`, after the existing imports, add:
```python
from app.models.issue import Issue
```

Replace each MCP tool function body with the version that emits after commit. Here are all 9 issue-related tools:

**`create_issue_spec`** — add emit after commit:
```python
@mcp.tool(description=_desc["tool.create_issue_spec.description"])
async def create_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create_spec(issue_id, project_id, spec)
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status.value,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value, "specification": issue.specification}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`edit_issue_spec`**:
```python
@mcp.tool(description=_desc["tool.edit_issue_spec.description"])
async def edit_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.edit_spec(issue_id, project_id, spec)
            await session.commit()
            await event_service.emit({
                "type": "issue_content_updated",
                "content_type": "spec",
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value, "specification": issue.specification}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`create_issue_plan`**:
```python
@mcp.tool(description=_desc["tool.create_issue_plan.description"])
async def create_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create_plan(issue_id, project_id, plan)
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status.value,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value, "plan": issue.plan}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`edit_issue_plan`**:
```python
@mcp.tool(description=_desc["tool.edit_issue_plan.description"])
async def edit_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.edit_plan(issue_id, project_id, plan)
            await session.commit()
            await event_service.emit({
                "type": "issue_content_updated",
                "content_type": "plan",
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value, "plan": issue.plan}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`accept_issue`**:
```python
@mcp.tool(description=_desc["tool.accept_issue.description"])
async def accept_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.accept_issue(issue_id, project_id)
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status.value,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value}
        except AppError as e:
            return {"error": e.message}
```

**`cancel_issue`**:
```python
@mcp.tool(description=_desc["tool.cancel_issue.description"])
async def cancel_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.cancel_issue(issue_id, project_id)
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status.value,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value}
        except AppError as e:
            return {"error": e.message}
```

**`complete_issue`** — emit after the existing RAG task:
```python
@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.complete_issue(issue_id, project_id, recap)
            issue_data = {
                "name": issue.name or (issue.description or "")[:100],
                "specification": issue.specification,
                "plan": issue.plan,
                "recap": issue.recap,
            }
            issue_id_val = issue.id
            issue_name = issue.name or (issue.description or "")[:50] or ""
            await session.commit()
            rag = get_rag_service()
            asyncio.create_task(rag.embed_issue(
                project_id=project_id,
                source_id=issue_id_val,
                issue_data=issue_data,
            ))
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status.value,
                "project_id": project_id,
                "issue_id": issue_id_val,
                "issue_name": issue_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue_id_val, "status": issue.status.value, "recap": issue.recap}
        except AppError as e:
            return {"error": e.message}
```

**`set_issue_name`**:
```python
@mcp.tool(description=_desc["tool.set_issue_name.description"])
async def set_issue_name(project_id: str, issue_id: str, name: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.set_name(issue_id, project_id, name)
            await session.commit()
            await event_service.emit({
                "type": "issue_content_updated",
                "content_type": "name",
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "name": issue.name}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`update_project_context`**:
```python
@mcp.tool(description=_desc["tool.update_project_context.description"])
async def update_project_context(project_id: str, description: str | None = None, tech_stack: str | None = None) -> dict:
    async with async_session() as session:
        project_service = ProjectService(session)
        try:
            project = await project_service.update(project_id, description=description, tech_stack=tech_stack)
            await session.commit()
            await event_service.emit({
                "type": "project_updated",
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "description": project.description,
                "tech_stack": project.tech_stack,
            }
        except AppError as e:
            return {"error": e.message}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_mcp_events.py -v
```

Expected: PASS for all 3 tests

- [ ] **Step 5: Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_mcp_events.py
git commit -m "feat: emit issue events from MCP tools after commit (3.1)"
```

---

## Task 2: Emit task events from MCP tools (3.1)

**Files:**
- Modify: `backend/app/mcp/server.py`
- Test: `backend/tests/test_mcp_events.py` (add to existing)

Task MCP tools (update_task_status, update_task_name, delete_task, create_plan_tasks, replace_plan_tasks) need to emit `task_updated` events. They need `project_id` which requires loading the parent Issue.

- [ ] **Step 1: Write the failing tests (add to test_mcp_events.py)**

```python
@pytest_asyncio.fixture
async def planned_issue(db_session, project):
    """Issue with tasks, in Planned status"""
    svc = IssueService(db_session)
    issue = await svc.create(project_id=project.id, description="Task test issue", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    await svc.create_plan(issue.id, project.id, "# Plan")
    return issue


@pytest.mark.asyncio
async def test_create_plan_tasks_emits_event(db_session, project, planned_issue):
    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.create_plan_tasks(
            issue_id=planned_issue.id,
            tasks=[{"name": "Task A"}, {"name": "Task B"}]
        )
    assert len(result["tasks"]) == 2
    event = emit_mock.call_args[0][0]
    assert event["type"] == "task_updated"
    assert event["project_id"] == project.id
    assert event["issue_id"] == planned_issue.id


@pytest.mark.asyncio
async def test_update_task_status_emits_event(db_session, project, planned_issue):
    from app.services.task_service import TaskService
    task_svc = TaskService(db_session)
    tasks = await task_svc.create_bulk(planned_issue.id, [{"name": "Task X"}])
    task = tasks[0]

    emit_mock = AsyncMock()
    with patch("app.mcp.server.async_session", make_session_patcher(db_session)), \
         patch.object(mcp_server.event_service, "emit", emit_mock):
        result = await mcp_server.update_task_status(task_id=task.id, status="In Progress")
    assert result["status"] == "In Progress"
    event = emit_mock.call_args[0][0]
    assert event["type"] == "task_updated"
    assert event["project_id"] == project.id
    assert event["issue_id"] == planned_issue.id
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && python -m pytest tests/test_mcp_events.py::test_create_plan_tasks_emits_event tests/test_mcp_events.py::test_update_task_status_emits_event -v
```

Expected: FAIL

- [ ] **Step 3: Add emit calls to task MCP tools in server.py**

**`create_plan_tasks`**:
```python
@mcp.tool(description=_desc["tool.create_plan_tasks.description"])
async def create_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            created = await task_service.create_bulk(issue_id, tasks)
            issue = await session.get(Issue, issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": issue_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in created]}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`replace_plan_tasks`**:
```python
@mcp.tool(description=_desc["tool.replace_plan_tasks.description"])
async def replace_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            created = await task_service.replace_all(issue_id, tasks)
            issue = await session.get(Issue, issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": issue_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in created]}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`update_task_status`**:
```python
@mcp.tool(description=_desc["tool.update_task_status.description"])
async def update_task_status(task_id: str, status: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, status=status)
            issue = await session.get(Issue, task.issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": task.issue_id,
                    "task_id": task.id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return {"id": task.id, "name": task.name, "status": task.status.value}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`update_task_name`**:
```python
@mcp.tool(description=_desc["tool.update_task_name.description"])
async def update_task_name(task_id: str, name: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, name=name)
            issue = await session.get(Issue, task.issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": task.issue_id,
                    "task_id": task.id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return {"id": task.id, "name": task.name}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

**`delete_task`** — load task before deleting so we have the issue_id:
```python
@mcp.tool(description=_desc["tool.delete_task.description"])
async def delete_task(task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_by_id(task_id)
            issue = await session.get(Issue, task.issue_id)
            project_id = issue.project_id if issue else None
            issue_id = task.issue_id
            await session.delete(task)
            await session.flush()
            await session.commit()
            if project_id:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": project_id,
                    "issue_id": issue_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return {"deleted": True}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

- [ ] **Step 4: Run all MCP event tests**

```bash
cd backend && python -m pytest tests/test_mcp_events.py -v
```

Expected: all PASS

- [ ] **Step 5: Run full test suite to check no regressions**

```bash
cd backend && python -m pytest -x -q
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_mcp_events.py
git commit -m "feat: emit task events from MCP tools after commit (3.1)"
```

---

## Task 3: Typed toasts + sound toggle (3.2)

**Files:**
- Modify: `frontend/src/shared/context/event-context.tsx`
- Modify: `frontend/src/routes/settings.tsx`

Currently every WebSocket event shows the same plain `toast()`. ROADMAP 3.2 requires color-coded toasts and a per-user sound toggle stored in `localStorage`.

- [ ] **Step 1: Update event-context.tsx with typed toasts and sound toggle**

Replace the `ws.onmessage` handler and audio playback logic in `frontend/src/shared/context/event-context.tsx`:

```tsx
import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { queryClient } from "@/shared/lib/query-client";

interface EventContextValue {}

const EventContext = createContext<EventContextValue | null>(null);

const notificationAudio = new Audio("/sounds/notification.wav");
notificationAudio.volume = 0.5;

function unlockAudio() {
  notificationAudio.play().then(() => {
    notificationAudio.pause();
    notificationAudio.currentTime = 0;
  }).catch(() => {});
  document.removeEventListener("click", unlockAudio);
  document.removeEventListener("keydown", unlockAudio);
}
document.addEventListener("click", unlockAudio);
document.addEventListener("keydown", unlockAudio);

function isSoundEnabled(): boolean {
  return localStorage.getItem("manager_ai_sound") !== "false";
}

function playNotificationSound() {
  if (!isSoundEnabled()) return;
  try {
    notificationAudio.currentTime = 0;
    notificationAudio.play().catch(() => {});
  } catch {
    // Audio API unavailable
  }
}

function showTypedToast(
  eventType: string | undefined,
  title: string,
  description: string,
  action?: { label: string; onClick: () => void }
) {
  const opts = { description, action };
  if (eventType === "hook_failed") {
    toast.error(title, opts);
  } else if (eventType === "hook_completed") {
    toast.success(title, opts);
  } else if (eventType === "notification") {
    toast.info(title, opts);
  } else if (eventType === "hook_started") {
    toast(title, { ...opts, duration: 2000 });
  } else {
    toast(title, opts);
  }
}

export function EventProvider({ children }: { children: React.ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const backoffRef = useRef(1000);
  const cleanedUpRef = useRef(false);
  const navigate = useNavigate();

  const connect = useCallback(() => {
    if (cleanedUpRef.current) return;

    const backendPort = import.meta.env.VITE_BACKEND_PORT || "8000";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.hostname}:${backendPort}/api/events/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cleanedUpRef.current) { ws.close(); return; }
      backoffRef.current = 1000;
    };

    ws.onmessage = (event) => {
      if (cleanedUpRef.current) return;
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;
        const projectId = data.project_id as string | undefined;
        const issueId = data.issue_id as string | undefined;
        const issueName = data.issue_name as string | undefined;
        const eventType = data.type as string | undefined;
        const message = (data.message as string) || (data.status as string) || "New event";
        const title = issueName || eventType || "Event";

        const action = projectId && issueId
          ? { label: "View", onClick: () => navigate({ to: "/projects/$projectId/issues/$issueId", params: { projectId, issueId } }) }
          : undefined;

        showTypedToast(eventType, title, message, action);
        playNotificationSound();

        if (projectId && issueId) {
          queryClient.invalidateQueries({ queryKey: ["projects", projectId, "issues", issueId] });
          queryClient.invalidateQueries({ queryKey: ["projects", projectId, "issues"] });
        } else if (projectId) {
          queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
        }
      } catch {
        // Ignore unparseable messages
      }
    };

    ws.onclose = () => {
      if (cleanedUpRef.current) return;
      const delay = Math.min(backoffRef.current, 30000);
      backoffRef.current = Math.min(backoffRef.current * 2, 30000);
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => { ws.close(); };
  }, [navigate]);

  useEffect(() => {
    cleanedUpRef.current = false;
    connect();
    return () => {
      cleanedUpRef.current = true;
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN) wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return <EventContext.Provider value={{}}>{children}</EventContext.Provider>;
}

export function useEvents() {
  return useContext(EventContext);
}
```

- [ ] **Step 2: Add "Preferences" tab to settings.tsx**

In `frontend/src/routes/settings.tsx`, make these changes:

1. Change the `TABS` constant to add "Preferences":
```tsx
const TABS = ["Server", "Tool Descriptions", "Response Messages", "Terminal", "Preferences"] as const;
```

2. Add a `PreferencesPanel` component before `SettingsPage`:
```tsx
function PreferencesPanel() {
  const [soundEnabled, setSoundEnabled] = useState(
    () => localStorage.getItem("manager_ai_sound") !== "false"
  );

  function handleToggleSound(enabled: boolean) {
    setSoundEnabled(enabled);
    localStorage.setItem("manager_ai_sound", enabled ? "true" : "false");
  }

  return (
    <div className="space-y-4">
      <div className="border rounded-lg p-4 flex items-center justify-between">
        <div>
          <p className="font-medium text-sm">Sound Notifications</p>
          <p className="text-xs text-muted-foreground mt-0.5">Play a sound when events arrive</p>
        </div>
        <button
          role="switch"
          aria-checked={soundEnabled}
          onClick={() => handleToggleSound(!soundEnabled)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
            soundEnabled ? "bg-primary" : "bg-input"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              soundEnabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>
    </div>
  );
}
```

3. Add the Preferences tab rendering in `SettingsPage`:

After the existing `{activeTab === "Terminal" ? (...) : (...)}` block, wrap it so that "Preferences" is handled:

```tsx
{activeTab === "Terminal" ? (
  <div>
    <div className="mb-5 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800">
      These commands run automatically when opening a terminal. They apply only when a project has no project-specific commands.
    </div>
    <TerminalCommandsEditor projectId={null} />
  </div>
) : activeTab === "Preferences" ? (
  <PreferencesPanel />
) : (
  <SettingsForm settings={filteredSettings} />
)}
```

Also hide the "Reset all to defaults" button for Preferences tab by changing the condition:
```tsx
{activeTab !== "Terminal" && activeTab !== "Preferences" && (
  <div className="mt-8 pt-6 border-t">
    ...
  </div>
)}
```

- [ ] **Step 3: Verify in browser**

Run `npm run dev` and:
1. Open Settings → Preferences tab — toggle should be visible and persist on page reload
2. Trigger any Claude MCP action and verify toast colors: hook_failed = red, hook_completed = green, notification = blue

- [ ] **Step 4: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/context/event-context.tsx frontend/src/routes/settings.tsx
git commit -m "feat: typed toasts and sound toggle (3.2)"
```

---

## Task 4: ActivityLog model + migration (3.3)

**Files:**
- Create: `backend/app/models/activity_log.py`
- Create: `backend/alembic/versions/XXXX_add_activity_log_table.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Create the model**

Create `backend/app/models/activity_log.py`:

```python
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    def get_details(self) -> dict:
        try:
            return json.loads(self.details)
        except (json.JSONDecodeError, TypeError):
            return {}
```

- [ ] **Step 2: Export from models __init__.py**

Read `backend/app/models/__init__.py`, then add `ActivityLog` to the imports:

```python
from app.models.activity_log import ActivityLog
from app.models.issue import Issue, IssueStatus
from app.models.issue_feedback import IssueFeedback
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.setting import Setting
from app.models.task import Task, TaskStatus
from app.models.terminal_command import TerminalCommand

__all__ = [
    "ActivityLog",
    "Issue",
    "IssueStatus",
    "IssueFeedback",
    "Project",
    "ProjectFile",
    "Setting",
    "Task",
    "TaskStatus",
    "TerminalCommand",
]
```

- [ ] **Step 3: Update conftest.py to import ActivityLog**

In `backend/tests/conftest.py`, add `ActivityLog` to the import line:

```python
from app.models import ActivityLog, Issue, IssueFeedback, Project, Setting, Task, TerminalCommand  # noqa: F401
```

- [ ] **Step 4: Generate migration**

```bash
cd backend && python -m alembic revision --autogenerate -m "add_activity_log_table"
```

Expected: new file created in `alembic/versions/`

- [ ] **Step 5: Review and clean the migration**

Open the generated migration and verify it creates the `activity_logs` table with the right columns and foreign keys. Expected upgrade() looks like:

```python
def upgrade() -> None:
    op.create_table('activity_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('issue_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('details', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_logs_created_at'), 'activity_logs', ['created_at'])
    op.create_index(op.f('ix_activity_logs_issue_id'), 'activity_logs', ['issue_id'])
    op.create_index(op.f('ix_activity_logs_project_id'), 'activity_logs', ['project_id'])
```

- [ ] **Step 6: Apply migration**

```bash
cd backend && python -m alembic upgrade head
```

Expected: migration applied successfully

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/activity_log.py backend/app/models/__init__.py \
        backend/tests/conftest.py backend/alembic/versions/
git commit -m "feat: add ActivityLog model and migration (3.3)"
```

---

## Task 5: ActivityService + router + tests (3.3)

**Files:**
- Create: `backend/app/services/activity_service.py`
- Create: `backend/app/schemas/activity.py`
- Create: `backend/app/routers/activity.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_activity_service.py`
- Create: `backend/tests/test_routers_activity.py`

- [ ] **Step 1: Write service tests**

Create `backend/tests/test_activity_service.py`:

```python
import pytest
import pytest_asyncio

from app.services.project_service import ProjectService
from app.services.issue_service import IssueService
from app.services.activity_service import ActivityService


@pytest_asyncio.fixture
async def project(db_session):
    svc = ProjectService(db_session)
    return await svc.create(name="Activity Test", path="/tmp/activity", description="")


@pytest_asyncio.fixture
async def issue(db_session, project):
    svc = IssueService(db_session)
    return await svc.create(project_id=project.id, description="Test issue", priority=1)


@pytest.mark.asyncio
async def test_log_creates_entry(db_session, project, issue):
    svc = ActivityService(db_session)
    log = await svc.log(
        project_id=project.id,
        issue_id=issue.id,
        event_type="status_changed",
        details={"new_status": "Reasoning"},
    )
    assert log.id is not None
    assert log.project_id == project.id
    assert log.issue_id == issue.id
    assert log.event_type == "status_changed"
    assert log.get_details() == {"new_status": "Reasoning"}


@pytest.mark.asyncio
async def test_log_without_issue(db_session, project):
    svc = ActivityService(db_session)
    log = await svc.log(project_id=project.id, issue_id=None, event_type="project_updated")
    assert log.issue_id is None


@pytest.mark.asyncio
async def test_list_for_project_returns_logs(db_session, project, issue):
    svc = ActivityService(db_session)
    await svc.log(project_id=project.id, issue_id=issue.id, event_type="status_changed")
    await svc.log(project_id=project.id, issue_id=issue.id, event_type="spec_created")
    logs = await svc.list_for_project(project.id)
    assert len(logs) == 2


@pytest.mark.asyncio
async def test_list_for_project_filters_by_issue(db_session, project, issue):
    svc_issue = IssueService(db_session)
    other_issue = await svc_issue.create(project_id=project.id, description="Other", priority=2)
    svc = ActivityService(db_session)
    await svc.log(project_id=project.id, issue_id=issue.id, event_type="status_changed")
    await svc.log(project_id=project.id, issue_id=other_issue.id, event_type="status_changed")
    logs = await svc.list_for_project(project.id, issue_id=issue.id)
    assert len(logs) == 1
    assert logs[0].issue_id == issue.id


@pytest.mark.asyncio
async def test_list_for_project_ordered_newest_first(db_session, project):
    svc = ActivityService(db_session)
    await svc.log(project_id=project.id, issue_id=None, event_type="first")
    await svc.log(project_id=project.id, issue_id=None, event_type="second")
    logs = await svc.list_for_project(project.id)
    assert logs[0].event_type == "second"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_activity_service.py -v
```

Expected: FAIL — `ActivityService` not yet defined

- [ ] **Step 3: Create ActivityService**

Create `backend/app/services/activity_service.py`:

```python
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog


class ActivityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        project_id: str,
        issue_id: Optional[str],
        event_type: str,
        details: dict | None = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            project_id=project_id,
            issue_id=issue_id,
            event_type=event_type,
            details=json.dumps(details or {}),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_project(
        self,
        project_id: str,
        issue_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ActivityLog]:
        query = (
            select(ActivityLog)
            .where(ActivityLog.project_id == project_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if issue_id is not None:
            query = query.where(ActivityLog.issue_id == issue_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())
```

- [ ] **Step 4: Run service tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_activity_service.py -v
```

Expected: all PASS

- [ ] **Step 5: Create Pydantic schema**

Create `backend/app/schemas/activity.py`:

```python
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator
import json


class ActivityLogResponse(BaseModel):
    id: str
    project_id: str
    issue_id: Optional[str]
    event_type: str
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("details", mode="before")
    @classmethod
    def parse_details(cls, v: Any) -> dict:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}
```

- [ ] **Step 6: Write router tests**

Create `backend/tests/test_routers_activity.py`:

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.services.activity_service import ActivityService
from app.services.project_service import ProjectService
from app.services.issue_service import IssueService


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def project(db_session):
    svc = ProjectService(db_session)
    return await svc.create(name="Activity Router Test", path="/tmp/ar", description="")


@pytest_asyncio.fixture
async def issue(db_session, project):
    svc = IssueService(db_session)
    return await svc.create(project_id=project.id, description="Test issue", priority=1)


@pytest.mark.asyncio
async def test_list_activity_empty(client, project):
    resp = await client.get(f"/api/projects/{project['id'] if isinstance(project, dict) else project.id}/activity")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_activity_returns_logs(client, db_session, project):
    pid = project.id
    svc = ActivityService(db_session)
    await svc.log(project_id=pid, issue_id=None, event_type="test_event", details={"key": "value"})
    await db_session.flush()
    resp = await client.get(f"/api/projects/{pid}/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_type"] == "test_event"
    assert data[0]["details"] == {"key": "value"}


@pytest.mark.asyncio
async def test_list_activity_filter_by_issue(client, db_session, project, issue):
    pid = project.id
    svc = ActivityService(db_session)
    await svc.log(project_id=pid, issue_id=issue.id, event_type="issue_event")
    await svc.log(project_id=pid, issue_id=None, event_type="project_event")
    await db_session.flush()
    resp = await client.get(f"/api/projects/{pid}/activity?issue_id={issue.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_type"] == "issue_event"


@pytest.mark.asyncio
async def test_list_activity_project_not_found(client):
    resp = await client.get("/api/projects/nonexistent-id/activity")
    assert resp.status_code == 404
```

- [ ] **Step 7: Run router tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_routers_activity.py -v
```

Expected: FAIL — router not registered yet

- [ ] **Step 8: Create the activity router**

Create `backend/app/routers/activity.py`:

```python
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError
from app.schemas.activity import ActivityLogResponse
from app.services.activity_service import ActivityService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/activity", tags=["activity"])


@router.get("", response_model=list[ActivityLogResponse])
async def list_activity(
    project_id: str,
    issue_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    project_service = ProjectService(db)
    await project_service.get_by_id(project_id)  # raises NotFoundError if not found
    activity_service = ActivityService(db)
    return await activity_service.list_for_project(
        project_id, issue_id=issue_id, limit=limit, offset=offset
    )
```

- [ ] **Step 9: Register the router in main.py**

In `backend/app/main.py`, add to the imports:
```python
from app.routers import activity, events, files, issues, projects, settings as settings_router, tasks, terminals, terminal_commands
```

And add after the existing `app.include_router(events.router)` line:
```python
app.include_router(activity.router)
```

- [ ] **Step 10: Run router tests**

```bash
cd backend && python -m pytest tests/test_routers_activity.py -v
```

Expected: all PASS

- [ ] **Step 11: Run full test suite**

```bash
cd backend && python -m pytest -x -q
```

Expected: all pass

- [ ] **Step 12: Commit**

```bash
git add backend/app/services/activity_service.py backend/app/schemas/activity.py \
        backend/app/routers/activity.py backend/app/main.py \
        backend/tests/test_activity_service.py backend/tests/test_routers_activity.py
git commit -m "feat: ActivityService, schema and router (3.3)"
```

---

## Task 6: Integrate activity logging in IssueService and hooks (3.3)

**Files:**
- Modify: `backend/app/services/issue_service.py`
- Modify: `backend/app/hooks/registry.py`
- Test: add assertions to `backend/tests/test_issue_service.py`

- [ ] **Step 1: Write tests for activity log creation**

Add to `backend/tests/test_issue_service.py`:

```python
from app.services.activity_service import ActivityService


async def test_create_spec_logs_activity(db_session, project):
    svc = IssueService(db_session)
    activity_svc = ActivityService(db_session)
    issue = await svc.create(project_id=project.id, description="Log test", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    logs = await activity_svc.list_for_project(project.id, issue_id=issue.id)
    assert any(log.event_type == "spec_created" for log in logs)


async def test_create_plan_logs_activity(db_session, project):
    svc = IssueService(db_session)
    activity_svc = ActivityService(db_session)
    issue = await svc.create(project_id=project.id, description="Plan log test", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    await svc.create_plan(issue.id, project.id, "# Plan")
    logs = await activity_svc.list_for_project(project.id, issue_id=issue.id)
    assert any(log.event_type == "plan_created" for log in logs)


async def test_complete_issue_logs_activity(db_session, project):
    svc = IssueService(db_session)
    activity_svc = ActivityService(db_session)
    issue = await svc.create(project_id=project.id, description="Complete log test", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    await svc.create_plan(issue.id, project.id, "# Plan")
    await svc.accept_issue(issue.id, project.id)
    await svc.complete_issue(issue.id, project.id, "Done")
    logs = await activity_svc.list_for_project(project.id, issue_id=issue.id)
    assert any(log.event_type == "issue_completed" for log in logs)
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_issue_service.py::test_create_spec_logs_activity -v
```

Expected: FAIL — no activity logs created yet

- [ ] **Step 3: Add ActivityService calls to IssueService**

In `backend/app/services/issue_service.py`, add the import:
```python
from app.services.activity_service import ActivityService
```

Then add `await ActivityService(self.session).log(...)` calls to these methods. Each call goes after the `await self.session.flush()`:

**`create_spec`** — add after flush:
```python
async def create_spec(self, issue_id: str, project_id: str, spec: str) -> Issue:
    if not spec or not spec.strip():
        raise ValidationError("Specification cannot be blank")
    issue = await self.get_for_project(issue_id, project_id)
    if issue.status != IssueStatus.NEW:
        raise InvalidTransitionError(
            f"Can only create spec for issues in New status, got {issue.status.value}"
        )
    issue.specification = spec
    issue.status = IssueStatus.REASONING
    await self.session.flush()
    await ActivityService(self.session).log(
        project_id=project_id,
        issue_id=issue_id,
        event_type="spec_created",
        details={"issue_name": issue.name or ""},
    )
    return issue
```

**`create_plan`** — add after flush:
```python
async def create_plan(self, issue_id: str, project_id: str, plan: str) -> Issue:
    if not plan or not plan.strip():
        raise ValidationError("Plan cannot be blank")
    issue = await self.get_for_project(issue_id, project_id)
    if issue.status != IssueStatus.REASONING:
        raise InvalidTransitionError(
            f"Can only create plan for issues in Reasoning status, got {issue.status.value}"
        )
    issue.plan = plan
    issue.status = IssueStatus.PLANNED
    await self.session.flush()
    await ActivityService(self.session).log(
        project_id=project_id,
        issue_id=issue_id,
        event_type="plan_created",
        details={"issue_name": issue.name or ""},
    )
    return issue
```

**`accept_issue`** — add after flush, before hook:
```python
async def accept_issue(self, issue_id: str, project_id: str) -> Issue:
    issue = await self.get_for_project(issue_id, project_id)
    if issue.status != IssueStatus.PLANNED:
        raise InvalidTransitionError(
            f"Can only accept issues in Planned status, got {issue.status.value}"
        )
    issue.status = IssueStatus.ACCEPTED
    await self.session.flush()
    await ActivityService(self.session).log(
        project_id=project_id,
        issue_id=issue_id,
        event_type="issue_accepted",
        details={"issue_name": issue.name or ""},
    )
    await hook_registry.fire(
        HookEvent.ISSUE_ACCEPTED,
        HookContext(project_id=project_id, issue_id=issue_id, event=HookEvent.ISSUE_ACCEPTED),
    )
    return issue
```

**`cancel_issue`** — add after flush, before hook:
```python
async def cancel_issue(self, issue_id: str, project_id: str) -> Issue:
    issue = await self.get_for_project(issue_id, project_id)
    issue.status = IssueStatus.CANCELED
    await self.session.flush()
    await ActivityService(self.session).log(
        project_id=project_id,
        issue_id=issue_id,
        event_type="issue_canceled",
        details={"issue_name": issue.name or ""},
    )
    await hook_registry.fire(
        HookEvent.ISSUE_CANCELLED,
        HookContext(project_id=project_id, issue_id=issue_id, event=HookEvent.ISSUE_CANCELLED),
    )
    return issue
```

**`complete_issue`** — add after `issue.status = IssueStatus.FINISHED` flush, before existing hook:
```python
    issue.recap = recap
    issue.status = IssueStatus.FINISHED
    await self.session.flush()
    await ActivityService(self.session).log(
        project_id=project_id,
        issue_id=issue_id,
        event_type="issue_completed",
        details={"issue_name": issue.name or "", "recap_preview": (recap or "")[:100]},
    )
    # Fire hook with project context ...
```

**`start_analysis`** — add at end before return:
```python
    await hook_registry.fire(...)
    await ActivityService(self.session).log(
        project_id=project_id,
        issue_id=issue_id,
        event_type="analysis_started",
        details={"issue_name": issue.name or ""},
    )
    return issue
```

- [ ] **Step 4: Run the new tests**

```bash
cd backend && python -m pytest tests/test_issue_service.py -v -k "logs_activity"
```

Expected: all 3 PASS

- [ ] **Step 5: Add hook activity logging to registry.py**

In `backend/app/hooks/registry.py`, in `_run_hook` after each `event_service.emit(...)` call, add an activity log. Use a lazy import inside the method to avoid circular dependencies:

```python
async def _run_hook(self, hook_class: type[BaseHook], context: HookContext) -> None:
    hook = hook_class()
    now = datetime.now(timezone.utc).isoformat()

    await event_service.emit({
        "type": "hook_started",
        "hook_name": hook.name,
        "hook_description": hook.description,
        "issue_id": context.issue_id,
        "project_id": context.project_id,
        "issue_name": context.metadata.get("issue_name", ""),
        "project_name": context.metadata.get("project_name", ""),
        "timestamp": now,
    })

    try:
        result = await hook.execute(context)
    except Exception as exc:
        logger.error("Hook %s failed with exception: %s", hook.name, exc)
        await event_service.emit({
            "type": "hook_failed",
            "hook_name": hook.name,
            "issue_id": context.issue_id,
            "project_id": context.project_id,
            "issue_name": context.metadata.get("issue_name", ""),
            "project_name": context.metadata.get("project_name", ""),
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await self._log_activity(context.project_id, context.issue_id, "hook_failed", {
            "hook_name": hook.name, "error": str(exc)
        })
        return

    if result.success:
        await event_service.emit({
            "type": "hook_completed",
            "hook_name": hook.name,
            "issue_id": context.issue_id,
            "project_id": context.project_id,
            "issue_name": context.metadata.get("issue_name", ""),
            "project_name": context.metadata.get("project_name", ""),
            "output": result.output,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await self._log_activity(context.project_id, context.issue_id, "hook_completed", {
            "hook_name": hook.name
        })
    else:
        logger.warning("Hook %s returned error: %s", hook.name, result.error)
        await event_service.emit({
            "type": "hook_failed",
            "hook_name": hook.name,
            "issue_id": context.issue_id,
            "project_id": context.project_id,
            "issue_name": context.metadata.get("issue_name", ""),
            "project_name": context.metadata.get("project_name", ""),
            "error": result.error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await self._log_activity(context.project_id, context.issue_id, "hook_failed", {
            "hook_name": hook.name, "error": result.error
        })

async def _log_activity(self, project_id: str, issue_id: str, event_type: str, details: dict) -> None:
    try:
        from app.database import async_session
        from app.services.activity_service import ActivityService
        async with async_session() as session:
            svc = ActivityService(session)
            await svc.log(project_id=project_id, issue_id=issue_id, event_type=event_type, details=details)
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to log activity for hook event: %s", exc)
```

- [ ] **Step 6: Run full test suite**

```bash
cd backend && python -m pytest -x -q
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/issue_service.py backend/app/hooks/registry.py \
        backend/tests/test_issue_service.py
git commit -m "feat: log activity in IssueService and hook registry (3.3)"
```

---

## Task 7: Activity frontend (3.3)

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Create: `frontend/src/features/activity/api.ts`
- Create: `frontend/src/features/activity/hooks.ts`
- Create: `frontend/src/features/activity/components/activity-timeline.tsx`
- Create: `frontend/src/routes/projects/$projectId/activity.tsx`
- Modify: `frontend/src/shared/components/app-sidebar.tsx`

- [ ] **Step 1: Add ActivityLog type to shared types**

In `frontend/src/shared/types/index.ts`, add at the end:

```typescript
// ── Activity ──

export interface ActivityLog {
  id: string;
  project_id: string;
  issue_id: string | null;
  event_type: string;
  details: Record<string, unknown>;
  created_at: string;
}
```

- [ ] **Step 2: Create activity API**

Create `frontend/src/features/activity/api.ts`:

```typescript
import { request } from "@/shared/api/client";
import type { ActivityLog } from "@/shared/types";

export function fetchActivity(
  projectId: string,
  params?: { issue_id?: string; limit?: number; offset?: number }
): Promise<ActivityLog[]> {
  const query = new URLSearchParams();
  if (params?.issue_id) query.set("issue_id", params.issue_id);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));
  const qs = query.toString();
  return request(`/projects/${projectId}/activity${qs ? `?${qs}` : ""}`);
}
```

- [ ] **Step 3: Create activity hooks**

Create `frontend/src/features/activity/hooks.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import * as api from "./api";

export const activityKeys = {
  list: (projectId: string, issueId?: string) =>
    ["projects", projectId, "activity", { issueId }] as const,
};

export function useActivity(projectId: string, issueId?: string) {
  return useQuery({
    queryKey: activityKeys.list(projectId, issueId),
    queryFn: () => api.fetchActivity(projectId, issueId ? { issue_id: issueId } : undefined),
  });
}
```

- [ ] **Step 4: Create the activity timeline component**

Create `frontend/src/features/activity/components/activity-timeline.tsx`:

```tsx
import { formatDistanceToNow } from "date-fns";
import {
  CheckCircle,
  XCircle,
  FileText,
  GitBranch,
  PlayCircle,
  Zap,
  ZapOff,
  Bell,
  Activity,
} from "lucide-react";
import type { ActivityLog } from "@/shared/types";

const EVENT_CONFIG: Record<string, { label: string; Icon: React.ElementType; className: string }> = {
  spec_created:      { label: "Spec written",      Icon: FileText,   className: "text-blue-500" },
  plan_created:      { label: "Plan written",       Icon: GitBranch,  className: "text-purple-500" },
  issue_accepted:    { label: "Plan accepted",      Icon: CheckCircle,className: "text-green-500" },
  issue_completed:   { label: "Issue completed",    Icon: CheckCircle,className: "text-green-600" },
  issue_canceled:    { label: "Issue canceled",     Icon: XCircle,    className: "text-gray-400" },
  analysis_started:  { label: "Analysis started",   Icon: PlayCircle, className: "text-indigo-500" },
  hook_completed:    { label: "Hook completed",     Icon: Zap,        className: "text-green-500" },
  hook_failed:       { label: "Hook failed",        Icon: ZapOff,     className: "text-red-500" },
  notification:      { label: "Notification",       Icon: Bell,       className: "text-blue-400" },
};

function getConfig(eventType: string) {
  return EVENT_CONFIG[eventType] ?? { label: eventType, Icon: Activity, className: "text-muted-foreground" };
}

interface ActivityTimelineProps {
  logs: ActivityLog[];
}

export function ActivityTimeline({ logs }: ActivityTimelineProps) {
  if (logs.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        No activity yet.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {logs.map((log) => {
        const { label, Icon, className } = getConfig(log.event_type);
        const issueName = log.details.issue_name as string | undefined;
        const hookName = log.details.hook_name as string | undefined;
        const errorMsg = log.details.error as string | undefined;

        return (
          <div key={log.id} className="flex gap-3 px-3 py-2.5 rounded-md hover:bg-muted/50 transition-colors">
            <div className={`mt-0.5 shrink-0 ${className}`}>
              <Icon className="size-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium truncate">
                  {label}
                  {hookName && ` — ${hookName}`}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                </span>
              </div>
              {issueName && (
                <div className="text-xs text-muted-foreground truncate">{issueName}</div>
              )}
              {errorMsg && (
                <div className="text-xs text-red-500 truncate">{errorMsg}</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 5: Create the activity route**

Create `frontend/src/routes/projects/$projectId/activity.tsx`:

```tsx
import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useActivity } from "@/features/activity/hooks";
import { useIssues } from "@/features/issues/hooks";
import { ActivityTimeline } from "@/features/activity/components/activity-timeline";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId/activity")({
  component: ActivityPage,
});

function ActivityPage() {
  const { projectId } = Route.useParams();
  const [selectedIssueId, setSelectedIssueId] = useState<string | undefined>(undefined);

  const { data: logs, isLoading, error } = useActivity(projectId, selectedIssueId);
  const { data: issues } = useIssues(projectId);

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-32" />
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-destructive">{error.message}</div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Activity</h1>
        <select
          value={selectedIssueId ?? ""}
          onChange={(e) => setSelectedIssueId(e.target.value || undefined)}
          className="text-sm border rounded-md px-2 py-1 bg-background"
        >
          <option value="">All issues</option>
          {(issues ?? []).map((issue) => (
            <option key={issue.id} value={issue.id}>
              {issue.name || issue.description.slice(0, 50)}
            </option>
          ))}
        </select>
      </div>
      <ActivityTimeline logs={logs ?? []} />
    </div>
  );
}
```

- [ ] **Step 6: Add Activity link to app-sidebar.tsx**

In `frontend/src/shared/components/app-sidebar.tsx`, add the `Activity` icon import:
```tsx
import {
  Activity,
  CircleDot,
  // ... existing imports ...
} from "lucide-react";
```

Add to the `projectNav` array:
```tsx
const projectNav = projectId
  ? [
      {
        label: "Issues",
        to: "/projects/$projectId/issues" as const,
        params: { projectId },
        icon: CircleDot,
      },
      {
        label: "Files",
        to: "/projects/$projectId/files" as const,
        params: { projectId },
        icon: FileText,
      },
      {
        label: "Commands",
        to: "/projects/$projectId/commands" as const,
        params: { projectId },
        icon: SquareTerminal,
      },
      {
        label: "Activity",
        to: "/projects/$projectId/activity" as const,
        params: { projectId },
        icon: Activity,
      },
    ]
  : [];
```

- [ ] **Step 7: Install date-fns if not already present**

```bash
cd frontend && npm list date-fns 2>/dev/null || npm install date-fns
```

- [ ] **Step 8: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors

- [ ] **Step 9: Verify in browser**

Run `python start.py` and:
1. Go to a project → sidebar shows "Activity" link
2. Click Activity → page loads with empty state or existing logs
3. Trigger a Claude MCP action (e.g. start analysis on an issue)
4. Return to Activity page → the log entry appears
5. Use the issue filter dropdown → logs filter correctly

- [ ] **Step 10: Commit**

```bash
git add frontend/src/shared/types/index.ts \
        frontend/src/features/activity/ \
        frontend/src/routes/projects/\$projectId/activity.tsx \
        frontend/src/shared/components/app-sidebar.tsx
git commit -m "feat: activity log frontend — timeline page, sidebar nav (3.3)"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Implemented by |
|-------------|---------------|
| `issue_status_changed` events | Task 1 — MCP issue tools emit after commit |
| `task_updated` events | Task 2 — MCP task tools emit after commit |
| `issue_content_updated` events | Task 1 — edit_spec, edit_plan, set_name tools |
| EventContext auto-refresh | Already in EventContext; events now actually fired |
| IssueDetailPage refreshes | Via queryClient.invalidateQueries in EventContext |
| ProjectDetailPage refreshes | Via queryClient.invalidateQueries in EventContext |
| Typed toasts: error/success/info | Task 3 — showTypedToast() in EventContext |
| `hook_failed` → red toast | Task 3 |
| `hook_completed` → green toast | Task 3 |
| `notification` → blue toast | Task 3 |
| Sound toggle in settings | Task 3 — localStorage + Preferences tab |
| ActivityLog model | Task 4 |
| Log issue transitions | Task 6 — IssueService |
| Log hook events | Task 6 — HookRegistry._log_activity |
| Activity page (scrollable timeline) | Task 7 |
| Filter by project/issue | Task 7 — dropdown filter in ActivityPage |

**Placeholder scan:** No TODOs or TBDs. All code blocks complete.

**Type consistency:** `ActivityLog.event_type` uses string constants (`"spec_created"`, `"plan_created"`, etc.) consistently between backend and frontend `EVENT_CONFIG` map.

**Note on `project_updated` event:** The `update_project_context` MCP tool emits `{ type: "project_updated", project_id }` (no `issue_id`). The EventContext handles this via the `else if (projectId)` branch which invalidates `["projects", projectId]`. The activity log is NOT written for project updates (only issue-level activities are logged); this is intentional — project context edits are not tracked as activity.
