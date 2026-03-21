# Terminal Startup Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to configure startup commands (global or per-project) that execute automatically when a terminal is opened.

**Architecture:** New `terminal_commands` DB table with CRUD service + API. Global commands act as fallback when no project-specific commands exist. On terminal creation, the router queries resolved commands and writes them to the PTY before the WebSocket connects.

**Tech Stack:** FastAPI, SQLAlchemy (async), Alembic, React, Tailwind CSS

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `backend/app/models/terminal_command.py` | SQLAlchemy model |
| Modify | `backend/app/models/__init__.py` | Register new model |
| Create | `backend/app/schemas/terminal_command.py` | Pydantic schemas |
| Create | `backend/app/services/terminal_command_service.py` | CRUD + resolve logic |
| Create | `backend/app/routers/terminal_commands.py` | REST endpoints |
| Modify | `backend/app/main.py` | Register new router |
| Create | `backend/alembic/versions/e5f6a7b8c9d0_add_terminal_commands_table.py` | Migration |
| Modify | `backend/app/routers/terminals.py` | Inject startup commands on create |
| Create | `backend/tests/test_terminal_command_service.py` | Service tests |
| Create | `backend/tests/test_terminal_command_router.py` | API tests |
| Modify | `backend/tests/conftest.py` | Register TerminalCommand model |
| Modify | `frontend/src/api/client.js` | API client methods |
| Create | `frontend/src/components/TerminalCommandsEditor.jsx` | Reusable command list editor |
| Modify | `frontend/src/pages/SettingsPage.jsx` | Add Terminal tab |
| Modify | `frontend/src/pages/ProjectDetailPage.jsx` | Add Terminal Settings section |

---

### Task 1: Database Model

