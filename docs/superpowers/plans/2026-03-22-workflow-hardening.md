# Workflow Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the issue lifecycle state machine, unify business logic in the service layer, and make hooks fire consistently regardless of entry point (REST or MCP).

**Architecture:** All business logic (validation, state transitions, hook firing, event emission) moves into service methods. Routers and MCP tools become thin wrappers. A custom exception hierarchy replaces ad-hoc ValueError/KeyError/None patterns, handled by a global FastAPI exception handler.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, SQLite, pytest, React

**Spec:** `docs/superpowers/specs/2026-03-22-workflow-hardening-design.md`

---

### Task 1: Custom Exception Hierarchy

**Files:**
- Create: `backend/app/exceptions.py`
- Test: `backend/tests/test_exceptions.py`

- [ ] **Step 1: Write the test file**

```python
# backend/tests/test_exceptions.py
from app.exceptions import AppError, NotFoundError, InvalidTransitionError, ValidationError


def test_not_found_error_has_404_status():
    err = NotFoundError("Issue not found")
    assert err.status_code == 404
    assert err.message == "Issue not found"
    assert isinstance(err, AppError)


def test_invalid_transition_error_has_409_status():
    err = InvalidTransitionError("Cannot transition from New to Finished")
    assert err.status_code == 409
    assert err.message == "Cannot transition from New to Finished"


def test_validation_error_has_422_status():
    err = ValidationError("Recap cannot be blank")
    assert err.status_code == 422
    assert err.message == "Recap cannot be blank"


def test_app_error_base_has_500_status():
    err = AppError("Something went wrong")
    assert err.status_code == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_exceptions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.exceptions'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/exceptions.py
"""Custom exception hierarchy for Manager AI services."""


class AppError(Exception):
    """Base for all application errors."""
    status_code: int = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""
    status_code = 404


class InvalidTransitionError(AppError):
    """Invalid state transition attempted."""
    status_code = 409


class ValidationError(AppError):
    """Input validation failed."""
    status_code = 422
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_exceptions.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/exceptions.py backend/tests/test_exceptions.py
git commit -m "feat: add custom exception hierarchy"
```

---

### Task 2: Global Exception Handler in FastAPI

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_exception_handler.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_exception_handler.py
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_404_returns_json_detail(client):
    """A non-existent project returns 404 with JSON detail from global handler."""
    resp = await client.get("/api/projects/nonexistent-id")
    assert resp.status_code == 404
    assert "detail" in resp.json()
```

- [ ] **Step 2: Run test to verify baseline behavior**

Run: `cd backend && python -m pytest tests/test_exception_handler.py -v`
Expected: PASS (404 already returned by router, but this confirms the pattern works)

- [ ] **Step 3: Add global exception handler to main.py**

In `backend/app/main.py`, add after the imports:

```python
from fastapi.responses import JSONResponse
from app.exceptions import AppError
```

Add after `app = FastAPI(...)`:

```python
@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

- [ ] **Step 4: Run test to confirm it still passes**

Run: `cd backend && python -m pytest tests/test_exception_handler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_exception_handler.py
git commit -m "feat: add global AppError exception handler"
```

---

### Task 3: Remove DECLINED State from Issue Model

**Files:**
- Modify: `backend/app/models/issue.py`
- Modify: `backend/app/schemas/issue.py`
- Create: Alembic migration
- Test: `backend/tests/test_issue_model.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_issue_model.py
from app.models.issue import IssueStatus, VALID_TRANSITIONS


def test_declined_not_in_status_enum():
    statuses = [s.value for s in IssueStatus]
    assert "Declined" not in statuses


def test_valid_transitions_include_new_to_reasoning():
    assert (IssueStatus.NEW, IssueStatus.REASONING) in VALID_TRANSITIONS


def test_valid_transitions_do_not_include_declined():
    for src, dst in VALID_TRANSITIONS:
        assert src != "Declined" and dst != "Declined"


def test_all_expected_transitions_present():
    expected = {
        (IssueStatus.NEW, IssueStatus.REASONING),
        (IssueStatus.REASONING, IssueStatus.PLANNED),
        (IssueStatus.PLANNED, IssueStatus.ACCEPTED),
        (IssueStatus.ACCEPTED, IssueStatus.FINISHED),
    }
    assert VALID_TRANSITIONS == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_issue_model.py -v`
