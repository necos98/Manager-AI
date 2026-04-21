# Project Archive + Issue List Refresh + Alphabetical Sort Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix issue-list cache invalidation after creating an issue; add archive/unarchive for projects with a dedicated `/projects/archived` page; sort all project lists alphabetically.

**Architecture:** Backend adds a nullable `archived_at` column to `projects`, a `?archived` query filter, and `archive`/`unarchive` POST endpoints; `ProjectService.list_all` also switches to ORDER BY lower(name) ASC. Frontend aligns the issue-query key so prefix invalidation matches, wires up archive hooks/api, adds an "Archive project" button to the settings dialog, and ships a new `/projects/archived` route plus a dropdown link.

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy async / Alembic (SQLite + aiosqlite); React 19 / TanStack Router / TanStack Query / Vite / TypeScript; pytest (backend); manual browser verification + `npm run lint` + `tsc --noEmit` (frontend — no unit-test framework in this repo).

**Reference spec:** `docs/superpowers/specs/2026-04-17-project-archive-and-issue-fixes-design.md`

---

## File Structure

**Backend — create:**
- `backend/alembic/versions/a1b2c3d4e5f6_add_project_archived_at.py` — add `archived_at` column

**Backend — modify:**
- `backend/app/models/project.py` — add `archived_at` field
- `backend/app/services/project_service.py` — filter + alphabetical sort + archive methods
- `backend/app/routers/projects.py` — `?archived` query param, archive/unarchive endpoints
- `backend/tests/test_routers_projects.py` — new tests for sort, filter, archive/unarchive, 404s
- `backend/tests/test_routers_dashboard.py` — assert archived projects excluded

**Frontend — create:**
- `frontend/src/routes/projects/archived.tsx` — archived projects list page

**Frontend — modify:**
- `frontend/src/features/issues/hooks.ts` — fix query key shape
- `frontend/src/shared/types/index.ts` — add `archived_at` to `Project`
- `frontend/src/features/projects/api.ts` — `fetchProjects(archived?)`, archive/unarchive fns
- `frontend/src/features/projects/hooks.ts` — archive hooks
- `frontend/src/features/projects/components/project-settings-dialog.tsx` — archive button + redirect
- `frontend/src/features/projects/components/project-switcher.tsx` — "View archived" link

---

## Task 1: Backend — add `archived_at` column to Project model

**Files:**
- Modify: `backend/app/models/project.py`

- [ ] **Step 1: Add the column to the model**

Edit `backend/app/models/project.py`. Add after the `updated_at` column:

```python
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

Final file:

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
    shell: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/project.py
git commit -m "feat(projects): add archived_at column to Project model"
```

---

## Task 2: Backend — Alembic migration for `archived_at`

**Files:**
- Create: `backend/alembic/versions/a1b2c3d4e5f6_add_project_archived_at.py`

- [ ] **Step 1: Find the current head revision**

Run: `cd backend && python -m alembic heads`
Expected output ends with the current head like `8768ea9ac530 (head)`.

Record that ID — you will use it as `down_revision` in Step 2.

- [ ] **Step 2: Create the migration file**

Create `backend/alembic/versions/a1b2c3d4e5f6_add_project_archived_at.py` with the content below. Replace `<HEAD_FROM_STEP_1>` with the head revision captured above.

```python
"""add archived_at to projects

Revision ID: a1b2c3d4e5f6
Revises: <HEAD_FROM_STEP_1>
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "<HEAD_FROM_STEP_1>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("archived_at")
```

The `batch_alter_table` wrapper is required because the backing database is SQLite (see existing `de00ebdfc1c2_*.py` for precedent).

- [ ] **Step 3: Apply the migration**

Run: `cd backend && python -m alembic upgrade head`
Expected: `INFO [alembic.runtime.migration] Running upgrade <HEAD_FROM_STEP_1> -> a1b2c3d4e5f6, add archived_at to projects`

- [ ] **Step 4: Verify head**

