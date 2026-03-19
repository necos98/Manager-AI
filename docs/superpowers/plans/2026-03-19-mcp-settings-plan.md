# MCP Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable settings system for MCP text (tool descriptions + response messages), stored in a DB `settings` table and editable from a frontend Settings page.

**Architecture:** Key-value `settings` table stores user overrides; `backend/app/mcp/default_settings.json` holds defaults. `SettingsService` merges both (DB wins). Response messages are read from DB on each MCP call (real-time). Tool descriptions are read from JSON at server startup (require restart). REST router at `/api/settings`. New `SettingsPage` with 3 tabs.

**Tech Stack:** FastAPI, SQLAlchemy async (aiosqlite), Alembic, React + Tailwind CSS

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `backend/app/mcp/default_settings.json` | Source of truth for all 9 default setting values |
| Create | `backend/app/models/setting.py` | SQLAlchemy ORM model for the `settings` table |
| Modify | `backend/app/models/__init__.py` | Export `Setting` alongside `Project` and `Task` |
| Create | `backend/app/schemas/setting.py` | Pydantic `SettingOut` and `SettingUpdate` schemas |
| Create | `backend/app/services/settings_service.py` | Business logic: get/set/reset settings with DB+JSON merge |
| Create | `backend/alembic/versions/b1c2d3e4f5a6_add_settings_table.py` | DB migration creating the `settings` table |
| Create | `backend/app/routers/settings.py` | REST endpoints: GET, PUT, DELETE per key, DELETE all |
| Modify | `backend/app/main.py` | Mount the settings router |
| Modify | `backend/app/mcp/server.py` | Read descriptions from JSON at startup; response messages from DB per call |
| Create | `backend/tests/test_settings_service.py` | Unit tests for `SettingsService` |
| Modify | `backend/tests/conftest.py` | Import `Setting` so test DB creates the table |
| Modify | `frontend/src/api/client.js` | Add `getSettings`, `updateSetting`, `resetSetting`, `resetAllSettings` |
| Create | `frontend/src/pages/SettingsPage.jsx` | New settings page with 3 tabs |
| Modify | `frontend/src/App.jsx` | Add `/settings` route and header link |

---

## Task 1: default_settings.json + Setting model + schemas

**Files:**
- Create: `backend/app/mcp/default_settings.json`
- Create: `backend/app/models/setting.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/setting.py`

- [ ] **Step 1: Create default_settings.json**

Create `backend/app/mcp/default_settings.json`:

```json
{
  "server.name": "Manager AI",
  "tool.get_next_task.description": "Get the highest priority task that needs work (Declined before New, then by priority). Returns task id, description, status, and decline_feedback if present. Returns null if none available.",
  "tool.get_task_details.description": "Get all details of a specific task.",
  "tool.get_task_status.description": "Get the current status of a task.",
  "tool.get_project_context.description": "Get project information (name, path, description, tech_stack).",
  "tool.set_task_name.description": "Set the name of a task after analysis.",
  "tool.save_task_plan.description": "Save a markdown plan for a task and set status to Planned. Only works for tasks in New or Declined status.\n\nIMPORTANT: After saving a plan, you MUST stop and wait for the user to approve or decline the plan via the frontend. Do NOT proceed with implementation until the task status changes to 'Accepted'. Poll get_task_status to check, but only after the user tells you they have reviewed the plan.",
  "tool.save_task_plan.response_message": "Plan saved. STOP HERE — do NOT proceed with implementation. The user must review and approve this plan in the frontend before you can continue. Wait for the user to confirm approval, then check the task status with get_task_status.",
  "tool.complete_task.description": "Mark a task as Finished and save the recap. Only works for tasks in Accepted status."
}
```

- [ ] **Step 2: Create the Setting model**

Create `backend/app/models/setting.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 3: Update models/__init__.py**

`backend/app/models/__init__.py` must export all three models so Alembic and conftest can see them. Replace the current content:

```python
from app.database import Base
from app.models.project import Project
from app.models.setting import Setting
from app.models.task import Task