Expected: FAIL — `DECLINED` still in enum, `NEW → REASONING` missing

- [ ] **Step 3: Update the model**

In `backend/app/models/issue.py`:

Remove `DECLINED = "Declined"` from `IssueStatus` enum.

Replace `VALID_TRANSITIONS`:
```python
VALID_TRANSITIONS = {
    (IssueStatus.NEW, IssueStatus.REASONING),
    (IssueStatus.REASONING, IssueStatus.PLANNED),
    (IssueStatus.PLANNED, IssueStatus.ACCEPTED),
    (IssueStatus.ACCEPTED, IssueStatus.FINISHED),
}
```

Remove `decline_feedback` column from the `Issue` class.

- [ ] **Step 4: Update the schemas**

In `backend/app/schemas/issue.py`:

Remove `decline_feedback` from `IssueStatusUpdate`.
Remove `decline_feedback` from `IssueResponse`.

```python
class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueResponse(BaseModel):
    id: str
    project_id: str
    name: str | None
    description: str
    status: IssueStatus
    priority: int
    plan: str | None
    specification: str | None = None
    recap: str | None
    tasks: list[TaskResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_issue_model.py -v`
Expected: 4 passed

- [ ] **Step 6: Remove decline_feedback from MCP get_issue_details**

In `backend/app/mcp/server.py`, remove `"decline_feedback": issue.decline_feedback,` from the `get_issue_details` return dict (line 41).

- [ ] **Step 7: Create Alembic migration**

Run: `cd backend && python -m alembic revision --autogenerate -m "remove declined state and decline_feedback column"`

Then review the generated migration. It should:
1. Drop the `decline_feedback` column
2. Handle any existing DECLINED issues (update to PLANNED)

Add this at the top of `upgrade()`:
```python
# Migrate any DECLINED issues to PLANNED before removing the status
op.execute("UPDATE issues SET status = 'Planned' WHERE status = 'Declined'")
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/issue.py backend/app/schemas/issue.py backend/app/mcp/server.py backend/tests/test_issue_model.py backend/alembic/versions/
git commit -m "feat: remove DECLINED state, add NEW→REASONING transition"
```

---

### Task 4: Migrate IssueService to Custom Exceptions

**Files:**
- Modify: `backend/app/services/issue_service.py`
- Modify: `backend/tests/test_issue_service.py`

- [ ] **Step 1: Update test expectations**

In `backend/tests/test_issue_service.py`:

Replace all `pytest.raises(ValueError, ...)` with the appropriate custom exceptions:
- `ValueError("Issue not found")` → `NotFoundError`
- `ValueError("Invalid state transition")` → `InvalidTransitionError`
- `ValueError("Can only complete")` → `InvalidTransitionError`
- `ValueError("blank")` → `ValidationError`
- `ValueError("Can only create spec")` → `InvalidTransitionError`
- `ValueError("Reasoning status")` → `InvalidTransitionError`
- `ValueError("Planned status")` → `InvalidTransitionError`
- `PermissionError` → `NotFoundError` (project mismatch = not found from caller's perspective)

Add imports:
```python
from app.exceptions import InvalidTransitionError, NotFoundError, ValidationError
```

Remove all tests that reference DECLINED:
- `test_get_next_issue_declined_before_new`
- `test_update_status_declined_saves_feedback`
- `test_decline_issue`
- `test_create_spec_from_declined`

Update `test_create_spec_invalid_status` match string from `"New or Declined"` to `"New"`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_issue_service.py -v`
Expected: FAIL — services still raise ValueError

- [ ] **Step 3: Rewrite issue_service.py with custom exceptions**

In `backend/app/services/issue_service.py`:

Add imports:
```python
from app.exceptions import InvalidTransitionError, NotFoundError, ValidationError
```

Key changes:
- `get_for_project`: raise `NotFoundError("Issue not found")` instead of `ValueError`, raise `NotFoundError("Issue not found")` instead of `PermissionError` (don't leak that the issue exists in another project)
- `update_status`: raise `InvalidTransitionError(...)` instead of `ValueError`
- `create_spec`: raise `ValidationError("Specification cannot be blank")`, raise `InvalidTransitionError(...)` for wrong status. Only allow from `IssueStatus.NEW` (not DECLINED anymore).
- `edit_spec`: `ValidationError` for blank, `InvalidTransitionError` for wrong status
- `create_plan`: same pattern
- `edit_plan`: same pattern
- `accept_issue`: `InvalidTransitionError` for wrong status
- `complete_issue`: `InvalidTransitionError` for wrong status

Remove `decline_issue()` method entirely.

Simplify `get_next_issue()`: only query `IssueStatus.NEW`, remove DECLINED priority logic:
```python
async def get_next_issue(self, project_id: str) -> Issue | None:
    query = (
        select(Issue)
        .where(Issue.project_id == project_id)
        .where(Issue.status == IssueStatus.NEW)
        .order_by(Issue.priority.asc(), Issue.created_at.asc())
        .limit(1)
    )
    result = await self.session.execute(query)
    return result.scalar_one_or_none()
```

Remove `decline_feedback` references from `update_status`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_issue_service.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/issue_service.py backend/tests/test_issue_service.py
git commit -m "refactor: migrate issue service to custom exceptions, remove decline"
```

---

### Task 5: Move Hook Firing into Service Layer

**Files:**
- Modify: `backend/app/services/issue_service.py`
- Modify: `backend/app/mcp/server.py`
- Test: `backend/tests/test_issue_service_hooks.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_issue_service_hooks.py
"""Test that service methods fire hooks on state transitions."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.issue import IssueStatus
from app.models.task import TaskStatus
from app.hooks.registry import HookEvent
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test", path="/tmp/test", description="Test")


@patch("app.services.issue_service.hook_registry")
async def test_complete_issue_fires_hook(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    # Reset mock after accept_issue (which also fires a hook)
    mock_registry.fire.reset_mock()
    await service.complete_issue(issue.id, project.id, "Done")
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_COMPLETED


@patch("app.services.issue_service.hook_registry")
async def test_accept_issue_fires_hook(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Accept me", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_ACCEPTED


@patch("app.services.issue_service.hook_registry")
async def test_cancel_issue_fires_hook(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Cancel me", priority=1)
    await service.cancel_issue(issue.id, project.id)
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_CANCELLED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_issue_service_hooks.py -v`
Expected: FAIL — `hook_registry` not imported in issue_service, no fire calls there

- [ ] **Step 3: Add hook firing to issue_service.py**

In `backend/app/services/issue_service.py`, add imports:
```python
from app.hooks.registry import hook_registry, HookEvent, HookContext
from app.services.event_service import event_service
from app.services.project_service import ProjectService
```

Update `complete_issue`:
```python
async def complete_issue(self, issue_id: str, project_id: str, recap: str) -> Issue:
    if not recap or not recap.strip():
        raise ValidationError("Recap cannot be blank")
    issue = await self.get_for_project(issue_id, project_id)
    if issue.status != IssueStatus.ACCEPTED:
        raise InvalidTransitionError(
            f"Can only complete issues in Accepted status, got {issue.status.value}"
        )
    # Enforce task completion
    from app.services.task_service import TaskService
    task_service = TaskService(self.session)
    tasks = await task_service.list_by_issue(issue.id)
    if tasks:
        from app.models.task import TaskStatus
        pending = [t for t in tasks if t.status != TaskStatus.COMPLETED]
        if pending:
            names = ", ".join(t.name for t in pending)
            raise ValidationError(
                f"Cannot complete: {len(pending)} tasks not finished: {names}"
            )
    issue.recap = recap
    issue.status = IssueStatus.FINISHED
    await self.session.flush()
    # Fire hook with project context
    project_service = ProjectService(self.session)
    project = await project_service.get_by_id(project_id)
    await hook_registry.fire(
        HookEvent.ISSUE_COMPLETED,
        HookContext(
            project_id=project_id,
            issue_id=issue_id,
            event=HookEvent.ISSUE_COMPLETED,
            metadata={
                "issue_name": issue.name or "",
                "recap": issue.recap or "",
                "project_name": project.name if project else "",
                "project_path": project.path if project else "",
                "project_description": project.description if project else "",
                "tech_stack": project.tech_stack if project else "",
            },
        ),
    )
    return issue
```

Update `accept_issue`:
```python
async def accept_issue(self, issue_id: str, project_id: str) -> Issue:
    issue = await self.get_for_project(issue_id, project_id)
    if issue.status != IssueStatus.PLANNED:
        raise InvalidTransitionError(
            f"Can only accept issues in Planned status, got {issue.status.value}"
        )
    issue.status = IssueStatus.ACCEPTED
    await self.session.flush()
    await hook_registry.fire(
        HookEvent.ISSUE_ACCEPTED,
        HookContext(project_id=project_id, issue_id=issue_id, event=HookEvent.ISSUE_ACCEPTED),
    )
    return issue
```

Update `cancel_issue`:
```python
async def cancel_issue(self, issue_id: str, project_id: str) -> Issue:
    issue = await self.get_for_project(issue_id, project_id)
    issue.status = IssueStatus.CANCELED
    await self.session.flush()
    await hook_registry.fire(
        HookEvent.ISSUE_CANCELLED,
        HookContext(project_id=project_id, issue_id=issue_id, event=HookEvent.ISSUE_CANCELLED),
    )
    return issue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_issue_service_hooks.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/issue_service.py backend/tests/test_issue_service_hooks.py
git commit -m "feat: move hook firing from MCP layer into service layer"
```

---

### Task 6: Simplify MCP Tools (Remove Duplicated Logic)

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`
- Modify: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1: Read current test_mcp_tools.py to understand existing tests**

Run: `cd backend && python -m pytest tests/test_mcp_tools.py -v --collect-only`

- [ ] **Step 2: Update MCP tools to be thin wrappers**

In `backend/app/mcp/server.py`:

Remove all hook-related imports (`hook_registry`, `HookEvent`, `HookContext`).

Remove `decline_issue` tool entirely.

Simplify `complete_issue` tool — remove hook firing (now in service):
```python
@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.complete_issue(issue_id, project_id, recap)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value, "recap": issue.recap}
        except AppError as e:
            return {"error": e.message}