Run: `cd backend && python -m alembic heads`
Expected: `a1b2c3d4e5f6 (head)`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/a1b2c3d4e5f6_add_project_archived_at.py
git commit -m "feat(projects): alembic migration for archived_at"
```

---

## Task 3: Backend — ProjectService filter, sort, archive/unarchive

**Files:**
- Modify: `backend/app/services/project_service.py`

- [ ] **Step 1: Write the failing service tests**

Create a new file `backend/tests/test_project_service_archive.py`:

```python
import pytest

from app.models.project import Project
from app.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_list_all_excludes_archived_by_default(db_session):
    svc = ProjectService(db_session)
    active = await svc.create(name="Active", path="/a")
    archived = await svc.create(name="Archived", path="/b")
    await svc.archive(archived.id)
    await db_session.flush()

    projects = await svc.list_all()

    ids = [p.id for p in projects]
    assert active.id in ids
    assert archived.id not in ids


@pytest.mark.asyncio
async def test_list_all_archived_true_returns_only_archived(db_session):
    svc = ProjectService(db_session)
    await svc.create(name="Active", path="/a")
    archived = await svc.create(name="Archived", path="/b")
    await svc.archive(archived.id)
    await db_session.flush()

    projects = await svc.list_all(archived=True)

    assert [p.id for p in projects] == [archived.id]


@pytest.mark.asyncio
async def test_list_all_orders_alphabetically_case_insensitive(db_session):
    svc = ProjectService(db_session)
    await svc.create(name="banana", path="/b")
    await svc.create(name="Apple", path="/a")
    await svc.create(name="cherry", path="/c")

    projects = await svc.list_all()

    assert [p.name for p in projects] == ["Apple", "banana", "cherry"]


@pytest.mark.asyncio
async def test_archive_sets_timestamp(db_session):
    svc = ProjectService(db_session)
    project = await svc.create(name="P", path="/p")
    await db_session.flush()

    await svc.archive(project.id)
    await db_session.flush()

    refreshed = await svc.get_by_id(project.id)
    assert refreshed.archived_at is not None


@pytest.mark.asyncio
async def test_unarchive_clears_timestamp(db_session):
    svc = ProjectService(db_session)
    project = await svc.create(name="P", path="/p")
    await svc.archive(project.id)
    await db_session.flush()

    await svc.unarchive(project.id)
    await db_session.flush()

    refreshed = await svc.get_by_id(project.id)
    assert refreshed.archived_at is None


@pytest.mark.asyncio
async def test_archive_is_idempotent(db_session):
    svc = ProjectService(db_session)
    project = await svc.create(name="P", path="/p")
    await svc.archive(project.id)
    await db_session.flush()

    first = (await svc.get_by_id(project.id)).archived_at

    await svc.archive(project.id)
    await db_session.flush()

    second = (await svc.get_by_id(project.id)).archived_at
    assert first == second
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_project_service_archive.py -v`
Expected: failures on `svc.archive` / `svc.unarchive` (AttributeError) and on alphabetical order (wrong ordering).

- [ ] **Step 3: Implement the service changes**

Replace the entire `backend/app/services/project_service.py` with:

```python
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.project import Project


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, name: str, path: str, description: str = "", tech_stack: str = "", shell: str | None = None
    ) -> Project:
        project = Project(name=name, path=path, description=description, tech_stack=tech_stack, shell=shell)
        self.session.add(project)
        await self.session.flush()
        return project

    async def list_all(self, archived: bool | None = False) -> list[Project]:
        stmt = select(Project)
        if archived is False:
            stmt = stmt.where(Project.archived_at.is_(None))
        elif archived is True:
            stmt = stmt.where(Project.archived_at.is_not(None))
        stmt = stmt.order_by(func.lower(Project.name).asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, project_id: str) -> Project:
        project = await self.session.get(Project, project_id)
        if project is None:
            raise NotFoundError("Project not found")
        return project

    async def update(self, project_id: str, **kwargs) -> Project:
        project = await self.get_by_id(project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)
        await self.session.flush()
        return project

    async def archive(self, project_id: str) -> Project:
        project = await self.get_by_id(project_id)
        if project.archived_at is None:
            project.archived_at = func.now()
            await self.session.flush()
        return project

    async def unarchive(self, project_id: str) -> Project:
        project = await self.get_by_id(project_id)
        if project.archived_at is not None:
            project.archived_at = None
            await self.session.flush()
        return project

    async def delete(self, project_id: str) -> None:
        project = await self.get_by_id(project_id)
        await self.session.delete(project)
        await self.session.flush()

    async def get_dashboard_data(self) -> list[dict]:
        from app.models.issue import Issue, IssueStatus
        projects = await self.list_all()
        result = []
        for project in projects:
            q = (
                select(Issue)
                .where(Issue.project_id == project.id)
                .where(Issue.status.notin_([IssueStatus.FINISHED, IssueStatus.CANCELED]))
                .order_by(Issue.priority.asc(), Issue.created_at.asc())
            )
            r = await self.session.execute(q)
            active = list(r.scalars().all())
            result.append({
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "active_issues": active,
            })
        return result

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

