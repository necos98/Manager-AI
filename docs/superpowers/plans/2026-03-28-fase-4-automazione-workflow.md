# Fase 4 — Automazione del Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trasformare Manager AI da "issue tracker con terminale" a "AI project manager che lavora per te" attraverso 4 subsistemi: auto-start workflow (4.1), auto-start implementazione (4.2), auto-completion detection (4.3), e coda di lavoro (4.4).

**Architecture:** Hook event-driven — aggiunge `ISSUE_CREATED` e `ALL_TASKS_COMPLETED` all'enum esistente. Usa il pattern `@hook(event=...)` già consolidato. Per-project settings salvate nel modello `Setting` con chiavi namespaced `project:{project_id}:{key}` tramite un nuovo `ProjectSettingService`, senza nuove tabelle. I nuovi handler si registrano via import in `handlers/__init__.py` come gli esistenti.

**Tech Stack:** FastAPI, SQLAlchemy async, Python asyncio, ClaudeCodeExecutor, React/JSX, Vite

---

## File Map

**Create (backend):**
- `backend/app/services/project_setting_service.py` — get/set per-project settings (namespace `project:{id}:{key}`)
- `backend/app/schemas/project_setting.py` — Pydantic schemas per-project settings
- `backend/app/routers/project_settings.py` — REST API per-project settings
- `backend/app/hooks/handlers/auto_start_workflow.py` — 4.1: fires on ISSUE_CREATED
- `backend/app/hooks/handlers/auto_start_implementation.py` — 4.2: fires on ISSUE_ACCEPTED
- `backend/app/hooks/handlers/auto_completion.py` — 4.3: fires on ALL_TASKS_COMPLETED
- `backend/tests/test_project_setting_service.py`
- `backend/tests/test_auto_start_workflow.py`
- `backend/tests/test_auto_start_implementation.py`
- `backend/tests/test_auto_completion.py`
- `backend/tests/test_work_queue.py`

**Create (frontend):**
- `frontend/src/api/projectSettings.js`
- `frontend/src/components/AutomationPanel.jsx`
- `frontend/src/components/WorkQueueStatus.jsx`

**Modify (backend):**
- `backend/app/hooks/registry.py` — add `ISSUE_CREATED`, `ALL_TASKS_COMPLETED` to `HookEvent`
- `backend/app/services/issue_service.py` — fire ISSUE_CREATED in `create()`; enrich `accept_issue()` metadata; update `get_next_issue()` priority
- `backend/app/services/task_service.py` — add `all_completed(issue_id)` method
- `backend/app/hooks/handlers/__init__.py` — import new handlers
- `backend/app/mcp/server.py` — fire ALL_TASKS_COMPLETED in `update_task_status`; add `get_next_issue` tool
- `backend/app/routers/tasks.py` — fire ALL_TASKS_COMPLETED after REST task update
- `backend/app/mcp/default_settings.json` — add `work_queue_paused`, `get_next_issue` tool description
- `backend/app/main.py` — include project_settings router

**Modify (frontend):**
- `frontend/src/pages/ProjectDetailPage.jsx` — embed AutomationPanel + WorkQueueStatus

---

## Task 1: HookEvent.ISSUE_CREATED + ALL_TASKS_COMPLETED, fire ISSUE_CREATED from IssueService.create()

**Files:**
- Modify: `backend/app/hooks/registry.py:17-21`
- Modify: `backend/app/services/issue_service.py:21-25`
- Modify: `backend/tests/test_issue_service_hooks.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_issue_service_hooks.py`:
```python
@patch("app.services.issue_service.hook_registry")
async def test_create_issue_fires_issue_created_hook(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    await service.create(project_id=project.id, description="New issue", priority=2)
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_CREATED
    ctx = args[0][1]
    assert ctx.project_id == project.id
    assert ctx.metadata["issue_description"] == "New issue"
    assert ctx.metadata["project_name"] == "Test"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_issue_service_hooks.py::test_create_issue_fires_issue_created_hook -v
```
Expected: FAIL — `AttributeError: 'HookEvent' object has no value 'ISSUE_CREATED'`

- [ ] **Step 3: Add new events to HookEvent in registry.py**

In `backend/app/hooks/registry.py`, replace the `HookEvent` class body:
```python
class HookEvent(str, Enum):
    ISSUE_COMPLETED = "issue_completed"
    ISSUE_ACCEPTED = "issue_accepted"
    ISSUE_CANCELLED = "issue_cancelled"
    ISSUE_ANALYSIS_STARTED = "issue_analysis_started"
    ISSUE_CREATED = "issue_created"
    ALL_TASKS_COMPLETED = "all_tasks_completed"
```

- [ ] **Step 4: Fire ISSUE_CREATED in IssueService.create()**

In `backend/app/services/issue_service.py`, replace the entire `create()` method:
```python
async def create(self, project_id: str, description: str, priority: int = 3) -> Issue:
    issue = Issue(project_id=project_id, description=description, priority=priority)
    self.session.add(issue)
    await self.session.flush()
    project_service = ProjectService(self.session)
    project = await project_service.get_by_id(project_id)
    await hook_registry.fire(
        HookEvent.ISSUE_CREATED,
        HookContext(
            project_id=project_id,
            issue_id=issue.id,
            event=HookEvent.ISSUE_CREATED,
            metadata={
                "issue_description": description,
                "project_name": project.name if project else "",
                "project_path": project.path if project else "",
                "project_description": project.description if project else "",
                "tech_stack": project.tech_stack if project else "",
            },
        ),
    )
    return issue
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_issue_service_hooks.py::test_create_issue_fires_issue_created_hook -v
```
Expected: PASS

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all previously passing tests still PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/hooks/registry.py backend/app/services/issue_service.py backend/tests/test_issue_service_hooks.py
git commit -m "feat: add ISSUE_CREATED and ALL_TASKS_COMPLETED to HookEvent, fire ISSUE_CREATED on issue create"
```

---

## Task 2: ProjectSettingService — per-project key-value settings

**Files:**
- Create: `backend/app/services/project_setting_service.py`
- Create: `backend/app/schemas/project_setting.py`
- Create: `backend/app/routers/project_settings.py`
- Create: `backend/tests/test_project_setting_service.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_project_setting_service.py`:
```python
import pytest_asyncio
from app.services.project_setting_service import ProjectSettingService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(name="Proj", path="/tmp/p", description="")


