# Task Specification & Autonomous Claude Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `specification` field and `Reasoning` status to tasks, replace `get_next_task`/`save_task_plan` MCP tools with 6 new autonomous tools, and make the frontend read-only.

**Architecture:** Backend-first — model/schema/service/MCP in sequence; frontend last. Each task is independently committable. Tests run after every backend task. No blocking waits in MCP tools.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, SQLite, FastMCP, React 19, Tailwind CSS, Vite.

**Spec:** `docs/superpowers/specs/2026-03-19-task-spec-autonomous-workflow-design.md`

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `backend/alembic/versions/c3d4e5f6a7b8_add_specification_column.py` | Create | Migration: add `specification TEXT NULL` to `tasks` |
| `backend/app/models/task.py` | Modify | Add `REASONING` to `TaskStatus`; add `specification` column; add `(REASONING, PLANNED)` to `VALID_TRANSITIONS` |
| `backend/app/schemas/task.py` | Modify | Add `specification: str \| None` to `TaskResponse` |
| `backend/app/services/task_service.py` | Modify | Add 6 new methods: `create_spec`, `edit_spec`, `create_plan`, `edit_plan`, `accept_task`, `cancel_task` |
| `backend/tests/test_task_service.py` | Modify | Add tests for all 6 new service methods |
| `backend/app/mcp/server.py` | Modify | Comment out `get_next_task` + `save_task_plan`; update `get_task_details`; add 6 new tools |
| `backend/app/mcp/default_settings.json` | Modify | Remove old keys; update `get_task_details` description; add 6 new tool description keys |
| `backend/tests/test_mcp_tools.py` | Modify | Update tests that reference removed tools; add tests for new tools |
| `frontend/src/components/StatusBadge.jsx` | Modify | Add `Reasoning` badge (indigo) |
| `frontend/src/pages/ProjectDetailPage.jsx` | Modify | Add `"Reasoning"` to `STATUSES` filter array |
| `frontend/src/pages/TaskDetailPage.jsx` | Modify | Remove action buttons + decline form; add Specification section |

---

## Task 1: Database migration — add `specification` column

**Files:**
- Create: `backend/alembic/versions/c3d4e5f6a7b8_add_specification_column.py`

- [ ] **Step 1: Create the migration file**

```python
# backend/alembic/versions/c3d4e5f6a7b8_add_specification_column.py
"""add specification column to tasks

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("specification", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "specification")
```

- [ ] **Step 2: Apply the migration**

```bash
cd backend
alembic upgrade head
```

Expected output contains: `Running upgrade b1c2d3e4f5a6 -> c3d4e5f6a7b8`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/c3d4e5f6a7b8_add_specification_column.py
git commit -m "feat: add specification column migration"
```

---

## Task 2: Model and schema — add `Reasoning` status and `specification` field

**Files:**
- Modify: `backend/app/models/task.py`
- Modify: `backend/app/schemas/task.py`

- [ ] **Step 1: Update `TaskStatus` enum and `VALID_TRANSITIONS` in `models/task.py`**

Replace the `TaskStatus` class and `VALID_TRANSITIONS` set:

```python
class TaskStatus(str, enum.Enum):
    NEW = "New"
    REASONING = "Reasoning"
    PLANNED = "Planned"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    FINISHED = "Finished"
    CANCELED = "Canceled"


# Valid state transitions: (from_status, to_status)
VALID_TRANSITIONS = {
    (TaskStatus.NEW, TaskStatus.PLANNED),
    (TaskStatus.DECLINED, TaskStatus.PLANNED),
    (TaskStatus.REASONING, TaskStatus.PLANNED),
    (TaskStatus.PLANNED, TaskStatus.ACCEPTED),
    (TaskStatus.PLANNED, TaskStatus.DECLINED),
    (TaskStatus.ACCEPTED, TaskStatus.FINISHED),
}
# Any → Canceled is always valid (handled in code)
```

- [ ] **Step 2: Add `specification` column to `Task` model in `models/task.py`**

Add this line after `plan`:

```python
specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

The Task class body should look like:

```python
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.NEW)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decline_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
```

- [ ] **Step 3: Add `specification` to `TaskResponse` in `schemas/task.py`**