Notes:
- `archive` idempotency: only writes `archived_at` if currently `None`, so calling twice preserves the original timestamp.
- `list_all(archived=None)` is reserved but unused by callers today.
- `get_dashboard_data()` keeps calling `list_all()` with the default, so archived projects are excluded from the dashboard automatically.

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/test_project_service_archive.py -v`
Expected: all 6 tests pass.

- [ ] **Step 5: Run the full backend suite to catch regressions**

Run: `cd backend && python -m pytest -q`
Expected: suite passes. The existing `test_list_projects` continues to pass because filtering defaults to active-only and the two test projects in that test are active.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/project_service.py backend/tests/test_project_service_archive.py
git commit -m "feat(projects): archive/unarchive service + alphabetical list"
```

---

## Task 4: Backend — router `?archived` filter and archive/unarchive endpoints

**Files:**
- Modify: `backend/app/routers/projects.py`
- Modify: `backend/app/schemas/project.py`

- [ ] **Step 1: Write the failing router tests**

Append to `backend/tests/test_routers_projects.py`:

```python
@pytest.mark.asyncio
async def test_list_projects_excludes_archived_by_default(client):
    active = await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/projects")
    ids = [p["id"] for p in response.json()]

    assert active.json()["id"] in ids
    assert archived.json()["id"] not in ids


@pytest.mark.asyncio
async def test_list_projects_archived_true_returns_archived_only(client):
    await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/projects?archived=true")
    ids = [p["id"] for p in response.json()]

    assert ids == [archived.json()["id"]]


@pytest.mark.asyncio
async def test_list_projects_alphabetical(client):
    await client.post("/api/projects", json={"name": "banana", "path": "/b"})
    await client.post("/api/projects", json={"name": "Apple", "path": "/a"})
    await client.post("/api/projects", json={"name": "cherry", "path": "/c"})

    response = await client.get("/api/projects")
    names = [p["name"] for p in response.json()]

    assert names == ["Apple", "banana", "cherry"]


@pytest.mark.asyncio
async def test_archive_project_sets_archived_at_and_returns_response(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]

    response = await client.post(f"/api/projects/{project_id}/archive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is not None


@pytest.mark.asyncio
async def test_archive_project_not_found(client):
    response = await client.post(f"/api/projects/{uuid.uuid4()}/archive")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unarchive_project_clears_archived_at(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]
    await client.post(f"/api/projects/{project_id}/archive")

    response = await client.post(f"/api/projects/{project_id}/unarchive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_archive_is_idempotent(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]

    first = await client.post(f"/api/projects/{project_id}/archive")
    second = await client.post(f"/api/projects/{project_id}/archive")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["archived_at"] == second.json()["archived_at"]
```

The endpoints return `200` with the updated project body (not `204`) so the frontend can update cached data from the response. This is a slight refinement of the spec wording.

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_routers_projects.py -v -k "archived or archive or alphabetical"`
Expected: each new test fails (404s on unknown archive endpoints, wrong ordering).

- [ ] **Step 3: Update `ProjectResponse` schema**

Edit `backend/app/schemas/project.py`. Add `archived_at` to `ProjectResponse`:

```python
class ProjectResponse(BaseModel):
    id: str
    name: str
    path: str
    description: str
    tech_stack: str
    shell: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    issue_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Update the projects router**

