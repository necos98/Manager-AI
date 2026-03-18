# Docker-to-Local Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove Docker dependency, replace PostgreSQL with SQLite + LanceDB, and provide a single `start.py` that launches the full stack locally with venv.

**Architecture:** SQLite (via aiosqlite) replaces PostgreSQL for relational data, LanceDB provides embedded vector storage for future AI features. A root-level `start.py` manages venv creation, dependency installation, Alembic migrations, and launches both backend (Uvicorn) and frontend (Vite dev server) as child processes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async + aiosqlite, Alembic, LanceDB, React 19, Vite 8

---

## File Structure

### New Files
- `start.py` — orchestrator: venv, deps, migrations, process management
- `backend/app/lancedb_store.py` — LanceDB connection and table definitions
- `backend/alembic/versions/xxxx_initial_sqlite_schema.py` — new initial migration for SQLite

### Modified Files
- `backend/requirements.txt` — remove asyncpg/pgvector, add aiosqlite/lancedb
- `backend/app/config.py` — new DATABASE_URL default for SQLite
- `backend/app/database.py` — SQLite engine config with check_same_thread
- `backend/app/models/project.py` — remove Vector column, UUID→String(36)
- `backend/app/models/task.py` — remove Vector columns, UUID→String(36)
- `backend/app/schemas/project.py` — id field UUID→str
- `backend/app/schemas/task.py` — id/project_id fields UUID→str
- `backend/app/routers/projects.py` — path params uuid.UUID→str
- `backend/app/routers/tasks.py` — path params uuid.UUID→str
- `backend/app/services/project_service.py` — type annotations uuid.UUID→str
- `backend/app/services/task_service.py` — type annotations uuid.UUID→str
- `backend/app/mcp/server.py` — remove UUID parsing (IDs are already strings)
- `backend/app/main.py` — update CORS origin to port 5173
- `backend/alembic/env.py` — remove pgvector extension creation
- `backend/alembic.ini` — no changes needed (URL comes from config)
- `frontend/vite.config.js` — no changes needed (proxy already correct)
- `.env` — remove DB_PASSWORD
- `.env.example` — remove DB_PASSWORD
- `.gitignore` — add data/, venv/

### Deleted Files
- `docker-compose.yml`
- `docker-compose.override.yml`
- `docker-compose.prod.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `backend/alembic/versions/55bc4073dd1c_initial_schema.py`
- `backend/alembic/versions/7bc067397cd0_add_tech_stack_to_projects.py`

---

### Task 1: Update dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Update requirements.txt**

Remove `asyncpg` and `pgvector`. Keep `aiosqlite` (already present). Add `lancedb`.

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy[asyncio]==2.0.40
aiosqlite==0.21.0
alembic==1.15.2
lancedb>=0.20.0
pydantic==2.11.1
pydantic-settings==2.9.1
mcp[cli]==1.9.2
python-dotenv==1.1.0
httpx==0.28.1
pytest==8.3.5
pytest-asyncio==0.25.3
```

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: update deps — remove asyncpg/pgvector, add lancedb"
```

---

### Task 2: Update config and database engine for SQLite

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/database.py`
- Modify: `.env`
- Modify: `.env.example`

- [ ] **Step 1: Update config.py**

Replace the default DATABASE_URL and remove DB_PASSWORD dependency:

```python
import os
from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve project root (two levels up from this file: config.py -> app -> backend)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    lancedb_path: str = str(_PROJECT_ROOT / "data" / "lancedb")

    model_config = {"env_file": ".env"}

settings = Settings()
```

- [ ] **Step 2: Update database.py**

Add `check_same_thread` for SQLite and ensure data directory creation:

```python
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 3: Update .env and .env.example**

`.env` — remove DB_PASSWORD, leave empty or minimal:
```
# No configuration needed for local SQLite setup
```

`.env.example` — same:
```
# DATABASE_URL=sqlite+aiosqlite:///data/manager_ai.db  (default, no config needed)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/app/database.py .env .env.example
git commit -m "feat: configure SQLite async engine and data directory"
```

---

### Task 3: Update SQLAlchemy models for SQLite compatibility

**Files:**
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/models/task.py`