async def test_get_returns_default_when_not_set(db_session, project):
    svc = ProjectSettingService(db_session)
    value = await svc.get(project.id, "auto_workflow_enabled", default="false")
    assert value == "false"


async def test_set_and_get(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await db_session.commit()
    value = await svc.get(project.id, "auto_workflow_enabled", default="false")
    assert value == "true"


async def test_get_all_for_project(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await svc.set(project.id, "auto_implementation_enabled", "false")
    await db_session.commit()
    all_settings = await svc.get_all_for_project(project.id)
    assert all_settings["auto_workflow_enabled"] == "true"
    assert all_settings["auto_implementation_enabled"] == "false"


async def test_set_overwrites_existing(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await db_session.commit()
    await svc.set(project.id, "auto_workflow_enabled", "false")
    await db_session.commit()
    value = await svc.get(project.id, "auto_workflow_enabled", default="true")
    assert value == "false"


async def test_delete_setting(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await db_session.commit()
    await svc.delete(project.id, "auto_workflow_enabled")
    await db_session.commit()
    value = await svc.get(project.id, "auto_workflow_enabled", default="false")
    assert value == "false"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_project_setting_service.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.project_setting_service'`

- [ ] **Step 3: Implement ProjectSettingService**

Create `backend/app/services/project_setting_service.py`:
```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting


class ProjectSettingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _key(self, project_id: str, key: str) -> str:
        return f"project:{project_id}:{key}"

    async def get(self, project_id: str, key: str, default: str = "") -> str:
        row = await self.session.get(Setting, self._key(project_id, key))
        return row.value if row else default

    async def set(self, project_id: str, key: str, value: str) -> None:
        full_key = self._key(project_id, key)
        row = await self.session.get(Setting, full_key)
        if row is None:
            self.session.add(Setting(key=full_key, value=value))
        else:
            row.value = value
        await self.session.flush()

    async def delete(self, project_id: str, key: str) -> None:
        row = await self.session.get(Setting, self._key(project_id, key))
        if row is not None:
            await self.session.delete(row)
            await self.session.flush()

    async def get_all_for_project(self, project_id: str) -> dict[str, str]:
        prefix = f"project:{project_id}:"
        result = await self.session.execute(
            select(Setting).where(Setting.key.like(f"{prefix}%"))
        )
        return {row.key[len(prefix):]: row.value for row in result.scalars().all()}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_project_setting_service.py -v
```
Expected: PASS (5 tests)

- [ ] **Step 5: Create Pydantic schemas**

Create `backend/app/schemas/project_setting.py`:
```python
from pydantic import BaseModel


class ProjectSettingSet(BaseModel):
    value: str


class ProjectSettingOut(BaseModel):
    key: str
    value: str
```

- [ ] **Step 6: Create the router**

Create `backend/app/routers/project_settings.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_setting import ProjectSettingOut, ProjectSettingSet
from app.services.project_setting_service import ProjectSettingService

router = APIRouter(prefix="/api/projects/{project_id}/settings", tags=["project-settings"])


@router.get("", response_model=dict[str, str])
async def get_project_settings(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectSettingService(db)
    return await svc.get_all_for_project(project_id)


@router.put("/{key}", response_model=ProjectSettingOut)
async def set_project_setting(
    project_id: str, key: str, data: ProjectSettingSet, db: AsyncSession = Depends(get_db)
):
    svc = ProjectSettingService(db)
    await svc.set(project_id, key, data.value)
    await db.commit()
    return ProjectSettingOut(key=key, value=data.value)


@router.delete("/{key}", status_code=204)
async def delete_project_setting(
    project_id: str, key: str, db: AsyncSession = Depends(get_db)
):
    svc = ProjectSettingService(db)
    await svc.delete(project_id, key)
    await db.commit()
```

- [ ] **Step 7: Register router in main.py**

In `backend/app/main.py`, change the routers import line to:
```python
from app.routers import activity, events, files, issues, project_settings, projects, settings as settings_router, tasks, terminals, terminal_commands
```

And after `app.include_router(projects.router)`, add:
```python
app.include_router(project_settings.router)
```

- [ ] **Step 8: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/project_setting_service.py backend/app/schemas/project_setting.py backend/app/routers/project_settings.py backend/tests/test_project_setting_service.py backend/app/main.py
git commit -m "feat: ProjectSettingService and REST API for per-project settings"
```

---

## Task 3: AutoStartWorkflow handler (4.1)

**Files:**
- Create: `backend/app/hooks/handlers/auto_start_workflow.py`
- Create: `backend/tests/test_auto_start_workflow.py`
- Modify: `backend/app/hooks/handlers/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_auto_start_workflow.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio

from app.hooks.registry import HookContext, HookEvent
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(
        name="Proj", path="/tmp/p", description="Desc", tech_stack="Python"
    )


@patch("app.hooks.handlers.auto_start_workflow.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_workflow.ProjectSettingService")
async def test_auto_start_runs_claude_when_enabled(MockSettingService, MockExecutor, db_session, project):
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(side_effect=lambda pid, key, default="": {
        "auto_workflow_enabled": "true",
        "auto_workflow_prompt": "",
        "auto_workflow_timeout": "600",
    }.get(key, default))
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    mock_exec.run = AsyncMock(return_value=MagicMock(success=True, output="done", error=None))
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_workflow import AutoStartWorkflow
    handler = AutoStartWorkflow()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_CREATED,
        metadata={
            "issue_description": "Build a login page",
            "project_name": project.name,
            "project_path": project.path,
            "project_description": project.description,
            "tech_stack": project.tech_stack,
        },
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_called_once()
    call_kwargs = mock_exec.run.call_args
    prompt_used = call_kwargs.kwargs.get("prompt") or call_kwargs.args[0]
    assert "Build a login page" in prompt_used


@patch("app.hooks.handlers.auto_start_workflow.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_workflow.ProjectSettingService")
async def test_auto_start_skips_when_disabled(MockSettingService, MockExecutor, db_session, project):
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="false")
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_workflow import AutoStartWorkflow
    handler = AutoStartWorkflow()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_CREATED,
        metadata={"issue_description": "Test", "project_path": project.path},
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_not_called()


@patch("app.hooks.handlers.auto_start_workflow.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_workflow.ProjectSettingService")
async def test_auto_start_uses_custom_prompt(MockSettingService, MockExecutor, db_session, project):
    custom = "Custom: {{issue_description}} per {{project_name}}"
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(side_effect=lambda pid, key, default="": {
        "auto_workflow_enabled": "true",
        "auto_workflow_prompt": custom,
        "auto_workflow_timeout": "300",
    }.get(key, default))
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    mock_exec.run = AsyncMock(return_value=MagicMock(success=True, output="ok", error=None))
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_workflow import AutoStartWorkflow
    handler = AutoStartWorkflow()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_CREATED,
        metadata={
            "issue_description": "Fix the bug",
            "project_name": "MyApp",
            "project_path": project.path,
            "project_description": "",
            "tech_stack": "",
        },
    )
    result = await handler.execute(ctx)
    prompt_used = mock_exec.run.call_args.kwargs.get("prompt") or mock_exec.run.call_args.args[0]
    assert "Fix the bug" in prompt_used
    assert "MyApp" in prompt_used
    assert "Custom:" in prompt_used
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_auto_start_workflow.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.hooks.handlers.auto_start_workflow'`

- [ ] **Step 3: Implement AutoStartWorkflow handler**

Create `backend/app/hooks/handlers/auto_start_workflow.py`:
```python
"""AutoStartWorkflow hook: when an issue is created and auto_workflow_enabled is true for
   the project, spawns Claude Code to write spec, plan, and tasks automatically."""
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService


@hook(event=HookEvent.ISSUE_CREATED)
class AutoStartWorkflow(BaseHook):
    name = "auto_start_workflow"
    description = "Avvia automaticamente spec+piano+task quando viene creata una issue"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            enabled = await svc.get(context.project_id, "auto_workflow_enabled", default="false")
            if enabled != "true":
                return HookResult(success=True, output="auto_workflow disabled for this project")
            custom_prompt = await svc.get(context.project_id, "auto_workflow_prompt", default="")
            timeout_str = await svc.get(context.project_id, "auto_workflow_timeout", default="600")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 600

        issue_description = context.metadata.get("issue_description", "")
        project_name = context.metadata.get("project_name", "")
        project_path = context.metadata.get("project_path", "")
        project_description = context.metadata.get("project_description", "")
        tech_stack = context.metadata.get("tech_stack", "")

        if custom_prompt:
            prompt = (
                custom_prompt
                .replace("{{issue_description}}", issue_description)
                .replace("{{project_name}}", project_name)
                .replace("{{project_description}}", project_description)
                .replace("{{tech_stack}}", tech_stack)
            )
        else:
            prompt = f"""Sei il project manager di "{project_name}".

È stata creata una nuova issue con questa descrizione:
{issue_description}

Contesto del progetto:
{project_description}
Tech stack: {tech_stack}

Il tuo compito:
1. Usa `create_issue_spec` per scrivere una specifica tecnica dettagliata
2. Usa `create_issue_plan` per scrivere un piano di implementazione step-by-step
3. Usa `create_plan_tasks` per creare i task atomici del piano
4. Usa `send_notification` per notificare l'utente che il piano è pronto per la review

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Lavora in sequenza, non saltare passi."""

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": context.project_id,
                "MANAGER_AI_ISSUE_ID": context.issue_id,
            },
            timeout=timeout,
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
```

- [ ] **Step 4: Register handler in __init__.py**

In `backend/app/hooks/handlers/__init__.py`:
```python
"""Hook handlers package: import modules here to trigger @hook decorator autodiscovery."""

from app.hooks.handlers import auto_start_workflow  # noqa: F401
from app.hooks.handlers import enrich_context  # noqa: F401
from app.hooks.handlers import start_analysis  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_auto_start_workflow.py -v
```
Expected: PASS (3 tests)

- [ ] **Step 6: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/hooks/handlers/auto_start_workflow.py backend/app/hooks/handlers/__init__.py backend/tests/test_auto_start_workflow.py
git commit -m "feat: AutoStartWorkflow handler — auto-generates spec/plan/tasks on issue creation (4.1)"
```

---

## Task 4: ALL_TASKS_COMPLETED detection + TaskService.all_completed()

**Files:**
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/mcp/server.py` (`update_task_status`)
- Modify: `backend/app/routers/tasks.py` (`update_task` endpoint)
- Create: `backend/tests/test_auto_completion.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_auto_completion.py`:
```python
import pytest_asyncio
from app.models.task import TaskStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(name="Test", path="/tmp/t", description="")


async def test_all_completed_true_when_all_done(db_session, project):
    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)
    issue = await issue_svc.create(project_id=project.id, description="Test")
    await task_svc.create_bulk(issue.id, [{"name": "Task A"}, {"name": "Task B"}])
    await db_session.commit()
    tasks = await task_svc.list_by_issue(issue.id)
    for t in tasks:
        await task_svc.update(t.id, status=TaskStatus.IN_PROGRESS)
        await task_svc.update(t.id, status=TaskStatus.COMPLETED)
    result = await task_svc.all_completed(issue.id)
    assert result is True


async def test_all_completed_false_when_some_pending(db_session, project):
    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)
    issue = await issue_svc.create(project_id=project.id, description="Test")
    await task_svc.create_bulk(issue.id, [{"name": "Task A"}, {"name": "Task B"}])
    await db_session.commit()
    tasks = await task_svc.list_by_issue(issue.id)
    await task_svc.update(tasks[0].id, status=TaskStatus.IN_PROGRESS)
    await task_svc.update(tasks[0].id, status=TaskStatus.COMPLETED)
    # tasks[1] remains PENDING
    result = await task_svc.all_completed(issue.id)
    assert result is False


async def test_all_completed_false_when_no_tasks(db_session, project):
    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)
    issue = await issue_svc.create(project_id=project.id, description="Test")
    await db_session.commit()
    result = await task_svc.all_completed(issue.id)
    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_auto_completion.py -v
```
Expected: FAIL — `AttributeError: 'TaskService' object has no attribute 'all_completed'`

- [ ] **Step 3: Add all_completed() to TaskService**

In `backend/app/services/task_service.py`, add after `list_by_issue`:
```python
async def all_completed(self, issue_id: str) -> bool:
    """Returns True only if the issue has at least one task and all are COMPLETED."""
    tasks = await self.list_by_issue(issue_id)
    if not tasks:
        return False
    return all(t.status == TaskStatus.COMPLETED for t in tasks)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_auto_completion.py -v
```
Expected: PASS (3 tests)

- [ ] **Step 5: Fire ALL_TASKS_COMPLETED from update_task_status in mcp/server.py**

In `backend/app/mcp/server.py`, replace the `update_task_status` tool (starting at `@mcp.tool(description=_desc["tool.update_task_status.description"])`):
```python
@mcp.tool(description=_desc["tool.update_task_status.description"])
async def update_task_status(task_id: str, status: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, status=status)
            task_issue_id = task.issue_id
            task_id_val = task.id
            task_name = task.name
            task_status = task.status.value
            issue = await session.get(Issue, task_issue_id)
            all_done = (
                await task_service.all_completed(task_issue_id)
                if task.status.value == "Completed"
                else False
            )
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": task_issue_id,
                    "task_id": task_id_val,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            if all_done and issue:
                from app.hooks.registry import HookContext, HookEvent, hook_registry
                from app.services.project_service import ProjectService as _PS
                async with async_session() as s2:
                    project = await _PS(s2).get_by_id(issue.project_id)
                await hook_registry.fire(
                    HookEvent.ALL_TASKS_COMPLETED,
                    HookContext(
                        project_id=issue.project_id,
                        issue_id=task_issue_id,
                        event=HookEvent.ALL_TASKS_COMPLETED,
                        metadata={
                            "issue_name": issue.name or "",
                            "project_name": project.name if project else "",
                            "project_path": project.path if project else "",
                        },
                    ),
                )
            return {"id": task_id_val, "name": task_name, "status": task_status}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}
```

- [ ] **Step 6: Fire ALL_TASKS_COMPLETED from REST task update endpoint**

In `backend/app/routers/tasks.py`, replace `update_task`:
```python
from app.models.task import TaskStatus

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: str, issue_id: str, task_id: str, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    try:
        task = await service.update(task_id, **data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    all_done = False
    if task.status == TaskStatus.COMPLETED:
        all_done = await service.all_completed(issue_id)
    await db.commit()
    await db.refresh(task)
    if all_done:
        from app.database import async_session
        from app.hooks.registry import HookContext, HookEvent, hook_registry
        from app.services.project_service import ProjectService
        async with async_session() as session:
            project = await ProjectService(session).get_by_id(project_id)
        await hook_registry.fire(
            HookEvent.ALL_TASKS_COMPLETED,
            HookContext(
                project_id=project_id,
                issue_id=issue_id,
                event=HookEvent.ALL_TASKS_COMPLETED,
                metadata={
                    "project_name": project.name if project else "",
                    "project_path": project.path if project else "",
                },
            ),
        )
    return task
```

- [ ] **Step 7: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/task_service.py backend/app/mcp/server.py backend/app/routers/tasks.py backend/tests/test_auto_completion.py
git commit -m "feat: ALL_TASKS_COMPLETED detection in TaskService, MCP, and REST task update"
```

---

## Task 5: AutoCompletion handler (4.3)

**Files:**
- Create: `backend/app/hooks/handlers/auto_completion.py`
- Modify: `backend/app/hooks/handlers/__init__.py`

- [ ] **Step 1: Implement AutoCompletion handler**

Create `backend/app/hooks/handlers/auto_completion.py`:
```python
"""AutoCompletion hook: when all tasks are completed, notify user or auto-complete the issue
   depending on the project's auto_complete_mode setting (off/notify/auto)."""
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.event_service import event_service
from app.services.project_setting_service import ProjectSettingService


@hook(event=HookEvent.ALL_TASKS_COMPLETED)
class AutoCompletion(BaseHook):
    name = "auto_completion"
    description = "Notifica o completa automaticamente l'issue quando tutti i task sono completati"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            mode = await svc.get(context.project_id, "auto_complete_mode", default="off")

        if mode == "off":
            return HookResult(success=True, output="auto_complete_mode is off")

        issue_name = context.metadata.get("issue_name", "")
        project_path = context.metadata.get("project_path", "")

        if mode == "notify":
            await event_service.emit({
                "type": "notification",
                "project_id": context.project_id,
                "issue_id": context.issue_id,
                "title": "Tutti i task completati",
                "message": (
                    f'Issue "{issue_name}" ha tutti i task completati. '
                    "Puoi ora completare l'issue con un recap."
                ),
            })
            return HookResult(success=True, output="notification sent")

        if mode == "auto":
            prompt = f"""Tutti i task dell'issue "{issue_name}" sono stati completati.

Il tuo compito:
1. Usa `get_issue_details` per leggere il piano e i task completati
2. Usa `complete_issue` con un recap dettagliato che descrive cosa è stato implementato

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Il recap deve essere completo e basato sul piano effettivamente eseguito."""

            executor = ClaudeCodeExecutor()
            result = await executor.run(
                prompt=prompt,
                project_path=project_path,
                env_vars={
                    "MANAGER_AI_PROJECT_ID": context.project_id,
                    "MANAGER_AI_ISSUE_ID": context.issue_id,
                },
                timeout=120,
            )
            return HookResult(success=result.success, output=result.output, error=result.error)

        return HookResult(success=True, output=f"unknown mode: {mode}")
```

- [ ] **Step 2: Register all new handlers in __init__.py**

In `backend/app/hooks/handlers/__init__.py`:
```python
"""Hook handlers package: import modules here to trigger @hook decorator autodiscovery."""

from app.hooks.handlers import auto_completion  # noqa: F401
from app.hooks.handlers import auto_start_workflow  # noqa: F401
from app.hooks.handlers import enrich_context  # noqa: F401
from app.hooks.handlers import start_analysis  # noqa: F401
```

- [ ] **Step 3: Write a smoke test for AutoCompletion**

Append to `backend/tests/test_auto_completion.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch


@patch("app.hooks.handlers.auto_completion.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_completion.ProjectSettingService")
async def test_auto_completion_notifies_when_mode_notify(MockSettingService, MockExecutor, db_session):
    from app.hooks.handlers.auto_completion import AutoCompletion
    from app.hooks.registry import HookContext, HookEvent

    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="notify")
    MockSettingService.return_value = mock_svc

    with patch("app.hooks.handlers.auto_completion.event_service") as mock_events:
        mock_events.emit = AsyncMock()
        handler = AutoCompletion()
        ctx = HookContext(
            project_id="proj-1",
            issue_id="issue-1",
            event=HookEvent.ALL_TASKS_COMPLETED,
            metadata={"issue_name": "Fix login", "project_path": "/tmp"},
        )
        result = await handler.execute(ctx)
        assert result.success is True
        mock_events.emit.assert_called_once()
        emitted = mock_events.emit.call_args[0][0]
        assert emitted["type"] == "notification"
        assert "Fix login" in emitted["title"] or "Fix login" in emitted.get("message", "")


@patch("app.hooks.handlers.auto_completion.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_completion.ProjectSettingService")
async def test_auto_completion_skips_when_off(MockSettingService, MockExecutor, db_session):
    from app.hooks.handlers.auto_completion import AutoCompletion
    from app.hooks.registry import HookContext, HookEvent

    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="off")
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    MockExecutor.return_value = mock_exec

    handler = AutoCompletion()
    ctx = HookContext(
        project_id="proj-1",
        issue_id="issue-1",
        event=HookEvent.ALL_TASKS_COMPLETED,
        metadata={"issue_name": "Test", "project_path": "/tmp"},
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_not_called()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_auto_completion.py -v
```
Expected: PASS (5 tests)

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/hooks/handlers/auto_completion.py backend/app/hooks/handlers/__init__.py backend/tests/test_auto_completion.py
git commit -m "feat: AutoCompletion handler — notify or auto-complete when all tasks done (4.3)"
```

---

## Task 6: AutoStartImplementation handler (4.2)

**Files:**
- Modify: `backend/app/services/issue_service.py` (enrich accept_issue metadata)
- Create: `backend/app/hooks/handlers/auto_start_implementation.py`
- Create: `backend/tests/test_auto_start_implementation.py`
- Modify: `backend/app/hooks/handlers/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_auto_start_implementation.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio

from app.hooks.registry import HookContext, HookEvent
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(
        name="Test", path="/tmp/p", description="Desc", tech_stack="Python"
    )


@patch("app.hooks.handlers.auto_start_implementation.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_implementation.ProjectSettingService")
async def test_auto_implementation_runs_when_enabled(MockSettingService, MockExecutor, db_session, project):
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(side_effect=lambda pid, key, default="": {
        "auto_implementation_enabled": "true",
        "auto_implementation_timeout": "900",
    }.get(key, default))
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    mock_exec.run = AsyncMock(return_value=MagicMock(success=True, output="done", error=None))
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_implementation import AutoStartImplementation
    handler = AutoStartImplementation()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_ACCEPTED,
        metadata={
            "issue_name": "Build login",
            "project_name": project.name,
            "project_path": project.path,
            "project_description": project.description,
            "tech_stack": project.tech_stack,
            "specification": "# Spec content",
            "plan": "# Plan content",
        },
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_called_once()
    prompt_used = mock_exec.run.call_args.kwargs.get("prompt") or mock_exec.run.call_args.args[0]
    assert "# Plan content" in prompt_used


@patch("app.hooks.handlers.auto_start_implementation.ClaudeCodeExecutor")
@patch("app.hooks.handlers.auto_start_implementation.ProjectSettingService")
async def test_auto_implementation_skips_when_disabled(MockSettingService, MockExecutor, db_session, project):
    mock_svc = AsyncMock()
    mock_svc.get = AsyncMock(return_value="false")
    MockSettingService.return_value = mock_svc

    mock_exec = AsyncMock()
    MockExecutor.return_value = mock_exec

    from app.hooks.handlers.auto_start_implementation import AutoStartImplementation
    handler = AutoStartImplementation()
    ctx = HookContext(
        project_id=project.id,
        issue_id="issue-1",
        event=HookEvent.ISSUE_ACCEPTED,
        metadata={"project_path": project.path},
    )
    result = await handler.execute(ctx)
    assert result.success is True
    mock_exec.run.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_auto_start_implementation.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Enrich accept_issue() metadata in IssueService**

In `backend/app/services/issue_service.py`, in `accept_issue()`, replace the `await hook_registry.fire(...)` call:
```python
    project = await ProjectService(self.session).get_by_id(project_id)
    await hook_registry.fire(
        HookEvent.ISSUE_ACCEPTED,
        HookContext(
            project_id=project_id,
            issue_id=issue_id,
            event=HookEvent.ISSUE_ACCEPTED,
            metadata={
                "issue_name": issue.name or (issue.description or "")[:50] or "Untitled",
                "issue_description": issue.description or "",
                "specification": issue.specification or "",
                "plan": issue.plan or "",
                "project_name": project.name if project else "",
                "project_path": project.path if project else "",
                "project_description": project.description if project else "",
                "tech_stack": project.tech_stack if project else "",
            },
        ),
    )
```

- [ ] **Step 4: Implement AutoStartImplementation handler**

Create `backend/app/hooks/handlers/auto_start_implementation.py`:
```python
"""AutoStartImplementation hook: when an issue is accepted and auto_implementation_enabled
   is true for the project, spawns Claude Code to implement the plan task by task."""
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService


@hook(event=HookEvent.ISSUE_ACCEPTED)
class AutoStartImplementation(BaseHook):
    name = "auto_start_implementation"
    description = "Avvia automaticamente l'implementazione quando una issue viene accettata"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            enabled = await svc.get(context.project_id, "auto_implementation_enabled", default="false")
            if enabled != "true":
                return HookResult(success=True, output="auto_implementation disabled for this project")
            timeout_str = await svc.get(context.project_id, "auto_implementation_timeout", default="900")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 900

        issue_name = context.metadata.get("issue_name", "")
        project_name = context.metadata.get("project_name", "")
        project_path = context.metadata.get("project_path", "")
        project_description = context.metadata.get("project_description", "")
        tech_stack = context.metadata.get("tech_stack", "")
        specification = context.metadata.get("specification", "")
        plan = context.metadata.get("plan", "")

        prompt = f"""Sei il developer assegnato all'issue "{issue_name}" nel progetto "{project_name}".

Contesto del progetto:
{project_description}
Tech stack: {tech_stack}

Specifica dell'issue:
{specification}

Piano di implementazione:
{plan}

Il tuo compito è implementare il piano passo per passo:
1. Usa `get_plan_tasks` per ottenere la lista dei task
2. Per ogni task, in ordine:
   a. Usa `update_task_status` per marcarlo "In Progress"
   b. Implementa il task nel codice del progetto
   c. Usa `update_task_status` per marcarlo "Completed"
3. Quando tutti i task sono completati, usa `complete_issue` con un recap dettagliato

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Lavora metodicamente. Non saltare task."""

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": context.project_id,
                "MANAGER_AI_ISSUE_ID": context.issue_id,
            },
            timeout=timeout,
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
```

- [ ] **Step 5: Register in __init__.py**

In `backend/app/hooks/handlers/__init__.py`:
```python
"""Hook handlers package: import modules here to trigger @hook decorator autodiscovery."""