Add after `plan: str | None`:

```python
specification: str | None = None
```

The full `TaskResponse` class:

```python
class TaskResponse(BaseModel):
    id: str
    project_id: str
    name: str | None
    description: str
    status: TaskStatus
    priority: int
    plan: str | None
    specification: str | None
    recap: str | None
    decline_feedback: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run existing tests to confirm nothing broke**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all existing tests pass (some may reference `save_plan` — they'll still pass since we haven't changed that method yet).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/task.py backend/app/schemas/task.py
git commit -m "feat: add Reasoning status and specification field to task model"
```

---

## Task 3: Tests — write failing tests for 6 new service methods (TDD)

**Files:**
- Modify: `backend/tests/test_task_service.py`

- [ ] **Step 1: Append tests for all 6 new methods to `test_task_service.py`**

These tests will fail with `AttributeError` until Task 4 implements the methods — that failure is the expected TDD starting state.

Append to `backend/tests/test_task_service.py`:

```python
# ── create_spec ──────────────────────────────────────────────────────────────

async def test_create_spec_from_new(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Spec me", priority=1)
    updated = await service.create_spec(task.id, project.id, "# Spec\n\nDo X.")
    assert updated.specification == "# Spec\n\nDo X."
    assert updated.status == TaskStatus.REASONING


async def test_create_spec_from_declined(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Respec me", priority=1)
    task.status = TaskStatus.DECLINED
    await db_session.flush()
    updated = await service.create_spec(task.id, project.id, "# New Spec")
    assert updated.status == TaskStatus.REASONING


async def test_create_spec_invalid_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Already reasoning", priority=1)
    task.status = TaskStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValueError, match="New or Declined"):
        await service.create_spec(task.id, project.id, "# Spec")


async def test_create_spec_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    with pytest.raises(ValueError, match="blank"):
        await service.create_spec(task.id, project.id, "   ")


# ── edit_spec ─────────────────────────────────────────────────────────────────

async def test_edit_spec(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Edit spec", priority=1)
    await service.create_spec(task.id, project.id, "# Original")
    updated = await service.edit_spec(task.id, project.id, "# Updated Spec")
    assert updated.specification == "# Updated Spec"
    assert updated.status == TaskStatus.REASONING


async def test_edit_spec_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not reasoning", priority=1)
    with pytest.raises(ValueError, match="Reasoning status"):
        await service.edit_spec(task.id, project.id, "# Spec")


async def test_edit_spec_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    task.status = TaskStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValueError, match="blank"):
        await service.edit_spec(task.id, project.id, "")


# ── create_plan ───────────────────────────────────────────────────────────────

async def test_create_plan_from_reasoning(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Plan me", priority=1)
    await service.create_spec(task.id, project.id, "# Spec")
    updated = await service.create_plan(task.id, project.id, "# Plan\n\nStep 1.")
    assert updated.plan == "# Plan\n\nStep 1."
    assert updated.status == TaskStatus.PLANNED


async def test_create_plan_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not reasoned", priority=1)
    with pytest.raises(ValueError, match="Reasoning status"):
        await service.create_plan(task.id, project.id, "# Plan")


async def test_create_plan_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    task.status = TaskStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValueError, match="blank"):
        await service.create_plan(task.id, project.id, "  ")


# ── edit_plan ─────────────────────────────────────────────────────────────────

async def test_edit_plan(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Edit plan", priority=1)
    await service.create_spec(task.id, project.id, "# Spec")
    await service.create_plan(task.id, project.id, "# Plan v1")
    updated = await service.edit_plan(task.id, project.id, "# Plan v2")
    assert updated.plan == "# Plan v2"
    assert updated.status == TaskStatus.PLANNED


async def test_edit_plan_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not planned", priority=1)
    with pytest.raises(ValueError, match="Planned status"):
        await service.edit_plan(task.id, project.id, "# Plan")


async def test_edit_plan_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    task.status = TaskStatus.PLANNED
    await db_session.flush()
    with pytest.raises(ValueError, match="blank"):
        await service.edit_plan(task.id, project.id, "")


# ── accept_task ───────────────────────────────────────────────────────────────

async def test_accept_task(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Accept me", priority=1)
    task.status = TaskStatus.PLANNED
    await db_session.flush()
    updated = await service.accept_task(task.id, project.id)
    assert updated.status == TaskStatus.ACCEPTED


async def test_accept_task_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not planned", priority=1)
    with pytest.raises(ValueError, match="Planned status"):
        await service.accept_task(task.id, project.id)


# ── cancel_task ───────────────────────────────────────────────────────────────

async def test_cancel_task_from_any_status(db_session, project):
    service = TaskService(db_session)
    for status in [TaskStatus.NEW, TaskStatus.REASONING, TaskStatus.PLANNED, TaskStatus.ACCEPTED]:
        task = await service.create(project_id=project.id, description=f"Cancel from {status}", priority=1)
        task.status = status
        await db_session.flush()
        updated = await service.cancel_task(task.id, project.id)
        assert updated.status == TaskStatus.CANCELED
```