Replace the body of `backend/app/routers/projects.py` up through `delete_project` with:

```python
import json
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project import DashboardProject, ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService
from app.services.terminal_service import terminal_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _enrich_project(service: ProjectService, project) -> dict:
    """Add issue_counts to a project response."""
    counts = await service.get_issue_counts(project.id)
    result = ProjectResponse.model_validate(project)
    result.issue_counts = counts
    return result


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description,
        tech_stack=data.tech_stack, shell=data.shell
    )
    await db.commit()
    return await _enrich_project(service, project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(archived: bool = False, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    projects = await service.list_all(archived=archived)
    return [await _enrich_project(service, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    return await _enrich_project(service, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update(project_id, **data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.archive(project_id)
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.unarchive(project_id)
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    await service.get_by_id(project_id)
    for term in terminal_service.list_active(project_id=project_id):
        try:
            terminal_service.kill(term["id"])
        except KeyError:
            pass
    await service.delete(project_id)
    await db.commit()
```

Leave the `install_manager_json`, `install_claude_resources`, and `dashboard_router` sections below untouched.

- [ ] **Step 5: Run router tests to verify pass**

Run: `cd backend && python -m pytest tests/test_routers_projects.py -v`
Expected: every test passes, including the new archive/unarchive/alphabetical cases.

- [ ] **Step 6: Run the dashboard tests**

Run: `cd backend && python -m pytest tests/test_routers_dashboard.py -v`
Expected: passes. If an existing test breaks because of new ordering, append a new test rather than silencing the break:

```python
@pytest.mark.asyncio
async def test_dashboard_excludes_archived_projects(client):
    active = await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/dashboard")
    ids = [p["id"] for p in response.json()]

    assert active.json()["id"] in ids
    assert archived.json()["id"] not in ids
```

Append it to `backend/tests/test_routers_dashboard.py` and re-run.

- [ ] **Step 7: Full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: suite passes.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/projects.py backend/app/schemas/project.py backend/tests/test_routers_projects.py backend/tests/test_routers_dashboard.py
git commit -m "feat(projects): archive/unarchive endpoints + ?archived filter"
```

---

## Task 5: Frontend — fix `useIssues` query-key mismatch

**Files:**
- Modify: `frontend/src/features/issues/hooks.ts`

- [ ] **Step 1: Edit `useIssues` to use the `issueKeys.all` prefix**

Replace the `useIssues` function in `frontend/src/features/issues/hooks.ts` (currently around lines 16-21) with:

```ts
export function useIssues(projectId: string, status?: IssueStatus, search?: string) {
  return useQuery({
    queryKey: [...issueKeys.all(projectId), "list", { status, search }],
    queryFn: () => api.fetchIssues(projectId, status, search),
  });
}
```

- [ ] **Step 2: Edit `useUpdateIssueStatus` to use the same prefix for consistency**

Replace the `onSuccess` in `useUpdateIssueStatus` (around lines 58-60):

```ts
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
```

- [ ] **Step 3: Verify no other caller depends on the old key shape**

Run: `cd frontend && npx tsc --noEmit`
Expected: no type errors.

Run: grep for the old raw string key across the frontend:

```bash
grep -rn '"issues", projectId' frontend/src || echo "none"
```

Expected: the only remaining matches are inside `useIssues`/`useUpdateIssueStatus` (if any). No consumer directly references the old tuple.

- [ ] **Step 4: Lint**

Run: `cd frontend && npm run lint`
Expected: no new warnings introduced.

- [ ] **Step 5: Manual browser smoke — issue list refresh**

1. Start the stack: `python start.py` (from repo root).
2. Open a project, go to Issues.
3. Click "New Issue", fill description, submit.
4. Confirm: dialog closes **and** the new issue appears in the Kanban board **without** a page refresh.

Report back with pass/fail and paste any console errors. Proceed only on pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/issues/hooks.ts
git commit -m "fix(issues): align useIssues query key so createIssue invalidation hits"
```

---