- [ ] **Step 1: Update project.py**

Remove pgvector import and Vector column. Replace PostgreSQL UUID with String(36):

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tech_stack: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
```

- [ ] **Step 2: Update task.py**

Remove pgvector import and all Vector columns. Replace PostgreSQL UUID with String(36):

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, case, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    NEW = "New"
    PLANNED = "Planned"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    FINISHED = "Finished"
    CANCELED = "Canceled"


# Valid state transitions: (from_status, to_status)
VALID_TRANSITIONS = {
    (TaskStatus.NEW, TaskStatus.PLANNED),
    (TaskStatus.DECLINED, TaskStatus.PLANNED),
    (TaskStatus.PLANNED, TaskStatus.ACCEPTED),
    (TaskStatus.PLANNED, TaskStatus.DECLINED),
    (TaskStatus.ACCEPTED, TaskStatus.FINISHED),
}
# Any → Canceled is always valid (handled in code)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.NEW)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    recap: Mapped[str | None] = mapped_column(Text, nullable=True)
    decline_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/project.py backend/app/models/task.py
git commit -m "feat: update models for SQLite — remove pgvector, use String UUIDs"
```

---

### Task 4: Update schemas, routers, services, and MCP for string UUIDs

Since models now use `String(36)` instead of PostgreSQL `UUID`, the entire API layer must switch from `uuid.UUID` to `str` for ID fields. This prevents runtime errors when SQLAlchemy looks up a `String(36)` column with a `uuid.UUID` object.

**Files:**
- Modify: `backend/app/schemas/project.py`
- Modify: `backend/app/schemas/task.py`
- Modify: `backend/app/routers/projects.py`
- Modify: `backend/app/routers/tasks.py`
- Modify: `backend/app/services/project_service.py`
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/mcp/server.py`

- [ ] **Step 1: Update schemas/project.py**

Change `id` from `uuid.UUID` to `str`:

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    tech_stack: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    tech_stack: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    path: str
    description: str
    tech_stack: str
    created_at: datetime
    updated_at: datetime
    task_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Update schemas/task.py**

Change `id` and `project_id` from `uuid.UUID` to `str`:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    description: str = Field(..., min_length=1)
    priority: int = Field(default=3, ge=1, le=5)


class TaskUpdate(BaseModel):
    description: str | None = Field(None, min_length=1)
    priority: int | None = Field(None, ge=1, le=5)


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    decline_feedback: str | None = None


class TaskResponse(BaseModel):
    id: str
    project_id: str
    name: str | None
    description: str
    status: TaskStatus
    priority: int
    plan: str | None
    recap: str | None
    decline_feedback: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Update routers/projects.py**

Change path parameter types from `uuid.UUID` to `str`, remove `import uuid`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _enrich_project(service: ProjectService, project) -> dict:
    """Add task_counts to a project response."""
    counts = await service.get_task_counts(project.id)
    result = ProjectResponse.model_validate(project)
    result.task_counts = counts
    return result


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description, tech_stack=data.tech_stack
    )
    await db.commit()
    return await _enrich_project(service, project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    projects = await service.list_all()
    return [await _enrich_project(service, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return await _enrich_project(service, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update(project_id, **data.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    deleted = await service.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    await db.commit()
```

- [ ] **Step 4: Update routers/tasks.py**