- [ ] **Step 2: Run the new tests — confirm they FAIL (methods not implemented yet)**

```bash
cd backend
python -m pytest tests/test_task_service.py -v -k "spec or create_plan or edit_plan or accept_task or cancel_task"
```

Expected: tests FAIL with `AttributeError: 'TaskService' object has no attribute 'create_spec'` (or similar). This confirms TDD red state.

- [ ] **Step 3: Commit the failing tests**

```bash
git add backend/tests/test_task_service.py
git commit -m "test: add failing tests for new task service methods (TDD red)"
```

---

## Task 4: Service — implement 6 new methods (TDD green)

**Files:**
- Modify: `backend/app/services/task_service.py`

> **Note on implementation pattern:** These methods use direct attribute assignment (`task.specification = spec`, `task.status = TaskStatus.REASONING`) rather than delegating to `update_status()`, consistent with the existing `save_plan` and `complete_task` patterns in this codebase. Each method performs its own status validation before writing, making the `update_status()` guard redundant. The `(REASONING, PLANNED)` entry in `VALID_TRANSITIONS` remains because it documents the valid state machine and would guard any direct REST `PATCH /status` calls.

- [ ] **Step 1: Add `create_spec` method**

Add after `complete_task` method (before `delete`):

```python
async def create_spec(self, task_id: str, project_id: str, spec: str) -> Task:
    if not spec or not spec.strip():
        raise ValueError("Specification cannot be blank")
    task = await self.get_for_project(task_id, project_id)
    if task.status not in (TaskStatus.NEW, TaskStatus.DECLINED):
        raise ValueError(
            f"Can only create spec for tasks in New or Declined status, got {task.status.value}"
        )
    task.specification = spec
    task.status = TaskStatus.REASONING
    await self.session.flush()
    return task
```

- [ ] **Step 2: Add `edit_spec` method**

```python
async def edit_spec(self, task_id: str, project_id: str, spec: str) -> Task:
    if not spec or not spec.strip():
        raise ValueError("Specification cannot be blank")
    task = await self.get_for_project(task_id, project_id)
    if task.status != TaskStatus.REASONING:
        raise ValueError("Task must be in Reasoning status to edit spec")
    task.specification = spec
    await self.session.flush()
    return task
```

- [ ] **Step 3: Add `create_plan` method**

```python
async def create_plan(self, task_id: str, project_id: str, plan: str) -> Task:
    if not plan or not plan.strip():
        raise ValueError("Plan cannot be blank")
    task = await self.get_for_project(task_id, project_id)
    if task.status != TaskStatus.REASONING:
        raise ValueError(
            f"Can only create plan for tasks in Reasoning status, got {task.status.value}"
        )
    task.plan = plan
    task.status = TaskStatus.PLANNED
    await self.session.flush()
    return task
```

- [ ] **Step 4: Add `edit_plan` method**

```python
async def edit_plan(self, task_id: str, project_id: str, plan: str) -> Task:
    if not plan or not plan.strip():
        raise ValueError("Plan cannot be blank")
    task = await self.get_for_project(task_id, project_id)
    if task.status != TaskStatus.PLANNED:
        raise ValueError("Task must be in Planned status to edit plan")
    task.plan = plan
    await self.session.flush()
    return task
```

- [ ] **Step 5: Add `accept_task` method**