## Task 6: Frontend — extend Project type + api client

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/features/projects/api.ts`

- [ ] **Step 1: Add `archived_at` to the `Project` type**

Edit `frontend/src/shared/types/index.ts`. Update the `Project` interface (around lines 81-91):

```ts
export interface Project {
  id: string;
  name: string;
  path: string;
  description: string;
  tech_stack: string;
  shell?: string | null;
  created_at: string;
  updated_at: string;
  archived_at?: string | null;
  issue_counts?: Record<string, number>;
}
```

- [ ] **Step 2: Update `fetchProjects` and add archive/unarchive api calls**

Edit `frontend/src/features/projects/api.ts`. Replace `fetchProjects` and add two new functions:

```ts
export function fetchProjects(archived: boolean = false): Promise<Project[]> {
  const query = archived ? "?archived=true" : "";
  return apiGet<Project[]>(`/projects${query}`);
}

export function archiveProject(projectId: string): Promise<Project> {
  return apiPost<Project>(`/projects/${projectId}/archive`);
}

export function unarchiveProject(projectId: string): Promise<Project> {
  return apiPost<Project>(`/projects/${projectId}/unarchive`);
}
```

Leave the rest of the file unchanged.

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/types/index.ts frontend/src/features/projects/api.ts
git commit -m "feat(projects): archived_at type + archive/unarchive api client"
```

---

## Task 7: Frontend — project hooks for archive/unarchive

**Files:**
- Modify: `frontend/src/features/projects/hooks.ts`

- [ ] **Step 1: Extend `useProjects` signature (archived flag) and add archived-list key**

Edit `frontend/src/features/projects/hooks.ts`. Replace the `projectKeys` and `useProjects` sections at the top:

```ts
export const projectKeys = {
  all: ["projects"] as const,
  list: (archived: boolean) => ["projects", "list", { archived }] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects(archived: boolean = false) {
  return useQuery({
    queryKey: projectKeys.list(archived),
    queryFn: () => api.fetchProjects(archived),
  });
}
```

The new list key nests under `["projects", ...]` so existing `invalidateQueries({ queryKey: projectKeys.all })` calls continue to match both active and archived lists by prefix.

- [ ] **Step 2: Add the archive/unarchive mutations**

Append to the same file (at the bottom, before the existing `useInstallManagerJson` or at the end — order does not matter):

```ts
export function useArchiveProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.archiveProject(projectId),
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
    },
    onError: onMutationError,
  });
}

export function useUnarchiveProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.unarchiveProject(projectId),
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
    },
    onError: onMutationError,
  });
}
```

- [ ] **Step 3: Typecheck + verify no callers broke**

Run: `cd frontend && npx tsc --noEmit`
Expected: no type errors. The `useProjects()` default value (`archived=false`) keeps all existing zero-argument callers working unchanged.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/projects/hooks.ts
git commit -m "feat(projects): useArchiveProject/useUnarchiveProject hooks"
```

---

## Task 8: Frontend — "Archive project" button in settings dialog + redirect

**Files:**
- Modify: `frontend/src/features/projects/components/project-settings-dialog.tsx`

- [ ] **Step 1: Add the archive action and imports**

Open `frontend/src/features/projects/components/project-settings-dialog.tsx`.

Add imports at the top (merge into existing blocks):

```ts
import { Archive } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { useArchiveProject, useUpdateProject, useCodebaseIndexStatus, useTriggerCodebaseIndex } from "@/features/projects/hooks";
```

(Replace the existing `useUpdateProject, useCodebaseIndexStatus, useTriggerCodebaseIndex` import with the line above.)

Inside the component, right after `const updateProject = useUpdateProject(project.id);`, add:

```ts
  const archiveProject = useArchiveProject();
  const navigate = useNavigate();

  const handleArchive = () => {
    const confirmed = window.confirm(
      `Archive "${project.name}"? It will be hidden from the sidebar and dashboard. You can restore it from the archived page.`,
    );
    if (!confirmed) return;
    archiveProject.mutate(project.id, {
      onSuccess: () => {
        toast.success("Project archived");
        onOpenChange(false);
        navigate({ to: "/" });
      },
    });
  };