from app.hooks.handlers import auto_completion  # noqa: F401
from app.hooks.handlers import auto_start_implementation  # noqa: F401
from app.hooks.handlers import auto_start_workflow  # noqa: F401
from app.hooks.handlers import enrich_context  # noqa: F401
from app.hooks.handlers import start_analysis  # noqa: F401
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_auto_start_implementation.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 7: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/hooks/handlers/auto_start_implementation.py backend/app/hooks/handlers/__init__.py backend/app/services/issue_service.py backend/tests/test_auto_start_implementation.py
git commit -m "feat: AutoStartImplementation hook — auto-implements plan when issue accepted (4.2)"
```

---

## Task 7: Work queue — get_next_issue MCP tool + global pause (4.4)

**Files:**
- Modify: `backend/app/services/issue_service.py` (`get_next_issue`)
- Modify: `backend/app/mcp/server.py` (add `get_next_issue` tool)
- Modify: `backend/app/mcp/default_settings.json`
- Modify: `backend/app/hooks/handlers/auto_start_workflow.py` (pause check)
- Modify: `backend/app/hooks/handlers/auto_start_implementation.py` (pause check)
- Create: `backend/tests/test_work_queue.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_work_queue.py`:
```python
import pytest_asyncio
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(name="Q", path="/tmp/q", description="")