__all__ = ["Base", "Project", "Setting", "Task"]
```

- [ ] **Step 4: Create Pydantic schemas**

Create `backend/app/schemas/setting.py`:

```python
from pydantic import BaseModel, Field


class SettingOut(BaseModel):
    key: str
    value: str           # active value (DB if customized, else default)
    default: str         # original value from default_settings.json
    is_customized: bool  # True if a DB row exists for this key

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    value: str = Field(..., min_length=1)
```

- [ ] **Step 5: Run existing tests to confirm nothing is broken**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all existing tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/default_settings.json \
        backend/app/models/setting.py \
        backend/app/models/__init__.py \
        backend/app/schemas/setting.py
git commit -m "feat: add Setting model, schemas, and default_settings.json"
```

---

## Task 2: SettingsService (TDD)

**Files:**
- Create: `backend/tests/test_settings_service.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/app/services/settings_service.py`

- [ ] **Step 1: Update conftest.py to import Setting**

Open `backend/tests/conftest.py`. Find the models import line:

```python
from app.models import Project, Task  # noqa: F401
```

Change it to:

```python
from app.models import Project, Setting, Task  # noqa: F401
```

This is needed so `Base.metadata.create_all()` in the fixture also creates the `settings` table.

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_settings_service.py`:

```python
import pytest
import pytest_asyncio

from app.services.settings_service import SettingsService


@pytest_asyncio.fixture
async def service(db_session):
    return SettingsService(db_session)


async def test_get_returns_default_when_not_customized(service):
    value = await service.get("server.name")
    assert value == "Manager AI"


async def test_get_returns_db_value_when_customized(db_session, service):
    await service.set("server.name", "My Custom Name")
    await db_session.commit()
    value = await service.get("server.name")
    assert value == "My Custom Name"


async def test_get_raises_keyerror_for_unknown_key(service):
    with pytest.raises(KeyError):
        await service.get("nonexistent.key")


async def test_get_all_returns_all_defaults_not_customized(service):
    settings = await service.get_all()
    keys = [s.key for s in settings]
    assert "server.name" in keys
    assert "tool.save_task_plan.response_message" in keys
    assert all(not s.is_customized for s in settings)
    for s in settings:
        assert s.value == s.default


async def test_get_all_marks_customized_correctly(db_session, service):
    await service.set("server.name", "Custom")
    await db_session.commit()
    settings = await service.get_all()
    server_name = next(s for s in settings if s.key == "server.name")
    assert server_name.is_customized is True
    assert server_name.value == "Custom"
    assert server_name.default == "Manager AI"


async def test_get_all_ignores_db_keys_not_in_json(db_session, service):
    # Simulate a stale DB row with a key that no longer exists in JSON
    from app.models.setting import Setting
    stale = Setting(key="obsolete.key", value="old")
    db_session.add(stale)
    await db_session.flush()
    settings = await service.get_all()
    keys = [s.key for s in settings]
    assert "obsolete.key" not in keys


async def test_set_creates_new_row(db_session, service):
    setting = await service.set("server.name", "New Name")
    await db_session.commit()
    assert setting.key == "server.name"
    assert setting.value == "New Name"


async def test_set_updates_existing_row(db_session, service):
    await service.set("server.name", "First")
    await db_session.commit()
    await service.set("server.name", "Second")
    await db_session.commit()
    value = await service.get("server.name")
    assert value == "Second"


async def test_set_raises_keyerror_for_unknown_key(service):
    with pytest.raises(KeyError):
        await service.set("nonexistent.key", "value")


async def test_reset_removes_customization(db_session, service):
    await service.set("server.name", "Custom")
    await db_session.commit()
    await service.reset("server.name")
    await db_session.commit()
    value = await service.get("server.name")
    assert value == "Manager AI"  # back to default