```

- [ ] **Step 2: Render the archive section**

Insert the new section **between** the existing "Codebase Index" `<div className="pt-2 border-t">` block and the error paragraph. The new block:

```tsx
          <div className="pt-2 border-t">
            <label className="text-sm font-medium flex items-center gap-1.5 mb-2 text-destructive">
              <Archive className="size-3.5" />
              Archive
            </label>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">
                Hides the project from sidebar and dashboard. You can restore it later from the archived page.
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive shrink-0"
                disabled={archiveProject.isPending}
                onClick={handleArchive}
              >
                <Archive className="size-3.5 mr-1.5" />
                {archiveProject.isPending ? "Archiving..." : "Archive project"}
              </Button>
            </div>
          </div>
```

- [ ] **Step 3: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: no errors.

- [ ] **Step 4: Manual browser smoke — archive flow from settings dialog**

1. Open a project, click the settings icon / trigger to open the Edit Project dialog.
2. Confirm: a new "Archive" section is visible below the codebase index section.
3. Click "Archive project", accept the confirm prompt.
4. Confirm: dialog closes, URL becomes `/`, the project disappears from the switcher dropdown.

Proceed only on pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/projects/components/project-settings-dialog.tsx
git commit -m "feat(projects): archive action in settings dialog + redirect"
```

---

## Task 9: Frontend — `/projects/archived` page

**Files:**
- Create: `frontend/src/routes/projects/archived.tsx`

- [ ] **Step 1: Create the route file**

Create `frontend/src/routes/projects/archived.tsx` with:

```tsx
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArchiveRestore, FolderKanban } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { useProjects, useUnarchiveProject } from "@/features/projects/hooks";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/archived")({
  component: ArchivedProjectsPage,
});

function ArchivedProjectsPage() {
  const { data: projects, isLoading } = useProjects(true);
  const unarchive = useUnarchiveProject();

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  const handleUnarchive = (projectId: string, name: string) => {
    unarchive.mutate(projectId, {
      onSuccess: () => toast.success(`"${name}" restored`),
    });
  };

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <p className="text-sm text-muted-foreground mb-0.5">Projects</p>
        <h1 className="text-xl font-semibold">Archived</h1>
      </div>

      {projects && projects.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <FolderKanban className="size-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No archived projects.</p>
          <Link to="/" className="text-sm text-primary underline mt-2 inline-block">
            Back to dashboard
          </Link>
        </div>
      ) : (
        <ul className="divide-y rounded-lg border">
          {projects?.map((project) => (
            <li
              key={project.id}
              className="flex items-center justify-between gap-3 px-4 py-3"
            >
              <div className="min-w-0">
                <p className="font-medium truncate">{project.name}</p>
                <p className="text-xs text-muted-foreground font-mono truncate">
                  {project.path}
                </p>
                {project.archived_at && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    archived{" "}
                    {formatDistanceToNow(new Date(project.archived_at), {
                      addSuffix: true,
                    })}
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={unarchive.isPending && unarchive.variables === project.id}
                onClick={() => handleUnarchive(project.id, project.name)}
              >
                <ArchiveRestore className="size-3.5 mr-1.5" />
                {unarchive.isPending && unarchive.variables === project.id
                  ? "Restoring..."
                  : "Unarchive"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

Notes:
- The route sits at `/projects/archived`. TanStack Router's file-based convention treats this file as a sibling to `routes/projects/$projectId.tsx`, so it does not require a `$projectId` layout wrapper.
- `date-fns` is already a dependency (see `frontend/package.json`).
- `unarchive.variables` holds the last mutation argument, which lets us disable/spin only the row being restored.

- [ ] **Step 2: Regenerate the TanStack Router type tree**

Run: `cd frontend && npm run dev` briefly (it regenerates `routeTree.gen.ts` on start). Stop the server once the file updates (watch for console log `✓ Generated routeTree.gen.ts`). Alternatively, typecheck should still pass since the plugin auto-regenerates during build as well.

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors. The new route is reachable via `navigate({ to: "/projects/archived" })`.

- [ ] **Step 3: Manual browser smoke — archived page**

1. Ensure at least one archived project exists (archive one from Task 8 if needed).
2. Navigate to `/projects/archived` (either via URL bar or via the "View archived" link after Task 10).
3. Confirm: the archived project is listed with its name, path, and relative archive timestamp.
4. Click "Unarchive".
5. Confirm: toast appears, row disappears, the project reappears in the switcher dropdown.

Proceed only on pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/projects/archived.tsx frontend/src/routeTree.gen.ts
git commit -m "feat(projects): /projects/archived list page"
```