async def test_get_next_returns_accepted_before_new(db_session, project):
    svc = IssueService(db_session)
    new_issue = await svc.create(project_id=project.id, description="New issue", priority=1)
    accepted_issue = await svc.create(project_id=project.id, description="Accepted issue", priority=2)
    await svc.create_spec(accepted_issue.id, project.id, "# Spec")
    await svc.create_plan(accepted_issue.id, project.id, "# Plan")
    await svc.accept_issue(accepted_issue.id, project.id)
    await db_session.commit()
    next_issue = await svc.get_next_issue(project.id)
    assert next_issue is not None
    assert next_issue.id == accepted_issue.id


async def test_get_next_returns_highest_priority_new(db_session, project):
    svc = IssueService(db_session)
    low = await svc.create(project_id=project.id, description="Low prio", priority=3)
    high = await svc.create(project_id=project.id, description="High prio", priority=1)
    await db_session.commit()
    next_issue = await svc.get_next_issue(project.id)
    assert next_issue is not None
    assert next_issue.id == high.id


async def test_get_next_returns_none_when_no_workable(db_session, project):
    svc = IssueService(db_session)
    issue = await svc.create(project_id=project.id, description="Issue", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")  # REASONING — not workable
    await db_session.commit()
    next_issue = await svc.get_next_issue(project.id)
    assert next_issue is None
```

- [ ] **Step 2: Run tests to verify the first test fails**

```bash
cd backend && python -m pytest tests/test_work_queue.py -v
```
Expected: `test_get_next_returns_accepted_before_new` FAIL (current impl returns only NEW)

- [ ] **Step 3: Update get_next_issue() in IssueService**

In `backend/app/services/issue_service.py`, replace `get_next_issue()`:
```python
async def get_next_issue(self, project_id: str) -> Issue | None:
    """Return next workable issue: ACCEPTED first (ready to implement), then NEW (needs planning)."""
    accepted_query = (
        select(Issue)
        .where(Issue.project_id == project_id)
        .where(Issue.status == IssueStatus.ACCEPTED)
        .order_by(Issue.priority.asc(), Issue.created_at.asc())
        .limit(1)
    )
    result = await self.session.execute(accepted_query)
    issue = result.scalar_one_or_none()
    if issue:
        return issue
    new_query = (
        select(Issue)
        .where(Issue.project_id == project_id)
        .where(Issue.status == IssueStatus.NEW)
        .order_by(Issue.priority.asc(), Issue.created_at.asc())
        .limit(1)
    )
    result = await self.session.execute(new_query)
    return result.scalar_one_or_none()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_work_queue.py -v
```
Expected: PASS (3 tests)

- [ ] **Step 5: Add work_queue_paused and get_next_issue to default_settings.json**

In `backend/app/mcp/default_settings.json`, add before the closing `}`:
```json
  "work_queue_paused": "false",
  "tool.get_next_issue.description": "Get the next workable issue for a project, ordered by priority. Returns an ACCEPTED issue (ready for implementation) first, then a NEW issue (needs planning). Returns null if no workable issues exist. Use this to implement a continuous work queue: after completing an issue, call get_next_issue to find the next one to start."