```

Simplify `accept_issue` tool — remove hook firing:
```python
@mcp.tool(description=_desc["tool.accept_issue.description"])
async def accept_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.accept_issue(issue_id, project_id)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value}
        except AppError as e:
            return {"error": e.message}
```

Simplify `cancel_issue` tool — remove hook firing:
```python
@mcp.tool(description=_desc["tool.cancel_issue.description"])
async def cancel_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.cancel_issue(issue_id, project_id)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value}
        except AppError as e:
            return {"error": e.message}
```

Replace all `except (ValueError, PermissionError) as e:` with `except AppError as e:` across all tools.

Remove `decline_feedback` from `get_issue_details` return dict.

Add import: `from app.exceptions import AppError`

- [ ] **Step 3: Update default_settings.json**

Remove `"tool.decline_issue.description"` entry.

Update `"tool.create_issue_spec.description"` to reference only "New" status (not "Declined"):
```json
"tool.create_issue_spec.description": "Write a specification for an issue and move it to Reasoning status. Only works for issues in New status."
```

- [ ] **Step 4: Update MCP tests**

In `backend/tests/test_mcp_tools.py`: remove any tests for `decline_issue` tool, update references to DECLINED status, update expected error types.

- [ ] **Step 5: Run all tests**

Run: `cd backend && python -m pytest -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/server.py backend/app/mcp/default_settings.json backend/tests/test_mcp_tools.py
git commit -m "refactor: simplify MCP tools to thin service wrappers"
```

---

### Task 7: Simplify Routers (Remove Business Logic)

**Files:**
- Modify: `backend/app/routers/issues.py`
- Modify: `backend/app/routers/projects.py`
- Modify: `backend/tests/test_routers_issues.py`
- Modify: `backend/tests/test_routers_projects.py`

- [ ] **Step 1: Update router tests**

In `backend/tests/test_routers_issues.py`:

Remove `test_decline_with_feedback` test.

Update `test_update_status_invalid` — it should still return 422 (now via global handler from `InvalidTransitionError`).

- [ ] **Step 2: Simplify issues router**

In `backend/app/routers/issues.py`:

Remove all try/except blocks that catch `ValueError`/`PermissionError`. The global `AppError` handler now catches these. The router becomes:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.issue import Issue, IssueStatus
from app.schemas.issue import IssueCreate, IssueResponse, IssueStatusUpdate, IssueUpdate
from app.services.issue_service import IssueService

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


async def _reload_with_tasks(db: AsyncSession, issue_id: str) -> Issue:
    result = await db.execute(
        select(Issue).options(selectinload(Issue.tasks)).where(Issue.id == issue_id)
    )
    return result.scalar_one()


@router.post("", response_model=IssueResponse, status_code=201)
async def create_issue(project_id: str, data: IssueCreate, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    issue = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.get("", response_model=list[IssueResponse])
async def list_issues(
    project_id: str,
    status: IssueStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    return await service.list_by_project(project_id, status=status)


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    return await service.get_for_project(issue_id, project_id)


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    project_id: str, issue_id: str, data: IssueUpdate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.update_fields(issue_id, project_id, **data.model_dump(exclude_unset=True))
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.patch("/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(
    project_id: str,
    issue_id: str,
    data: IssueStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    issue = await service.update_status(issue_id, project_id, data.status)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    await service.delete(issue_id, project_id)
    await db.commit()
```