```python
async def accept_task(self, task_id: str, project_id: str) -> Task:
    task = await self.get_for_project(task_id, project_id)
    if task.status != TaskStatus.PLANNED:
        raise ValueError(
            f"Can only accept tasks in Planned status, got {task.status.value}"
        )
    task.status = TaskStatus.ACCEPTED
    await self.session.flush()
    return task
```

- [ ] **Step 6: Add `cancel_task` method**

```python
async def cancel_task(self, task_id: str, project_id: str) -> Task:
    task = await self.get_for_project(task_id, project_id)
    task.status = TaskStatus.CANCELED
    await self.session.flush()
    return task
```

- [ ] **Step 7: Run the previously-failing tests — confirm they now PASS**

```bash
cd backend
python -m pytest tests/test_task_service.py -v -k "spec or create_plan or edit_plan or accept_task or cancel_task"
```

Expected: all new tests PASS (TDD green).

- [ ] **Step 8: Run full test suite**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/task_service.py
git commit -m "feat: add create_spec, edit_spec, create_plan, edit_plan, accept_task, cancel_task service methods"
```

---

## Task 5: MCP Server — comment out old tools, add 6 new, update get_task_details

**Files:**
- Modify: `backend/app/mcp/server.py`

**Important:** Do this BEFORE editing `default_settings.json`. The server reads JSON keys at startup when tool decorators execute; commenting out the tool registration first prevents `KeyError` crashes.

- [ ] **Step 1: Comment out `get_next_task` tool**

Wrap the `get_next_task` function with block comments. Replace:

```python
@mcp.tool(description=_desc["tool.get_next_task.description"])
async def get_next_task(project_id: str) -> dict | None:
    async with async_session() as session:
        task_service = TaskService(session)
        task = await task_service.get_next_task(project_id)
        if task is None:
            return None
        result = {
            "id": task.id,
            "description": task.description,
            "status": task.status.value,
        }
        if task.decline_feedback:
            result["decline_feedback"] = task.decline_feedback
        return result