```

- [ ] **Step 6: Add get_next_issue MCP tool in server.py**

In `backend/app/mcp/server.py`, after the `get_project_context` tool, add:
```python
@mcp.tool(description=_desc["tool.get_next_issue.description"])
async def get_next_issue(project_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_next_issue(project_id)
            if issue is None:
                return {"issue": None, "message": "No workable issues in queue"}
            return {
                "issue": {
                    "id": issue.id,
                    "name": issue.name,
                    "description": issue.description,
                    "status": issue.status.value,
                    "priority": issue.priority,
                }
            }
        except AppError as e:
            return {"error": e.message}
```

- [ ] **Step 7: Add work_queue_paused check to auto_start_workflow.py**

In `backend/app/hooks/handlers/auto_start_workflow.py`, after the `if enabled != "true"` check (still inside `execute()`), add:
```python
        # Check global work queue pause
        from app.services.settings_service import SettingsService
        async with async_session() as session:
            paused = await SettingsService(session).get("work_queue_paused")
        if paused == "true":
            return HookResult(success=True, output="work queue is paused")
```

- [ ] **Step 8: Add work_queue_paused check to auto_start_implementation.py**

In `backend/app/hooks/handlers/auto_start_implementation.py`, after the `if enabled != "true"` check, add:
```python
        # Check global work queue pause
        from app.services.settings_service import SettingsService
        async with async_session() as session:
            paused = await SettingsService(session).get("work_queue_paused")
        if paused == "true":
            return HookResult(success=True, output="work queue is paused")
```

- [ ] **Step 9: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/issue_service.py backend/app/mcp/server.py backend/app/mcp/default_settings.json backend/app/hooks/handlers/auto_start_workflow.py backend/app/hooks/handlers/auto_start_implementation.py backend/tests/test_work_queue.py
git commit -m "feat: get_next_issue MCP tool, work_queue_paused setting, queue pause in auto handlers (4.4)"
```

---

## Task 8: Frontend — automation settings UI (4.1–4.3)

**Files:**
- Create: `frontend/src/api/projectSettings.js`
- Create: `frontend/src/components/AutomationPanel.jsx`
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`

- [ ] **Step 1: Create the API client**

Create `frontend/src/api/projectSettings.js`:
```javascript
const BASE = "/api";

export async function getProjectSettings(projectId) {
  const res = await fetch(`${BASE}/projects/${projectId}/settings`);
  if (!res.ok) throw new Error("Failed to fetch project settings");
  return res.json(); // returns { key: value, ... }
}

export async function setProjectSetting(projectId, key, value) {
  const res = await fetch(`${BASE}/projects/${projectId}/settings/${key}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
  if (!res.ok) throw new Error(`Failed to set setting ${key}`);
  return res.json();
}

export async function deleteProjectSetting(projectId, key) {
  const res = await fetch(`${BASE}/projects/${projectId}/settings/${key}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete setting ${key}`);
}
```

- [ ] **Step 2: Create AutomationPanel component**

Create `frontend/src/components/AutomationPanel.jsx`:
```jsx
import { useEffect, useState } from "react";
import { getProjectSettings, setProjectSetting } from "../api/projectSettings";

export default function AutomationPanel({ projectId }) {
  const [settings, setSettings] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getProjectSettings(projectId).then(setSettings).catch(console.error);
  }, [projectId]);

  const toggle = async (key) => {
    const newValue = settings[key] === "true" ? "false" : "true";
    setSaving(true);
    try {
      await setProjectSetting(projectId, key, newValue);
      setSettings((prev) => ({ ...prev, [key]: newValue }));
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const updateText = async (key, value) => {
    if (!value && value !== "0") return;
    setSaving(true);
    try {
      await setProjectSetting(projectId, key, value);
      setSettings((prev) => ({ ...prev, [key]: value }));
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const autoWorkflow = settings.auto_workflow_enabled === "true";
  const autoImpl = settings.auto_implementation_enabled === "true";
  const autoCompleteMode = settings.auto_complete_mode || "off";

  return (
    <div className="automation-panel">
      <h3>Automazione</h3>

      <div className="setting-row">
        <label>
          <input
            type="checkbox"
            checked={autoWorkflow}
            onChange={() => toggle("auto_workflow_enabled")}
            disabled={saving}
          />
          {" "}Auto-start workflow (spec + piano + task) alla creazione issue
        </label>
      </div>

      {autoWorkflow && (
        <div className="setting-row setting-indent">
          <label>Prompt custom (vuoto = default):</label>
          <textarea
            rows={4}
            defaultValue={settings.auto_workflow_prompt || ""}
            onBlur={(e) => updateText("auto_workflow_prompt", e.target.value)}
            placeholder="Variabili: {{issue_description}} {{project_name}} {{project_description}} {{tech_stack}}"
          />
          <label>Timeout (secondi, default 600):</label>
          <input
            type="number"
            defaultValue={settings.auto_workflow_timeout || "600"}
            onBlur={(e) => updateText("auto_workflow_timeout", e.target.value)}
            min={60}
            max={3600}
          />
        </div>
      )}

      <div className="setting-row">
        <label>
          <input
            type="checkbox"
            checked={autoImpl}
            onChange={() => toggle("auto_implementation_enabled")}
            disabled={saving}
          />
          {" "}Auto-start implementazione all'accettazione issue
        </label>
      </div>

      <div className="setting-row">
        <label>Completamento automatico:</label>
        <select
          value={autoCompleteMode}
          onChange={(e) => updateText("auto_complete_mode", e.target.value)}
          disabled={saving}
        >
          <option value="off">Disabilitato</option>
          <option value="notify">Notifica utente</option>
          <option value="auto">Auto-completa con recap (Claude)</option>
        </select>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Embed AutomationPanel in ProjectDetailPage**

In `frontend/src/pages/ProjectDetailPage.jsx`, add the import:
```jsx
import AutomationPanel from "../components/AutomationPanel";
```

In the JSX body, add after the project info section:
```jsx
<AutomationPanel projectId={project.id} />
```

- [ ] **Step 4: Verify manually**

```bash
python start.py
```
Open a project detail page. Verify:
- "Automazione" section appears
- Checkboxes toggle and persist on page refresh
- Prompt textarea and timeout field appear when workflow is enabled
- Auto-complete dropdown persists

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/projectSettings.js frontend/src/components/AutomationPanel.jsx frontend/src/pages/ProjectDetailPage.jsx
git commit -m "feat: AutomationPanel — per-project automation settings UI"
```

---

## Task 9: Frontend — Work Queue Status dashboard (4.4)

**Files:**
- Create: `frontend/src/components/WorkQueueStatus.jsx`
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`

- [ ] **Step 1: Check how EventProvider exposes events**

Read `frontend/src/context/EventProvider.jsx`. Note the hook name (e.g., `useEvents()`) and what it returns — a list of event objects, a ref, or a callback-based system. Adapt `WorkQueueStatus.jsx` accordingly in Step 2.

- [ ] **Step 2: Create WorkQueueStatus component**

Create `frontend/src/components/WorkQueueStatus.jsx` (adapt the event subscription to match what `EventProvider` actually exports):
```jsx
import { useEffect, useState } from "react";
import { useEvents } from "../context/EventProvider"; // adjust import if hook name differs

export default function WorkQueueStatus({ projectId }) {
  const [activeHook, setActiveHook] = useState(null);
  const [paused, setPaused] = useState(false);
  const [saving, setSaving] = useState(false);
  const events = useEvents(); // array of recent events from WebSocket

  // Load global work_queue_paused setting
  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((all) => {
        const entry = Array.isArray(all)
          ? all.find((s) => s.key === "work_queue_paused")
          : null;
        setPaused(entry?.value === "true");
      })
      .catch(console.error);
  }, []);

  // Track active hooks for this project by watching event stream
  useEffect(() => {
    if (!events || !events.length) return;
    const projectEvents = events.filter((e) => e.project_id === projectId);
    const last = projectEvents[projectEvents.length - 1];
    if (!last) return;
    if (last.type === "hook_started") {
      setActiveHook({
        name: last.hook_name,
        description: last.hook_description,
        issue: last.issue_name,
      });
    } else if (last.type === "hook_completed" || last.type === "hook_failed") {
      setActiveHook(null);
    }
  }, [events, projectId]);

  const togglePause = async () => {
    const newVal = paused ? "false" : "true";
    setSaving(true);
    try {
      await fetch("/api/settings/work_queue_paused", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: newVal }),
      });
      setPaused(!paused);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="work-queue-status">
      <div className="queue-header">
        <h3>Coda di Lavoro</h3>
        <button
          onClick={togglePause}
          disabled={saving}
          className={paused ? "btn-resume" : "btn-pause"}
        >
          {paused ? "Riprendi Coda" : "Pausa Coda"}
        </button>
      </div>

      {paused && (
        <div className="queue-paused-banner">
          La coda automatica è in pausa. I nuovi trigger non avvieranno Claude.
        </div>
      )}

      {activeHook ? (
        <div className="active-hook">
          <span className="spinner" aria-hidden="true" />
          <strong>Claude sta lavorando:</strong> {activeHook.description}
          {activeHook.issue && <span> su &ldquo;{activeHook.issue}&rdquo;</span>}
        </div>
      ) : (
        <div className="queue-idle">Nessuna operazione automatica attiva</div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add WorkQueueStatus to ProjectDetailPage**

In `frontend/src/pages/ProjectDetailPage.jsx`, add the import:
```jsx
import WorkQueueStatus from "../components/WorkQueueStatus";
```

In the JSX body, add next to `AutomationPanel`:
```jsx
<WorkQueueStatus projectId={project.id} />
```

- [ ] **Step 4: Verify manually**

```bash
python start.py
```
Open a project detail page. Verify:
- "Coda di Lavoro" section is visible with Pausa/Riprendi button
- Clicking "Pausa Coda" shows the paused banner; "Riprendi Coda" removes it
- State persists on page refresh
- When a hook fires (trigger manually via start-analysis), the "Claude sta lavorando" indicator appears

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/WorkQueueStatus.jsx frontend/src/pages/ProjectDetailPage.jsx
git commit -m "feat: WorkQueueStatus dashboard — shows active hook, pause/resume queue (4.4)"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Covered by |
|---|---|
| 4.1 `HookEvent.ISSUE_CREATED` | Task 1 |
| 4.1 `AutoStartSpecification` hook (spec+piano+task+notify) | Task 3 |
| 4.1 Configurabile per progetto on/off + prompt template custom | Task 2 (ProjectSettingService), Task 3 (custom_prompt), Task 8 (UI) |
| 4.1 Timeout e gestione errori | Task 3 (configurable timeout, errors caught by HookRegistry) |
| 4.2 PLANNED→ACCEPTED apre terminale + lancia Claude | Task 6 (AutoStartImplementation on ISSUE_ACCEPTED) |
| 4.2 Claude implementa task per task | Task 6 (prompt instructs get_plan_tasks + update_task_status loop) |
| 4.2 Possibilità di interrompere | Task 7 (work_queue_paused check), Task 9 (Pausa UI) |
| 4.3 Auto-completion detection | Task 4 (all_completed() check in TaskService, MCP, REST) |
| 4.3 Opzione notify / auto-complete con recap Claude | Task 5 (AutoCompletion, mode notify/auto) |
| 4.4 `get_next_issue` per priorità (ACCEPTED→NEW) | Task 7 (updated get_next_issue + MCP tool) |
| 4.4 Dashboard "Claude sta lavorando" | Task 9 (WorkQueueStatus with hook event tracking) |
| 4.4 Pausa/resume coda | Task 7 (work_queue_paused setting), Task 9 (UI toggle) |

**Gap — 4.4 workflow continuo (finita un'issue, parte la prossima):** Non cablato automaticamente, perché dipende da una scelta di prompt engineering. Il MCP tool `get_next_issue` è disponibile — Claude può essere istruito di chiamarlo dopo `complete_issue` tramite il prompt di `AutoStartImplementation` o `EnrichProjectContext`. Questo è sufficiente per V1 senza over-engineering.

**Placeholder scan:** Nessun TBD, TODO, o "add appropriate" nel piano.

**Type consistency:** `ProjectSettingService.get(project_id, key, default)` usato identicamente in Task 2, 3, 5, 6, 7. `all_completed(issue_id: str) -> bool` definito in Task 4 e referenziato in Task 4 (mcp/server.py, routers/tasks.py). `HookEvent.ISSUE_CREATED` e `HookEvent.ALL_TASKS_COMPLETED` definiti in Task 1 e usati in Task 3, 4, 5, 6.