**Files:**
- Create: `backend/app/models/terminal_command.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the SQLAlchemy model**

```python
# backend/app/models/terminal_command.py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TerminalCommand(Base):
    __tablename__ = "terminal_commands"
    __table_args__ = (
        UniqueConstraint("project_id", "sort_order", name="uq_project_sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: Register model in `__init__.py`**

Add to `backend/app/models/__init__.py`:

```python
from app.models.terminal_command import TerminalCommand
```

And add `"TerminalCommand"` to `__all__`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/terminal_command.py backend/app/models/__init__.py
git commit -m "feat: add TerminalCommand model"
```

---

### Task 2: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/e5f6a7b8c9d0_add_terminal_commands_table.py`

- [ ] **Step 1: Create migration file**

```python
# backend/alembic/versions/e5f6a7b8c9d0_add_terminal_commands_table.py
"""add terminal_commands table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "terminal_commands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "sort_order", name="uq_project_sort_order"),
    )


def downgrade() -> None:
    op.drop_table("terminal_commands")
```

- [ ] **Step 2: Run migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/e5f6a7b8c9d0_add_terminal_commands_table.py
git commit -m "feat: add terminal_commands migration"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/terminal_command.py`

- [ ] **Step 1: Create schemas**

```python
# backend/app/schemas/terminal_command.py
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TerminalCommandCreate(BaseModel):
    command: str = Field(..., min_length=1)
    sort_order: int
    project_id: str | None = None

    @field_validator("command")
    @classmethod
    def no_newlines(cls, v):
        if "\n" in v or "\r" in v:
            raise ValueError("Command must not contain newlines")
        return v


class TerminalCommandUpdate(BaseModel):
    command: str | None = Field(None, min_length=1)
    sort_order: int | None = None


class TerminalCommandOut(BaseModel):
    id: int
    command: str
    sort_order: int
    project_id: str | None
    created_at: datetime
    updated_at: datetime


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class TerminalCommandReorder(BaseModel):
    commands: list[ReorderItem]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/terminal_command.py
git commit -m "feat: add TerminalCommand schemas"
```

---

### Task 4: Service Layer

**Files:**
- Create: `backend/app/services/terminal_command_service.py`
- Create: `backend/tests/test_terminal_command_service.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Update conftest to register TerminalCommand model**

In `backend/tests/conftest.py`, add import:

```python
from app.models import Issue, Project, Setting, Task, TerminalCommand  # noqa: F401
```

(The `TerminalCommand` import ensures the model is registered with `Base.metadata` so tables are created in tests.)

- [ ] **Step 2: Write failing tests for the service**

```python
# backend/tests/test_terminal_command_service.py
import pytest
import pytest_asyncio

from app.models.project import Project
from app.services.terminal_command_service import TerminalCommandService


@pytest_asyncio.fixture
async def project(db_session):
    p = Project(name="Test Project", path="/tmp/test")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def service(db_session):
    return TerminalCommandService(db_session)


@pytest.mark.asyncio
async def test_list_global_empty(service):
    result = await service.list(project_id=None)
    assert result == []


@pytest.mark.asyncio
async def test_create_global_command(service):
    cmd = await service.create("echo hello", 0, project_id=None)
    assert cmd.command == "echo hello"
    assert cmd.sort_order == 0
    assert cmd.project_id is None


@pytest.mark.asyncio
async def test_create_project_command(service, project):
    cmd = await service.create("npm install", 0, project_id=project.id)
    assert cmd.project_id == project.id


@pytest.mark.asyncio
async def test_list_returns_ordered(service):
    await service.create("second", 1, project_id=None)
    await service.create("first", 0, project_id=None)
    result = await service.list(project_id=None)
    assert [c.command for c in result] == ["first", "second"]


@pytest.mark.asyncio
async def test_resolve_uses_project_commands_when_present(service, project):
    await service.create("global cmd", 0, project_id=None)
    await service.create("project cmd", 0, project_id=project.id)
    result = await service.resolve(project.id)
    assert len(result) == 1
    assert result[0].command == "project cmd"


@pytest.mark.asyncio
async def test_resolve_falls_back_to_global(service, project):
    await service.create("global cmd", 0, project_id=None)
    result = await service.resolve(project.id)
    assert len(result) == 1
    assert result[0].command == "global cmd"


@pytest.mark.asyncio
async def test_resolve_returns_empty_when_no_commands(service, project):
    result = await service.resolve(project.id)
    assert result == []


@pytest.mark.asyncio
async def test_update_command(service):
    cmd = await service.create("echo old", 0, project_id=None)
    updated = await service.update(cmd.id, command="echo new")
    assert updated.command == "echo new"


@pytest.mark.asyncio
async def test_update_sort_order(service):
    cmd = await service.create("echo hello", 0, project_id=None)
    updated = await service.update(cmd.id, sort_order=5)
    assert updated.sort_order == 5


@pytest.mark.asyncio
async def test_delete_command(service):
    cmd = await service.create("echo hello", 0, project_id=None)
    await service.delete(cmd.id)
    result = await service.list(project_id=None)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_raises(service):
    with pytest.raises(KeyError):
        await service.delete(9999)


@pytest.mark.asyncio
async def test_reorder(service):
    c1 = await service.create("first", 0, project_id=None)
    c2 = await service.create("second", 1, project_id=None)
    await service.reorder([
        {"id": c1.id, "sort_order": 1},
        {"id": c2.id, "sort_order": 0},
    ])
    result = await service.list(project_id=None)
    assert [c.command for c in result] == ["second", "first"]


@pytest.mark.asyncio
async def test_cascade_delete_removes_commands(db_session, project, service):
    await service.create("project cmd", 0, project_id=project.id)
    await db_session.delete(project)
    await db_session.flush()
    result = await service.list(project_id=project.id)
    assert result == []
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_terminal_command_service.py -v
```

Expected: ImportError (module doesn't exist yet)

- [ ] **Step 4: Implement the service**

```python
# backend/app/services/terminal_command_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.terminal_command import TerminalCommand


class TerminalCommandService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, project_id: str | None) -> list[TerminalCommand]:
        if project_id is None:
            stmt = (
                select(TerminalCommand)
                .where(TerminalCommand.project_id.is_(None))
                .order_by(TerminalCommand.sort_order)
            )
        else:
            stmt = (
                select(TerminalCommand)
                .where(TerminalCommand.project_id == project_id)
                .order_by(TerminalCommand.sort_order)
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def resolve(self, project_id: str) -> list[TerminalCommand]:
        project_cmds = await self.list(project_id)
        if project_cmds:
            return project_cmds
        return await self.list(project_id=None)

    async def create(
        self, command: str, sort_order: int, project_id: str | None = None
    ) -> TerminalCommand:
        row = TerminalCommand(
            command=command, sort_order=sort_order, project_id=project_id
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(
        self, cmd_id: int, command: str | None = None, sort_order: int | None = None
    ) -> TerminalCommand:
        row = await self.session.get(TerminalCommand, cmd_id)
        if row is None:
            raise KeyError(f"TerminalCommand {cmd_id} not found")
        if command is not None:
            row.command = command
        if sort_order is not None:
            row.sort_order = sort_order
        await self.session.flush()
        return row

    async def reorder(self, commands: list[dict]) -> None:
        for item in commands:
            row = await self.session.get(TerminalCommand, item["id"])
            if row is not None:
                row.sort_order = item["sort_order"]
        await self.session.flush()

    async def delete(self, cmd_id: int) -> None:
        row = await self.session.get(TerminalCommand, cmd_id)
        if row is None:
            raise KeyError(f"TerminalCommand {cmd_id} not found")
        await self.session.delete(row)
        await self.session.flush()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_terminal_command_service.py -v
```

Expected: All 13 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/terminal_command_service.py backend/tests/test_terminal_command_service.py backend/tests/conftest.py
git commit -m "feat: add TerminalCommandService with tests"
```

---

### Task 5: API Router

**Files:**
- Create: `backend/app/routers/terminal_commands.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_terminal_command_router.py`

- [ ] **Step 1: Write failing API tests**

```python
# backend/tests/test_terminal_command_router.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.project import Project


@pytest_asyncio.fixture
async def project(db_session):
    p = Project(name="Test Project", path="/tmp/test")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def client(db_session):
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_global_commands_empty(client):
    resp = await client.get("/api/terminal-commands")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_global_command(client):
    resp = await client.post(
        "/api/terminal-commands",
        json={"command": "echo hello", "sort_order": 0},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["command"] == "echo hello"
    assert data["sort_order"] == 0
    assert data["project_id"] is None


@pytest.mark.asyncio
async def test_create_project_command(client, project):
    resp = await client.post(
        "/api/terminal-commands",
        json={"command": "npm install", "sort_order": 0, "project_id": project.id},
    )
    assert resp.status_code == 201
    assert resp.json()["project_id"] == project.id


@pytest.mark.asyncio
async def test_list_filters_by_project_id(client, project):
    await client.post(
        "/api/terminal-commands",
        json={"command": "global", "sort_order": 0},
    )
    await client.post(
        "/api/terminal-commands",
        json={"command": "project", "sort_order": 0, "project_id": project.id},
    )
    # Global
    resp = await client.get("/api/terminal-commands")
    assert len(resp.json()) == 1
    assert resp.json()[0]["command"] == "global"
    # Project
    resp = await client.get(f"/api/terminal-commands?project_id={project.id}")
    assert len(resp.json()) == 1
    assert resp.json()[0]["command"] == "project"


@pytest.mark.asyncio
async def test_update_command(client):
    create = await client.post(
        "/api/terminal-commands",
        json={"command": "old", "sort_order": 0},
    )
    cmd_id = create.json()["id"]
    resp = await client.put(
        f"/api/terminal-commands/{cmd_id}",
        json={"command": "new"},
    )
    assert resp.status_code == 200
    assert resp.json()["command"] == "new"


@pytest.mark.asyncio
async def test_update_nonexistent_returns_404(client):
    resp = await client.put(
        "/api/terminal-commands/9999",
        json={"command": "new"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reorder(client):
    r1 = await client.post(
        "/api/terminal-commands",
        json={"command": "first", "sort_order": 0},
    )
    r2 = await client.post(
        "/api/terminal-commands",
        json={"command": "second", "sort_order": 1},
    )
    resp = await client.put(
        "/api/terminal-commands/reorder",
        json={"commands": [
            {"id": r1.json()["id"], "sort_order": 1},
            {"id": r2.json()["id"], "sort_order": 0},
        ]},
    )
    assert resp.status_code == 200
    # Verify order changed
    listing = await client.get("/api/terminal-commands")
    cmds = listing.json()
    assert cmds[0]["command"] == "second"
    assert cmds[1]["command"] == "first"


@pytest.mark.asyncio
async def test_delete_command(client):
    create = await client.post(
        "/api/terminal-commands",
        json={"command": "to delete", "sort_order": 0},
    )
    cmd_id = create.json()["id"]
    resp = await client.delete(f"/api/terminal-commands/{cmd_id}")
    assert resp.status_code == 204
    listing = await client.get("/api/terminal-commands")
    assert len(listing.json()) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client):
    resp = await client.delete("/api/terminal-commands/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_command_with_newlines_rejected(client):
    resp = await client.post(
        "/api/terminal-commands",
        json={"command": "echo\nhello", "sort_order": 0},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_terminal_command_router.py -v
```

Expected: FAIL (router doesn't exist yet)

- [ ] **Step 3: Create the router**

```python
# backend/app/routers/terminal_commands.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.terminal_command import (
    TerminalCommandCreate,
    TerminalCommandOut,
    TerminalCommandReorder,
    TerminalCommandUpdate,
)
from app.services.terminal_command_service import TerminalCommandService

router = APIRouter(prefix="/api/terminal-commands", tags=["terminal-commands"])


@router.get("", response_model=list[TerminalCommandOut])
async def list_terminal_commands(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    return await service.list(project_id)


@router.post("", response_model=TerminalCommandOut, status_code=201)
async def create_terminal_command(
    data: TerminalCommandCreate,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    cmd = await service.create(data.command, data.sort_order, data.project_id)
    await db.commit()
    return cmd


# NOTE: /reorder MUST be before /{cmd_id} to avoid "reorder" matching as an id
@router.put("/reorder", response_model=list[TerminalCommandOut])
async def reorder_terminal_commands(
    data: TerminalCommandReorder,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    await service.reorder([item.model_dump() for item in data.commands])
    await db.commit()
    # Return the updated list (infer project_id from first item if possible)
    if data.commands:
        from app.models.terminal_command import TerminalCommand
        first = await db.get(TerminalCommand, data.commands[0].id)
        return await service.list(first.project_id if first else None)
    return []


@router.put("/{cmd_id}", response_model=TerminalCommandOut)
async def update_terminal_command(
    cmd_id: int,
    data: TerminalCommandUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    try:
        cmd = await service.update(cmd_id, command=data.command, sort_order=data.sort_order)
        await db.commit()
        return cmd
    except KeyError:
        raise HTTPException(status_code=404, detail="Command not found")


@router.delete("/{cmd_id}", status_code=204)
async def delete_terminal_command(
    cmd_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    try:
        await service.delete(cmd_id)
        await db.commit()
    except KeyError:
        raise HTTPException(status_code=404, detail="Command not found")
```

- [ ] **Step 4: Register router in `main.py`**

In `backend/app/main.py`, add:

```python
from app.routers import issues, projects, settings, tasks, terminals, terminal_commands
```

And add:

```python
app.include_router(terminal_commands.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_terminal_command_router.py -v
```

Expected: All 11 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/terminal_commands.py backend/app/main.py backend/tests/test_terminal_command_router.py
git commit -m "feat: add terminal-commands API router with tests"
```

---

### Task 6: Inject Startup Commands on Terminal Creation

**Files:**
- Modify: `backend/app/routers/terminals.py:40-63` (the `create_terminal` endpoint)

- [ ] **Step 1: Modify `create_terminal` to inject commands after PTY creation**

In `backend/app/routers/terminals.py`, add the import at the top:

```python
from app.services.terminal_command_service import TerminalCommandService
```

Then in the `create_terminal` function, after `terminal = service.create(...)` and before `return TerminalResponse(**terminal)`, add:

```python
    # Inject startup commands into the PTY
    try:
        cmd_service = TerminalCommandService(db)
        commands = await cmd_service.resolve(data.project_id)
        if commands:
            pty = service.get_pty(terminal["id"])
            cmd_string = " && ".join(c.command for c in commands) + "\n"
            pty.write(cmd_string)
    except Exception:
        logger.warning("Failed to inject startup commands for terminal %s", terminal["id"], exc_info=True)
```

- [ ] **Step 2: Run all existing terminal tests to verify nothing is broken**

```bash
cd backend && python -m pytest tests/test_terminal_router.py tests/test_terminal_service.py -v
```

Expected: All existing tests PASS (startup command injection is a no-op when no commands are configured)

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/terminals.py
git commit -m "feat: inject startup commands on terminal creation"
```

---

### Task 7: Frontend API Client

**Files:**
- Modify: `frontend/src/api/client.js`

- [ ] **Step 1: Add terminal command API methods**

Add to the `api` object in `frontend/src/api/client.js`, after the Terminals section:

```javascript
  // Terminal Commands
  listTerminalCommands: (projectId) => {
    const params = projectId != null ? `?project_id=${projectId}` : "";
    return request(`/terminal-commands${params}`);
  },
  createTerminalCommand: (data) =>
    request("/terminal-commands", { method: "POST", body: JSON.stringify(data) }),
  updateTerminalCommand: (id, data) =>
    request(`/terminal-commands/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  reorderTerminalCommands: (commands) =>
    request("/terminal-commands/reorder", { method: "PUT", body: JSON.stringify({ commands }) }),
  deleteTerminalCommand: (id) =>
    request(`/terminal-commands/${id}`, { method: "DELETE" }),
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.js
git commit -m "feat: add terminal commands API client methods"
```

---

### Task 8: Reusable TerminalCommandsEditor Component

**Files:**
- Create: `frontend/src/components/TerminalCommandsEditor.jsx`

- [ ] **Step 1: Create the component**

This component is used by both SettingsPage (global) and ProjectDetailPage (per-project). It receives a `projectId` prop (null for global).

```jsx
// frontend/src/components/TerminalCommandsEditor.jsx
import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function TerminalCommandsEditor({ projectId = null }) {
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newCmd, setNewCmd] = useState("");

  const load = () => {
    setLoading(true);
    api
      .listTerminalCommands(projectId)
      .then(setCommands)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectId]);

  const handleAdd = async () => {
    const trimmed = newCmd.trim();
    if (!trimmed) return;
    const sortOrder = commands.length > 0 ? Math.max(...commands.map((c) => c.sort_order)) + 1 : 0;
    await api.createTerminalCommand({
      command: trimmed,
      sort_order: sortOrder,
      project_id: projectId,
    });
    setNewCmd("");
    load();
  };

  const handleDelete = async (id) => {
    await api.deleteTerminalCommand(id);
    load();
  };

  const handleBlur = async (cmd, newValue) => {
    const trimmed = newValue.trim();
    if (!trimmed || trimmed === cmd.command) return;
    await api.updateTerminalCommand(cmd.id, { command: trimmed });
    load();
  };

  const handleMove = async (index, direction) => {
    const swapIndex = index + direction;
    if (swapIndex < 0 || swapIndex >= commands.length) return;
    const reordered = [
      { id: commands[index].id, sort_order: commands[swapIndex].sort_order },
      { id: commands[swapIndex].id, sort_order: commands[index].sort_order },
    ];
    await api.reorderTerminalCommands(reordered);
    load();
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>;

  return (
    <div className="space-y-2">
      {commands.length === 0 && projectId != null && (
        <p className="text-sm text-gray-500 italic">
          No project commands configured. Global commands will be used.
        </p>
      )}

      {commands.map((cmd, index) => (
        <div key={cmd.id} className="flex items-center gap-2">
          <div className="flex flex-col">
            <button
              onClick={() => handleMove(index, -1)}
              disabled={index === 0}
              className="text-gray-400 hover:text-gray-600 text-xs leading-none disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move up"
            >
              ▲
            </button>
            <button
              onClick={() => handleMove(index, 1)}
              disabled={index === commands.length - 1}
              className="text-gray-400 hover:text-gray-600 text-xs leading-none disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move down"
            >
              ▼
            </button>
          </div>
          <input
            type="text"
            defaultValue={cmd.command}
            onBlur={(e) => handleBlur(cmd, e.target.value)}
            className="flex-1 border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <button
            onClick={() => handleDelete(cmd.id)}
            className="text-gray-400 hover:text-red-600 text-lg leading-none"
            title="Delete"
          >
            &times;
          </button>
        </div>
      ))}

      <div className="flex gap-2 mt-3">
        <input
          type="text"
          value={newCmd}
          onChange={(e) => setNewCmd(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a command..."
          className="flex-1 border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
        <button
          onClick={handleAdd}
          disabled={!newCmd.trim()}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TerminalCommandsEditor.jsx
git commit -m "feat: add TerminalCommandsEditor component"
```

---

### Task 9: Add Terminal Tab to Settings Page

**Files:**
- Modify: `frontend/src/pages/SettingsPage.jsx`

- [ ] **Step 1: Add Terminal tab**

Three changes to `frontend/src/pages/SettingsPage.jsx`:

1. Add import at the top:

```jsx
import TerminalCommandsEditor from "../components/TerminalCommandsEditor";
```

2. Change the TABS constant (line 4):

```javascript
const TABS = ["Server", "Tool Descriptions", "Response Messages", "Terminal"];
```

3. Add Terminal tab content. After the `{/* Settings list */}` section `</div>` (after line 200) and before the `{/* Reset all */}` section, add:

```jsx
      {/* Terminal commands tab */}
      {activeTab === "Terminal" && (
        <div>
          <div className="mb-5 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
            These commands run automatically when opening a terminal. They apply only when a project has no project-specific commands.
          </div>
          <TerminalCommandsEditor projectId={null} />
        </div>
      )}
```

Also wrap the existing settings list in a conditional so it doesn't show on the Terminal tab. Change line 150 from:

```jsx
      <div className="space-y-5">
```

to:

```jsx
      {activeTab !== "Terminal" && <div className="space-y-5">
```

And after the closing `</div>` of the settings list (line 200), change it to:

```jsx
      </div>}
```

Similarly, wrap the "Reset all" section with `{activeTab !== "Terminal" && ... }`.

- [ ] **Step 2: Verify manually**

Open `http://localhost:5173/settings` and verify:
- The "Terminal" tab appears
- Clicking it shows the info message and the command editor
- Adding, reordering, editing, and deleting commands works
- Other tabs still work correctly

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SettingsPage.jsx
git commit -m "feat: add Terminal tab to Settings page"
```

---

### Task 10: Add Terminal Settings Section to ProjectDetailPage

**Files:**
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`

- [ ] **Step 1: Add Terminal Settings section**

Two changes to `frontend/src/pages/ProjectDetailPage.jsx`:

1. Add import at the top:

```jsx
import TerminalCommandsEditor from "../components/TerminalCommandsEditor";
```

2. Add the Terminal Settings section after the `<IssueList>` component (after line 251) and before the MCP Setup modal:

```jsx
      {/* Terminal Settings */}
      <div className="mt-8 pt-6 border-t">
        <h2 className="text-lg font-bold mb-2">Terminal Settings</h2>
        <p className="text-sm text-gray-500 mb-4">
          These commands run when opening a terminal for this project. When set, they override the global terminal commands.
        </p>
        <TerminalCommandsEditor projectId={id} />
      </div>
```

- [ ] **Step 2: Verify manually**

Open a project detail page and verify:
- The "Terminal Settings" section appears below the issue list
- The fallback message shows when no project commands exist
- Adding project-specific commands works
- Reordering and deleting works

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ProjectDetailPage.jsx
git commit -m "feat: add Terminal Settings section to ProjectDetailPage"
```

---

### Task 11: Run All Tests and Final Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All tests PASS (existing + new terminal command tests)

- [ ] **Step 2: Manual end-to-end verification**

1. Configure 2 global commands in Settings → Terminal (e.g., `echo Global1`, `echo Global2`)
2. Open a terminal for a project with no project commands → verify global commands run (concatenated with `&&`)
3. Add a project command to that project (e.g., `echo ProjectCmd`)
4. Open a new terminal for that project → verify only the project command runs
5. Delete the project command → open terminal again → verify global commands run again

- [ ] **Step 3: Commit any fixes if needed**

```bash
git add -A && git commit -m "fix: address issues from final verification"
```