async def test_reset_is_idempotent_when_not_customized(service):
    # Should not raise even if key was never customized
    await service.reset("server.name")


async def test_reset_all_clears_all_customizations(db_session, service):
    await service.set("server.name", "Custom 1")
    await service.set("tool.get_task_status.description", "Custom 2")
    await db_session.commit()
    await service.reset_all()
    await db_session.commit()
    settings = await service.get_all()
    assert all(not s.is_customized for s in settings)


async def test_get_one_returns_correct_out(db_session, service):
    out = await service.get_one("server.name")
    assert out.key == "server.name"
    assert out.value == "Manager AI"
    assert out.default == "Manager AI"
    assert out.is_customized is False

    await service.set("server.name", "Custom")
    await db_session.commit()
    out = await service.get_one("server.name")
    assert out.value == "Custom"
    assert out.is_customized is True
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_settings_service.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `settings_service`. All tests fail.

- [ ] **Step 4: Implement SettingsService**

Create `backend/app/services/settings_service.py`:

```python
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.schemas.setting import SettingOut

_DEFAULTS_PATH = Path(__file__).parent.parent / "mcp" / "default_settings.json"
_DEFAULTS: dict[str, str] = json.loads(_DEFAULTS_PATH.read_text(encoding="utf-8"))


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> str:
        """Returns DB value if row exists, otherwise the JSON default.
        Raises KeyError if key is not in default_settings.json."""
        if key not in _DEFAULTS:
            raise KeyError(f"Unknown setting key: {key!r}")
        row = await self.session.get(Setting, key)
        if row is not None:
            return row.value
        return _DEFAULTS[key]

    async def get_one(self, key: str) -> SettingOut:
        """Returns a single SettingOut. Raises KeyError if key not in JSON."""
        if key not in _DEFAULTS:
            raise KeyError(f"Unknown setting key: {key!r}")
        row = await self.session.get(Setting, key)
        default = _DEFAULTS[key]
        is_customized = row is not None
        return SettingOut(
            key=key,
            value=row.value if is_customized else default,
            default=default,
            is_customized=is_customized,
        )

    async def get_all(self) -> list[SettingOut]:
        """Returns all settings from JSON, merging DB overrides.
        DB rows with keys not in JSON are ignored."""
        result = await self.session.execute(select(Setting))
        db_rows = {row.key: row.value for row in result.scalars().all()}
        return [
            SettingOut(
                key=key,
                value=db_rows[key] if key in db_rows else default,
                default=default,
                is_customized=key in db_rows,
            )
            for key, default in _DEFAULTS.items()
        ]

    async def set(self, key: str, value: str) -> Setting:
        """Upserts a setting row. Raises KeyError if key not in JSON."""
        if key not in _DEFAULTS:
            raise KeyError(f"Unknown setting key: {key!r}")
        row = await self.session.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
        await self.session.flush()
        return row

    async def reset(self, key: str) -> None:
        """Deletes the DB row for this key. Idempotent."""
        row = await self.session.get(Setting, key)
        if row is not None:
            await self.session.delete(row)
            await self.session.flush()

    async def reset_all(self) -> None:
        """Deletes all rows from the settings table via ORM-level deletes."""
        result = await self.session.execute(select(Setting))
        for row in result.scalars().all():
            await self.session.delete(row)
        await self.session.flush()
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
cd backend && python -m pytest tests/test_settings_service.py -v
```

Expected: all 13 tests pass.

- [ ] **Step 6: Run full test suite to confirm no regressions**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/conftest.py \
        backend/tests/test_settings_service.py \
        backend/app/services/settings_service.py
