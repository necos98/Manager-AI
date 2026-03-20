# Issues Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the `tasks` table to `issues`, create a new `tasks` table for atomic plan tasks, and update all backend/frontend/MCP references accordingly.

**Architecture:** The existing `tasks` table becomes `issues` (the high-level container with spec, plan, recap). A new `tasks` table stores atomic plan steps (`{name, status, order}`) with FK to `issues`. All layers (models, schemas, services, routers, MCP, frontend) are updated to reflect this hierarchy.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async), Alembic, SQLite, Pydantic v2, React 18, Vite

**Spec:** `docs/superpowers/specs/2026-03-20-issues-refactoring-design.md`

---

### Task 1: New Task model (atomic plan tasks)

**Files:**
- Create: `backend/app/models/task_atomic.py` (temporary, moved in Task 2)

This task creates the NEW `Task` model for atomic plan tasks. The existing `backend/app/models/task.py` will be handled in Task 2 (rename to issue.py). For now, we write the new model to a temporary name and move it in Task 2.

- [ ] **Step 1: Write the new Task model**

Create `backend/app/models/task_atomic.py` (temporary name — renamed in Task 2):

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


VALID_TASK_TRANSITIONS = {
    (TaskStatus.PENDING, TaskStatus.IN_PROGRESS),
    (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED),
}


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("issue_id", "order", name="uq_task_issue_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    issue = relationship("Issue", back_populates="tasks")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/task_atomic.py
git commit -m "feat: add new Task model for atomic plan tasks"
```

---

### Task 2: Rename Task model → Issue model

**Files:**
- Rename: `backend/app/models/task.py` → `backend/app/models/issue.py`
- Move: `backend/app/models/task_atomic.py` → `backend/app/models/task.py`
- Modify: `backend/app/models/project.py:21`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create `backend/app/models/issue.py`**

Copy from existing `task.py` and rename:
- `TaskStatus` → `IssueStatus`
- `Task` → `Issue`
- `__tablename__` → `"issues"`
- Update `VALID_TRANSITIONS`: remove `(NEW, PLANNED)` and `(DECLINED, PLANNED)`, keep only `(REASONING, PLANNED)`
- Add relationship: `tasks = relationship("Task", back_populates="issue", cascade="all, delete-orphan", order_by="Task.order")`
- Update `project = relationship("Project", back_populates="issues")`

```python
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IssueStatus(str, enum.Enum):
    NEW = "New"
    REASONING = "Reasoning"
    PLANNED = "Planned"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    FINISHED = "Finished"
    CANCELED = "Canceled"


VALID_TRANSITIONS = {
    (IssueStatus.REASONING, IssueStatus.PLANNED),
    (IssueStatus.PLANNED, IssueStatus.ACCEPTED),
    (IssueStatus.PLANNED, IssueStatus.DECLINED),
    (IssueStatus.ACCEPTED, IssueStatus.FINISHED),
}


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus), nullable=False, default=IssueStatus.NEW)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decline_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="issues")
    tasks = relationship("Task", back_populates="issue", cascade="all, delete-orphan", order_by="Task.order")
```

- [ ] **Step 2: Move `task_atomic.py` → `task.py`**

Delete the old `backend/app/models/task.py` and rename `task_atomic.py` to `task.py`.

- [ ] **Step 3: Update `backend/app/models/project.py`**

Change line 21:
```python
# OLD
tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
# NEW
issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan")
```

- [ ] **Step 4: Update `backend/app/models/__init__.py`**

```python
from app.database import Base
from app.models.issue import Issue
from app.models.project import Project
from app.models.setting import Setting
from app.models.task import Task