Change path parameter types from `uuid.UUID` to `str`, remove `import uuid`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(project_id: str, data: TaskCreate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str,
    status: TaskStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.list_by_project(project_id, status=status)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(project_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    try:
        task = await service.get_for_project(task_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: str, task_id: str, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    service = TaskService(db)
    try:
        task = await service.update_fields(task_id, project_id, **data.model_dump(exclude_unset=True))
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    project_id: str,
    task_id: str,
    data: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    try:
        task = await service.update_status(
            task_id, project_id, data.status, decline_feedback=data.decline_feedback
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(project_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    try:
        await service.delete(task_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
```

- [ ] **Step 5: Update services/project_service.py**

Change `uuid.UUID` type annotations to `str`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str, path: str, description: str = "", tech_stack: str = "") -> Project:
        project = Project(name=name, path=path, description=description, tech_stack=tech_stack)
        self.session.add(project)
        await self.session.flush()
        return project

    async def list_all(self) -> list[Project]:
        result = await self.session.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, project_id: str) -> Project | None:
        return await self.session.get(Project, project_id)

    async def update(self, project_id: str, **kwargs) -> Project | None:
        project = await self.get_by_id(project_id)
        if project is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)
        await self.session.flush()
        return project

    async def delete(self, project_id: str) -> bool:
        project = await self.get_by_id(project_id)
        if project is None:
            return False
        await self.session.delete(project)
        await self.session.flush()
        return True

    async def get_task_counts(self, project_id: str) -> dict[str, int]:
        from sqlalchemy import func as sqlfunc, select as sqlselect

        from app.models.task import Task, TaskStatus

        result = await self.session.execute(
            sqlselect(Task.status, sqlfunc.count())
            .where(Task.project_id == project_id)
            .group_by(Task.status)
        )
        return {row[0].value: row[1] for row in result.all()}
```

- [ ] **Step 6: Update services/task_service.py**

Change `uuid.UUID` type annotations to `str`:

```python
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import VALID_TRANSITIONS, Task, TaskStatus


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: str, description: str, priority: int = 3) -> Task:
        task = Task(project_id=project_id, description=description, priority=priority)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_by_id(self, task_id: str) -> Task | None:
        return await self.session.get(Task, task_id)

    async def get_for_project(self, task_id: str, project_id: str) -> Task:
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError("Task not found")
        if task.project_id != project_id:
            raise PermissionError("Task does not belong to project")
        return task

    async def list_by_project(
        self, project_id: str, status: TaskStatus | None = None
    ) -> list[Task]:
        query = select(Task).where(Task.project_id == project_id)
        if status is not None:
            query = query.where(Task.status == status)
        query = query.order_by(Task.priority.asc(), Task.created_at.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_next_task(self, project_id: str) -> Task | None:
        query = (
            select(Task)
            .where(Task.project_id == project_id)
            .where(Task.status.in_([TaskStatus.NEW, TaskStatus.DECLINED]))
            .order_by(
                case(
                    (Task.status == TaskStatus.DECLINED, 0),
                    (Task.status == TaskStatus.NEW, 1),
                ).asc(),
                Task.priority.asc(),
                Task.created_at.asc(),
            )
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        task_id: str,
        project_id: str,
        new_status: TaskStatus,
        decline_feedback: str | None = None,
    ) -> Task:
        task = await self.get_for_project(task_id, project_id)
        if new_status == TaskStatus.CANCELED:
            task.status = TaskStatus.CANCELED
            await self.session.flush()
            return task
        if (task.status, new_status) not in VALID_TRANSITIONS:
            raise ValueError(f"Invalid state transition from {task.status.value} to {new_status.value}")
        task.status = new_status
        if new_status == TaskStatus.DECLINED and decline_feedback:
            task.decline_feedback = decline_feedback
        await self.session.flush()
        return task

    async def update_fields(self, task_id: str, project_id: str, **kwargs) -> Task:
        task = await self.get_for_project(task_id, project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(task, key, value)
        await self.session.flush()
        return task

    async def set_name(self, task_id: str, project_id: str, name: str) -> Task:
        return await self.update_fields(task_id, project_id, name=name)

    async def save_plan(self, task_id: str, project_id: str, plan: str) -> Task:
        task = await self.get_for_project(task_id, project_id)
        if task.status not in (TaskStatus.NEW, TaskStatus.DECLINED):
            raise ValueError(f"Can only save plan for tasks in New or Declined status, got {task.status.value}")
        task.plan = plan
        task.status = TaskStatus.PLANNED
        await self.session.flush()
        return task

    async def complete_task(self, task_id: str, project_id: str, recap: str) -> Task:
        task = await self.get_for_project(task_id, project_id)
        if task.status != TaskStatus.ACCEPTED:
            raise ValueError(f"Can only complete tasks in Accepted status, got {task.status.value}")
        task.recap = recap
        task.status = TaskStatus.FINISHED
        await self.session.flush()
        return task

    async def delete(self, task_id: str, project_id: str) -> bool:
        task = await self.get_for_project(task_id, project_id)
        await self.session.delete(task)
        await self.session.flush()
        return True
```

- [ ] **Step 7: Update mcp/server.py**

Remove `uuid.UUID` parsing — IDs are now plain strings passed directly:

```python
from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

mcp = FastMCP("Manager AI", streamable_http_path="/")


@mcp.tool()
async def get_next_task(project_id: str) -> dict | None:
    """Get the highest priority task that needs work (Declined before New, then by priority).
    Returns task id, description, status, and decline_feedback if present. Returns null if none available.
    """
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


@mcp.tool()
async def get_task_details(project_id: str, task_id: str) -> dict:
    """Get all details of a specific task."""
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
            "plan": task.plan,
            "recap": task.recap,
            "decline_feedback": task.decline_feedback,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


@mcp.tool()
async def get_task_status(project_id: str, task_id: str) -> dict:
    """Get the current status of a task."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_for_project(task_id, project_id)
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {"id": task.id, "status": task.status.value}


@mcp.tool()
async def get_project_context(project_id: str) -> dict:
    """Get project information (name, path, description, tech_stack)."""
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


@mcp.tool()
async def set_task_name(project_id: str, task_id: str, name: str) -> dict:
    """Set the name of a task after analysis."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.set_name(task_id, project_id, name)
            await session.commit()
            return {"id": task.id, "name": task.name}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool()
async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    """Save a markdown plan for a task and set status to Planned. Only works for tasks in New or Declined status.

    IMPORTANT: After saving a plan, you MUST stop and wait for the user to approve or decline
    the plan via the frontend. Do NOT proceed with implementation until the task status
    changes to 'Accepted'. Poll get_task_status to check, but only after the user tells you
    they have reviewed the plan.
    """
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.save_plan(task_id, project_id, plan)
            await session.commit()
            return {
                "id": task.id,
                "status": task.status.value,
                "plan": task.plan,
                "message": "Plan saved. STOP HERE — do NOT proceed with implementation. "
                "The user must review and approve this plan in the frontend before you can continue. "
                "Wait for the user to confirm approval, then check the task status with get_task_status.",
            }
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool()
async def complete_task(project_id: str, task_id: str, recap: str) -> dict:
    """Mark a task as Finished and save the recap. Only works for tasks in Accepted status."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.complete_task(task_id, project_id, recap)
            await session.commit()
            return {"id": task.id, "status": task.status.value, "recap": task.recap}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/ backend/app/routers/ backend/app/services/ backend/app/mcp/server.py
git commit -m "feat: switch API layer from uuid.UUID to str for SQLite String(36) IDs"
```

---

### Task 5: Update Alembic for SQLite

**Files:**
- Modify: `backend/alembic/env.py`
- Delete: `backend/alembic/versions/55bc4073dd1c_initial_schema.py`
- Delete: `backend/alembic/versions/7bc067397cd0_add_tech_stack_to_projects.py`
- Create: new initial migration

- [ ] **Step 1: Update alembic/env.py**

Remove the pgvector extension creation:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base, ensure_data_dir
from app.models import Project, Task  # noqa: F401 — ensure models are registered

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    ensure_data_dir()
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

Note: `render_as_batch=True` is important for SQLite — it enables batch mode for ALTER TABLE operations which SQLite doesn't natively support.

- [ ] **Step 2: Delete old migrations**

```bash
rm backend/alembic/versions/55bc4073dd1c_initial_schema.py
rm backend/alembic/versions/7bc067397cd0_add_tech_stack_to_projects.py
```

- [ ] **Step 3: Generate new initial migration**

**Prerequisite:** You need a working venv with deps installed. If start.py hasn't been created yet, manually create one:

```bash
python -m venv venv
venv/Scripts/pip install -r backend/requirements.txt   # Windows
# or: venv/bin/pip install -r backend/requirements.txt  # Linux/Mac
```

From `backend/` directory, with venv active:

```bash
cd backend
alembic revision --autogenerate -m "initial sqlite schema"
```

Verify the generated migration creates `projects` and `tasks` tables without any pgvector references.

- [ ] **Step 4: Test migration runs**

```bash
cd backend
alembic upgrade head
```

Verify `data/manager_ai.db` is created with the correct schema.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/env.py backend/alembic/versions/
git commit -m "feat: reset Alembic migrations for SQLite"
```

---

### Task 6: Update CORS and main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update CORS origin**

Change the allowed origin from port 3000 to port 5173 (Vite default):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.mcp.server import mcp
from app.routers import projects, tasks

# Get the MCP Starlette sub-app (creates session manager lazily)
mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Manager AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(tasks.router)

# Mount MCP sub-app at /mcp (sub-app routes at / internally)
app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: update CORS origin for Vite dev server on port 5173"
```

---

### Task 7: Create LanceDB store module

**Files:**
- Create: `backend/app/lancedb_store.py`

- [ ] **Step 1: Create lancedb_store.py**

This sets up the LanceDB connection and defines table schemas, ready for future AI features:

```python
"""LanceDB vector store for embedding-based search.

This module provides the LanceDB connection and table definitions.
Tables are created lazily on first use. Currently a placeholder for
future AI/embedding features.
"""

from pathlib import Path

import lancedb

from app.config import settings

_db = None


def get_lancedb():
    """Get or create the LanceDB connection."""
    global _db
    if _db is None:
        path = Path(settings.lancedb_path)
        path.mkdir(parents=True, exist_ok=True)
        _db = lancedb.connect(str(path))
    return _db


# Table schemas for future use:
# - "project_embeddings": id (str), vector (1536-dim), text (str)
# - "task_embeddings": id (str), field (str), vector (1536-dim), text (str)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/lancedb_store.py
git commit -m "feat: add LanceDB store module for future vector search"
```

---

### Task 8: Update .gitignore and delete Docker files

**Files:**
- Modify: `.gitignore`
- Delete: `docker-compose.yml`
- Delete: `docker-compose.override.yml`
- Delete: `docker-compose.prod.yml`
- Delete: `backend/Dockerfile`
- Delete: `frontend/Dockerfile`
- Delete: `frontend/nginx.conf`

- [ ] **Step 1: Update .gitignore**

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# Node
node_modules/
dist/

# Environment
.env

# Data
data/

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
```

- [ ] **Step 2: Delete Docker files**

```bash
rm docker-compose.yml docker-compose.override.yml docker-compose.prod.yml
rm backend/Dockerfile
rm frontend/Dockerfile frontend/nginx.conf
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git add -u docker-compose.yml docker-compose.override.yml docker-compose.prod.yml backend/Dockerfile frontend/Dockerfile frontend/nginx.conf
git commit -m "chore: remove Docker setup, update .gitignore for local dev"
```

---

### Task 9: Create start.py

**Files:**
- Create: `start.py`

- [ ] **Step 1: Create start.py**

```python
"""Manager AI — local development launcher.

Usage: python start.py

Starts both the FastAPI backend and the Vite frontend dev server.
Press Ctrl+C to stop both.
"""

import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_DIR = ROOT / "venv"
DATA_DIR = ROOT / "data"

IS_WINDOWS = platform.system() == "Windows"
VENV_PYTHON = VENV_DIR / ("Scripts" / "python.exe" if IS_WINDOWS else "bin" / "python")
VENV_PIP = VENV_DIR / ("Scripts" / "pip.exe" if IS_WINDOWS else "bin" / "pip")
VENV_ALEMBIC = VENV_DIR / ("Scripts" / "alembic.exe" if IS_WINDOWS else "bin" / "alembic")


def check_prerequisites():
    """Verify Python and Node.js are available."""
    if shutil.which("node") is None:
        print("ERROR: Node.js is not installed or not in PATH.")
        sys.exit(1)
    if shutil.which("npm") is None:
        print("ERROR: npm is not installed or not in PATH.")
        sys.exit(1)
    print("[ok] Node.js and npm found")


def setup_venv():
    """Create venv and install backend dependencies if needed."""
    if not VENV_PYTHON.exists():
        print("[...] Creating Python virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("[ok] Virtual environment created")

    print("[...] Installing backend dependencies...")
    subprocess.run(
        [str(VENV_PIP), "install", "-r", str(BACKEND_DIR / "requirements.txt")],
        check=True,
    )
    print("[ok] Backend dependencies installed")


def setup_frontend():
    """Install frontend dependencies if needed."""
    if not (FRONTEND_DIR / "node_modules").exists():
        print("[...] Installing frontend dependencies...")
        subprocess.run(
            ["npm", "install", "--legacy-peer-deps"],
            cwd=str(FRONTEND_DIR),
            check=True,
            shell=IS_WINDOWS,
        )
        print("[ok] Frontend dependencies installed")


def run_migrations():
    """Run Alembic migrations."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("[...] Running database migrations...")
    subprocess.run(
        [str(VENV_ALEMBIC), "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        check=True,
    )
    print("[ok] Database migrations complete")


def main():
    check_prerequisites()
    setup_venv()
    setup_frontend()
    run_migrations()

    print()
    print("=" * 50)
    print("  Manager AI")
    print("  Frontend: http://localhost:5173")
    print("  Backend:  http://localhost:8000")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    print()

    # Start backend
    backend_proc = subprocess.Popen(
        [
            str(VENV_PYTHON), "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--host", "127.0.0.1",
            "--port", "8000",
        ],
        cwd=str(BACKEND_DIR),
    )

    # Start frontend
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    processes = [backend_proc, frontend_proc]

    def shutdown(sig=None, frame=None):
        print("\n[...] Shutting down...")
        for proc in processes:
            if proc.poll() is None:
                if IS_WINDOWS:
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[ok] All processes stopped")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for any process to exit
    try:
        while True:
            for proc in processes:
                ret = proc.poll()
                if ret is not None:
                    proc_name = "Backend" if proc == backend_proc else "Frontend"
                    print(f"\n[!] {proc_name} exited with code {ret}")
                    shutdown()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test start.py**

```bash
python start.py
```

Verify:
- Venv is created in `venv/`
- Backend deps install
- Frontend deps install (if node_modules missing)
- Migrations run, `data/manager_ai.db` created
- Backend starts on http://localhost:8000
- Frontend starts on http://localhost:5173
- Ctrl+C stops both

- [ ] **Step 3: Commit**

```bash
git add start.py
git commit -m "feat: add start.py — local launcher for backend + frontend"
```

---

### Task 10: End-to-end verification

- [ ] **Step 1: Clean start**

Delete `data/` and `venv/` if they exist, then run:

```bash
python start.py
```

- [ ] **Step 2: Test frontend**

Open http://localhost:5173 — verify the app loads, create a project, create a task.

- [ ] **Step 3: Test API**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/projects
```

- [ ] **Step 4: Test MCP**

Verify MCP endpoint responds:

```bash
curl -X POST http://localhost:8000/mcp/ -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"initialize","params":{"capabilities":{}},"id":1}'
```

- [ ] **Step 5: Final commit**

If any fixes were needed during verification, commit them:

```bash
git add -A
git commit -m "fix: address issues found during e2e verification"
```
