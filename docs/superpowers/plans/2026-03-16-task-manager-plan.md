# Task Manager for Claude Code — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a task management system with FastAPI backend (REST + MCP), PostgreSQL + pgvector, and React frontend for managing Claude Code development workflows.

**Architecture:** Single Python backend serves both REST API (for React frontend) and MCP server (for Claude Code) via shared service layer. PostgreSQL with pgvector for storage. React + Vite + Tailwind frontend served by nginx. All orchestrated with Docker Compose.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, `mcp` SDK, PostgreSQL 16 + pgvector, Vite, React 18, Tailwind CSS 4, Docker Compose

**Spec:** `docs/superpowers/specs/2026-03-16-task-manager-design.md`

---

## Chunk 1: Project Scaffolding, Docker, and Database

### Task 1: Initialize git repo and project structure

**Files:**
- Create: `.gitignore`
- Create: `.env`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `frontend/.gitkeep`

- [ ] **Step 1: Initialize git repo**

```bash
cd /home/jacob/manager_ai
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/

# Node
node_modules/
dist/

# Environment
.env

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
```

- [ ] **Step 3: Create .env and .env.example**

`.env`:
```
DB_PASSWORD=manager_secret_2026
```

`.env.example`:
```
DB_PASSWORD=changeme
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: manager_ai
      POSTGRES_USER: manager
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U manager -d manager_ai"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://manager:${DB_PASSWORD}@db:5432/manager_ai
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 5: Create backend/requirements.txt**

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy[asyncio]==2.0.40
asyncpg==0.30.0
alembic==1.15.2
pgvector==0.3.6
pydantic==2.11.1
pydantic-settings==2.9.1
mcp[cli]==1.9.2
python-dotenv==1.1.0
httpx==0.28.1
pytest==8.3.5
pytest-asyncio==0.25.3
aiosqlite==0.21.0
```

- [ ] **Step 6: Create backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 7: Create backend/app/__init__.py and backend/app/config.py**

`backend/app/__init__.py`: empty file

`backend/app/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://manager:changeme@localhost:5432/manager_ai"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 8: Create placeholder frontend/.gitkeep**

Empty file — frontend will be scaffolded in Chunk 4.

- [ ] **Step 9: Commit**

```bash
git add .gitignore .env.example docker-compose.yml backend/ frontend/.gitkeep
git commit -m "chore: scaffold project structure with Docker and backend config"
```

---

### Task 2: Database connection and SQLAlchemy setup

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: Create backend/app/models/__init__.py**

```python
from app.database import Base
from app.models.project import Project
from app.models.task import Task

__all__ = ["Base", "Project", "Task"]
```

Note: This will fail until we create the model files in Task 3. That's expected.

- [ ] **Step 3: Create minimal backend/app/main.py**

```python
from fastapi import FastAPI