__all__ = ["Base", "Issue", "Project", "Setting", "Task"]
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/
git commit -m "refactor: rename Task model to Issue, add new Task model for atomic plan tasks"
```

---

### Task 3: Alembic migration

**Files:**
- Create: `backend/alembic/versions/d4e5f6a7b8c9_rename_tasks_to_issues.py`

- [ ] **Step 1: Write the migration**

```python
"""rename tasks to issues, create new tasks table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("tasks", "issues")
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("issue_id", sa.String(36), sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.Enum("Pending", "In Progress", "Completed", name="taskstatus"), nullable=False, server_default="Pending"),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("issue_id", "order", name="uq_task_issue_order"),
    )


def downgrade() -> None:
    op.drop_table("tasks")
    op.rename_table("issues", "tasks")
```

- [ ] **Step 2: Run migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/d4e5f6a7b8c9_rename_tasks_to_issues.py
git commit -m "feat: add migration to rename tasks→issues and create new tasks table"
```

---

### Task 4: Issue schemas (rename from task schemas)

**Files:**
- Rename: `backend/app/schemas/task.py` → `backend/app/schemas/issue.py`
- Create: `backend/app/schemas/task.py` (new, for atomic tasks)

- [ ] **Step 1: Create `backend/app/schemas/task.py`** (new atomic task schemas)

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TaskBulkCreate(BaseModel):
    tasks: list[TaskCreate] = Field(..., min_length=1)


class TaskUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    status: TaskStatus | None = None


class TaskResponse(BaseModel):
    id: str
    issue_id: str
    name: str
    status: TaskStatus
    order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `backend/app/schemas/issue.py`**

Based on old `schemas/task.py`, rename types and add `tasks` field:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.issue import IssueStatus
from app.schemas.task import TaskResponse


class IssueCreate(BaseModel):
    description: str = Field(..., min_length=1)
    priority: int = Field(default=3, ge=1, le=5)


class IssueUpdate(BaseModel):
    description: str | None = Field(None, min_length=1)
    priority: int | None = Field(None, ge=1, le=5)


class IssueStatusUpdate(BaseModel):
    status: IssueStatus
    decline_feedback: str | None = None


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
    decline_feedback: str | None
    tasks: list[TaskResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Delete old `backend/app/schemas/task.py`** (it was replaced by the new one in step 1)

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/
git commit -m "refactor: rename task schemas to issue, add new task schemas for atomic tasks"
```

---

### Task 5: Issue service (rename from task service)

**Files:**
- Rename: `backend/app/services/task_service.py` → `backend/app/services/issue_service.py`
- Create: `backend/app/services/task_service.py` (new, for atomic tasks)

- [ ] **Step 1: Create `backend/app/services/issue_service.py`**

Copy from existing `task_service.py` and rename:
- All `Task` → `Issue`, `TaskStatus` → `IssueStatus`, `TaskService` → `IssueService`
- `get_next_task` → `get_next_issue`
- `accept_task` → `accept_issue`
- `cancel_task` → `cancel_issue`
- `complete_task` → `complete_issue`
- Remove `save_plan` method (legacy)
- Add `decline_issue` method
- Add `selectinload(Issue.tasks)` to `get_for_project`
- Update all error messages from "Task" to "Issue"

```python
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.issue import VALID_TRANSITIONS, Issue, IssueStatus


class IssueService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: str, description: str, priority: int = 3) -> Issue:
        issue = Issue(project_id=project_id, description=description, priority=priority)
        self.session.add(issue)
        await self.session.flush()
        return issue

    async def get_by_id(self, issue_id: str) -> Issue | None:
        return await self.session.get(Issue, issue_id)

    async def get_for_project(self, issue_id: str, project_id: str) -> Issue:
        result = await self.session.execute(
            select(Issue)
            .options(selectinload(Issue.tasks))
            .where(Issue.id == issue_id)
        )
        issue = result.scalar_one_or_none()
        if issue is None:
            raise ValueError("Issue not found")
        if issue.project_id != project_id:
            raise PermissionError("Issue does not belong to project")
        return issue

    async def list_by_project(
        self, project_id: str, status: IssueStatus | None = None
    ) -> list[Issue]:
        query = select(Issue).options(selectinload(Issue.tasks)).where(Issue.project_id == project_id)
        if status is not None:
            query = query.where(Issue.status == status)
        query = query.order_by(Issue.priority.asc(), Issue.created_at.asc())
        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_next_issue(self, project_id: str) -> Issue | None:
        query = (
            select(Issue)
            .where(Issue.project_id == project_id)
            .where(Issue.status.in_([IssueStatus.NEW, IssueStatus.DECLINED]))
            .order_by(
                case(
                    (Issue.status == IssueStatus.DECLINED, 0),
                    (Issue.status == IssueStatus.NEW, 1),
                ).asc(),
                Issue.priority.asc(),
                Issue.created_at.asc(),
            )
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        issue_id: str,
        project_id: str,
        new_status: IssueStatus,
        decline_feedback: str | None = None,
    ) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if new_status == IssueStatus.CANCELED:
            issue.status = IssueStatus.CANCELED
            await self.session.flush()
            return issue
        if (issue.status, new_status) not in VALID_TRANSITIONS:
            raise ValueError(f"Invalid state transition from {issue.status.value} to {new_status.value}")
        issue.status = new_status
        if new_status == IssueStatus.DECLINED and decline_feedback:
            issue.decline_feedback = decline_feedback
        await self.session.flush()
        return issue

    async def update_fields(self, issue_id: str, project_id: str, **kwargs) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(issue, key, value)
        await self.session.flush()
        return issue

    async def set_name(self, issue_id: str, project_id: str, name: str) -> Issue:
        return await self.update_fields(issue_id, project_id, name=name)

    async def complete_issue(self, issue_id: str, project_id: str, recap: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.ACCEPTED:
            raise ValueError(f"Can only complete issues in Accepted status, got {issue.status.value}")
        issue.recap = recap
        issue.status = IssueStatus.FINISHED
        await self.session.flush()
        return issue

    async def create_spec(self, issue_id: str, project_id: str, spec: str) -> Issue:
        if not spec or not spec.strip():
            raise ValueError("Specification cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status not in (IssueStatus.NEW, IssueStatus.DECLINED):
            raise ValueError(
                f"Can only create spec for issues in New or Declined status, got {issue.status.value}"
            )
        issue.specification = spec
        issue.status = IssueStatus.REASONING
        await self.session.flush()
        return issue

    async def edit_spec(self, issue_id: str, project_id: str, spec: str) -> Issue:
        if not spec or not spec.strip():
            raise ValueError("Specification cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.REASONING:
            raise ValueError("Issue must be in Reasoning status to edit spec")
        issue.specification = spec
        await self.session.flush()
        return issue

    async def create_plan(self, issue_id: str, project_id: str, plan: str) -> Issue:
        if not plan or not plan.strip():
            raise ValueError("Plan cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.REASONING:
            raise ValueError(
                f"Can only create plan for issues in Reasoning status, got {issue.status.value}"
            )
        issue.plan = plan
        issue.status = IssueStatus.PLANNED
        await self.session.flush()
        return issue

    async def edit_plan(self, issue_id: str, project_id: str, plan: str) -> Issue:
        if not plan or not plan.strip():
            raise ValueError("Plan cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise ValueError("Issue must be in Planned status to edit plan")
        issue.plan = plan
        await self.session.flush()
        return issue

    async def accept_issue(self, issue_id: str, project_id: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise ValueError(
                f"Can only accept issues in Planned status, got {issue.status.value}"
            )
        issue.status = IssueStatus.ACCEPTED
        await self.session.flush()
        return issue

    async def decline_issue(self, issue_id: str, project_id: str, feedback: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise ValueError(
                f"Can only decline issues in Planned status, got {issue.status.value}"
            )
        issue.status = IssueStatus.DECLINED
        issue.decline_feedback = feedback
        await self.session.flush()
        return issue

    async def cancel_issue(self, issue_id: str, project_id: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        issue.status = IssueStatus.CANCELED
        await self.session.flush()
        return issue

    async def delete(self, issue_id: str, project_id: str) -> bool:
        issue = await self.get_for_project(issue_id, project_id)
        await self.session.delete(issue)
        await self.session.flush()
        return True
```

- [ ] **Step 2: Create new `backend/app/services/task_service.py`** (atomic tasks)

```python
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import VALID_TASK_TRANSITIONS, Task, TaskStatus


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bulk(self, issue_id: str, tasks: list[dict]) -> list[Task]:
        created = []
        for i, t in enumerate(tasks):
            task = Task(issue_id=issue_id, name=t["name"], order=i)
            self.session.add(task)
            created.append(task)
        await self.session.flush()
        return created

    async def replace_all(self, issue_id: str, tasks: list[dict]) -> list[Task]:
        await self.session.execute(
            delete(Task).where(Task.issue_id == issue_id)
        )
        return await self.create_bulk(issue_id, tasks)

    async def get_by_id(self, task_id: str) -> Task:
        task = await self.session.get(Task, task_id)
        if task is None:
            raise ValueError("Task not found")
        return task

    async def update(self, task_id: str, **kwargs) -> Task:
        task = await self.get_by_id(task_id)
        if "status" in kwargs and kwargs["status"] is not None:
            new_status = kwargs["status"]
            if isinstance(new_status, str):
                new_status = TaskStatus(new_status)
            if (task.status, new_status) not in VALID_TASK_TRANSITIONS:
                raise ValueError(f"Invalid task transition from {task.status.value} to {new_status.value}")
            task.status = new_status
        if "name" in kwargs and kwargs["name"] is not None:
            task.name = kwargs["name"]
        await self.session.flush()
        return task

    async def delete(self, task_id: str) -> bool:
        task = await self.get_by_id(task_id)
        await self.session.delete(task)
        await self.session.flush()
        return True

    async def list_by_issue(self, issue_id: str) -> list[Task]:
        result = await self.session.execute(
            select(Task).where(Task.issue_id == issue_id).order_by(Task.order.asc())
        )
        return list(result.scalars().all())
```

- [ ] **Step 3: Delete old `backend/app/services/task_service.py`** (replaced in steps 1-2)

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/
git commit -m "refactor: rename TaskService to IssueService, add new TaskService for atomic tasks"
```

---

### Task 6: Issue router (rename from tasks router)

**Files:**
- Rename: `backend/app/routers/tasks.py` → `backend/app/routers/issues.py`
- Create: `backend/app/routers/tasks.py` (new, for atomic tasks)
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/routers/issues.py`**

Based on old `routers/tasks.py`, rename all references:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.issue import IssueStatus
from app.schemas.issue import IssueCreate, IssueResponse, IssueStatusUpdate, IssueUpdate
from app.services.issue_service import IssueService

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


@router.post("", response_model=IssueResponse, status_code=201)
async def create_issue(project_id: str, data: IssueCreate, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    issue = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return issue


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
    try:
        issue = await service.get_for_project(issue_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return issue


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    project_id: str, issue_id: str, data: IssueUpdate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    try:
        issue = await service.update_fields(issue_id, project_id, **data.model_dump(exclude_unset=True))
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(issue)
    return issue


@router.patch("/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(
    project_id: str,
    issue_id: str,
    data: IssueStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    try:
        issue = await service.update_status(
            issue_id, project_id, data.status, decline_feedback=data.decline_feedback
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    try:
        await service.delete(issue_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
```

- [ ] **Step 2: Create new `backend/app/routers/tasks.py`** (atomic tasks)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.task import TaskBulkCreate, TaskResponse, TaskUpdate
from app.services.issue_service import IssueService
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/projects/{project_id}/issues/{issue_id}/tasks", tags=["tasks"])


async def _verify_issue(project_id: str, issue_id: str, db: AsyncSession):
    """Verify issue exists and belongs to project."""
    service = IssueService(db)
    try:
        await service.get_for_project(issue_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Issue not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("", response_model=list[TaskResponse], status_code=201)
async def create_tasks(
    project_id: str, issue_id: str, data: TaskBulkCreate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    tasks = await service.create_bulk(issue_id, [t.model_dump() for t in data.tasks])
    await db.commit()
    return tasks


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    return await service.list_by_issue(issue_id)


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
    await db.commit()
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    project_id: str, issue_id: str, task_id: str, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    try:
        await service.delete(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.commit()


@router.put("", response_model=list[TaskResponse])
async def replace_tasks(
    project_id: str, issue_id: str, data: TaskBulkCreate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    tasks = await service.replace_all(issue_id, [t.model_dump() for t in data.tasks])
    await db.commit()
    return tasks
```

- [ ] **Step 3: Update `backend/app/main.py`**

```python
from app.routers import issues, projects, settings, tasks, terminals

# ...
app.include_router(projects.router)
app.include_router(issues.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(terminals.router)
```

- [ ] **Step 4: Delete old `backend/app/routers/tasks.py`** (replaced in step 2)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/ backend/app/main.py
git commit -m "refactor: rename tasks router to issues, add new tasks router for atomic tasks"
```

---

### Task 7: Update project service and schema (`task_counts` → `issue_counts`)

**Files:**
- Modify: `backend/app/services/project_service.py:42-52`
- Modify: `backend/app/schemas/project.py:28`
- Modify: `backend/app/routers/projects.py:14-19`

- [ ] **Step 1: Update `backend/app/services/project_service.py`**

Rename `get_task_counts` → `get_issue_counts`, update import from `app.models.issue`:

```python
# Line 42-52: rename method and update import
async def get_issue_counts(self, project_id: str) -> dict[str, int]:
    from sqlalchemy import func as sqlfunc, select as sqlselect

    from app.models.issue import Issue

    result = await self.session.execute(
        sqlselect(Issue.status, sqlfunc.count())
        .where(Issue.project_id == project_id)
        .group_by(Issue.status)
    )
    return {row[0].value: row[1] for row in result.all()}
```

- [ ] **Step 2: Update `backend/app/schemas/project.py`**

Line 28: `task_counts` → `issue_counts`:
```python
issue_counts: dict[str, int] = {}
```

- [ ] **Step 3: Update `backend/app/routers/projects.py`**

Update `_enrich_project`:
```python
async def _enrich_project(service: ProjectService, project) -> dict:
    """Add issue_counts to a project response."""
    counts = await service.get_issue_counts(project.id)
    result = ProjectResponse.model_validate(project)
    result.issue_counts = counts
    return result
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/project_service.py backend/app/schemas/project.py backend/app/routers/projects.py
git commit -m "refactor: rename task_counts to issue_counts in project service/schema/router"
```

---

### Task 8: Update terminal system (`task_id` → `issue_id`)

**Files:**
- Modify: `backend/app/schemas/terminal.py`
- Modify: `backend/app/services/terminal_service.py`
- Modify: `backend/app/routers/terminals.py:56,85-98`

- [ ] **Step 1: Update `backend/app/schemas/terminal.py`**

```python
from datetime import datetime

from pydantic import BaseModel


class TerminalCreate(BaseModel):
    issue_id: str
    project_id: str


class TerminalResponse(BaseModel):
    id: str
    issue_id: str
    project_id: str
    project_path: str
    status: str
    created_at: datetime
    cols: int
    rows: int


class TerminalListResponse(BaseModel):
    id: str
    issue_id: str
    project_id: str
    project_path: str
    issue_name: str | None = None
    project_name: str | None = None
    status: str
    created_at: datetime
```

- [ ] **Step 2: Update `backend/app/services/terminal_service.py`**

Replace all `task_id` with `issue_id` throughout. Key changes:
- `create(self, issue_id, ...)` parameter
- Deduplication check: `term["issue_id"] == issue_id`
- Entry dict: `"issue_id": issue_id`
- `_to_response`: `"issue_id": entry["issue_id"]`
- `list_active(self, project_id, issue_id)` parameter

- [ ] **Step 3: Update `backend/app/routers/terminals.py`**

- Line 56: `task_id=data.task_id` → `issue_id=data.issue_id`
- Line 85: query param `task_id` → `issue_id`
- Line 90: import `Task` → `Issue` from `app.models.issue`
- Line 92: `service.list_active(project_id=project_id, task_id=task_id)` → `service.list_active(project_id=project_id, issue_id=issue_id)`
- Line 96: `db.get(Task, term["task_id"])` → `db.get(Issue, term["issue_id"])`
- Line 98: `term["task_name"]` → `term["issue_name"]`, reference `issue.name or issue.description[:50]`

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/terminal.py backend/app/services/terminal_service.py backend/app/routers/terminals.py
git commit -m "refactor: rename task_id to issue_id in terminal system"
```

---

### Task 9: MCP server + default_settings.json

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`

- [ ] **Step 1: Update `backend/app/mcp/default_settings.json`**

Rename all keys from `tool.*_task_*` to `tool.*_issue_*`, add new task tool descriptions:

```json
{
  "server.name": "Manager AI",
  "tool.get_issue_details.description": "Get all details of a specific issue. Returns: id, project_id, name, description, status, priority, specification (markdown), plan (markdown), recap (markdown), decline_feedback, tasks (atomic plan tasks), created_at, updated_at.",
  "tool.get_issue_status.description": "Get the current status of an issue.",
  "tool.get_project_context.description": "Get project information (name, path, description, tech_stack).",
  "tool.set_issue_name.description": "Set the name of an issue after analysis.",
  "tool.complete_issue.description": "Mark an issue as Finished and save the recap. Only works for issues in Accepted status.",
  "tool.create_issue_spec.description": "Write a specification for an issue and move it to Reasoning status. Only works for issues in New or Declined status.",
  "tool.edit_issue_spec.description": "Update the specification of an issue in Reasoning status.",
  "tool.create_issue_plan.description": "Write an implementation plan for an issue and move it to Planned status. Only works for issues in Reasoning status.",
  "tool.edit_issue_plan.description": "Update the implementation plan of an issue in Planned status.",
  "tool.accept_issue.description": "Accept an issue and move it to Accepted status. Only works for issues in Planned status.",
  "tool.decline_issue.description": "Decline an issue and move it back to Declined status with feedback. Only works for issues in Planned status.",
  "tool.cancel_issue.description": "Cancel an issue from any status.",
  "tool.create_plan_tasks.description": "Create atomic tasks for an issue's plan. Accepts a list of task names. Tasks track implementation progress.",
  "tool.replace_plan_tasks.description": "Replace all tasks for an issue. Deletes existing tasks and creates new ones from the provided list.",
  "tool.update_task_status.description": "Update the status of an atomic plan task. Valid transitions: Pending → In Progress → Completed.",
  "tool.update_task_name.description": "Update the name of an atomic plan task.",
  "tool.delete_task.description": "Delete a single atomic plan task.",
  "tool.get_plan_tasks.description": "Get all atomic plan tasks for an issue, ordered by execution order.",
  "terminal_soft_limit": "5"
}
```

- [ ] **Step 2: Rewrite `backend/app/mcp/server.py`**

Rename all tool functions, update imports, add new task tools and `decline_issue`:

```python
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

_defaults_path = Path(__file__).parent / "default_settings.json"
_desc = json.loads(_defaults_path.read_text(encoding="utf-8"))

mcp = FastMCP(_desc["server.name"], streamable_http_path="/")


@mcp.tool(description=_desc["tool.get_issue_details.description"])
async def get_issue_details(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except ValueError:
            return {"error": "Issue not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {
            "id": issue.id,
            "project_id": issue.project_id,
            "name": issue.name,
            "description": issue.description,
            "status": issue.status.value,
            "priority": issue.priority,
            "specification": issue.specification,
            "plan": issue.plan,
            "recap": issue.recap,
            "decline_feedback": issue.decline_feedback,
            "tasks": [
                {"id": t.id, "name": t.name, "status": t.status.value, "order": t.order}
                for t in issue.tasks
            ],
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        }


@mcp.tool(description=_desc["tool.get_issue_status.description"])
async def get_issue_status(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except ValueError:
            return {"error": "Issue not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {"id": issue.id, "status": issue.status.value}


@mcp.tool(description=_desc["tool.get_project_context.description"])
async def get_project_context(project_id: str) -> dict:
    async with async_session() as session:
        project_service = ProjectService(session)
        project = await project_service.get_by_id(project_id)
        if project is None:
            return {"error": "Project not found"}
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "description": project.description,
            "tech_stack": project.tech_stack,
        }


@mcp.tool(description=_desc["tool.set_issue_name.description"])
async def set_issue_name(project_id: str, issue_id: str, name: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.set_name(issue_id, project_id, name)
            await session.commit()
            return {"id": issue.id, "name": issue.name}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.complete_issue(issue_id, project_id, recap)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value, "recap": issue.recap}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.create_issue_spec.description"])
async def create_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create_spec(issue_id, project_id, spec)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value, "specification": issue.specification}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.edit_issue_spec.description"])
async def edit_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.edit_spec(issue_id, project_id, spec)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value, "specification": issue.specification}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.create_issue_plan.description"])
async def create_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create_plan(issue_id, project_id, plan)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value, "plan": issue.plan}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.edit_issue_plan.description"])
async def edit_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.edit_plan(issue_id, project_id, plan)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value, "plan": issue.plan}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.accept_issue.description"])
async def accept_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.accept_issue(issue_id, project_id)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.decline_issue.description"])
async def decline_issue(project_id: str, issue_id: str, feedback: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.decline_issue(issue_id, project_id, feedback)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value, "decline_feedback": issue.decline_feedback}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.cancel_issue.description"])
async def cancel_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.cancel_issue(issue_id, project_id)
            await session.commit()
            return {"id": issue.id, "status": issue.status.value}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


# ── Task tools (atomic plan tasks) ──────────────────────────────────────────


@mcp.tool(description=_desc["tool.create_plan_tasks.description"])
async def create_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            created = await task_service.create_bulk(issue_id, tasks)
            await session.commit()
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in created]}
        except Exception as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.replace_plan_tasks.description"])
async def replace_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            created = await task_service.replace_all(issue_id, tasks)
            await session.commit()
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in created]}
        except Exception as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.update_task_status.description"])
async def update_task_status(task_id: str, status: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, status=status)
            await session.commit()
            return {"id": task.id, "name": task.name, "status": task.status.value}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.update_task_name.description"])
async def update_task_name(task_id: str, name: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, name=name)
            await session.commit()
            return {"id": task.id, "name": task.name}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.delete_task.description"])
async def delete_task(task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            await task_service.delete(task_id)
            await session.commit()
            return {"deleted": True}
        except ValueError as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.get_plan_tasks.description"])
async def get_plan_tasks(issue_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.list_by_issue(issue_id)
        return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in tasks]}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/mcp/
git commit -m "refactor: rename MCP tools from task to issue, add atomic task tools + decline_issue"
```

---

### Task 10: Update backend tests

**Files:**
- Rename: `backend/tests/test_task_service.py` → `backend/tests/test_issue_service.py`
- Create: `backend/tests/test_task_service.py` (new, for atomic TaskService)
- Rename: `backend/tests/test_routers_tasks.py` → `backend/tests/test_routers_issues.py`
- Create: `backend/tests/test_routers_tasks.py` (new, for atomic task router)
- Modify: `backend/tests/test_mcp_tools.py`
- Modify: `backend/tests/test_terminal_service.py`
- Modify: `backend/tests/test_terminal_router.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Update `backend/tests/conftest.py`**

```python
from app.models import Issue, Project, Setting, Task  # noqa: F401
```

- [ ] **Step 2: Create `backend/tests/test_issue_service.py`**

Copy from `test_task_service.py`, rename all:
- `TaskService` → `IssueService`, `TaskStatus` → `IssueStatus`
- `task_service` → `issue_service`, `task` → `issue`
- `get_next_task` → `get_next_issue`, `accept_task` → `accept_issue`, etc.
- Remove `test_save_plan*` tests (method removed)
- Add `test_decline_issue` test
- Update import: `from app.services.issue_service import IssueService`
- Update import: `from app.models.issue import IssueStatus`
- **Critical test rewrites** (NEW→PLANNED is no longer valid, must go through REASONING first):
  - `test_update_status_valid_transition`: call `create_spec` first to reach REASONING, then test REASONING→PLANNED
  - `test_update_status_declined_saves_feedback`: call `create_spec` + `create_plan` first, then PLANNED→DECLINED
  - `test_save_plan` / `test_save_plan_from_declined` / `test_save_plan_invalid_status`: delete (method removed)

- [ ] **Step 3: Create `backend/tests/test_task_service.py`** (new atomic tasks)

```python
import pytest
import pytest_asyncio

from app.models.task import TaskStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test", path="/tmp/test")


@pytest_asyncio.fixture
async def issue(db_session, project):
    service = IssueService(db_session)
    return await service.create(project_id=project.id, description="Test issue")


async def test_create_bulk(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Task 1"}, {"name": "Task 2"}])
    assert len(tasks) == 2
    assert tasks[0].name == "Task 1"
    assert tasks[0].order == 0
    assert tasks[1].order == 1
    assert tasks[0].status == TaskStatus.PENDING


async def test_list_by_issue_ordered(db_session, issue):
    service = TaskService(db_session)
    await service.create_bulk(issue.id, [{"name": "B"}, {"name": "A"}])
    tasks = await service.list_by_issue(issue.id)
    assert tasks[0].name == "B"
    assert tasks[1].name == "A"


async def test_replace_all(db_session, issue):
    service = TaskService(db_session)
    await service.create_bulk(issue.id, [{"name": "Old"}])
    tasks = await service.replace_all(issue.id, [{"name": "New 1"}, {"name": "New 2"}])
    assert len(tasks) == 2
    all_tasks = await service.list_by_issue(issue.id)
    assert len(all_tasks) == 2
    assert all_tasks[0].name == "New 1"


async def test_update_status_valid(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Do it"}])
    updated = await service.update(tasks[0].id, status=TaskStatus.IN_PROGRESS)
    assert updated.status == TaskStatus.IN_PROGRESS


async def test_update_status_invalid(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Do it"}])
    with pytest.raises(ValueError, match="Invalid task transition"):
        await service.update(tasks[0].id, status=TaskStatus.COMPLETED)


async def test_update_name(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Old name"}])
    updated = await service.update(tasks[0].id, name="New name")
    assert updated.name == "New name"


async def test_delete_task(db_session, issue):
    service = TaskService(db_session)
    tasks = await service.create_bulk(issue.id, [{"name": "Delete me"}])
    await service.delete(tasks[0].id)
    remaining = await service.list_by_issue(issue.id)
    assert len(remaining) == 0


async def test_delete_nonexistent(db_session):
    service = TaskService(db_session)
    with pytest.raises(ValueError, match="Task not found"):
        await service.delete("nonexistent-id")
```

- [ ] **Step 4: Create `backend/tests/test_routers_issues.py`**

Copy from `test_routers_tasks.py`, update all URLs from `/tasks` to `/issues`, rename variables. Update the `test_update_status_valid` test to go through REASONING→PLANNED (not NEW→PLANNED).

- [ ] **Step 5: Create `backend/tests/test_routers_tasks.py`** (new atomic task router tests)

```python
import pytest
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


@pytest_asyncio.fixture
async def project_and_issue(client):
    proj = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    pid = proj.json()["id"]
    issue = await client.post(f"/api/projects/{pid}/issues", json={"description": "Test issue", "priority": 1})
    return pid, issue.json()["id"]


@pytest.mark.asyncio
async def test_create_tasks(client, project_and_issue):
    pid, iid = project_and_issue
    resp = await client.post(
        f"/api/projects/{pid}/issues/{iid}/tasks",
        json={"tasks": [{"name": "Step 1"}, {"name": "Step 2"}]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Step 1"
    assert data[0]["status"] == "Pending"


@pytest.mark.asyncio
async def test_list_tasks(client, project_and_issue):
    pid, iid = project_and_issue
    await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "T1"}]})
    resp = await client.get(f"/api/projects/{pid}/issues/{iid}/tasks")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_update_task_status(client, project_and_issue):
    pid, iid = project_and_issue
    create_resp = await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "T1"}]})
    tid = create_resp.json()[0]["id"]
    resp = await client.patch(f"/api/projects/{pid}/issues/{iid}/tasks/{tid}", json={"status": "In Progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "In Progress"


@pytest.mark.asyncio
async def test_replace_tasks(client, project_and_issue):
    pid, iid = project_and_issue
    await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "Old"}]})
    resp = await client.put(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "New 1"}, {"name": "New 2"}]})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_delete_task(client, project_and_issue):
    pid, iid = project_and_issue
    create_resp = await client.post(f"/api/projects/{pid}/issues/{iid}/tasks", json={"tasks": [{"name": "Del"}]})
    tid = create_resp.json()[0]["id"]
    resp = await client.delete(f"/api/projects/{pid}/issues/{iid}/tasks/{tid}")
    assert resp.status_code == 204
```

- [ ] **Step 6: Update `backend/tests/test_mcp_tools.py`**

- Rename all imports: `TaskStatus` → `IssueStatus`, `TaskService` → `IssueService`
- Rename `task_service` fixture → `issue_service`
- Rename all `task` variables to `issue`
- Update function calls: `create_spec`, `create_plan`, `accept_task` → `accept_issue`, `complete_task` → `complete_issue`, `cancel_task` → `cancel_issue`
- Update mock patch: `app.mcp.server.get_task_details` → `app.mcp.server.get_issue_details`
- Add test for `decline_issue`
- Add test for `create_plan_tasks` and `update_task_status`

- [ ] **Step 7: Update `backend/tests/test_terminal_service.py`**

Replace all `task_id` with `issue_id` in test parameters and assertions.

- [ ] **Step 8: Update `backend/tests/test_terminal_router.py`**

Replace all `task_id` with `issue_id` in mock data, JSON payloads, and assertions.

- [ ] **Step 9: Run all tests**

```bash
cd backend && python -m pytest -v
```
Expected: all tests pass.

- [ ] **Step 10: Commit**

```bash
git add backend/tests/
git commit -m "refactor: update all tests for issues refactoring + add atomic task tests"
```

---

### Task 11: Frontend API client

**Files:**
- Modify: `frontend/src/api/client.js`

- [ ] **Step 1: Update `frontend/src/api/client.js`**

```javascript
const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  // Projects
  listProjects: () => request("/projects"),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (data) => request("/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id, data) => request(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (id) => request(`/projects/${id}`, { method: "DELETE" }),
  installManagerJson: (id) => request(`/projects/${id}/install-manager-json`, { method: "POST" }),

  // Issues (ex Tasks)
  listIssues: (projectId, status) => {
    const params = status ? `?status=${status}` : "";
    return request(`/projects/${projectId}/issues${params}`);
  },
  getIssue: (projectId, issueId) => request(`/projects/${projectId}/issues/${issueId}`),
  createIssue: (projectId, data) =>
    request(`/projects/${projectId}/issues`, { method: "POST", body: JSON.stringify(data) }),
  updateIssue: (projectId, issueId, data) =>
    request(`/projects/${projectId}/issues/${issueId}`, { method: "PUT", body: JSON.stringify(data) }),
  updateIssueStatus: (projectId, issueId, data) =>
    request(`/projects/${projectId}/issues/${issueId}/status`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteIssue: (projectId, issueId) =>
    request(`/projects/${projectId}/issues/${issueId}`, { method: "DELETE" }),

  // Tasks (atomic plan tasks)
  listTasks: (projectId, issueId) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks`),
  createTasks: (projectId, issueId, tasks) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks`, { method: "POST", body: JSON.stringify({ tasks }) }),
  replaceTasks: (projectId, issueId, tasks) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks`, { method: "PUT", body: JSON.stringify({ tasks }) }),
  updateTask: (projectId, issueId, taskId, data) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (projectId, issueId, taskId) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, { method: "DELETE" }),

  // Settings
  getSettings: () => request("/settings"),
  updateSetting: (key, value) =>
    request(`/settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  resetSetting: (key) =>
    request(`/settings/${encodeURIComponent(key)}`, { method: "DELETE" }),
  resetAllSettings: () => request("/settings", { method: "DELETE" }),

  // Terminals
  listTerminals: (projectId, issueId) => {
    const params = new URLSearchParams();
    if (projectId) params.set("project_id", projectId);
    if (issueId) params.set("issue_id", issueId);
    const qs = params.toString();
    return request(`/terminals${qs ? `?${qs}` : ""}`);
  },
  createTerminal: (issueId, projectId) =>
    request("/terminals", { method: "POST", body: JSON.stringify({ issue_id: issueId, project_id: projectId }) }),
  killTerminal: (terminalId) =>
    request(`/terminals/${terminalId}`, { method: "DELETE" }),
  terminalCount: () => request("/terminals/count"),
  terminalConfig: () => request("/terminals/config"),
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.js
git commit -m "refactor: update frontend API client for issues refactoring"
```

---

### Task 12: Frontend pages and components

**Files:**
- Rename: `frontend/src/pages/NewTaskPage.jsx` → `frontend/src/pages/NewIssuePage.jsx`
- Rename: `frontend/src/pages/TaskDetailPage.jsx` → `frontend/src/pages/IssueDetailPage.jsx`
- Rename: `frontend/src/components/TaskList.jsx` → `frontend/src/components/IssueList.jsx`
- Modify: `frontend/src/components/StatusBadge.jsx`
- Modify: `frontend/src/components/ProjectCard.jsx`
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`
- Modify: `frontend/src/pages/TerminalsPage.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create `frontend/src/pages/NewIssuePage.jsx`**

Copy from `NewTaskPage.jsx`, rename:
- `NewTaskPage` → `NewIssuePage`
- `api.createTask` → `api.createIssue`
- Labels: "New Task" → "New Issue"

- [ ] **Step 2: Create `frontend/src/pages/IssueDetailPage.jsx`**

Copy from `TaskDetailPage.jsx`, rename:
- `TaskDetailPage` → `IssueDetailPage`
- `taskId` (from URL params) → `issueId`
- `api.getTask` → `api.getIssue`
- `api.listTerminals(null, taskId)` → `api.listTerminals(null, issueId)`
- `api.createTerminal(taskId, projectId)` → `api.createTerminal(issueId, projectId)`
- `task` state → `issue`
- Labels: "Untitled Task" → "Untitled Issue", "Back to tasks" → "Back to issues"
- Add a tasks section below the plan that displays `issue.tasks` if non-empty:

```jsx
{issue.tasks && issue.tasks.length > 0 && (
  <div className="mb-4">
    <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Tasks</h2>
    <div className="space-y-1">
      {issue.tasks.map((task) => (
        <div key={task.id} className="flex items-center gap-2 text-sm">
          <StatusBadge status={task.status} />
          <span className="text-gray-700">{task.name}</span>
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 3: Create `frontend/src/components/IssueList.jsx`**

Copy from `TaskList.jsx`, rename:
- `TaskList` → `IssueList`
- `tasks` prop → `issues`
- `activeTerminalTaskIds` → `activeTerminalIssueIds`
- Link to: `/projects/${projectId}/issues/${issue.id}`
- `task.name` → `issue.name`, etc.

- [ ] **Step 4: Update `frontend/src/components/StatusBadge.jsx`**

Add TaskStatus colors:

```jsx
const STATUS_COLORS = {
  // Issue statuses
  New: "bg-blue-100 text-blue-800",
  Reasoning: "bg-indigo-100 text-indigo-800",
  Planned: "bg-yellow-100 text-yellow-800",
  Accepted: "bg-green-100 text-green-800",
  Declined: "bg-red-100 text-red-800",
  Finished: "bg-gray-100 text-gray-800",
  Canceled: "bg-gray-100 text-gray-500",
  // Task statuses
  Pending: "bg-slate-100 text-slate-700",
  "In Progress": "bg-amber-100 text-amber-800",
  Completed: "bg-emerald-100 text-emerald-800",
};
```

- [ ] **Step 5: Update `frontend/src/components/ProjectCard.jsx`**

- `project.task_counts` → `project.issue_counts`

- [ ] **Step 6: Update `frontend/src/pages/ProjectDetailPage.jsx`**

- Import `IssueList` instead of `TaskList`
- `api.listTasks` → `api.listIssues`
- `api.listTerminals(id)` returns terminals with `issue_id`
- `setActiveTerminalTaskIds(terms.map(...term.task_id))` → `setActiveTerminalIssueIds(terms.map(...term.issue_id))`
- Link: `/projects/${id}/tasks/new` → `/projects/${id}/issues/new`
- Label: "New Task" → "New Issue"
- `<TaskList tasks={tasks} ...>` → `<IssueList issues={issues} ...>`

- [ ] **Step 7: Update `frontend/src/pages/TerminalsPage.jsx`**

- `term.task_name` → `term.issue_name`
- `term.task_id` → `term.issue_id`
- Link: `/projects/${term.project_id}/tasks/${term.task_id}` → `/projects/${term.project_id}/issues/${term.issue_id}`
- Label: "Go to Task" → "Go to Issue"

- [ ] **Step 8: Update `frontend/src/App.jsx`**

```jsx
import NewIssuePage from "./pages/NewIssuePage";
import IssueDetailPage from "./pages/IssueDetailPage";

// Routes:
<Route path="/projects/:id/issues/new" element={<NewIssuePage />} />
<Route path="/projects/:id/issues/:issueId" element={<IssueDetailPage />} />
```

Remove old imports of `NewTaskPage` and `TaskDetailPage`.

- [ ] **Step 9: Delete old files**

Delete `frontend/src/pages/NewTaskPage.jsx`, `frontend/src/pages/TaskDetailPage.jsx`, `frontend/src/components/TaskList.jsx`.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/
git commit -m "refactor: update frontend for issues refactoring, add task list in issue detail"
```

---

### Task 13: Final verification

- [ ] **Step 1: Run backend tests**

```bash
cd backend && python -m pytest -v
```

- [ ] **Step 2: Run Alembic migration check**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 3: Start backend and verify endpoints**

```bash
cd backend && uvicorn app.main:app --reload
```

Test manually:
- `GET /api/projects` — should return `issue_counts`
- `POST /api/projects/{pid}/issues` — creates issue
- `POST /api/projects/{pid}/issues/{iid}/tasks` — creates atomic tasks

- [ ] **Step 4: Start frontend and verify UI**

```bash
cd frontend && npm run dev
```

Verify:
- Project detail shows issues list
- Issue detail shows plan tasks section
- Terminal links work correctly
- StatusBadge renders both issue and task statuses

- [ ] **Step 5: Search for orphaned "task" references**

```bash
# In backend (should only find atomic task references)
grep -rn "task" backend/app/ --include="*.py" | grep -iv "import\|#\|Task\|TaskS" | head -30

# In frontend (should only find atomic task references)
grep -rn "task" frontend/src/ --include="*.jsx" --include="*.js" | grep -iv "import\|Task\|task\." | head -30
```

- [ ] **Step 6: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address any remaining orphaned task references"
```