- [ ] **Step 3: Create terminal_service module-level singleton**

The `TerminalService` singleton is currently created inside `backend/app/routers/terminals.py`. To make it importable from other modules, add a singleton at the bottom of `backend/app/services/terminal_service.py`:

```python
# Module-level singleton
terminal_service = TerminalService()
```

Then update `backend/app/routers/terminals.py` to import from there instead of creating its own instance:
```python
from app.services.terminal_service import terminal_service
```

- [ ] **Step 4: Update projects router**

In `backend/app/routers/projects.py`, for `delete_project`:

Add terminal cleanup by importing and using the terminal service singleton:

```python
from app.services.terminal_service import terminal_service

@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    # Kill active terminals for this project
    for term in terminal_service.list_active(project_id=project_id):
        try:
            terminal_service.kill(term["id"])
        except KeyError:
            pass
    await service.delete(project_id)
    await db.commit()
```

- [ ] **Step 5: Run all router tests**

Run: `cd backend && python -m pytest tests/test_routers_issues.py tests/test_routers_projects.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/terminal_service.py backend/app/routers/terminals.py backend/app/routers/issues.py backend/app/routers/projects.py backend/tests/test_routers_issues.py backend/tests/test_routers_projects.py
git commit -m "refactor: simplify routers, add terminal cleanup on project delete"
```

---

### Task 8: Task Completion Enforcement

**Files:**
- Modify: `backend/app/services/issue_service.py` (already partially done in Task 5)
- Modify: `backend/tests/test_issue_service.py`

- [ ] **Step 1: Write the tests**

Add to `backend/tests/test_issue_service.py`:

```python
async def test_complete_issue_with_pending_tasks_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Has tasks", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    # Add pending tasks
    task_service = TaskService(db_session)
    await task_service.create_bulk(issue.id, [{"name": "Task 1"}, {"name": "Task 2"}])
    with pytest.raises(ValidationError, match="tasks not finished"):
        await service.complete_issue(issue.id, project.id, "Done")


async def test_complete_issue_with_all_tasks_completed(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Tasks done", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    # Add and complete tasks
    task_service = TaskService(db_session)
    tasks = await task_service.create_bulk(issue.id, [{"name": "Task 1"}])
    await task_service.update(tasks[0].id, status="In Progress")
    await task_service.update(tasks[0].id, status="Completed")
    updated = await service.complete_issue(issue.id, project.id, "All done")
    assert updated.status == IssueStatus.FINISHED


async def test_complete_issue_without_tasks_allowed(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="No tasks", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    updated = await service.complete_issue(issue.id, project.id, "Done without tasks")
    assert updated.status == IssueStatus.FINISHED


async def test_complete_issue_blank_recap_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Blank recap", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    with pytest.raises(ValidationError, match="blank"):
        await service.complete_issue(issue.id, project.id, "   ")
```

Add imports at top of test file:
```python
from app.exceptions import ValidationError
from app.services.task_service import TaskService
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `cd backend && python -m pytest tests/test_issue_service.py::test_complete_issue_with_pending_tasks_raises tests/test_issue_service.py::test_complete_issue_blank_recap_raises -v`
Expected: FAIL — no task validation or recap validation yet

- [ ] **Step 3: Verify implementation is already in place from Task 5**

The `complete_issue` method was updated in Task 5 to include both task enforcement and recap validation. Verify the code is correct.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_issue_service.py -v`
Expected: All pass

- [ ] **Step 5: Update the existing test_complete_issue to use the full lifecycle**

The existing `test_complete_issue` directly sets `issue.status = IssueStatus.ACCEPTED` via DB manipulation. Now that hooks fire in the service, update it to use the service lifecycle:

```python
async def test_complete_issue(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Finish me", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    updated = await service.complete_issue(issue.id, project.id, "All done. Implemented X and Y.")
    assert updated.status == IssueStatus.FINISHED
    assert updated.recap == "All done. Implemented X and Y."
```

- [ ] **Step 6: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_issue_service.py backend/app/services/issue_service.py
git commit -m "feat: enforce task completion before issue can be finished"
```

---

### Task 9: Hook Failure Observability

**Files:**
- Modify: `backend/app/hooks/registry.py`
- Modify: `backend/app/hooks/executor.py`
- Modify: `backend/app/hooks/__init__.py`
- Test: `backend/tests/test_hook_registry.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_hook_registry.py
"""Test hook registry error handling and observability."""
from unittest.mock import AsyncMock, patch

from app.hooks.registry import BaseHook, HookContext, HookEvent, HookRegistry, HookResult


class FailingHook(BaseHook):
    name = "failing_hook"
    description = "A hook that always fails"

    async def execute(self, context: HookContext) -> HookResult:
        raise RuntimeError("Something broke")


class ErrorResultHook(BaseHook):
    name = "error_result_hook"
    description = "A hook that returns error result"

    async def execute(self, context: HookContext) -> HookResult:
        return HookResult(success=False, error="CLI not found")


@patch("app.hooks.registry.event_service")
async def test_hook_exception_emits_hook_failed_event(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, FailingHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)
    await registry._run_hook(FailingHook, ctx)
    # Should have emitted hook_started and hook_failed
    assert mock_event_service.emit.call_count == 2
    failed_call = mock_event_service.emit.call_args_list[1][0][0]
    assert failed_call["type"] == "hook_failed"
    assert "Something broke" in failed_call["error"]


@patch("app.hooks.registry.event_service")
async def test_hook_error_result_emits_hook_failed_event(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, ErrorResultHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)
    await registry._run_hook(ErrorResultHook, ctx)
    assert mock_event_service.emit.call_count == 2
    failed_call = mock_event_service.emit.call_args_list[1][0][0]
    assert failed_call["type"] == "hook_failed"
    assert "CLI not found" in failed_call["error"]
```

- [ ] **Step 2: Run test to verify baseline**

Run: `cd backend && python -m pytest tests/test_hook_registry.py -v`
Expected: PASS (existing behavior already emits events — this confirms it)

- [ ] **Step 3: Add logging to registry.py**

In `backend/app/hooks/registry.py`, add at top:
```python
import logging