app = FastAPI(title="Manager AI", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Test Docker Compose boots**

```bash
cd /home/jacob/manager_ai
docker compose up -d db
docker compose up -d backend
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/app/models/__init__.py backend/app/main.py
git commit -m "feat: add database setup and health endpoint"
```

---

### Task 3: SQLAlchemy models (Project + Task)

**Files:**
- Create: `backend/app/models/project.py`
- Create: `backend/app/models/task.py`

- [ ] **Step 1: Create backend/app/models/project.py**

```python
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_embedding = Column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
```

- [ ] **Step 2: Create backend/app/models/task.py**

```python
import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.NEW)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    recap: Mapped[str | None] = mapped_column(Text, nullable=True)
    decline_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_embedding = Column(Vector(1536), nullable=True)
    plan_embedding = Column(Vector(1536), nullable=True)
    recap_embedding = Column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add Project and Task SQLAlchemy models with state machine"
```

---

### Task 4: Alembic setup and initial migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (auto-generated)

- [ ] **Step 1: Initialize Alembic inside backend container**

```bash
docker compose exec backend alembic init alembic
```

- [ ] **Step 2: Edit backend/alembic.ini**

Set `sqlalchemy.url` to empty (we'll use env.py to set it from config):

```ini
# In alembic.ini, replace the sqlalchemy.url line:
sqlalchemy.url =
```

- [ ] **Step 3: Edit backend/alembic/env.py**

Replace the content with async-compatible version:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base
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
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Generate initial migration**

```bash
docker compose exec backend alembic revision --autogenerate -m "create projects and tasks tables"
```

- [ ] **Step 5: Run migration**

```bash
docker compose exec backend alembic upgrade head
```

- [ ] **Step 6: Verify tables exist**

```bash
docker compose exec db psql -U manager -d manager_ai -c "\dt"
```

Expected: `projects` and `tasks` tables listed.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic migrations for projects and tasks tables"
```

---

## Chunk 2: Backend Services and Pydantic Schemas

### Task 5: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/schemas/task.py`

- [ ] **Step 1: Create backend/app/schemas/project.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    path: str
    description: str
    created_at: datetime
    updated_at: datetime
    task_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create backend/app/schemas/task.py**

```python
import uuid
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
    id: uuid.UUID
    project_id: uuid.UUID
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

- [ ] **Step 3: Create backend/app/schemas/__init__.py**

```python
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate

__all__ = [
    "ProjectCreate",
    "ProjectResponse",
    "ProjectUpdate",
    "TaskCreate",
    "TaskResponse",
    "TaskStatusUpdate",
    "TaskUpdate",
]
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic schemas for Project and Task"
```

---

### Task 6: Project service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/project_service.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_project_service.py`

- [ ] **Step 1: Create backend/pyproject.toml for pytest config**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create test fixtures in backend/tests/conftest.py**

```python
import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import Project, Task  # noqa: F401


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

`backend/tests/__init__.py`: empty file

- [ ] **Step 3: Write failing tests for project service**

`backend/tests/test_project_service.py`:

```python
import pytest

from app.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_create_project(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test", description="A test project")
    assert project.name == "Test"
    assert project.path == "/tmp/test"
    assert project.id is not None


@pytest.mark.asyncio
async def test_list_projects(db_session):
    service = ProjectService(db_session)
    await service.create(name="P1", path="/p1", description="")
    await service.create(name="P2", path="/p2", description="")
    projects = await service.list_all()
    assert len(projects) == 2


@pytest.mark.asyncio
async def test_get_project(db_session):
    service = ProjectService(db_session)
    created = await service.create(name="Test", path="/tmp", description="desc")
    fetched = await service.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Test"


@pytest.mark.asyncio
async def test_get_project_not_found(db_session):
    import uuid

    service = ProjectService(db_session)
    result = await service.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_project(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Old", path="/old", description="")
    updated = await service.update(project.id, name="New")
    assert updated.name == "New"
    assert updated.path == "/old"


@pytest.mark.asyncio
async def test_delete_project(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Del", path="/del", description="")
    deleted = await service.delete(project.id)
    assert deleted is True
    assert await service.get_by_id(project.id) is None
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_project_service.py -v
```

Expected: ImportError — `app.services.project_service` does not exist.

- [ ] **Step 5: Implement project service**

`backend/app/services/__init__.py`: empty file

`backend/app/services/project_service.py`:

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str, path: str, description: str = "") -> Project:
        project = Project(name=name, path=path, description=description)
        self.session.add(project)
        await self.session.flush()
        return project

    async def list_all(self) -> list[Project]:
        result = await self.session.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        return await self.session.get(Project, project_id)

    async def update(self, project_id: uuid.UUID, **kwargs) -> Project | None:
        project = await self.get_by_id(project_id)
        if project is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)
        await self.session.flush()
        return project

    async def delete(self, project_id: uuid.UUID) -> bool:
        project = await self.get_by_id(project_id)
        if project is None:
            return False
        await self.session.delete(project)
        await self.session.flush()
        return True

    async def get_task_counts(self, project_id: uuid.UUID) -> dict[str, int]:
        from sqlalchemy import func as sqlfunc, select as sqlselect

        from app.models.task import Task, TaskStatus

        result = await self.session.execute(
            sqlselect(Task.status, sqlfunc.count())
            .where(Task.project_id == project_id)
            .group_by(Task.status)
        )
        return {row[0].value: row[1] for row in result.all()}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_project_service.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: add ProjectService with CRUD operations and tests"
```

---

### Task 7: Task service

**Files:**
- Create: `backend/app/services/task_service.py`
- Create: `backend/tests/test_task_service.py`

- [ ] **Step 1: Write failing tests for task service**

`backend/tests/test_task_service.py`:

```python
import uuid

import pytest
import pytest_asyncio

from app.models.task import TaskStatus
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test Project", path="/tmp/test", description="Test")


@pytest.mark.asyncio
async def test_create_task(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Do something", priority=1)
    assert task.description == "Do something"
    assert task.priority == 1
    assert task.status == TaskStatus.NEW
    assert task.project_id == project.id


@pytest.mark.asyncio
async def test_list_tasks_by_project(db_session, project):
    service = TaskService(db_session)
    await service.create(project_id=project.id, description="Task 1", priority=1)
    await service.create(project_id=project.id, description="Task 2", priority=2)
    tasks = await service.list_by_project(project.id)
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_list_tasks_filter_status(db_session, project):
    service = TaskService(db_session)
    await service.create(project_id=project.id, description="New task", priority=1)
    tasks = await service.list_by_project(project.id, status=TaskStatus.NEW)
    assert len(tasks) == 1
    tasks = await service.list_by_project(project.id, status=TaskStatus.PLANNED)
    assert len(tasks) == 0


@pytest.mark.asyncio
async def test_get_next_task_priority_order(db_session, project):
    service = TaskService(db_session)
    await service.create(project_id=project.id, description="Low priority", priority=5)
    await service.create(project_id=project.id, description="High priority", priority=1)
    task = await service.get_next_task(project.id)
    assert task is not None
    assert task.description == "High priority"


@pytest.mark.asyncio
async def test_get_next_task_declined_before_new(db_session, project):
    service = TaskService(db_session)
    new_task = await service.create(project_id=project.id, description="New task", priority=1)
    declined_task = await service.create(project_id=project.id, description="Declined task", priority=5)
    # Manually set status to simulate decline flow
    declined_task.status = TaskStatus.DECLINED
    declined_task.decline_feedback = "Try again"
    await db_session.flush()

    task = await service.get_next_task(project.id)
    assert task.id == declined_task.id


@pytest.mark.asyncio
async def test_get_next_task_none_available(db_session, project):
    service = TaskService(db_session)
    task = await service.get_next_task(project.id)
    assert task is None


@pytest.mark.asyncio
async def test_update_status_valid_transition(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Plan me", priority=1)
    updated = await service.update_status(task.id, project.id, TaskStatus.PLANNED)
    assert updated.status == TaskStatus.PLANNED


@pytest.mark.asyncio
async def test_update_status_invalid_transition(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Skip ahead", priority=1)
    with pytest.raises(ValueError, match="Invalid state transition"):
        await service.update_status(task.id, project.id, TaskStatus.FINISHED)


@pytest.mark.asyncio
async def test_update_status_canceled_from_any(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Cancel me", priority=1)
    updated = await service.update_status(task.id, project.id, TaskStatus.CANCELED)
    assert updated.status == TaskStatus.CANCELED


@pytest.mark.asyncio
async def test_update_status_declined_saves_feedback(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Decline me", priority=1)
    await service.update_status(task.id, project.id, TaskStatus.PLANNED)
    updated = await service.update_status(task.id, project.id, TaskStatus.DECLINED, decline_feedback="Not good enough")
    assert updated.status == TaskStatus.DECLINED
    assert updated.decline_feedback == "Not good enough"


@pytest.mark.asyncio
async def test_set_task_name(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Name me", priority=1)
    updated = await service.set_name(task.id, project.id, "My Task Name")
    assert updated.name == "My Task Name"


@pytest.mark.asyncio
async def test_save_plan(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Plan me", priority=1)
    updated = await service.save_plan(task.id, project.id, "# The Plan\n\nDo things.")
    assert updated.plan == "# The Plan\n\nDo things."
    assert updated.status == TaskStatus.PLANNED


@pytest.mark.asyncio
async def test_save_plan_from_declined(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Replan me", priority=1)
    task.status = TaskStatus.DECLINED
    await db_session.flush()
    updated = await service.save_plan(task.id, project.id, "# New Plan")
    assert updated.status == TaskStatus.PLANNED


@pytest.mark.asyncio
async def test_save_plan_invalid_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Already planned", priority=1)
    task.status = TaskStatus.ACCEPTED
    await db_session.flush()
    with pytest.raises(ValueError, match="Can only save plan"):
        await service.save_plan(task.id, project.id, "# Plan")


@pytest.mark.asyncio
async def test_complete_task(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Finish me", priority=1)
    task.status = TaskStatus.ACCEPTED
    await db_session.flush()
    updated = await service.complete_task(task.id, project.id, "All done. Implemented X and Y.")
    assert updated.status == TaskStatus.FINISHED
    assert updated.recap == "All done. Implemented X and Y."


@pytest.mark.asyncio
async def test_complete_task_invalid_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not ready", priority=1)
    with pytest.raises(ValueError, match="Can only complete"):
        await service.complete_task(task.id, project.id, "Done")


@pytest.mark.asyncio
async def test_task_project_mismatch(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    other_project_id = uuid.uuid4()
    with pytest.raises(PermissionError, match="does not belong"):
        await service.set_name(task.id, other_project_id, "Name")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_task_service.py -v
```

Expected: ImportError — `app.services.task_service` does not exist.

- [ ] **Step 3: Implement task service**

`backend/app/services/task_service.py`:

```python
import uuid

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import VALID_TRANSITIONS, Task, TaskStatus


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: uuid.UUID, description: str, priority: int = 3) -> Task:
        task = Task(project_id=project_id, description=description, priority=priority)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return await self.session.get(Task, task_id)

    async def _get_task_for_project(self, task_id: uuid.UUID, project_id: uuid.UUID) -> Task:
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError("Task not found")
        if task.project_id != project_id:
            raise PermissionError("Task does not belong to project")
        return task

    async def list_by_project(
        self, project_id: uuid.UUID, status: TaskStatus | None = None
    ) -> list[Task]:
        query = select(Task).where(Task.project_id == project_id)
        if status is not None:
            query = query.where(Task.status == status)
        query = query.order_by(Task.priority.asc(), Task.created_at.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_next_task(self, project_id: uuid.UUID) -> Task | None:
        """Get the highest priority task that needs work.
        Declined tasks come before New tasks, then sorted by priority (lowest number = highest priority).
        """
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
        task_id: uuid.UUID,
        project_id: uuid.UUID,
        new_status: TaskStatus,
        decline_feedback: str | None = None,
    ) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
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

    async def update_fields(self, task_id: uuid.UUID, project_id: uuid.UUID, **kwargs) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(task, key, value)
        await self.session.flush()
        return task

    async def set_name(self, task_id: uuid.UUID, project_id: uuid.UUID, name: str) -> Task:
        return await self.update_fields(task_id, project_id, name=name)

    async def save_plan(self, task_id: uuid.UUID, project_id: uuid.UUID, plan: str) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
        if task.status not in (TaskStatus.NEW, TaskStatus.DECLINED):
            raise ValueError(f"Can only save plan for tasks in New or Declined status, got {task.status.value}")
        task.plan = plan
        task.status = TaskStatus.PLANNED
        await self.session.flush()
        return task

    async def complete_task(self, task_id: uuid.UUID, project_id: uuid.UUID, recap: str) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
        if task.status != TaskStatus.ACCEPTED:
            raise ValueError(f"Can only complete tasks in Accepted status, got {task.status.value}")
        task.recap = recap
        task.status = TaskStatus.FINISHED
        await self.session.flush()
        return task

    async def delete(self, task_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        task = await self._get_task_for_project(task_id, project_id)
        await self.session.delete(task)
        await self.session.flush()
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_task_service.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Run all tests together**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/ -v
```

Expected: All tests PASS (project + task service tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/task_service.py backend/tests/test_task_service.py
git commit -m "feat: add TaskService with state machine, priority ordering, and tests"
```

---

## Chunk 3: REST API Routers

### Task 8: Project router

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/projects.py`
- Create: `backend/tests/test_routers_projects.py`

- [ ] **Step 1: Write failing tests for project router**

`backend/tests/test_routers_projects.py`:

```python
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


@pytest.mark.asyncio
async def test_create_project(client):
    response = await client.post("/api/projects", json={"name": "Test", "path": "/tmp/test", "description": "Desc"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client):
    await client.post("/api/projects", json={"name": "P1", "path": "/p1"})
    await client.post("/api/projects", json={"name": "P2", "path": "/p2"})
    response = await client.get("/api/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_get_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test"


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    import uuid

    response = await client.get(f"/api/projects/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Old", "path": "/old"})
    project_id = create_resp.json()["id"]
    response = await client.put(f"/api/projects/{project_id}", json={"name": "New"})
    assert response.status_code == 200
    assert response.json()["name"] == "New"


@pytest.mark.asyncio
async def test_delete_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Del", "path": "/del"})
    project_id = create_resp.json()["id"]
    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_routers_projects.py -v
```

Expected: ImportError or 404s — router not registered.

- [ ] **Step 3: Implement project router**

`backend/app/routers/__init__.py`: empty file

`backend/app/routers/projects.py`:

```python
import uuid

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
    project = await service.create(name=data.name, path=data.path, description=data.description)
    await db.commit()
    return await _enrich_project(service, project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    projects = await service.list_all()
    return [await _enrich_project(service, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return await _enrich_project(service, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: uuid.UUID, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update(project_id, **data.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    await db.commit()
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    deleted = await service.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    await db.commit()
```

- [ ] **Step 4: Register router in main.py**

Update `backend/app/main.py`:

```python
from fastapi import FastAPI

from app.routers import projects

app = FastAPI(title="Manager AI", version="0.1.0")

app.include_router(projects.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_routers_projects.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/ backend/app/main.py backend/tests/test_routers_projects.py
git commit -m "feat: add Project REST API router with CRUD endpoints"
```

---

### Task 9: Task router

**Files:**
- Create: `backend/app/routers/tasks.py`
- Create: `backend/tests/test_routers_tasks.py`

- [ ] **Step 1: Write failing tests for task router**

`backend/tests/test_routers_tasks.py`:

```python
import uuid

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
async def project(client):
    resp = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    return resp.json()


async def test_create_task(client, project):
    resp = await client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"description": "Do something", "priority": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Do something"
    assert data["status"] == "New"


@pytest.mark.asyncio
async def test_create_task_invalid_priority(client, project):
    resp = await client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"description": "Bad priority", "priority": 0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_tasks(client, project):
    await client.post(f"/api/projects/{project['id']}/tasks", json={"description": "T1", "priority": 1})
    await client.post(f"/api/projects/{project['id']}/tasks", json={"description": "T2", "priority": 2})
    resp = await client.get(f"/api/projects/{project['id']}/tasks")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_list_tasks_filter_status(client, project):
    await client.post(f"/api/projects/{project['id']}/tasks", json={"description": "T1", "priority": 1})
    resp = await client.get(f"/api/projects/{project['id']}/tasks?status=New")
    assert len(resp.json()) == 1
    resp = await client.get(f"/api/projects/{project['id']}/tasks?status=Planned")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_get_task(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/tasks", json={"description": "Get me", "priority": 1}
    )
    task_id = create_resp.json()["id"]
    resp = await client.get(f"/api/projects/{project['id']}/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["description"] == "Get me"


@pytest.mark.asyncio
async def test_update_task(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/tasks", json={"description": "Update me", "priority": 3}
    )
    task_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/projects/{project['id']}/tasks/{task_id}", json={"priority": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == 1


@pytest.mark.asyncio
async def test_update_status_valid(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/tasks", json={"description": "Plan me", "priority": 1}
    )
    task_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/projects/{project['id']}/tasks/{task_id}/status",
        json={"status": "Planned"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Planned"


@pytest.mark.asyncio
async def test_update_status_invalid(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/tasks", json={"description": "Skip", "priority": 1}
    )
    task_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/projects/{project['id']}/tasks/{task_id}/status",
        json={"status": "Finished"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_decline_with_feedback(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/tasks", json={"description": "Decline me", "priority": 1}
    )
    task_id = create_resp.json()["id"]
    # First move to Planned
    await client.patch(
        f"/api/projects/{project['id']}/tasks/{task_id}/status",
        json={"status": "Planned"},
    )
    # Then decline
    resp = await client.patch(
        f"/api/projects/{project['id']}/tasks/{task_id}/status",
        json={"status": "Declined", "decline_feedback": "Not good enough"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Declined"
    assert resp.json()["decline_feedback"] == "Not good enough"


@pytest.mark.asyncio
async def test_delete_task(client, project):
    create_resp = await client.post(
        f"/api/projects/{project['id']}/tasks", json={"description": "Delete me", "priority": 1}
    )
    task_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/projects/{project['id']}/tasks/{task_id}")
    assert resp.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_routers_tasks.py -v
```

Expected: 404 — task routes not registered.

- [ ] **Step 3: Implement task router**

`backend/app/routers/tasks.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(project_id: uuid.UUID, data: TaskCreate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: uuid.UUID,
    status: TaskStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.list_by_project(project_id, status=status)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(project_id: uuid.UUID, task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    try:
        task = await service._get_task_for_project(task_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    service = TaskService(db)
    try:
        task = await service.update_fields(task_id, project_id, **data.model_dump(exclude_unset=True))
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    return task


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
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
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(project_id: uuid.UUID, task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    try:
        await service.delete(task_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
```

- [ ] **Step 4: Register task router in main.py**

Update `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import projects, tasks

app = FastAPI(title="Manager AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_routers_tasks.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/tasks.py backend/app/main.py backend/tests/test_routers_tasks.py
git commit -m "feat: add Task REST API router with status transitions and validation"
```

---

## Chunk 4: MCP Server

### Task 10: MCP server with all tools

**Files:**
- Create: `backend/app/mcp/__init__.py`
- Create: `backend/app/mcp/server.py`
- Create: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1: Write failing tests for MCP tools**

`backend/tests/test_mcp_tools.py`:

```python
import uuid

import pytest

from app.models.task import TaskStatus
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="MCP Test", path="/tmp/mcp", description="MCP test project")


@pytest.fixture
def task_service(db_session):
    return TaskService(db_session)


@pytest.fixture
def project_service(db_session):
    return ProjectService(db_session)


@pytest.mark.asyncio
async def test_mcp_get_next_task_flow(task_service, project):
    """Simulates the full MCP flow: get_next_task → set_name → save_plan"""
    # Create tasks
    await task_service.create(project_id=project.id, description="Low priority task", priority=3)
    await task_service.create(project_id=project.id, description="High priority task", priority=1)

    # get_next_task should return high priority
    task = await task_service.get_next_task(project.id)
    assert task.description == "High priority task"

    # set_name
    await task_service.set_name(task.id, project.id, "Important Feature")
    assert task.name == "Important Feature"

    # save_plan → status becomes Planned
    await task_service.save_plan(task.id, project.id, "# Plan\n\nStep 1: Do it")
    assert task.status == TaskStatus.PLANNED
    assert task.plan == "# Plan\n\nStep 1: Do it"


@pytest.mark.asyncio
async def test_mcp_decline_and_replan_flow(task_service, project):
    """Simulates: plan → decline with feedback → get_next_task returns declined → replan"""
    task = await task_service.create(project_id=project.id, description="Feature X", priority=1)

    # Plan it
    await task_service.save_plan(task.id, project.id, "# Plan v1")
    assert task.status == TaskStatus.PLANNED

    # User declines
    await task_service.update_status(task.id, project.id, TaskStatus.DECLINED, decline_feedback="Need more detail")
    assert task.status == TaskStatus.DECLINED
    assert task.decline_feedback == "Need more detail"

    # get_next_task returns the declined task
    next_task = await task_service.get_next_task(project.id)
    assert next_task.id == task.id
    assert next_task.decline_feedback == "Need more detail"

    # Replan
    await task_service.save_plan(task.id, project.id, "# Plan v2\n\nMore detailed plan")
    assert task.status == TaskStatus.PLANNED


@pytest.mark.asyncio
async def test_mcp_complete_flow(task_service, project):
    """Simulates: plan → accept → complete with recap"""
    task = await task_service.create(project_id=project.id, description="Feature Y", priority=1)
    await task_service.save_plan(task.id, project.id, "# Plan")
    await task_service.update_status(task.id, project.id, TaskStatus.ACCEPTED)
    assert task.status == TaskStatus.ACCEPTED

    result = await task_service.complete_task(task.id, project.id, "Implemented feature Y successfully")
    assert result.status == TaskStatus.FINISHED
    assert result.recap == "Implemented feature Y successfully"


@pytest.mark.asyncio
async def test_mcp_project_context(project_service, project):
    """get_project_context returns project info"""
    fetched = await project_service.get_by_id(project.id)
    assert fetched.name == "MCP Test"
    assert fetched.path == "/tmp/mcp"
    assert fetched.description == "MCP test project"


@pytest.mark.asyncio
async def test_mcp_task_project_validation(task_service, project):
    """All MCP tools must validate project_id ownership"""
    task = await task_service.create(project_id=project.id, description="Test", priority=1)
    fake_project_id = uuid.uuid4()

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.set_name(task.id, fake_project_id, "Name")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.save_plan(task.id, fake_project_id, "Plan")

    with pytest.raises(PermissionError, match="does not belong"):
        await task_service.complete_task(task.id, fake_project_id, "Recap")
```

- [ ] **Step 2: Run tests to verify they pass**

These tests use the existing service layer — they should pass already since the services are implemented.

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/test_mcp_tools.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Implement MCP server**

`backend/app/mcp/__init__.py`: empty file

`backend/app/mcp/server.py`:

```python
import uuid

from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

mcp = FastMCP("Manager AI")


@mcp.tool()
async def get_next_task(project_id: str) -> dict | None:
    """Get the highest priority task that needs work (Declined before New, then by priority).
    Returns task id, description, status, and decline_feedback if present. Returns null if none available.
    """
    async with async_session() as session:
        task_service = TaskService(session)
        task = await task_service.get_next_task(uuid.UUID(project_id))
        if task is None:
            return None
        result = {
            "id": str(task.id),
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
            task = await task_service._get_task_for_project(uuid.UUID(task_id), uuid.UUID(project_id))
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {
            "id": str(task.id),
            "project_id": str(task.project_id),
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
            task = await task_service._get_task_for_project(uuid.UUID(task_id), uuid.UUID(project_id))
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {"id": str(task.id), "status": task.status.value}


@mcp.tool()
async def get_project_context(project_id: str) -> dict:
    """Get project information (name, path, description)."""
    async with async_session() as session:
        project_service = ProjectService(session)
        project = await project_service.get_by_id(uuid.UUID(project_id))
        if project is None:
            return {"error": "Project not found"}
        return {
            "id": str(project.id),
            "name": project.name,
            "path": project.path,
            "description": project.description,
        }


@mcp.tool()
async def set_task_name(project_id: str, task_id: str, name: str) -> dict:
    """Set the name of a task after analysis."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.set_name(uuid.UUID(task_id), uuid.UUID(project_id), name)
            await session.commit()
            return {"id": str(task.id), "name": task.name}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool()
async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    """Save a markdown plan for a task and set status to Planned. Only works for tasks in New or Declined status."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.save_plan(uuid.UUID(task_id), uuid.UUID(project_id), plan)
            await session.commit()
            return {"id": str(task.id), "status": task.status.value, "plan": task.plan}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool()
async def complete_task(project_id: str, task_id: str, recap: str) -> dict:
    """Mark a task as Finished and save the recap. Only works for tasks in Accepted status."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.complete_task(uuid.UUID(task_id), uuid.UUID(project_id), recap)
            await session.commit()
            return {"id": str(task.id), "status": task.status.value, "recap": task.recap}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}
```

- [ ] **Step 4: Mount MCP server in FastAPI app**

Update `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.mcp.server import mcp
from app.routers import projects, tasks

app = FastAPI(title="Manager AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(tasks.router)

# Mount MCP server on /mcp using Streamable HTTP
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Verify MCP server starts**

```bash
docker compose up -d --build backend
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}` — app starts without import errors.

- [ ] **Step 6: Run full test suite**

```bash
cd /home/jacob/manager_ai/backend
python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/ backend/app/main.py backend/tests/test_mcp_tools.py
git commit -m "feat: add MCP server with all tools mounted on /mcp"
```

---

## Chunk 5: Frontend

### Task 11: Scaffold React app with Vite and Tailwind

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/index.css`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

- [ ] **Step 1: Scaffold Vite React project**

```bash
cd /home/jacob/manager_ai
rm frontend/.gitkeep
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite @tailwindcss/typography
npm install react-router-dom react-markdown
```

- [ ] **Step 2: Configure Tailwind**

Update `frontend/vite.config.js`:

```javascript
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";
@plugin "@tailwindcss/typography";
```

- [ ] **Step 3: Create frontend/Dockerfile**

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 4: Create frontend/nginx.conf**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React frontend with Vite, Tailwind, and nginx"
```

---

### Task 12: API client and routing

**Files:**
- Create: `frontend/src/api/client.js`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/main.jsx`

- [ ] **Step 1: Create frontend/src/api/client.js**

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

  // Tasks
  listTasks: (projectId, status) => {
    const params = status ? `?status=${status}` : "";
    return request(`/projects/${projectId}/tasks${params}`);
  },
  getTask: (projectId, taskId) => request(`/projects/${projectId}/tasks/${taskId}`),
  createTask: (projectId, data) =>
    request(`/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(data) }),
  updateTask: (projectId, taskId, data) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "PUT", body: JSON.stringify(data) }),
  updateTaskStatus: (projectId, taskId, data) =>
    request(`/projects/${projectId}/tasks/${taskId}/status`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (projectId, taskId) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),
};
```

- [ ] **Step 2: Update frontend/src/App.jsx with routing**

```jsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import NewProjectPage from "./pages/NewProjectPage";
import NewTaskPage from "./pages/NewTaskPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import TaskDetailPage from "./pages/TaskDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-5xl mx-auto px-4 py-4">
            <a href="/" className="text-xl font-bold text-gray-900">
              Manager AI
            </a>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/projects/new" element={<NewProjectPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/projects/:id/tasks/new" element={<NewTaskPage />} />
            <Route path="/projects/:id/tasks/:taskId" element={<TaskDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
```

- [ ] **Step 3: Update frontend/src/main.jsx**

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add API client and React Router setup"
```

---

### Task 13: Shared components

**Files:**
- Create: `frontend/src/components/StatusBadge.jsx`
- Create: `frontend/src/components/MarkdownViewer.jsx`

- [ ] **Step 1: Create StatusBadge component**

`frontend/src/components/StatusBadge.jsx`:

```jsx
const STATUS_COLORS = {
  New: "bg-blue-100 text-blue-800",
  Planned: "bg-yellow-100 text-yellow-800",
  Accepted: "bg-green-100 text-green-800",
  Declined: "bg-red-100 text-red-800",
  Finished: "bg-gray-100 text-gray-800",
  Canceled: "bg-gray-100 text-gray-500",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[status] || "bg-gray-100"}`}>
      {status}
    </span>
  );
}
```

- [ ] **Step 2: Create MarkdownViewer component**

`frontend/src/components/MarkdownViewer.jsx`:

```jsx
import ReactMarkdown from "react-markdown";

export default function MarkdownViewer({ content }) {
  if (!content) return <p className="text-gray-400 italic">No content</p>;
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add StatusBadge and MarkdownViewer components"
```

---

### Task 14: Projects pages

**Files:**
- Create: `frontend/src/pages/ProjectsPage.jsx`
- Create: `frontend/src/pages/NewProjectPage.jsx`
- Create: `frontend/src/components/ProjectCard.jsx`

- [ ] **Step 1: Create ProjectCard component**

`frontend/src/components/ProjectCard.jsx`:

```jsx
import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function ProjectCard({ project }) {
  const counts = project.task_counts || {};
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <Link
      to={`/projects/${project.id}`}
      className="block bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow"
    >
      <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
      <p className="text-sm text-gray-500 mt-1 font-mono">{project.path}</p>
      {project.description && (
        <p className="text-sm text-gray-600 mt-2 line-clamp-2">{project.description}</p>
      )}
      {total > 0 && (
        <div className="flex gap-2 mt-3 flex-wrap">
          {Object.entries(counts).map(([status, count]) => (
            <span key={status} className="text-xs">
              <StatusBadge status={status} /> {count}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}
```

- [ ] **Step 2: Create ProjectsPage**

`frontend/src/pages/ProjectsPage.jsx`:

```jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import ProjectCard from "../components/ProjectCard";

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listProjects().then(setProjects).finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Link
          to="/projects/new"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Project
        </Link>
      </div>
      {projects.length === 0 ? (
        <p className="text-gray-500">No projects yet.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create NewProjectPage**

`frontend/src/pages/NewProjectPage.jsx`:

```jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function NewProjectPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", path: "", description: "" });
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const project = await api.createProject(form);
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold mb-6">New Project</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Path</label>
          <input
            type="text"
            required
            value={form.path}
            onChange={(e) => setForm({ ...form, path: e.target.value })}
            className="w-full border rounded px-3 py-2 font-mono"
            placeholder="/home/user/my-project"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border rounded px-3 py-2"
            rows={4}
            placeholder="Describe the project context..."
          />
        </div>
        <div className="flex gap-3">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Create
          </button>
          <button type="button" onClick={() => navigate("/")} className="px-4 py-2 rounded border hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Verify frontend compiles**

```bash
cd /home/jacob/manager_ai/frontend
npm run build
```

Expected: Build succeeds (some pages are placeholder imports, will fail — create stubs first).

Create stub pages before build:

`frontend/src/pages/ProjectDetailPage.jsx`:
```jsx
export default function ProjectDetailPage() { return <p>TODO</p>; }
```

`frontend/src/pages/NewTaskPage.jsx`:
```jsx
export default function NewTaskPage() { return <p>TODO</p>; }
```

`frontend/src/pages/TaskDetailPage.jsx`:
```jsx
export default function TaskDetailPage() { return <p>TODO</p>; }
```

Then run build.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add Projects pages and ProjectCard component"
```

---

### Task 15: Project detail page with task list

**Files:**
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`
- Create: `frontend/src/components/TaskList.jsx`

- [ ] **Step 1: Create TaskList component**

`frontend/src/components/TaskList.jsx`:

```jsx
import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function TaskList({ tasks, projectId }) {
  if (tasks.length === 0) return <p className="text-gray-500">No tasks yet.</p>;

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <Link
          key={task.id}
          to={`/projects/${projectId}/tasks/${task.id}`}
          className="flex items-center justify-between bg-white rounded border p-3 hover:shadow-sm transition-shadow"
        >
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate">{task.name || task.description}</p>
            {task.name && <p className="text-sm text-gray-500 truncate">{task.description}</p>}
          </div>
          <div className="flex items-center gap-3 ml-4">
            <span className="text-sm text-gray-400">P{task.priority}</span>
            <StatusBadge status={task.status} />
          </div>
        </Link>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Implement ProjectDetailPage**

`frontend/src/pages/ProjectDetailPage.jsx`:

```jsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import TaskList from "../components/TaskList";

const STATUSES = ["All", "New", "Planned", "Accepted", "Declined", "Finished", "Canceled"];

export default function ProjectDetailPage() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getProject(id),
      api.listTasks(id, filter === "All" ? null : filter),
    ]).then(([p, t]) => {
      setProject(p);
      setTasks(t);
    }).finally(() => setLoading(false));
  }, [id, filter]);

  if (loading) return <p>Loading...</p>;
  if (!project) return <p>Project not found.</p>;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{project.name}</h1>
        <p className="text-sm text-gray-500 font-mono">{project.path}</p>
        {project.description && <p className="text-gray-600 mt-2">{project.description}</p>}
        <p className="text-xs text-gray-400 mt-1 font-mono">ID: {project.id}</p>
      </div>

      <div className="flex justify-between items-center mb-4">
        <div className="flex gap-2">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1 rounded text-sm ${
                filter === s ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <Link
          to={`/projects/${id}/tasks/new`}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Task
        </Link>
      </div>

      <TaskList tasks={tasks} projectId={id} />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add ProjectDetailPage with TaskList and status filters"
```

---

### Task 16: New task page and task detail page

**Files:**
- Modify: `frontend/src/pages/NewTaskPage.jsx`
- Modify: `frontend/src/pages/TaskDetailPage.jsx`
- Create: `frontend/src/components/TaskDetail.jsx`

- [ ] **Step 1: Implement NewTaskPage**

`frontend/src/pages/NewTaskPage.jsx`:

```jsx
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";

export default function NewTaskPage() {
  const { id: projectId } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({ description: "", priority: 3 });
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.createTask(projectId, form);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold mb-6">New Task</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            required
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border rounded px-3 py-2"
            rows={4}
            placeholder="Describe what needs to be done..."
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority (1 = highest, 5 = lowest)</label>
          <select
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
            className="w-full border rounded px-3 py-2"
          >
            {[1, 2, 3, 4, 5].map((p) => (
              <option key={p} value={p}>
                {p} {p === 1 ? "(Highest)" : p === 5 ? "(Lowest)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-3">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Create
          </button>
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}`)}
            className="px-4 py-2 rounded border hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Implement TaskDetailPage**

`frontend/src/pages/TaskDetailPage.jsx`:

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
  const [showDeclineForm, setShowDeclineForm] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState(null);

  const loadTask = () => {
    api.getTask(projectId, taskId).then(setTask).finally(() => setLoading(false));
  };

  useEffect(loadTask, [projectId, taskId]);

  const handleStatusChange = async (status, declineFeedback) => {
    try {
      const data = { status };
      if (declineFeedback) data.decline_feedback = declineFeedback;
      const updated = await api.updateTaskStatus(projectId, taskId, data);
      setTask(updated);
      setShowDeclineForm(false);
      setFeedback("");
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

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

        {error && <p className="text-red-600 mb-4">{error}</p>}

        <div className="flex gap-3 pt-4 border-t">
          {task.status === "Planned" && (
            <>
              <button
                onClick={() => handleStatusChange("Accepted")}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Accept
              </button>
              <button
                onClick={() => setShowDeclineForm(true)}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Decline
              </button>
            </>
          )}
          <button
            onClick={() => handleStatusChange("Canceled")}
            className="px-4 py-2 rounded border text-gray-600 hover:bg-gray-50"
          >
            Cancel Task
          </button>
        </div>

        {showDeclineForm && (
          <div className="mt-4 p-4 bg-red-50 rounded">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Why are you declining this task?
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="w-full border rounded px-3 py-2 mb-2"
              rows={3}
              placeholder="Explain what needs to change..."
            />
            <div className="flex gap-2">
              <button
                onClick={() => handleStatusChange("Declined", feedback)}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Submit Decline
              </button>
              <button
                onClick={() => { setShowDeclineForm(false); setFeedback(""); }}
                className="px-4 py-2 rounded border hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd /home/jacob/manager_ai/frontend
npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add NewTaskPage and TaskDetailPage with accept/decline flow"
```

---

### Task 17: Full stack integration test

- [ ] **Step 1: Build and start all services**

```bash
cd /home/jacob/manager_ai
docker compose up -d --build
```

- [ ] **Step 2: Verify health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Test REST API manually**

```bash
# Create project
curl -s -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Project","path":"/tmp/test","description":"Integration test"}' | python -m json.tool

# Create task (use project id from above)
curl -s -X POST http://localhost:8000/api/projects/{PROJECT_ID}/tasks \
  -H "Content-Type: application/json" \
  -d '{"description":"Implement feature X","priority":1}' | python -m json.tool
```

- [ ] **Step 4: Verify frontend loads**

Open `http://localhost:3000` in browser. Verify:
- Projects page loads
- Can create a project
- Can navigate to project detail
- Can create a task
- Can view task detail

- [ ] **Step 5: Verify MCP endpoint responds**

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Expected: MCP initialize response with server capabilities.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: finalize full stack integration"
```