---

## Task 10: Frontend — "View archived" dropdown link

**Files:**
- Modify: `frontend/src/features/projects/components/project-switcher.tsx`

- [ ] **Step 1: Add the link**

Open `frontend/src/features/projects/components/project-switcher.tsx`.

Add `Archive` to the existing `lucide-react` import:

```ts
import { Archive, Check, ChevronsUpDown, FolderKanban, Plus } from "lucide-react";
```

Inside `<DropdownMenuContent>`, **after** the existing `DropdownMenuItem` for "New Project" (currently the final item), add:

```tsx
        <DropdownMenuItem
          onClick={() => navigate({ to: "/projects/archived" })}
          className="gap-2"
        >
          <Archive className="size-4" />
          <span>View archived</span>
        </DropdownMenuItem>
```

- [ ] **Step 2: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: no errors.

- [ ] **Step 3: Manual browser smoke — dropdown link**

1. Open the project switcher dropdown (top-left).
2. Confirm: "View archived" item appears below "New Project".
3. Click it — URL becomes `/projects/archived` and the archived page renders.
4. Re-open the dropdown and confirm the project list is sorted alphabetically A→Z (this verifies Task 3's backend sort surfacing here).

Proceed only on pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/projects/components/project-switcher.tsx
git commit -m "feat(projects): View archived link in project switcher"
```

---

## Task 11: End-to-end verification

**Files:** none — this is a manual checklist.

- [ ] **Step 1: Full backend test run**

Run: `cd backend && python -m pytest -q`
Expected: suite passes.

- [ ] **Step 2: Frontend typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: no errors.

- [ ] **Step 3: Manual golden-path walkthrough**

Start `python start.py` and verify in order:

1. **Dropdown sort:** Create three projects named `Zeta`, `alpha`, `Mango`. Open the dropdown — confirm order is `alpha`, `Mango`, `Zeta`.
2. **Issue list refresh:** Open any project → Issues → New Issue → submit. New issue appears without reload.
3. **Archive from settings:** Edit project dialog → Archive project → confirm prompt → dialog closes, URL at `/`, project gone from dropdown and dashboard.
4. **View archived:** Dropdown → "View archived" → archived project listed with relative archive time.
5. **Unarchive:** Click "Unarchive" → toast → row disappears → project reappears in dropdown in alphabetical position.
6. **Dashboard filter:** Go to `/dashboard`. Archived projects must not appear. Unarchive them and they reappear.

- [ ] **Step 4: If anything fails, file a follow-up task rather than papering over**

Before claiming complete, every step in Step 3 must pass cleanly. If a bug surfaces, stop, fix it, and re-run the full checklist.

- [ ] **Step 5: Final commit (if any lint/typecheck fixups were needed)**

```bash
git status
# If there are uncommitted touch-ups:
git add -p
git commit -m "chore: post-verification cleanup"
```

---

## Self-review notes (for reference — do not execute)

- Spec §1 (bug) → Task 5.
- Spec §2 data model → Tasks 1, 2.
- Spec §2 backend service + endpoints → Tasks 3, 4.
- Spec §2 frontend hooks/api → Tasks 6, 7.
- Spec §2 settings dialog archive button + redirect → Task 8.
- Spec §2 archived page → Task 9.
- Spec §2 dropdown "View archived" → Task 10.
- Spec §3 alphabetical sort → Task 3 (service) + surfaced in Tasks 4, 9, 10.
- Spec "Active resources during archive" (terminals preserved) → no work required; dashboard filter covered by Task 4 Step 6.
- Spec "Tests" for frontend — the repo has no frontend test framework configured, so frontend verification is tsc + lint + manual browser smoke. Documented explicitly in the plan header.