```

With:

```python
# DISABLED: Claude Code selects tasks autonomously via conversation
# @mcp.tool(description=_desc["tool.get_next_task.description"])
# async def get_next_task(project_id: str) -> dict | None:
#     async with async_session() as session:
#         task_service = TaskService(session)
#         task = await task_service.get_next_task(project_id)
#         if task is None:
#             return None
#         result = {
#             "id": task.id,
#             "description": task.description,
#             "status": task.status.value,
#         }
#         if task.decline_feedback:
#             result["decline_feedback"] = task.decline_feedback
#         return result
```

- [ ] **Step 2: Comment out `save_task_plan` tool**

Replace:

```python
@mcp.tool(description=_desc["tool.save_task_plan.description"])
async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        settings_service = SettingsService(session)
        try:
            task = await task_service.save_plan(task_id, project_id, plan)
            await session.commit()
            # Response message is read from DB on every call — real-time updates.
            response_msg = await settings_service.get("tool.save_task_plan.response_message")
            return {
                "id": task.id,
                "status": task.status.value,
                "plan": task.plan,
                "message": response_msg,
            }
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}
```

With:

```python
# DISABLED: Replaced by create_task_plan + edit_task_plan
# @mcp.tool(description=_desc["tool.save_task_plan.description"])
# async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
#     async with async_session() as session:
#         task_service = TaskService(session)
#         settings_service = SettingsService(session)
#         try:
#             task = await task_service.save_plan(task_id, project_id, plan)
#             await session.commit()
#             response_msg = await settings_service.get("tool.save_task_plan.response_message")
#             return {
#                 "id": task.id,
#                 "status": task.status.value,
#                 "plan": task.plan,
#                 "message": response_msg,
#             }
#         except (ValueError, PermissionError) as e:
#             await session.rollback()
#             return {"error": str(e)}
```

- [ ] **Step 3: Update `get_task_details` to include `specification`**

Add `"specification": task.specification,` to the return dict. The updated function:

```python
@mcp.tool(description=_desc["tool.get_task_details.description"])
async def get_task_details(project_id: str, task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_for_project(task_id, project_id)
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {
            "id": task.id,
            "project_id": task.project_id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority,
            "specification": task.specification,
            "plan": task.plan,
            "recap": task.recap,
            "decline_feedback": task.decline_feedback,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
```

- [ ] **Step 4: Add the 6 new MCP tools after `complete_task`**

Append after the `complete_task` tool (and after the `SettingsService` import is no longer needed, but keep the import since it's still in the file):

```python
@mcp.tool(description=_desc["tool.create_task_spec.description"])
async def create_task_spec(project_id: str, task_id: str, spec: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.create_spec(task_id, project_id, spec)
            await session.commit()
            return {"id": task.id, "status": task.status.value, "specification": task.specification}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.edit_task_spec.description"])
async def edit_task_spec(project_id: str, task_id: str, spec: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.edit_spec(task_id, project_id, spec)
            await session.commit()
            return {"id": task.id, "status": task.status.value, "specification": task.specification}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.create_task_plan.description"])
async def create_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.create_plan(task_id, project_id, plan)
            await session.commit()
            return {"id": task.id, "status": task.status.value, "plan": task.plan}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.edit_task_plan.description"])
async def edit_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.edit_plan(task_id, project_id, plan)
            await session.commit()
            return {"id": task.id, "status": task.status.value, "plan": task.plan}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.accept_task.description"])
async def accept_task(project_id: str, task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.accept_task(task_id, project_id)
            await session.commit()
            return {"id": task.id, "status": task.status.value}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.cancel_task.description"])
async def cancel_task(project_id: str, task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.cancel_task(task_id, project_id)
            await session.commit()
            return {"id": task.id, "status": task.status.value}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}
```

- [ ] **Step 5: Commit the server changes**

```bash
git add backend/app/mcp/server.py
git commit -m "feat: add 6 new MCP tools, disable get_next_task and save_task_plan, add specification to get_task_details"
```

---

## Task 6: Update `default_settings.json`

**Files:**
- Modify: `backend/app/mcp/default_settings.json`

- [ ] **Step 1: Replace the entire file content**

The new `default_settings.json`:

```json
{
  "server.name": "Manager AI",
  "tool.get_task_details.description": "Get all details of a specific task. Returns: id, project_id, name, description, status, priority, specification (markdown, may be null), plan (markdown, may be null), recap (markdown, may be null), decline_feedback (may be null), created_at, updated_at.",
  "tool.get_task_status.description": "Get the current status of a task.",
  "tool.get_project_context.description": "Get project information (name, path, description, tech_stack).",
  "tool.set_task_name.description": "Set the name of a task after analysis.",
  "tool.complete_task.description": "Mark a task as Finished and save the recap. Only works for tasks in Accepted status.",
  "tool.create_task_spec.description": "Write a specification for a task and move it to Reasoning status. Only works for tasks in New or Declined status. The spec should describe what needs to be built, acceptance criteria, and any constraints.",
  "tool.edit_task_spec.description": "Update the specification of a task that is in Reasoning status. Use this to refine the spec based on user feedback. Does not change the task status.",
  "tool.create_task_plan.description": "Write an implementation plan for a task and move it to Planned status. Only works for tasks in Reasoning status. The plan should describe the step-by-step implementation approach.",
  "tool.edit_task_plan.description": "Update the implementation plan of a task that is in Planned status. Use this to revise the plan based on user feedback. Does not change the task status.",
  "tool.accept_task.description": "Accept a task and move it to Accepted status. Only works for tasks in Planned status. Call this after the user confirms the plan in conversation.",
  "tool.cancel_task.description": "Cancel a task, moving it to Canceled status. Can be called from any status. Use when the user says to discard or skip this task."
}
```

- [ ] **Step 2: Run all tests to confirm startup keys are consistent**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all tests pass. (The MCP server reads this JSON at module import time; test imports will catch any `KeyError`.)

- [ ] **Step 3: Commit**

```bash
git add backend/app/mcp/default_settings.json
git commit -m "feat: update MCP tool descriptions — remove disabled tools, add 6 new tools"
```

---

## Task 7: Update MCP tests

**Files:**
- Modify: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1: Remove tests that reference removed tools and update remaining tests**

The existing `test_mcp_get_next_task_flow` and `test_mcp_decline_and_replan_flow` tests reference `save_plan` / `get_next_task` which are now disabled tools. Rewrite `test_mcp_tools.py` to reflect the new autonomous workflow:

```python
import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio

from app.models.task import TaskStatus
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
import app.mcp.server as mcp_server
from unittest.mock import patch


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="MCP Test", path="/tmp/mcp", description="MCP test project", tech_stack="Python, FastAPI")


@pytest.fixture
def task_service(db_session):
    return TaskService(db_session)


@pytest.fixture
def project_service(db_session):
    return ProjectService(db_session)


@pytest.mark.asyncio
async def test_mcp_autonomous_workflow(task_service, project):
    """Simulates full autonomous flow: create_spec → create_plan → accept → complete"""
    task = await task_service.create(project_id=project.id, description="Feature Z", priority=1)

    # Claude writes spec
    await task_service.create_spec(task.id, project.id, "# Spec\n\nBuild feature Z.")
    assert task.status == TaskStatus.REASONING
    assert task.specification == "# Spec\n\nBuild feature Z."

    # Claude refines spec after user feedback
    await task_service.edit_spec(task.id, project.id, "# Spec v2\n\nBuild feature Z with extra.")
    assert task.specification == "# Spec v2\n\nBuild feature Z with extra."
    assert task.status == TaskStatus.REASONING

    # Claude writes plan
    await task_service.create_plan(task.id, project.id, "# Plan\n\nStep 1: Do it.")
    assert task.status == TaskStatus.PLANNED

    # User approves in conversation, Claude accepts
    await task_service.accept_task(task.id, project.id)
    assert task.status == TaskStatus.ACCEPTED

    # Claude completes
    result = await task_service.complete_task(task.id, project.id, "Done.")
    assert result.status == TaskStatus.FINISHED


@pytest.mark.asyncio
async def test_mcp_complete_flow(task_service, project):
    """Simulates: plan → accept → complete with recap"""
    task = await task_service.create(project_id=project.id, description="Feature Y", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec")
    await task_service.create_plan(task.id, project.id, "# Plan")
    await task_service.accept_task(task.id, project.id)
    assert task.status == TaskStatus.ACCEPTED

    result = await task_service.complete_task(task.id, project.id, "Implemented feature Y successfully")
    assert result.status == TaskStatus.FINISHED
    assert result.recap == "Implemented feature Y successfully"


@pytest.mark.asyncio
async def test_mcp_cancel_flow(task_service, project):
    """Claude can cancel from any status"""
    task = await task_service.create(project_id=project.id, description="Cancel me", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec")
    result = await task_service.cancel_task(task.id, project.id)
    assert result.status == TaskStatus.CANCELED


@pytest.mark.asyncio
async def test_mcp_project_context(project_service, project):
    """get_project_context returns project info"""
    fetched = await project_service.get_by_id(project.id)
    assert fetched.name == "MCP Test"
    assert fetched.path == "/tmp/mcp"
    assert fetched.description == "MCP test project"
    assert fetched.tech_stack == "Python, FastAPI"


@pytest.mark.asyncio
async def test_mcp_get_project_context_includes_tech_stack(db_session, project):
    """get_project_context tool returns tech_stack in its dict"""

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_project_context(str(project.id))

    assert result["tech_stack"] == "Python, FastAPI"
    assert result["name"] == "MCP Test"


@pytest.mark.asyncio
async def test_mcp_get_task_details_includes_specification(db_session, project):
    """get_task_details returns specification field"""
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="Spec task", priority=1)
    await task_service.create_spec(task.id, project.id, "# My Spec")

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_task_details(str(project.id), str(task.id))

    assert result["specification"] == "# My Spec"
    assert result["status"] == "Reasoning"


@pytest.mark.asyncio
async def test_mcp_task_project_validation(task_service, project):
    """All MCP tools must validate project_id ownership"""
    task = await task_service.create(project_id=project.id, description="Test", priority=1)
    fake_project_id = uuid.uuid4()

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.set_name(task.id, fake_project_id, "Name")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.create_spec(task.id, fake_project_id, "Spec")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.complete_task(task.id, fake_project_id, "Recap")
```

- [ ] **Step 2: Run the updated MCP tests**

```bash
cd backend
python -m pytest tests/test_mcp_tools.py -v
```

Expected: all tests PASS.

- [ ] **Step 3: Run full suite**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_mcp_tools.py
git commit -m "test: update MCP tests for autonomous workflow, add get_task_details spec test"
```

---

## Task 8: Frontend — StatusBadge and filter

**Files:**
- Modify: `frontend/src/components/StatusBadge.jsx`
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`

- [ ] **Step 1: Add `Reasoning` badge to `StatusBadge.jsx`**

Replace the `STATUS_COLORS` object:

```javascript
const STATUS_COLORS = {
  New: "bg-blue-100 text-blue-800",
  Reasoning: "bg-indigo-100 text-indigo-800",
  Planned: "bg-yellow-100 text-yellow-800",
  Accepted: "bg-green-100 text-green-800",
  Declined: "bg-red-100 text-red-800",
  Finished: "bg-gray-100 text-gray-800",
  Canceled: "bg-gray-100 text-gray-500",
};
```

- [ ] **Step 2: Add `"Reasoning"` to the `STATUSES` array in `ProjectDetailPage.jsx`**

Replace:

```javascript
const STATUSES = ["All", "New", "Planned", "Accepted", "Declined", "Finished", "Canceled"];
```

With:

```javascript
const STATUSES = ["All", "New", "Reasoning", "Planned", "Accepted", "Declined", "Finished", "Canceled"];
```

- [ ] **Step 3: Verify the frontend builds without errors**

```bash
cd frontend
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/StatusBadge.jsx frontend/src/pages/ProjectDetailPage.jsx
git commit -m "feat: add Reasoning status badge and filter"
```

---

## Task 9: Frontend — TaskDetailPage read-only + Specification section

**Files:**
- Modify: `frontend/src/pages/TaskDetailPage.jsx`

- [ ] **Step 1: Rewrite `TaskDetailPage.jsx`**

Replace the entire file content:

```jsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import MarkdownViewer from "../components/MarkdownViewer";
import StatusBadge from "../components/StatusBadge";

export default function TaskDetailPage() {
  const { id: projectId, taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTask(projectId, taskId).then(setTask).finally(() => setLoading(false));
  }, [projectId, taskId]);

  if (loading) return <p>Loading...</p>;
  if (!task) return <p>Task not found.</p>;

  return (
    <div>
      <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline mb-4 block">
        &larr; Back to tasks
      </button>

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-bold">{task.name || "Untitled Task"}</h1>
            <p className="text-sm text-gray-500 mt-1">Priority: {task.priority}</p>
          </div>
          <StatusBadge status={task.status} />
        </div>

        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Description</h2>
          <p className="text-gray-700">{task.description}</p>
        </div>

        {task.specification && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Specification</h2>
            <div className="bg-indigo-50 rounded p-4">
              <MarkdownViewer content={task.specification} />
            </div>
          </div>
        )}

        {task.plan && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Plan</h2>
            <div className="bg-gray-50 rounded p-4">
              <MarkdownViewer content={task.plan} />
            </div>
          </div>
        )}

        {task.recap && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Recap</h2>
            <div className="bg-green-50 rounded p-4">
              <MarkdownViewer content={task.recap} />
            </div>
          </div>
        )}

        {task.decline_feedback && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Decline Feedback</h2>
            <p className="text-red-700 bg-red-50 rounded p-4">{task.decline_feedback}</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build the frontend**

```bash
cd frontend
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TaskDetailPage.jsx
git commit -m "feat: make TaskDetailPage read-only, add Specification section"
```

---

## Final check

- [ ] **Run the full backend test suite one last time**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Start the backend and verify MCP tools list in logs**

```bash
cd backend
uvicorn app.main:app --reload
```

Confirm the startup log shows the new tools registered and does not show `get_next_task` or `save_task_plan`.

- [ ] **Start the frontend and do a quick smoke test**

```bash
cd frontend
npm run dev
```

Open a task in the browser. Confirm:
- No Accept/Decline/Cancel buttons visible
- Specification section appears (if a task has one)
- `Reasoning` badge shows in indigo when a task is in that status
- `Reasoning` filter button is visible on the project page