logger = logging.getLogger(__name__)
```

In `_run_hook`, add logging in the exception handler:
```python
except Exception as exc:  # noqa: BLE001
    logger.error("Hook %s failed with exception: %s", hook.name, exc)
    await event_service.emit(...)
```

And in the `result.success == False` branch:
```python
else:
    logger.warning("Hook %s returned error: %s", hook.name, result.error)
    await event_service.emit(...)
```

- [ ] **Step 4: Add logging to executor.py**

In `backend/app/hooks/executor.py`, add at top:
```python
import logging

logger = logging.getLogger(__name__)
```

In the `FileNotFoundError` handler:
```python
except FileNotFoundError:
    duration = time.monotonic() - start
    logger.error("'claude' CLI not found on PATH")
    return ExecutorResult(...)
```

In the generic `Exception` handler:
```python
except Exception as exc:  # noqa: BLE001
    duration = time.monotonic() - start
    logger.error("Claude Code executor failed: %s", exc)
    return ExecutorResult(...)
```

- [ ] **Step 5: Remove ISSUE_DECLINED from HookEvent**

In `backend/app/hooks/registry.py`:
```python
class HookEvent(str, Enum):
    ISSUE_COMPLETED = "issue_completed"
    ISSUE_ACCEPTED = "issue_accepted"
    ISSUE_CANCELLED = "issue_cancelled"
```

Update `backend/app/hooks/__init__.py` if it re-exports anything DECLINED-related (it doesn't, but verify).

- [ ] **Step 6: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/hooks/registry.py backend/app/hooks/executor.py backend/app/hooks/__init__.py backend/tests/test_hook_registry.py
git commit -m "feat: add logging to hook system, remove ISSUE_DECLINED event"
```

---

### Task 10: Input Validation for set_name

**Files:**
- Modify: `backend/app/services/issue_service.py`
- Modify: `backend/tests/test_issue_service.py`

- [ ] **Step 1: Write the test**

Add to `backend/tests/test_issue_service.py`:

```python
async def test_set_name_too_long_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    long_name = "x" * 501
    with pytest.raises(ValidationError, match="500"):
        await service.set_name(issue.id, project.id, long_name)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_issue_service.py::test_set_name_too_long_raises -v`
Expected: FAIL

- [ ] **Step 3: Add validation to set_name**

In `backend/app/services/issue_service.py`, update `set_name`:

```python
async def set_name(self, issue_id: str, project_id: str, name: str) -> Issue:
    if len(name) > 500:
        raise ValidationError("Name must be 500 characters or less")
    return await self.update_fields(issue_id, project_id, name=name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_issue_service.py::test_set_name_too_long_raises -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/issue_service.py backend/tests/test_issue_service.py
git commit -m "feat: add name length validation to set_name"
```

---

### Task 11: Frontend Cleanup — Remove Decline UI

**Files:**
- Modify: `frontend/src/pages/IssueDetailPage.jsx`
- Modify: `frontend/src/api/client.js` (if decline API calls exist)

- [ ] **Step 1: Remove decline_feedback display from IssueDetailPage.jsx**

Remove the entire block (lines 211-216):
```jsx
{issue.decline_feedback && (
  <div className="mb-4">
    <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Decline Feedback</h2>
    <p className="text-red-700 bg-red-50 rounded p-3 text-sm">{issue.decline_feedback}</p>
  </div>
)}
```

- [ ] **Step 2: Remove decline-related API calls from client.js (if any)**

Search `frontend/src/api/client.js` for any `decline` references and remove them.

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/IssueDetailPage.jsx frontend/src/api/client.js
git commit -m "feat: remove decline UI from frontend"
```

---

### Task 12: Final Integration Test Run

**Files:** None (verification only)

- [ ] **Step 1: Run complete backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: No errors

- [ ] **Step 3: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 4: Apply database migration**

Run: `cd backend && python -m alembic upgrade head`
Expected: Migration applies successfully

- [ ] **Step 5: Commit any remaining fixes**

If any fixes were needed, commit them.