git commit -m "feat: add SettingsService with tests"
```

---

## Task 3: Alembic migration

**Files:**
- Create: `backend/alembic/versions/b1c2d3e4f5a6_add_settings_table.py`

- [ ] **Step 1: Create the migration file**

Create `backend/alembic/versions/b1c2d3e4f5a6_add_settings_table.py`:

```python
"""add settings table

Revision ID: b1c2d3e4f5a6
Revises: 4a2b7ea62498
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "4a2b7ea62498"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("settings")
```

- [ ] **Step 2: Verify migration runs cleanly**

Run from the `backend` directory (the data/manager_ai.db must already exist from a previous run):

```bash
cd backend && python -m alembic upgrade head
```

Expected: output shows `Running upgrade 4a2b7ea62498 -> b1c2d3e4f5a6, add settings table` with no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/b1c2d3e4f5a6_add_settings_table.py
git commit -m "feat: add Alembic migration for settings table"
```

---

## Task 4: REST router

**Files:**
- Create: `backend/app/routers/settings.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the settings router**

Create `backend/app/routers/settings.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.setting import SettingOut, SettingUpdate
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=list[SettingOut])
async def list_settings(db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    return await service.get_all()


# IMPORTANT: register DELETE "" before DELETE "/{key}" so FastAPI
# matches the exact root path before the parameterized one.
@router.delete("", status_code=204)
async def reset_all_settings(db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    await service.reset_all()
    await db.commit()


@router.put("/{key}", response_model=SettingOut)
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    try:
        await service.set(key, data.value)
        await db.commit()
        return await service.get_one(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Setting not found")


@router.delete("/{key}", status_code=204)
async def reset_setting(key: str, db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    await service.reset(key)
    await db.commit()
```

- [ ] **Step 2: Mount the router in main.py**

Open `backend/app/main.py`. Find the router imports and include lines:

```python
from app.routers import projects, tasks
```

Change to:

```python
from app.routers import projects, settings, tasks
```

Find:

```python
app.include_router(projects.router)
app.include_router(tasks.router)
```

Change to:

```python
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(settings.router)
```

- [ ] **Step 3: Manual smoke test**

Start the backend (from the project root):

```bash
python start.py
```

Then test the endpoints:

```bash
# List all settings
curl http://localhost:8000/api/settings

# Update a setting
curl -X PUT http://localhost:8000/api/settings/server.name \
  -H "Content-Type: application/json" \
  -d '{"value": "My Manager"}'

# Verify the change
curl http://localhost:8000/api/settings | python -m json.tool

# Reset it
curl -X DELETE http://localhost:8000/api/settings/server.name

# Verify reset
curl http://localhost:8000/api/settings/server.name  # (this route doesn't exist, check via list)
curl http://localhost:8000/api/settings | python -m json.tool
```

Expected for GET: a JSON array with 9 objects, each having `key`, `value`, `default`, `is_customized`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/settings.py backend/app/main.py
git commit -m "feat: add settings REST router"
```

---

## Task 5: Update MCP server

**Files:**
- Modify: `backend/app/mcp/server.py`

The goal: tool descriptions come from `default_settings.json` at import time (passed to `@mcp.tool(description=...)`); the `save_task_plan` response message is read from DB on each call.

- [ ] **Step 1: Check for existing MCP tests**

Run `ls backend/tests/` and verify whether there is a `test_mcp_tools.py` or similar MCP test file. If one exists, read it before proceeding — it may need updating if it imports tool functions or checks docstrings directly. If no such file exists, proceed to Step 2.

- [ ] **Step 2: Rewrite server.py**

Replace the entire content of `backend/app/mcp/server.py` with:

```python
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.services.project_service import ProjectService
from app.services.settings_service import SettingsService
from app.services.task_service import TaskService

# Load descriptions from default_settings.json at startup.
# Tool descriptions are static for the lifetime of this process
# (MCP protocol exposes them at handshake time, not per-call).
# To apply DB-stored description overrides, restart the backend.
_defaults_path = Path(__file__).parent / "default_settings.json"
_desc = json.loads(_defaults_path.read_text(encoding="utf-8"))

mcp = FastMCP(_desc["server.name"], streamable_http_path="/")


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
            "plan": task.plan,
            "recap": task.recap,
            "decline_feedback": task.decline_feedback,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


@mcp.tool(description=_desc["tool.get_task_status.description"])
async def get_task_status(project_id: str, task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_for_project(task_id, project_id)
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {"id": task.id, "status": task.status.value}


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


@mcp.tool(description=_desc["tool.set_task_name.description"])
async def set_task_name(project_id: str, task_id: str, name: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.set_name(task_id, project_id, name)
            await session.commit()
            return {"id": task.id, "name": task.name}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


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


@mcp.tool(description=_desc["tool.complete_task.description"])
async def complete_task(project_id: str, task_id: str, recap: str) -> dict:
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

- [ ] **Step 2: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/app/mcp/server.py
git commit -m "feat: MCP server reads descriptions from JSON, response messages from DB"
```

---

## Task 6: Frontend — Settings page

**Files:**
- Modify: `frontend/src/api/client.js`
- Create: `frontend/src/pages/SettingsPage.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add API methods to client.js**

Open `frontend/src/api/client.js`. After the closing `}` of the `tasks` section, add the settings methods before the final `};`:

Find the end of the `api` object (just before the final `};`):

```js
  deleteTask: (projectId, taskId) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),
};
```

Replace with:

```js
  deleteTask: (projectId, taskId) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),

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
};
```

- [ ] **Step 2: Create SettingsPage.jsx**

Create `frontend/src/pages/SettingsPage.jsx`:

```jsx
import { useEffect, useState } from "react";
import { api } from "../api/client";

const TABS = ["Server", "Tool Descriptions", "Response Messages"];

function getCategory(key) {
  if (key.startsWith("server.")) return "Server";
  if (key.endsWith(".description")) return "Tool Descriptions";
  if (key.endsWith(".response_message")) return "Response Messages";
  return "Other";
}

function formatLabel(key) {
  const parts = key.split(".");
  if (parts[0] === "tool") {
    return parts[1].replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  if (parts[0] === "server") return parts[1].replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return key;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState([]);
  const [edited, setEdited] = useState({});
  const [saving, setSaving] = useState({});
  const [activeTab, setActiveTab] = useState("Server");
  const [resetConfirm, setResetConfirm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getSettings()
      .then(setSettings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const getValue = (s) => (edited[s.key] !== undefined ? edited[s.key] : s.value);

  const isDirty = (s) =>
    edited[s.key] !== undefined && edited[s.key] !== s.value;

  const handleSave = async (setting) => {
    setSaving((prev) => ({ ...prev, [setting.key]: true }));
    try {
      const updated = await api.updateSetting(setting.key, getValue(setting));
      setSettings((prev) => prev.map((s) => (s.key === setting.key ? updated : s)));
      setEdited((prev) => {
        const next = { ...prev };
        delete next[setting.key];
        return next;
      });
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving((prev) => {
        const next = { ...prev };
        delete next[setting.key];
        return next;
      });
    }
  };

  const handleReset = async (setting) => {
    try {
      await api.resetSetting(setting.key);
      setSettings((prev) =>
        prev.map((s) =>
          s.key === setting.key ? { ...s, value: s.default, is_customized: false } : s
        )
      );
      setEdited((prev) => {
        const next = { ...prev };
        delete next[setting.key];
        return next;
      });
    } catch (e) {
      alert(e.message);
    }
  };

  const handleResetAll = async () => {
    try {
      await api.resetAllSettings();
      setSettings((prev) =>
        prev.map((s) => ({ ...s, value: s.default, is_customized: false }))
      );
      setEdited({});
      setResetConfirm(false);
    } catch (e) {
      alert(e.message);
    }
  };

  const filteredSettings = settings.filter((s) => getCategory(s.key) === activeTab);

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-0 mb-6 border-b">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Description changes warning */}
      {activeTab === "Tool Descriptions" && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
          Le modifiche alle descrizioni dei tool hanno effetto dopo il riavvio del backend.
        </div>
      )}

      {/* Settings list */}
      <div className="space-y-5">
        {filteredSettings.length === 0 && (
          <p className="text-gray-500 text-sm">Nessun setting in questa categoria.</p>
        )}
        {filteredSettings.map((setting) => (
          <div key={setting.key} className="border rounded-lg p-4 bg-white">
            <div className="flex items-center justify-between mb-2">
              <label className="font-medium text-sm text-gray-800">
                {formatLabel(setting.key)}
              </label>
              <div className="flex items-center gap-2">
                {setting.is_customized && (
                  <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">
                    Customized
                  </span>
                )}
                {setting.is_customized && (
                  <button
                    onClick={() => handleReset(setting)}
                    title="Ripristina valore predefinito"
                    className="text-gray-400 hover:text-gray-600 text-base leading-none"
                  >
                    ↺
                  </button>
                )}
              </div>
            </div>
            <textarea
              value={getValue(setting)}
              onChange={(e) =>
                setEdited((prev) => ({ ...prev, [setting.key]: e.target.value }))
              }
              rows={setting.key.endsWith(".description") ? 4 : 5}
              className="w-full border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            {!setting.is_customized && (
              <p className="text-xs text-gray-400 mt-1">Valore predefinito</p>
            )}
            <div className="flex justify-end mt-2">
              <button
                onClick={() => handleSave(setting)}
                disabled={saving[setting.key] || !isDirty(setting)}
                className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving[setting.key] ? "Salvataggio..." : "Save"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Reset all */}
      <div className="mt-8 pt-6 border-t">
        {resetConfirm ? (
          <div className="flex items-center gap-3">
            <p className="text-sm text-gray-600">
              Ripristinare tutti i setting ai valori predefiniti?
            </p>
            <button
              onClick={handleResetAll}
              className="bg-red-600 text-white px-3 py-1.5 rounded text-sm hover:bg-red-700"
            >
              Conferma
            </button>
            <button
              onClick={() => setResetConfirm(false)}
              className="px-3 py-1.5 rounded text-sm border hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        ) : (
          <button
            onClick={() => setResetConfirm(true)}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Ripristina tutti i valori predefiniti
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update App.jsx — add route and header link**

Open `frontend/src/App.jsx`.

Add the import at the top alongside the other page imports:

```jsx
import SettingsPage from "./pages/SettingsPage";
```

Replace the header `<div>` (the one with `max-w-5xl`):

```jsx
<div className="max-w-5xl mx-auto px-4 py-4">
  <a href="/" className="text-xl font-bold text-gray-900">
    Manager AI
  </a>
</div>
```

With:

```jsx
<div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
  <a href="/" className="text-xl font-bold text-gray-900">
    Manager AI
  </a>
  <a href="/settings" className="text-sm text-gray-500 hover:text-gray-900">
    Settings
  </a>
</div>
```

Add the settings route inside `<Routes>`, after the last existing route:

```jsx
<Route path="/settings" element={<SettingsPage />} />
```

- [ ] **Step 4: Manual end-to-end test**

Start the full app (from project root):

```bash
python start.py
```

1. Open `http://localhost:5173`
2. Click "Settings" in the header
3. Verify the 3 tabs are visible: Server, Tool Descriptions, Response Messages
4. Check "Server" tab shows `server.name` with value "Manager AI"
5. Edit the value, click Save — the "Customized" badge appears and the ↺ reset icon appears
6. Click ↺ — the value resets to "Manager AI" and the badge disappears
7. Switch to "Tool Descriptions" tab — verify the amber warning banner appears
8. Switch to "Response Messages" tab — verify 1 entry (`save_task_plan`)
9. Edit the response message, save, then use "Ripristina tutti i valori predefiniti" → confirm reset → all badges disappear

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.js \
        frontend/src/pages/SettingsPage.jsx \
        frontend/src/App.jsx
git commit -m "feat: add Settings page with tab UI for MCP text configuration"
```
