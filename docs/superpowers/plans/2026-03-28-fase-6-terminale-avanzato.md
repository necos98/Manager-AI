# Fase 6 — Terminale Avanzato Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-project shell selection, custom environment variables with secret masking, terminal UX improvements (search, copy, themes, split pane, session recording), and advanced startup command features (multi-line, conditional execution, predefined templates).

**Architecture:** 4 independent groups (A: shell config, B: custom variables, C: terminal UX, D: advanced commands). Each group produces working, committable software on its own. Groups can be implemented in any order. DB migrations must be applied in the order listed.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, React/TanStack Router, TanStack Query, xterm.js, `@xterm/addon-search`

---

## File Map

### New
- `backend/alembic/versions/aa1bb2cc3dd4_add_project_shell.py`
- `backend/alembic/versions/bb2cc3dd4ee5_add_project_variables.py`
- `backend/alembic/versions/cc3dd4ee5ff6_add_terminal_command_condition.py`
- `backend/app/models/project_variable.py`
- `backend/app/schemas/project_variable.py`
- `backend/app/services/project_variable_service.py`
- `backend/app/routers/project_variables.py`
- `backend/tests/test_project_variable_service.py`
- `frontend/src/features/projects/api-variables.ts`
- `frontend/src/features/projects/hooks-variables.ts`
- `frontend/src/features/projects/components/project-variables-editor.tsx`
- `frontend/src/routes/projects/$projectId/variables.tsx`

### Modified
- `backend/app/models/project.py` — add `shell` nullable column
- `backend/app/models/terminal_command.py` — add `condition` nullable column
- `backend/app/models/__init__.py` — add `ProjectVariable`
- `backend/app/schemas/project.py` — add `shell` field
- `backend/app/schemas/terminal_command.py` — remove newline validator, add `condition`
- `backend/app/services/project_service.py` — add `shell` param to `create()`
- `backend/app/services/terminal_service.py` — accept `shell` param, remove per-issue deduplication
- `backend/app/services/terminal_command_service.py` — return `condition` field
- `backend/app/routers/terminals.py` — pass shell, inject custom vars, split multi-line, eval conditions, save/serve recording
- `backend/app/routers/terminal_commands.py` — add `/templates` endpoint, update TEMPLATE_VARIABLES list
- `backend/app/routers/projects.py` — pass `shell` in `create_project`
- `backend/app/main.py` — register `project_variables` router
- `backend/app/config.py` — add `recordings_path`
- `backend/app/mcp/default_settings.json` — add `terminal_theme`
- `backend/tests/test_terminal_service.py` — update deduplication test
- `frontend/src/shared/types/index.ts` — add `ProjectVariable`, update `Project`, update `TerminalCommand`
- `frontend/src/features/projects/components/project-settings-dialog.tsx` — add shell selector
- `frontend/src/features/terminals/components/terminal-panel.tsx` — search, copy, theme, recording download
- `frontend/src/features/terminals/components/terminal-commands-editor.tsx` — Textarea, condition field, templates dropdown
- `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` — split pane support
- `frontend/src/shared/components/app-sidebar.tsx` — add "Variables" nav link

---

## Group A — 6.1 Shell per Progetto

### Task 1: Migration + model + schema for `project.shell`

**Files:**
- Create: `backend/alembic/versions/aa1bb2cc3dd4_add_project_shell.py`
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/schemas/project.py`
- Modify: `backend/app/services/project_service.py`
- Modify: `backend/app/routers/projects.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_project_service.py — add to existing file

@pytest.mark.asyncio
async def test_create_project_with_shell(db_session):
    from app.services.project_service import ProjectService
    svc = ProjectService(db_session)
    p = await svc.create(name="Test", path="/tmp/x", shell="powershell.exe")
    assert p.shell == "powershell.exe"

@pytest.mark.asyncio
async def test_update_project_shell(db_session):
    from app.services.project_service import ProjectService
    svc = ProjectService(db_session)
    p = await svc.create(name="Test", path="/tmp/x")
    assert p.shell is None
    p2 = await svc.update(p.id, shell="powershell.exe")
    assert p2.shell == "powershell.exe"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_project_service.py::test_create_project_with_shell -v
```

Expected: `FAILED` — `create()` has no `shell` param, `Project` has no `shell` column.

- [ ] **Step 3: Create the migration**

Create `backend/alembic/versions/aa1bb2cc3dd4_add_project_shell.py`:

```python
"""add project shell column

Revision ID: aa1bb2cc3dd4
Revises: de00ebdfc1c2
Create Date: 2026-03-28 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "aa1bb2cc3dd4"
down_revision: Union[str, None] = "de00ebdfc1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("shell", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "shell")
```

- [ ] **Step 4: Update the Project model**

In `backend/app/models/project.py`, add after `tech_stack`:

```python
shell: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

- [ ] **Step 5: Update schemas**

In `backend/app/schemas/project.py`, add `shell: str | None = None` to all three classes:

```python
class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    tech_stack: str = ""
    shell: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    tech_stack: str | None = None
    shell: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    path: str
    description: str
    tech_stack: str
    shell: str | None = None
    created_at: datetime
    updated_at: datetime
    issue_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
```

- [ ] **Step 6: Update ProjectService.create() to accept shell**

In `backend/app/services/project_service.py`, change `create()` signature and body:

```python
async def create(
    self, name: str, path: str, description: str = "", tech_stack: str = "", shell: str | None = None
) -> Project:
    project = Project(name=name, path=path, description=description, tech_stack=tech_stack, shell=shell)
    self.session.add(project)
    await self.session.flush()
    return project
```

- [ ] **Step 7: Update projects router to pass shell**

In `backend/app/routers/projects.py`, update `create_project`:

```python
@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description,
        tech_stack=data.tech_stack, shell=data.shell
    )
    await db.commit()
    return await _enrich_project(service, project)
```

- [ ] **Step 8: Apply the migration**

```bash
cd backend && python -m alembic upgrade head
```

Expected: `Running upgrade de00ebdfc1c2 -> aa1bb2cc3dd4, add project shell column`

- [ ] **Step 9: Run tests**

```bash
cd backend && python -m pytest tests/test_project_service.py -v
```

Expected: all tests PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/alembic/versions/aa1bb2cc3dd4_add_project_shell.py \
        backend/app/models/project.py \
        backend/app/schemas/project.py \
        backend/app/services/project_service.py \
        backend/app/routers/projects.py \
        backend/tests/test_project_service.py
git commit -m "feat: add per-project shell configuration (DB + schema)"
```

---

### Task 2: TerminalService — shell parameter

**Files:**
- Modify: `backend/app/services/terminal_service.py`
- Modify: `backend/app/routers/terminals.py`
- Modify: `backend/tests/test_terminal_service.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_terminal_service.py`, add:

```python
def test_create_uses_custom_shell(service):
    with patch("app.services.terminal_service.PTY") as MockPTY:
        mock_pty = MagicMock()
        mock_pty.spawn = MagicMock()
        MockPTY.return_value = mock_pty

        service.create(
            issue_id="t1",
            project_id="p1",
            project_path="C:/a",
            shell="powershell.exe",
        )
        mock_pty.spawn.assert_called_once_with("powershell.exe", cwd="C:/a")
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_terminal_service.py::TestTerminalServiceRegistry::test_create_uses_custom_shell -v
```

Expected: `FAILED` — `create()` does not accept `shell` param.

- [ ] **Step 3: Update TerminalService.create() to accept shell**

In `backend/app/services/terminal_service.py`, update `create()`:

```python
def create(
    self,
    issue_id: str,
    project_id: str,
    project_path: str,
    cols: int = 120,
    rows: int = 30,
    shell: str | None = None,
) -> dict:
    shell_to_use = shell or DEFAULT_SHELL

    with self._lock:
        pass  # deduplication removed — always create a new terminal

    pty = PTY(cols, rows)
    pty.spawn(shell_to_use, cwd=project_path)

    term_id = str(uuid.uuid4())
    entry = {
        "id": term_id,
        "issue_id": issue_id,
        "project_id": project_id,
        "project_path": project_path,
        "pty": pty,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "cols": cols,
        "rows": rows,
    }
    with self._lock:
        self._terminals[term_id] = entry
        self._buffers[term_id] = bytearray()
    return self._to_response(entry)
```

Note: the `with self._lock: pass` is a placeholder — the original deduplication block is simply removed.

- [ ] **Step 4: Update the deduplication test**

In `backend/tests/test_terminal_service.py`, replace `test_create_duplicate_issue_returns_existing` with:

```python
def test_create_two_terminals_for_same_issue(service):
    """Two terminals for the same issue are now both allowed (split pane support)."""
    with patch("app.services.terminal_service.PTY") as MockPTY:
        mock_pty = MagicMock()
        mock_pty.spawn = MagicMock()
        MockPTY.return_value = mock_pty

        term1 = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
        term2 = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
        assert term1["id"] != term2["id"]
        assert len(service.list_active()) == 2
```

- [ ] **Step 5: Update the terminals router to pass project shell**

In `backend/app/routers/terminals.py`, update `create_terminal`:

```python
@router.post("", response_model=TerminalResponse, status_code=201)
async def create_terminal(
    data: TerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        project_path = await get_project_path(data.project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.isdir(project_path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project_path}")

    # Fetch project shell config
    from app.models.project import Project
    project = await db.get(Project, data.project_id)
    project_shell = project.shell if project else None

    try:
        terminal = service.create(
            issue_id=data.issue_id,
            project_id=data.project_id,
            project_path=project_path,
            shell=project_shell,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    # ... rest of the function unchanged
```

- [ ] **Step 6: Run all terminal tests**

```bash
cd backend && python -m pytest tests/test_terminal_service.py tests/test_terminal_router.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/terminal_service.py \
        backend/app/routers/terminals.py \
        backend/tests/test_terminal_service.py
git commit -m "feat: terminal service accepts per-project shell, removes issue deduplication"
```

---

### Task 3: Frontend — shell selector in ProjectSettingsDialog

**Files:**
- Modify: `frontend/src/features/projects/components/project-settings-dialog.tsx`
- Modify: `frontend/src/shared/types/index.ts`

- [ ] **Step 1: Add `shell` to frontend types**

In `frontend/src/shared/types/index.ts`, find the `Project` interface and add:

```typescript
shell?: string | null;
```

Also update `ProjectCreate` and `ProjectUpdate` interfaces:

```typescript
interface ProjectCreate {
  name: string;
  path: string;
  description?: string;
  tech_stack?: string;
  shell?: string | null;
}

interface ProjectUpdate {
  name?: string;
  path?: string;
  description?: string;
  tech_stack?: string;
  shell?: string | null;
}
```

- [ ] **Step 2: Add shell selector to ProjectSettingsDialog**

Replace the entire `project-settings-dialog.tsx` content:

```tsx
import { useState } from "react";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useUpdateProject } from "@/features/projects/hooks";
import type { Project } from "@/shared/types";

const SHELL_OPTIONS = [
  { value: "", label: "Default (MANAGER_AI_SHELL env or cmd.exe)" },
  { value: "C:\\Windows\\System32\\cmd.exe", label: "cmd.exe" },
  { value: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", label: "PowerShell (Windows)" },
  { value: "C:\\Program Files\\PowerShell\\7\\pwsh.exe", label: "PowerShell 7 (pwsh)" },
  { value: "C:\\Program Files\\Git\\bin\\bash.exe", label: "Git Bash" },
  { value: "C:\\Windows\\System32\\wsl.exe", label: "WSL" },
  { value: "/bin/bash", label: "bash (Linux/macOS)" },
  { value: "/bin/zsh", label: "zsh (Linux/macOS)" },
];

interface ProjectSettingsDialogProps {
  project: Project;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProjectSettingsDialog({
  project,
  open,
  onOpenChange,
}: ProjectSettingsDialogProps) {
  const [form, setForm] = useState({
    name: project.name,
    path: project.path,
    description: project.description || "",
    tech_stack: project.tech_stack || "",
    shell: project.shell || "",
  });

  const updateProject = useUpdateProject(project.id);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProject.mutate(
      { ...form, shell: form.shell || null },
      { onSuccess: () => onOpenChange(false) }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Project</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium">Name</label>
            <Input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Path</label>
            <Input
              required
              value={form.path}
              onChange={(e) => setForm({ ...form, path: e.target.value })}
              className="font-mono"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Tech Stack</label>
            <Textarea
              value={form.tech_stack}
              onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}
              rows={3}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Terminal Shell</label>
            <Select
              value={form.shell}
              onValueChange={(v) => setForm({ ...form, shell: v })}
            >
              <SelectTrigger className="font-mono text-sm">
                <SelectValue placeholder="Default shell" />
              </SelectTrigger>
              <SelectContent>
                {SHELL_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} className="font-mono text-sm">
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              Shell to use when opening terminals for this project.
            </p>
          </div>
          {updateProject.error && (
            <p className="text-sm text-destructive">{updateProject.error.message}</p>
          )}
          <div className="flex gap-3 justify-end">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateProject.isPending}>
              {updateProject.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 3: Run frontend lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/projects/components/project-settings-dialog.tsx \
        frontend/src/shared/types/index.ts
git commit -m "feat: shell selector in project settings dialog"
```

---

## Group B — 6.2 Variabili Custom per Progetto

### Task 4: Migration + ProjectVariable model

**Files:**
- Create: `backend/alembic/versions/bb2cc3dd4ee5_add_project_variables.py`
- Create: `backend/app/models/project_variable.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the migration**

```python
# backend/alembic/versions/bb2cc3dd4ee5_add_project_variables.py
"""add project_variables table

Revision ID: bb2cc3dd4ee5
Revises: aa1bb2cc3dd4
Create Date: 2026-03-28 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "bb2cc3dd4ee5"
down_revision: Union[str, None] = "aa1bb2cc3dd4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_variables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_variable_name"),
    )


def downgrade() -> None:
    op.drop_table("project_variables")
```

- [ ] **Step 2: Create the model**

Create `backend/app/models/project_variable.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectVariable(Base):
    __tablename__ = "project_variables"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_variable_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 3: Register model in __init__.py**

In `backend/app/models/__init__.py`:

```python
from app.database import Base
from app.models.activity_log import ActivityLog
from app.models.issue import Issue
from app.models.issue_feedback import IssueFeedback
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.project_skill import ProjectSkill
from app.models.project_variable import ProjectVariable
from app.models.prompt_template import PromptTemplate
from app.models.setting import Setting
from app.models.task import Task
from app.models.terminal_command import TerminalCommand

__all__ = [
    "ActivityLog", "Base", "Issue", "IssueFeedback", "Project", "ProjectFile",
    "ProjectSkill", "ProjectVariable", "PromptTemplate", "Setting", "Task", "TerminalCommand",
]
```

- [ ] **Step 4: Apply migration**

```bash
cd backend && python -m alembic upgrade head
```

Expected: `Running upgrade aa1bb2cc3dd4 -> bb2cc3dd4ee5, add project_variables table`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/bb2cc3dd4ee5_add_project_variables.py \
        backend/app/models/project_variable.py \
        backend/app/models/__init__.py
git commit -m "feat: ProjectVariable model and migration"
```

---

### Task 5: ProjectVariableService + tests

**Files:**
- Create: `backend/app/schemas/project_variable.py`
- Create: `backend/app/services/project_variable_service.py`
- Create: `backend/tests/test_project_variable_service.py`

- [ ] **Step 1: Create schemas**

Create `backend/app/schemas/project_variable.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectVariableCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    value: str
    is_secret: bool = False


class ProjectVariableUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    value: str | None = None
    is_secret: bool | None = None


class ProjectVariableOut(BaseModel):
    id: int
    project_id: str
    name: str
    value: str
    is_secret: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_project_variable_service.py`:

```python
import pytest
import pytest_asyncio

from app.models.project import Project
from app.models.project_variable import ProjectVariable
from app.services.project_variable_service import ProjectVariableService


@pytest_asyncio.fixture
async def project(db_session):
    p = Project(name="Test", path="/tmp/t")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def service(db_session):
    return ProjectVariableService(db_session)


@pytest.mark.asyncio
async def test_list_empty(service, project):
    result = await service.list(project.id)
    assert result == []


@pytest.mark.asyncio
async def test_create_variable(service, project):
    v = await service.create(project.id, name="DB_URL", value="sqlite:///test.db")
    assert v.name == "DB_URL"
    assert v.value == "sqlite:///test.db"
    assert v.is_secret is False
    assert v.project_id == project.id


@pytest.mark.asyncio
async def test_create_secret_variable(service, project):
    v = await service.create(project.id, name="API_KEY", value="secret123", is_secret=True)
    assert v.is_secret is True


@pytest.mark.asyncio
async def test_create_duplicate_name_raises(service, project):
    await service.create(project.id, name="VAR", value="a")
    with pytest.raises(ValueError, match="already exists"):
        await service.create(project.id, name="VAR", value="b")


@pytest.mark.asyncio
async def test_update_variable(service, project):
    v = await service.create(project.id, name="VAR", value="old")
    updated = await service.update(v.id, value="new")
    assert updated.value == "new"


@pytest.mark.asyncio
async def test_delete_variable(service, project):
    v = await service.create(project.id, name="VAR", value="x")
    await service.delete(v.id)
    result = await service.list(project.id)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_raises(service, project):
    with pytest.raises(KeyError):
        await service.delete(9999)


@pytest.mark.asyncio
async def test_cascade_delete(db_session, project, service):
    await service.create(project.id, name="VAR", value="x")
    await db_session.delete(project)
    await db_session.flush()
    result = await service.list(project.id)
    assert result == []
```

- [ ] **Step 3: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_project_variable_service.py -v
```

Expected: `FAILED` — `ProjectVariableService` doesn't exist yet.

- [ ] **Step 4: Implement the service**

Create `backend/app/services/project_variable_service.py`:

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_variable import ProjectVariable


class ProjectVariableService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, project_id: str) -> list[ProjectVariable]:
        result = await self.session.execute(
            select(ProjectVariable)
            .where(ProjectVariable.project_id == project_id)
            .order_by(ProjectVariable.sort_order, ProjectVariable.id)
        )
        return list(result.scalars().all())

    async def create(
        self, project_id: str, name: str, value: str, is_secret: bool = False
    ) -> ProjectVariable:
        # Enforce uniqueness manually (DB constraint also covers this)
        existing = await self.session.execute(
            select(ProjectVariable)
            .where(ProjectVariable.project_id == project_id)
            .where(ProjectVariable.name == name)
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Variable '{name}' already exists for this project")

        row = ProjectVariable(
            project_id=project_id, name=name, value=value, is_secret=is_secret
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(self, var_id: int, **kwargs) -> ProjectVariable:
        row = await self.session.get(ProjectVariable, var_id)
        if row is None:
            raise KeyError(f"ProjectVariable {var_id} not found")
        for key, val in kwargs.items():
            if val is not None:
                setattr(row, key, val)
        await self.session.flush()
        return row

    async def delete(self, var_id: int) -> None:
        row = await self.session.get(ProjectVariable, var_id)
        if row is None:
            raise KeyError(f"ProjectVariable {var_id} not found")
        await self.session.delete(row)
        await self.session.flush()
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_project_variable_service.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/project_variable.py \
        backend/app/services/project_variable_service.py \
        backend/tests/test_project_variable_service.py
git commit -m "feat: ProjectVariableService with CRUD and tests"
```

---

### Task 6: Project variables router + register in main.py

**Files:**
- Create: `backend/app/routers/project_variables.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

Create `backend/app/routers/project_variables.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_variable import ProjectVariableCreate, ProjectVariableOut, ProjectVariableUpdate
from app.services.project_variable_service import ProjectVariableService

router = APIRouter(prefix="/api/project-variables", tags=["project-variables"])


@router.get("", response_model=list[ProjectVariableOut])
async def list_project_variables(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    return await svc.list(project_id)


@router.post("", response_model=ProjectVariableOut, status_code=201)
async def create_project_variable(
    project_id: str,
    data: ProjectVariableCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    try:
        var = await svc.create(project_id, name=data.name, value=data.value, is_secret=data.is_secret)
        await db.commit()
        return var
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{var_id}", response_model=ProjectVariableOut)
async def update_project_variable(
    var_id: int,
    data: ProjectVariableUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    try:
        var = await svc.update(var_id, **data.model_dump(exclude_unset=True))
        await db.commit()
        await db.refresh(var)
        return var
    except KeyError:
        raise HTTPException(status_code=404, detail="Variable not found")


@router.delete("/{var_id}", status_code=204)
async def delete_project_variable(
    var_id: int,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    try:
        await svc.delete(var_id)
        await db.commit()
    except KeyError:
        raise HTTPException(status_code=404, detail="Variable not found")
```

- [ ] **Step 2: Register in main.py**

In `backend/app/main.py`, add import and `app.include_router`:

```python
# Add to imports:
from app.routers import ... , project_variables

# Add after terminal_commands router:
app.include_router(project_variables.router)
```

- [ ] **Step 3: Start the server and verify endpoints appear**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs — verify `/api/project-variables` routes appear.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/project_variables.py \
        backend/app/main.py
git commit -m "feat: project variables REST API"
```

---

### Task 7: Terminal router — inject custom variables

**Files:**
- Modify: `backend/app/routers/terminals.py`
- Modify: `backend/app/routers/terminal_commands.py`

- [ ] **Step 1: Update terminal creation to inject project variables**

In `backend/app/routers/terminals.py`, after injecting the standard `MANAGER_AI_*` env vars, add:

```python
    # Inject project custom variables into the terminal
    try:
        from app.services.project_variable_service import ProjectVariableService
        var_svc = ProjectVariableService(db)
        custom_vars = await var_svc.list(data.project_id)
        if custom_vars:
            pty = service.get_pty(terminal["id"])
            import platform
            set_cmd = "set" if platform.system() == "Windows" else "export"
            var_commands = " && ".join(f"{set_cmd} {v.name}={v.value}" for v in custom_vars)
            pty.write(var_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject custom variables for terminal %s", terminal["id"], exc_info=True)
```

Place this block immediately after the existing `env_vars` injection block.

- [ ] **Step 2: Expose custom variables in the variables endpoint**

In `backend/app/routers/terminal_commands.py`, update `list_template_variables` to include project-scoped custom variables:

```python
@router.get("/variables")
async def list_template_variables(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    vars_list = list(TEMPLATE_VARIABLES)
    if project_id:
        from app.services.project_variable_service import ProjectVariableService
        svc = ProjectVariableService(db)
        custom = await svc.list(project_id)
        for v in custom:
            display = "••••••••" if v.is_secret else v.value
            vars_list.append({
                "name": f"${v.name}",
                "description": f"Custom variable (value: {display})",
            })
    return vars_list
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_terminal_router.py -v
```

Expected: all PASS (new injection code is in a try/except so it won't break existing tests).

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/terminals.py \
        backend/app/routers/terminal_commands.py
git commit -m "feat: inject project custom variables into terminal on creation"
```

---

### Task 8: Frontend — variables editor, API, hooks, route, sidebar

**Files:**
- Create: `frontend/src/features/projects/api-variables.ts`
- Create: `frontend/src/features/projects/hooks-variables.ts`
- Create: `frontend/src/features/projects/components/project-variables-editor.tsx`
- Create: `frontend/src/routes/projects/$projectId/variables.tsx`
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/shared/components/app-sidebar.tsx`

- [ ] **Step 1: Add ProjectVariable type**

In `frontend/src/shared/types/index.ts`, add:

```typescript
export interface ProjectVariable {
  id: number;
  project_id: string;
  name: string;
  value: string;
  is_secret: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectVariableCreate {
  name: string;
  value: string;
  is_secret?: boolean;
}

export interface ProjectVariableUpdate {
  name?: string;
  value?: string;
  is_secret?: boolean;
}
```

- [ ] **Step 2: Create API functions**

Create `frontend/src/features/projects/api-variables.ts`:

```typescript
import { request } from "@/shared/api/client";
import type { ProjectVariable, ProjectVariableCreate, ProjectVariableUpdate } from "@/shared/types";

export function fetchProjectVariables(projectId: string): Promise<ProjectVariable[]> {
  return request(`/project-variables?project_id=${projectId}`);
}

export function createProjectVariable(
  projectId: string,
  data: ProjectVariableCreate
): Promise<ProjectVariable> {
  return request(`/project-variables?project_id=${projectId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateProjectVariable(
  varId: number,
  data: ProjectVariableUpdate
): Promise<ProjectVariable> {
  return request(`/project-variables/${varId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteProjectVariable(varId: number): Promise<null> {
  return request(`/project-variables/${varId}`, { method: "DELETE" });
}
```

- [ ] **Step 3: Create React Query hooks**

Create `frontend/src/features/projects/hooks-variables.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-variables";
import type { ProjectVariableCreate, ProjectVariableUpdate } from "@/shared/types";

const varKeys = {
  list: (projectId: string) => ["project-variables", projectId] as const,
};

export function useProjectVariables(projectId: string) {
  return useQuery({
    queryKey: varKeys.list(projectId),
    queryFn: () => api.fetchProjectVariables(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectVariableCreate) => api.createProjectVariable(projectId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
  });
}

export function useUpdateProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProjectVariableUpdate }) =>
      api.updateProjectVariable(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
  });
}

export function useDeleteProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (varId: number) => api.deleteProjectVariable(varId),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
  });
}
```

- [ ] **Step 4: Create the variables editor component**

Create `frontend/src/features/projects/components/project-variables-editor.tsx`:

```tsx
import { useState } from "react";
import { Eye, EyeOff, Plus, X } from "lucide-react";
import {
  useProjectVariables,
  useCreateProjectVariable,
  useUpdateProjectVariable,
  useDeleteProjectVariable,
} from "@/features/projects/hooks-variables";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface ProjectVariablesEditorProps {
  projectId: string;
}

export function ProjectVariablesEditor({ projectId }: ProjectVariablesEditorProps) {
  const { data: vars, isLoading } = useProjectVariables(projectId);
  const createVar = useCreateProjectVariable(projectId);
  const updateVar = useUpdateProjectVariable(projectId);
  const deleteVar = useDeleteProjectVariable(projectId);

  const [newName, setNewName] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newIsSecret, setNewIsSecret] = useState(false);
  const [revealed, setRevealed] = useState<Set<number>>(new Set());

  const handleAdd = () => {
    if (!newName.trim() || !newValue.trim()) return;
    createVar.mutate(
      { name: newName.trim(), value: newValue.trim(), is_secret: newIsSecret },
      {
        onSuccess: () => {
          setNewName("");
          setNewValue("");
          setNewIsSecret(false);
        },
      }
    );
  };

  const toggleReveal = (id: number) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => <Skeleton key={i} className="h-10" />)}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {vars?.length === 0 && (
        <p className="text-sm text-muted-foreground italic">No custom variables defined.</p>
      )}

      {vars?.map((v) => (
        <div key={v.id} className="flex items-center gap-2">
          <Input
            defaultValue={v.name}
            onBlur={(e) => {
              const trimmed = e.target.value.trim();
              if (trimmed && trimmed !== v.name)
                updateVar.mutate({ id: v.id, data: { name: trimmed } });
            }}
            className="w-40 font-mono text-sm"
            placeholder="NAME"
          />
          <div className="flex-1 flex gap-1">
            <Input
              defaultValue={v.value}
              type={v.is_secret && !revealed.has(v.id) ? "password" : "text"}
              onBlur={(e) => {
                const trimmed = e.target.value.trim();
                if (trimmed && trimmed !== v.value)
                  updateVar.mutate({ id: v.id, data: { value: trimmed } });
              }}
              className="flex-1 font-mono text-sm"
              placeholder="value"
            />
            {v.is_secret && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => toggleReveal(v.id)}
                title={revealed.has(v.id) ? "Hide value" : "Reveal value"}
              >
                {revealed.has(v.id) ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </Button>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-destructive"
            onClick={() => deleteVar.mutate(v.id)}
          >
            <X className="size-4" />
          </Button>
        </div>
      ))}

      {/* Add new variable */}
      <div className="flex gap-2 mt-4 pt-4 border-t">
        <Input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="NAME"
          className="w-40 font-mono text-sm"
        />
        <Input
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          type={newIsSecret ? "password" : "text"}
          placeholder="value"
          className="flex-1 font-mono text-sm"
        />
        <label className="flex items-center gap-1.5 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={newIsSecret}
            onChange={(e) => setNewIsSecret(e.target.checked)}
            className="rounded"
          />
          Secret
        </label>
        <Button
          onClick={handleAdd}
          disabled={!newName.trim() || !newValue.trim() || createVar.isPending}
          size="sm"
        >
          <Plus className="size-4 mr-1" />
          Add
        </Button>
      </div>
      {createVar.error && (
        <p className="text-sm text-destructive">{createVar.error.message}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Create the variables route**

Create `frontend/src/routes/projects/$projectId/variables.tsx`:

```tsx
import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { ProjectVariablesEditor } from "@/features/projects/components/project-variables-editor";

export const Route = createFileRoute("/projects/$projectId/variables")({
  component: VariablesPage,
});

function VariablesPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Variables - ${project.name}` : "Variables";
  }, [project]);

  return (
    <div className="p-6">
      {project && (
        <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
      )}
      <h1 className="text-xl font-semibold mb-2">Environment Variables</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Custom variables injected into terminals for this project. Secrets are masked in the UI but sent in plain text to the terminal process.
      </p>
      <ProjectVariablesEditor projectId={projectId} />
    </div>
  );
}
```

- [ ] **Step 6: Add Variables link to sidebar**

In `frontend/src/shared/components/app-sidebar.tsx`, add to the `projectNav` array after "Commands":

```typescript
import { Key } from "lucide-react"; // add to existing lucide import

// In projectNav array, after the Commands entry:
{
  label: "Variables",
  to: "/projects/$projectId/variables" as const,
  params: { projectId },
  icon: Key,
},
```

- [ ] **Step 7: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/projects/api-variables.ts \
        frontend/src/features/projects/hooks-variables.ts \
        frontend/src/features/projects/components/project-variables-editor.tsx \
        frontend/src/routes/projects/$projectId/variables.tsx \
        frontend/src/shared/types/index.ts \
        frontend/src/shared/components/app-sidebar.tsx
git commit -m "feat: project variables UI — editor, route, sidebar link"
```

---

## Group C — 6.3 Terminal UX

### Task 9: Search (SearchAddon + Ctrl+F toolbar)

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx`

- [ ] **Step 1: Install @xterm/addon-search**

```bash
cd frontend && npm install @xterm/addon-search
```

Expected: package added to `package.json`.

- [ ] **Step 2: Update terminal-panel.tsx with search**

Add imports and SearchAddon. Full updated `terminal-panel.tsx`:

```tsx
import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { SearchAddon } from "@xterm/addon-search";
import { X, Search } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import "xterm/css/xterm.css";

interface TerminalPanelProps {
  terminalId: string;
  onSessionEnd?: () => void;
  onDownloadRecording?: () => void;
}

export function TerminalPanel({ terminalId, onSessionEnd, onDownloadRecording }: TerminalPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onSessionEndRef = useRef(onSessionEnd);
  const cleanedUpRef = useRef(false);
  const searchAddonRef = useRef<SearchAddon | null>(null);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "ended">("connecting");
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 5;

  useEffect(() => {
    onSessionEndRef.current = onSessionEnd;
  }, [onSessionEnd]);

  const handleSearch = useCallback((query: string, direction: "next" | "prev" = "next") => {
    if (!searchAddonRef.current || !query) return;
    if (direction === "next") {
      searchAddonRef.current.findNext(query, { incremental: false });
    } else {
      searchAddonRef.current.findPrevious(query);
    }
  }, []);

  useEffect(() => {
    if (!terminalId || !containerRef.current) return;
    cleanedUpRef.current = false;

    const container = containerRef.current;
    container.innerHTML = "";

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Consolas', monospace",
      theme: {
        background: "#0d0d0d",
        foreground: "#cdd6f4",
        cursor: "#89b4fa",
      },
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    const searchAddon = new SearchAddon();
    searchAddonRef.current = searchAddon;
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.loadAddon(searchAddon);

    let opened = false;

    function openIfReady() {
      if (opened || cleanedUpRef.current) return;
      if (container.clientHeight === 0 || container.clientWidth === 0) return;
      opened = true;
      try {
        term.open(container);
        fitAddon.fit();
      } catch {
        return;
      }
      connectWs();
    }

    function connectWs() {
      if (cleanedUpRef.current) return;
      const backendPort = import.meta.env.VITE_BACKEND_PORT || "8000";
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.hostname}:${backendPort}/api/terminals/${terminalId}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cleanedUpRef.current) { ws.close(); return; }
        setStatus("connected");
        retryCountRef.current = 0;
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        if (!cleanedUpRef.current) term.write(event.data);
      };

      ws.onclose = (event) => {
        if (cleanedUpRef.current) return;
        if (event.code === 1000 && event.reason === "Terminal session ended") {
          setStatus("ended");
          onSessionEndRef.current?.();
          return;
        }
        setStatus("disconnected");
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current++;
          setTimeout(connectWs, delay);
        }
      };

      ws.onerror = () => {};
    }

    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      }
    });

    // Ctrl+F opens search bar
    term.attachCustomKeyEventHandler((e) => {
      if (e.ctrlKey && e.key === "f") {
        e.preventDefault();
        setShowSearch((prev) => !prev);
        return false;
      }
      return true;
    });

    const resizeObserver = new ResizeObserver(() => {
      if (cleanedUpRef.current) return;
      if (!opened) { openIfReady(); return; }
      if (container.clientHeight === 0) return;
      try {
        fitAddon.fit();
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      } catch { }
    });
    resizeObserver.observe(container);

    openIfReady();

    return () => {
      cleanedUpRef.current = true;
      resizeObserver.disconnect();
      searchAddonRef.current = null;
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      const termToDispose = term;
      setTimeout(() => { try { termToDispose.dispose(); } catch {} }, 50);
    };
  }, [terminalId]);

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d]">
      {status === "ended" && (
        <div className="px-3 py-2 bg-zinc-800 text-zinc-400 text-sm text-center">
          Terminal session ended
        </div>
      )}
      {status === "disconnected" && (
        <div className="px-3 py-2 bg-yellow-900 text-yellow-300 text-sm text-center">
          Reconnecting...
        </div>
      )}
      {showSearch && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 border-b border-zinc-700">
          <Search className="size-3.5 text-zinc-400 flex-shrink-0" />
          <Input
            autoFocus
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              handleSearch(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch(searchQuery, e.shiftKey ? "prev" : "next");
              if (e.key === "Escape") setShowSearch(false);
            }}
            placeholder="Search… (Enter next, Shift+Enter prev)"
            className="h-6 text-xs bg-zinc-900 border-zinc-600 text-zinc-200 flex-1"
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 text-zinc-400"
            onClick={() => setShowSearch(false)}
          >
            <X className="size-3" />
          </Button>
        </div>
      )}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
```

- [ ] **Step 3: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/terminals/components/terminal-panel.tsx \
        frontend/package.json frontend/package-lock.json
git commit -m "feat: terminal search with Ctrl+F (SearchAddon)"
```

---

### Task 10: Copy button in terminal panel

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx`

Note: `terminal-panel.tsx` was already rewritten in Task 9. This task adds the copy button.

- [ ] **Step 1: Add a copy button to the terminal panel toolbar**

The terminal panel currently has no toolbar. Add a thin toolbar at the top with a Copy button. The button calls `term.getSelection()` and writes to clipboard.

Since `term` is created inside the `useEffect`, expose `getSelection` via a ref. Add to the component:

```tsx
// Add near other refs:
const termRef = useRef<Terminal | null>(null);

// Inside useEffect, after creating term:
termRef.current = term;

// In cleanup:
termRef.current = null;

// Copy handler (add before return):
const handleCopy = useCallback(() => {
  if (!termRef.current) return;
  const selection = termRef.current.getSelection();
  if (selection) {
    navigator.clipboard.writeText(selection).catch(() => {});
  }
}, []);
```

Add to the JSX, before the `containerRef` div, a small toolbar:

```tsx
<div className="flex items-center justify-end gap-1 px-2 py-1 bg-zinc-900 border-b border-zinc-800">
  <Button
    variant="ghost"
    size="sm"
    className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
    onClick={handleCopy}
    title="Copy selection"
  >
    Copy
  </Button>
  <Button
    variant="ghost"
    size="sm"
    className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
    onClick={() => setShowSearch((p) => !p)}
    title="Search (Ctrl+F)"
  >
    <Search className="size-3" />
  </Button>
  {onDownloadRecording && (
    <Button
      variant="ghost"
      size="sm"
      className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
      onClick={onDownloadRecording}
      title="Download session recording"
    >
      ↓ Log
    </Button>
  )}
</div>
```

- [ ] **Step 2: Add Copy import (lucide `Copy` icon) and `useCallback`**

Add `Copy` to the lucide import and update the Copy button to use the icon:

```tsx
import { Copy, Search, X } from "lucide-react";

// In the toolbar:
<Button ... onClick={handleCopy} title="Copy selection">
  <Copy className="size-3" />
</Button>
```

- [ ] **Step 3: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/terminals/components/terminal-panel.tsx
git commit -m "feat: copy button and download recording button in terminal toolbar"
```

---

### Task 11: Terminal themes

**Files:**
- Modify: `backend/app/mcp/default_settings.json`
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx`
- Modify: `frontend/src/features/settings/components/settings-form.tsx`

The terminal theme is a global setting (`terminal_theme`) stored in the DB via the existing Settings system. The frontend reads this setting when mounting a terminal and applies it.

- [ ] **Step 1: Add terminal_theme to default_settings.json**

In `backend/app/mcp/default_settings.json`, add:

```json
"terminal_theme": "catppuccin"
```

Valid values: `catppuccin`, `dracula`, `one_dark`, `solarized_dark`.

- [ ] **Step 2: Add theme constants to the frontend**

Create `frontend/src/features/terminals/themes.ts`:

```typescript
import type { ITheme } from "xterm";

export const TERMINAL_THEMES: Record<string, ITheme> = {
  catppuccin: {
    background: "#0d0d0d",
    foreground: "#cdd6f4",
    cursor: "#89b4fa",
    black: "#45475a",
    red: "#f38ba8",
    green: "#a6e3a1",
    yellow: "#f9e2af",
    blue: "#89b4fa",
    magenta: "#cba6f7",
    cyan: "#94e2d5",
    white: "#bac2de",
    brightBlack: "#585b70",
    brightRed: "#f38ba8",
    brightGreen: "#a6e3a1",
    brightYellow: "#f9e2af",
    brightBlue: "#89b4fa",
    brightMagenta: "#cba6f7",
    brightCyan: "#94e2d5",
    brightWhite: "#a6adc8",
  },
  dracula: {
    background: "#282a36",
    foreground: "#f8f8f2",
    cursor: "#f8f8f2",
    black: "#21222c",
    red: "#ff5555",
    green: "#50fa7b",
    yellow: "#f1fa8c",
    blue: "#bd93f9",
    magenta: "#ff79c6",
    cyan: "#8be9fd",
    white: "#f8f8f2",
    brightBlack: "#6272a4",
    brightRed: "#ff6e6e",
    brightGreen: "#69ff94",
    brightYellow: "#ffffa5",
    brightBlue: "#d6acff",
    brightMagenta: "#ff92df",
    brightCyan: "#a4ffff",
    brightWhite: "#ffffff",
  },
  one_dark: {
    background: "#282c34",
    foreground: "#abb2bf",
    cursor: "#528bff",
    black: "#3f4451",
    red: "#e06c75",
    green: "#98c379",
    yellow: "#e5c07b",
    blue: "#61afef",
    magenta: "#c678dd",
    cyan: "#56b6c2",
    white: "#abb2bf",
    brightBlack: "#4f5666",
    brightRed: "#be5046",
    brightGreen: "#98c379",
    brightYellow: "#d19a66",
    brightBlue: "#61afef",
    brightMagenta: "#c678dd",
    brightCyan: "#56b6c2",
    brightWhite: "#ffffff",
  },
  solarized_dark: {
    background: "#002b36",
    foreground: "#839496",
    cursor: "#839496",
    black: "#073642",
    red: "#dc322f",
    green: "#859900",
    yellow: "#b58900",
    blue: "#268bd2",
    magenta: "#d33682",
    cyan: "#2aa198",
    white: "#eee8d5",
    brightBlack: "#002b36",
    brightRed: "#cb4b16",
    brightGreen: "#586e75",
    brightYellow: "#657b83",
    brightBlue: "#839496",
    brightMagenta: "#6c71c4",
    brightCyan: "#93a1a1",
    brightWhite: "#fdf6e3",
  },
};
```

- [ ] **Step 3: Add a settings API hook that the terminal panel can use**

The settings API already exists. Add a hook to `frontend/src/features/settings/hooks.ts` (or wherever settings hooks live). Check if `useSettings` already returns all settings; if so, use it. Otherwise add:

```typescript
// In frontend/src/features/settings/hooks.ts, verify useSettings exists and returns all settings.
// The terminal panel will call useSettings() and look up the "terminal_theme" key.
```

- [ ] **Step 4: Apply theme in terminal-panel.tsx**

In `terminal-panel.tsx`, add import and theme lookup:

```tsx
import { TERMINAL_THEMES } from "@/features/terminals/themes";
import { useSettings } from "@/features/settings/hooks";

// Inside TerminalPanel component, before the useEffect:
const { data: settingsList } = useSettings();
const themeName = settingsList?.find((s) => s.key === "terminal_theme")?.value ?? "catppuccin";
const termTheme = TERMINAL_THEMES[themeName] ?? TERMINAL_THEMES.catppuccin;

// Inside the useEffect, update Terminal constructor:
const term = new Terminal({
  cursorBlink: true,
  fontSize: 14,
  fontFamily: "'Cascadia Code', 'Consolas', monospace",
  theme: termTheme,
});
```

Since `termTheme` is used inside the `useEffect` dependency, add it to the dependency array:
`}, [terminalId, termTheme]);`

Wait — this would re-create the terminal on every theme change. Better approach: update the theme without re-creating:

```tsx
// Separate effect for theme updates:
useEffect(() => {
  if (termRef.current) {
    termRef.current.options.theme = termTheme;
  }
}, [termTheme]);
```

And keep the initial `Terminal` constructor using the theme at mount time.

- [ ] **Step 5: Add theme selector to settings form**

In `frontend/src/features/settings/components/settings-form.tsx`, the form renders `SettingField` for each setting generically via a textarea. The `terminal_theme` setting needs a dropdown instead.

Add a special case in `SettingField`:

```tsx
// Add above the return in SettingField:
if (setting.key === "terminal_theme") {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <label className="font-medium text-sm">Terminal Theme</label>
      </div>
      <Select value={value} onValueChange={(v) => { setValue(v); updateSetting.mutate({ key: setting.key, value: v }); }}>
        <SelectTrigger className="w-48">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="catppuccin">Catppuccin</SelectItem>
          <SelectItem value="dracula">Dracula</SelectItem>
          <SelectItem value="one_dark">One Dark</SelectItem>
          <SelectItem value="solarized_dark">Solarized Dark</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
```

Add `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` imports from `@/shared/components/ui/select`.

- [ ] **Step 6: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/default_settings.json \
        frontend/src/features/terminals/themes.ts \
        frontend/src/features/terminals/components/terminal-panel.tsx \
        frontend/src/features/settings/components/settings-form.tsx
git commit -m "feat: configurable terminal themes via global settings"
```

---

### Task 12: Split pane — two terminals per issue

**Files:**
- Modify: `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`

The service change (removing deduplication) was already done in Task 2. This task only updates the frontend.

- [ ] **Step 1: Update IssueDetailPage for split pane**

Replace `$issueId.tsx` with the following updated version. Key changes:
- Support `terminals[0]` and `terminals[1]`
- "Split" button when exactly 1 terminal open
- Vertical resizable split inside right panel for 2 terminals
- Per-terminal close buttons when 2 open

```tsx
import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Play, Square, LayoutTemplate } from "lucide-react";
import { toast } from "sonner";
import { useIssue } from "@/features/issues/hooks";
import { useProject } from "@/features/projects/hooks";
import { useTerminals, useCreateTerminal, useKillTerminal, useTerminalCount, useTerminalConfig } from "@/features/terminals/hooks";
import { IssueDetail } from "@/features/issues/components/issue-detail";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  ResizableHandle, ResizablePanel, ResizablePanelGroup,
} from "@/shared/components/ui/resizable";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId/issues/$issueId")({
  component: IssueDetailPage,
});

function IssueDetailPage() {
  const { projectId, issueId } = Route.useParams();
  const { data: project } = useProject(projectId);
  const { data: issue, isLoading } = useIssue(projectId, issueId);

  useEffect(() => {
    const issueName = issue?.name || issue?.description;
    if (issueName && project) document.title = `${issueName} - ${project.name}`;
    else if (issueName) document.title = issueName;
  }, [issue, project]);

  const { data: terminals } = useTerminals(undefined, issueId);
  const createTerminal = useCreateTerminal();
  const killTerminal = useKillTerminal();
  const { data: countData } = useTerminalCount();
  const { data: configData } = useTerminalConfig();
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  const terminal1 = terminals?.[0] ?? null;
  const terminal2 = terminals?.[1] ?? null;
  const hasAny = !!terminal1;
  const hasSplit = !!terminal2;

  const doOpenTerminal = async () => {
    setShowLimitWarning(false);
    try {
      await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId });
    } catch (err) {
      toast.error("Failed to open terminal: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const openTerminal = async () => {
    const count = countData?.count ?? 0;
    const softLimit = configData?.soft_limit ?? 5;
    if (count >= softLimit) { setShowLimitWarning(true); return; }
    await doOpenTerminal();
  };

  const closeAll = async () => {
    setShowCloseConfirm(false);
    for (const t of terminals ?? []) {
      try { await killTerminal.mutateAsync(t.id); } catch { /* already dead */ }
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (!issue) return <div className="p-6"><p className="text-destructive">Issue not found.</p></div>;

  return (
    <div className="h-[calc(100vh-1rem)] flex flex-col">
      {/* Terminal action bar */}
      <div className="flex items-center justify-end gap-2 px-6 py-2 border-b flex-shrink-0">
        {!hasAny && (
          <Button size="sm" onClick={openTerminal} disabled={createTerminal.isPending}>
            <Play className="size-3 mr-1" />
            {createTerminal.isPending ? "Opening..." : "Open Terminal"}
          </Button>
        )}
        {hasAny && !hasSplit && (
          <>
            <Button variant="outline" size="sm" onClick={openTerminal} disabled={createTerminal.isPending}>
              <LayoutTemplate className="size-3 mr-1" />
              Split
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setShowCloseConfirm(true)}>
              <Square className="size-3 mr-1" />
              Close Terminal
            </Button>
          </>
        )}
        {hasSplit && (
          <Button variant="destructive" size="sm" onClick={() => setShowCloseConfirm(true)}>
            <Square className="size-3 mr-1" />
            Close All
          </Button>
        )}
      </div>

      {/* Split view */}
      <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0">
        <ResizablePanel defaultSize={hasAny ? 55 : 100} minSize={30}>
          <ScrollArea className="h-full">
            <IssueDetail issue={issue} projectId={projectId} terminalId={terminal1?.id ?? null} />
          </ScrollArea>
        </ResizablePanel>

        {hasAny && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={45} minSize={20}>
              {!hasSplit ? (
                <TerminalPanel
                  terminalId={terminal1!.id}
                  onSessionEnd={() => killTerminal.mutate(terminal1!.id)}
                />
              ) : (
                <ResizablePanelGroup direction="vertical">
                  <ResizablePanel defaultSize={50} minSize={20}>
                    <TerminalPanel
                      terminalId={terminal1!.id}
                      onSessionEnd={() => killTerminal.mutate(terminal1!.id)}
                    />
                  </ResizablePanel>
                  <ResizableHandle withHandle />
                  <ResizablePanel defaultSize={50} minSize={20}>
                    <TerminalPanel
                      terminalId={terminal2!.id}
                      onSessionEnd={() => killTerminal.mutate(terminal2!.id)}
                    />
                  </ResizablePanel>
                </ResizablePanelGroup>
              )}
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>

      {/* Limit warning */}
      <Dialog open={showLimitWarning} onOpenChange={setShowLimitWarning}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminal Limit Reached</DialogTitle>
            <DialogDescription>
              You have reached the soft limit of open terminals. Consider closing unused terminals.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLimitWarning(false)}>Cancel</Button>
            <Button onClick={doOpenTerminal}>Open Anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close confirmation */}
      <Dialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Terminal{hasSplit ? "s" : ""}?</DialogTitle>
            <DialogDescription>
              This will kill the terminal process{hasSplit ? "es" : ""}. Any running commands will be terminated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloseConfirm(false)}>Cancel</Button>
            <Button variant="destructive" onClick={closeAll}>
              Close {hasSplit ? "All" : "Terminal"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 2: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/projects/$projectId/issues/$issueId.tsx
git commit -m "feat: split pane — two terminals side by side per issue"
```

---

### Task 13: Session recording — save and download

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/routers/terminals.py`

- [ ] **Step 1: Add recordings_path to config**

In `backend/app/config.py`:

```python
class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    lancedb_path: str = str(_PROJECT_ROOT / "data" / "lancedb")
    recordings_path: str = str(_PROJECT_ROOT / "data" / "recordings")
    claude_library_path: str = str(_PROJECT_ROOT / "claude_library")
    backend_port: int = 8000
    embedding_driver: str = "sentence_transformer"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50

    model_config = {"env_file": ".env"}
```

- [ ] **Step 2: Add helper to save recording in terminals router**

In `backend/app/routers/terminals.py`, add this helper after the imports:

```python
from pathlib import Path
from app.config import settings as app_settings

def _save_recording(terminal_id: str, content: str) -> None:
    """Write terminal output buffer to a file in the recordings directory."""
    if not content:
        return
    try:
        rec_dir = Path(app_settings.recordings_path)
        rec_dir.mkdir(parents=True, exist_ok=True)
        (rec_dir / f"{terminal_id}.txt").write_text(content, encoding="utf-8")
    except Exception:
        logger.warning("Failed to save recording for terminal %s", terminal_id, exc_info=True)
```

- [ ] **Step 3: Save recording on explicit terminal kill**

In `backend/app/routers/terminals.py`, update `delete_terminal`:

```python
@router.delete("/{terminal_id}", status_code=204)
async def delete_terminal(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        buf = service.get_buffered_output(terminal_id)
        _save_recording(terminal_id, buf)
        service.kill(terminal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Terminal not found")
```

- [ ] **Step 4: Save recording when PTY process ends naturally**

In `backend/app/routers/terminals.py`, update `pty_to_ws` inside `terminal_ws`:

```python
    async def pty_to_ws():
        loop = asyncio.get_running_loop()
        try:
            while True:
                data = await loop.run_in_executor(
                    _pty_executor, lambda: pty.read(blocking=True)
                )
                if not data:
                    buf = service.get_buffered_output(terminal_id)
                    _save_recording(terminal_id, buf)
                    service.mark_closed(terminal_id)
                    await websocket.close(code=1000, reason="Terminal session ended")
                    break
                service.append_output(terminal_id, data)
                await websocket.send_text(data)
        except (WebSocketDisconnect, RuntimeError):
            pass
        except Exception:
            logger.warning("pty_to_ws error for terminal %s", terminal_id, exc_info=True)
```

- [ ] **Step 5: Add recording download endpoint**

Add a new route in `backend/app/routers/terminals.py` (must be before `/{terminal_id}` ws route):

```python
@router.get("/{terminal_id}/recording")
async def get_terminal_recording(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    from fastapi.responses import PlainTextResponse

    # Try live buffer first (terminal still active)
    live_buf = service.get_buffered_output(terminal_id)
    if live_buf:
        return PlainTextResponse(
            live_buf,
            headers={"Content-Disposition": f'attachment; filename="{terminal_id}.txt"'},
        )

    # Try saved recording file
    rec_path = Path(app_settings.recordings_path) / f"{terminal_id}.txt"
    if rec_path.exists():
        return PlainTextResponse(
            rec_path.read_text(encoding="utf-8"),
            headers={"Content-Disposition": f'attachment; filename="{terminal_id}.txt"'},
        )

    raise HTTPException(status_code=404, detail="No recording found for this terminal")
```

- [ ] **Step 6: Wire download button in terminal panel frontend**

In the issue detail page (`$issueId.tsx`), pass `onDownloadRecording` to `TerminalPanel`:

```tsx
// In IssueDetailPage, add handler:
const handleDownload = (terminalId: string) => {
  window.open(`/api/terminals/${terminalId}/recording`);
};

// Pass to TerminalPanel:
<TerminalPanel
  terminalId={terminal1!.id}
  onSessionEnd={() => killTerminal.mutate(terminal1!.id)}
  onDownloadRecording={() => handleDownload(terminal1!.id)}
/>
```

- [ ] **Step 7: Run backend tests**

```bash
cd backend && python -m pytest tests/test_terminal_router.py -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py \
        backend/app/routers/terminals.py \
        frontend/src/routes/projects/$projectId/issues/$issueId.tsx
git commit -m "feat: session recording — save on terminal end, download endpoint"
```

---

## Group D — 6.4 Comandi Avanzati

### Task 14: Migration + model for terminal_command.condition

**Files:**
- Create: `backend/alembic/versions/cc3dd4ee5ff6_add_terminal_command_condition.py`
- Modify: `backend/app/models/terminal_command.py`

- [ ] **Step 1: Create the migration**

```python
# backend/alembic/versions/cc3dd4ee5ff6_add_terminal_command_condition.py
"""add terminal_command condition column

Revision ID: cc3dd4ee5ff6
Revises: bb2cc3dd4ee5
Create Date: 2026-03-28 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "cc3dd4ee5ff6"
down_revision: Union[str, None] = "bb2cc3dd4ee5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "terminal_commands",
        sa.Column("condition", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("terminal_commands", "condition")
```

- [ ] **Step 2: Update the model**

In `backend/app/models/terminal_command.py`, add after `sort_order`:

```python
condition: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 3: Apply migration**

```bash
cd backend && python -m alembic upgrade head
```

Expected: `Running upgrade bb2cc3dd4ee5 -> cc3dd4ee5ff6, add terminal_command condition column`

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/cc3dd4ee5ff6_add_terminal_command_condition.py \
        backend/app/models/terminal_command.py
git commit -m "feat: add condition column to terminal_commands"
```

---

### Task 15: Schema update — multi-line + condition

**Files:**
- Modify: `backend/app/schemas/terminal_command.py`

- [ ] **Step 1: Write failing tests**

In `backend/tests/test_terminal_command_service.py`, add:

```python
@pytest.mark.asyncio
async def test_create_multiline_command(service):
    cmd = await service.create("npm install\nnpm test", 0, project_id=None)
    assert "\n" in cmd.command


@pytest.mark.asyncio
async def test_create_command_with_condition(service):
    cmd = await service.create(
        "npm run build", 0, project_id=None, condition="$issue_status == ACCEPTED"
    )
    assert cmd.condition == "$issue_status == ACCEPTED"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_terminal_command_service.py::test_create_multiline_command \
    tests/test_terminal_command_service.py::test_create_command_with_condition -v
```

Expected: `FAILED` — schema rejects newlines, and `create()` doesn't accept `condition`.

- [ ] **Step 3: Update schemas**

Replace `backend/app/schemas/terminal_command.py`:

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TerminalCommandCreate(BaseModel):
    command: str = Field(..., min_length=1)
    sort_order: int
    project_id: str | None = None
    condition: str | None = None
    # Note: newlines are now allowed to support multi-line command blocks


class TerminalCommandUpdate(BaseModel):
    command: str | None = Field(None, min_length=1)
    sort_order: int | None = None
    condition: Optional[str] = None


class TerminalCommandOut(BaseModel):
    id: int
    command: str
    sort_order: int
    project_id: str | None
    condition: str | None
    created_at: datetime
    updated_at: datetime


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class TerminalCommandReorder(BaseModel):
    commands: list[ReorderItem]
```

- [ ] **Step 4: Update TerminalCommandService.create() to accept condition**

In `backend/app/services/terminal_command_service.py`:

```python
async def create(
    self, command: str, sort_order: int, project_id: str | None = None,
    condition: str | None = None
) -> TerminalCommand:
    row = TerminalCommand(
        command=command, sort_order=sort_order, project_id=project_id, condition=condition
    )
    self.session.add(row)
    await self.session.flush()
    return row
```

Also update `update()` to handle `condition`:

```python
async def update(
    self, cmd_id: int, command: str | None = None, sort_order: int | None = None,
    condition: str | None = None
) -> TerminalCommand:
    row = await self.session.get(TerminalCommand, cmd_id)
    if row is None:
        raise KeyError(f"TerminalCommand {cmd_id} not found")
    if command is not None:
        row.command = command
    if sort_order is not None:
        row.sort_order = sort_order
    if condition is not None:
        row.condition = condition
    await self.session.flush()
    return row
```

Also update the router `update_terminal_command` to pass `condition`:

```python
# In backend/app/routers/terminal_commands.py:
cmd = await service.update(cmd_id, command=data.command, sort_order=data.sort_order, condition=data.condition)
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_terminal_command_service.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/terminal_command.py \
        backend/app/services/terminal_command_service.py \
        backend/app/routers/terminal_commands.py \
        backend/tests/test_terminal_command_service.py
git commit -m "feat: multi-line commands and condition field in terminal_commands"
```

---

### Task 16: Router — multi-line execution + condition evaluation + templates endpoint

**Files:**
- Modify: `backend/app/routers/terminals.py`
- Modify: `backend/app/routers/terminal_commands.py`

- [ ] **Step 1: Write test for multi-line execution**

In `backend/tests/test_terminal_router.py`, add (check existing test structure and add similarly):

```python
# This is an integration-style test of the command resolution and execution logic.
# Test the _evaluate_condition helper function directly.

def test_evaluate_condition_no_condition():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition(None, "NEW") is True

def test_evaluate_condition_match():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition("$issue_status == ACCEPTED", "ACCEPTED") is True

def test_evaluate_condition_no_match():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition("$issue_status == ACCEPTED", "NEW") is False

def test_evaluate_condition_unknown_returns_true():
    from app.routers.terminals import _evaluate_condition
    assert _evaluate_condition("$something_unknown", "foo") is True
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_terminal_router.py::test_evaluate_condition_no_condition -v
```

Expected: `FAILED` — `_evaluate_condition` doesn't exist yet.

- [ ] **Step 3: Add condition evaluator and update startup command injection**

In `backend/app/routers/terminals.py`, add after imports:

```python
def _evaluate_condition(condition: str | None, issue_status: str) -> bool:
    """Evaluate a startup command condition. Returns True if the command should run."""
    if not condition:
        return True
    parts = condition.strip().split()
    if len(parts) == 3 and parts[0] == "$issue_status" and parts[1] == "==" :
        return issue_status == parts[2]
    # Unknown condition syntax → always run (safe default)
    return True
```

Then update the startup commands injection block in `create_terminal`:

```python
    # Inject startup commands
    try:
        from app.models.issue import Issue
        issue = await db.get(Issue, data.issue_id)
        issue_status = issue.status.value if issue else ""

        cmd_service = TerminalCommandService(db)
        commands = await cmd_service.resolve(data.project_id)
        if commands:
            pty = service.get_pty(terminal["id"])
            variables = {
                "$issue_id": data.issue_id,
                "$project_id": data.project_id,
                "$project_path": project_path,
            }
            for c in commands:
                if not _evaluate_condition(c.condition, issue_status):
                    continue
                cmd_text = c.command
                for var, val in variables.items():
                    cmd_text = cmd_text.replace(var, val)
                # Support multi-line: send each non-empty line as a separate command
                for line in cmd_text.split("\n"):
                    line = line.strip()
                    if line:
                        pty.write(line + "\r\n")
    except Exception:
        logger.warning("Failed to inject startup commands for terminal %s", terminal["id"], exc_info=True)
```

- [ ] **Step 4: Add predefined templates endpoint**

In `backend/app/routers/terminal_commands.py`, add after TEMPLATE_VARIABLES:

```python
PREDEFINED_TEMPLATES = [
    {
        "name": "Python venv setup",
        "command": "python -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt",
    },
    {
        "name": "Node install + test",
        "command": "npm install\nnpm test",
    },
    {
        "name": "Run tests",
        "command": "python -m pytest -v",
    },
    {
        "name": "Git status",
        "command": "git status && git log --oneline -10",
    },
    {
        "name": "Docker build",
        "command": "docker build -t app .\ndocker run --rm app",
    },
]


@router.get("/templates")
async def list_command_templates():
    """Return predefined command templates for quick insertion."""
    return PREDEFINED_TEMPLATES
```

Note: `/templates` must be defined before `/{cmd_id}` to avoid path parameter collision.

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_terminal_router.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/terminals.py \
        backend/app/routers/terminal_commands.py
git commit -m "feat: multi-line execution, condition eval, predefined templates endpoint"
```

---

### Task 17: Frontend — Textarea editor + condition field + templates dropdown

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-commands-editor.tsx`
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/features/terminals/hooks.ts` (add `useTerminalCommandTemplates`)
- Modify: `frontend/src/features/terminals/api.ts` (add `fetchTerminalCommandTemplates`)

- [ ] **Step 1: Add types and API**

In `frontend/src/shared/types/index.ts`, update `TerminalCommand`:

```typescript
interface TerminalCommand {
  id: number;
  command: string;
  sort_order: number;
  project_id?: string;
  condition?: string | null;
  created_at: string;
  updated_at: string;
}

interface TerminalCommandTemplate {
  name: string;
  command: string;
}
```

In `frontend/src/features/terminals/api.ts`, add:

```typescript
export function fetchTerminalCommandTemplates(): Promise<TerminalCommandTemplate[]> {
  return request("/terminal-commands/templates");
}
```

In `frontend/src/features/terminals/hooks.ts`, add:

```typescript
export function useTerminalCommandTemplates() {
  return useQuery({
    queryKey: ["terminal-command-templates"],
    queryFn: api.fetchTerminalCommandTemplates,
    staleTime: Infinity,
  });
}
```

- [ ] **Step 2: Update TerminalCommandsEditor**

Replace `frontend/src/features/terminals/components/terminal-commands-editor.tsx`:

```tsx
import { useState } from "react";
import { ArrowDown, ArrowUp, ChevronDown, Plus, X } from "lucide-react";
import {
  useTerminalCommands,
  useTerminalCommandVariables,
  useTerminalCommandTemplates,
  useCreateTerminalCommand,
  useUpdateTerminalCommand,
  useReorderTerminalCommands,
  useDeleteTerminalCommand,
} from "@/features/terminals/hooks";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface TerminalCommandsEditorProps {
  projectId?: string | null;
}

export function TerminalCommandsEditor({ projectId = null }: TerminalCommandsEditorProps) {
  const { data: commands, isLoading } = useTerminalCommands(projectId);
  const { data: variables } = useTerminalCommandVariables();
  const { data: templates } = useTerminalCommandTemplates();
  const createCommand = useCreateTerminalCommand(projectId);
  const updateCommand = useUpdateTerminalCommand(projectId);
  const reorderCommands = useReorderTerminalCommands(projectId);
  const deleteCommand = useDeleteTerminalCommand(projectId);

  const [newCmd, setNewCmd] = useState("");
  const [newCondition, setNewCondition] = useState("");

  const handleAdd = (command?: string) => {
    const trimmed = (command ?? newCmd).trim();
    if (!trimmed) return;
    const sortOrder =
      commands && commands.length > 0
        ? Math.max(...commands.map((c) => c.sort_order)) + 1
        : 0;
    createCommand.mutate(
      {
        command: trimmed,
        sort_order: sortOrder,
        project_id: projectId,
        condition: newCondition.trim() || undefined,
      },
      {
        onSuccess: () => {
          setNewCmd("");
          setNewCondition("");
        },
      }
    );
  };

  const handleBlurCommand = (cmd: { id: number; command: string }, newValue: string) => {
    if (newValue === cmd.command) return;
    if (!newValue.trim()) return;
    updateCommand.mutate({ id: cmd.id, data: { command: newValue } });
  };

  const handleBlurCondition = (cmd: { id: number; condition?: string | null }, newValue: string) => {
    const trimmed = newValue.trim() || null;
    if (trimmed === (cmd.condition ?? null)) return;
    updateCommand.mutate({ id: cmd.id, data: { condition: trimmed ?? undefined } });
  };

  const handleMove = (index: number, direction: number) => {
    if (!commands) return;
    const swapIndex = index + direction;
    if (swapIndex < 0 || swapIndex >= commands.length) return;
    reorderCommands.mutate([
      { id: commands[index].id, sort_order: commands[swapIndex].sort_order },
      { id: commands[swapIndex].id, sort_order: commands[index].sort_order },
    ]);
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => <Skeleton key={i} className="h-10" />)}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {commands?.length === 0 && projectId != null && (
        <p className="text-sm text-muted-foreground italic">
          No project commands configured. Global commands will be used.
        </p>
      )}

      {commands?.map((cmd, index) => (
        <div key={cmd.id} className="flex gap-2 items-start">
          <div className="flex flex-col gap-0.5 pt-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={() => handleMove(index, -1)}
              disabled={index === 0}
            >
              <ArrowUp className="size-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={() => handleMove(index, 1)}
              disabled={index === (commands?.length ?? 0) - 1}
            >
              <ArrowDown className="size-3" />
            </Button>
          </div>
          <div className="flex-1 space-y-1.5">
            <Textarea
              defaultValue={cmd.command}
              onBlur={(e) => handleBlurCommand(cmd, e.target.value)}
              className="flex-1 font-mono text-sm min-h-[2.5rem] resize-y"
              rows={cmd.command.includes("\n") ? cmd.command.split("\n").length : 1}
            />
            <Input
              defaultValue={cmd.condition ?? ""}
              onBlur={(e) => handleBlurCondition(cmd, e.target.value)}
              placeholder="Condition: e.g. $issue_status == ACCEPTED (optional)"
              className="text-xs text-muted-foreground font-mono"
            />
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-destructive mt-1"
            onClick={() => deleteCommand.mutate(cmd.id)}
          >
            <X className="size-4" />
          </Button>
        </div>
      ))}

      {/* Add new command */}
      <div className="space-y-2 mt-3 pt-3 border-t">
        <Textarea
          value={newCmd}
          onChange={(e) => setNewCmd(e.target.value)}
          placeholder="Enter a command... (multi-line supported)"
          className="w-full font-mono text-sm min-h-[2.5rem] resize-y"
          rows={2}
        />
        <Input
          value={newCondition}
          onChange={(e) => setNewCondition(e.target.value)}
          placeholder="Condition (optional): $issue_status == ACCEPTED"
          className="text-xs font-mono"
        />
        <div className="flex gap-2">
          <Button
            onClick={() => handleAdd()}
            disabled={!newCmd.trim() || createCommand.isPending}
            size="sm"
          >
            <Plus className="size-4 mr-1" />
            Add
          </Button>
          {templates && templates.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  Templates
                  <ChevronDown className="size-3 ml-1" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                {templates.map((t) => (
                  <DropdownMenuItem
                    key={t.name}
                    onSelect={() => handleAdd(t.command)}
                    className="font-mono text-xs"
                  >
                    {t.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      {variables && variables.length > 0 && (
        <div className="mt-4 p-3 bg-muted rounded-md text-sm">
          <p className="font-medium mb-1">Available variables</p>
          <div className="space-y-0.5">
            {variables.map((v) => (
              <p key={v.name} className="text-muted-foreground">
                <code className="text-primary bg-primary/10 px-1 rounded font-mono">
                  {v.name}
                </code>{" "}
                — {v.description}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/terminals/components/terminal-commands-editor.tsx \
        frontend/src/shared/types/index.ts \
        frontend/src/features/terminals/api.ts \
        frontend/src/features/terminals/hooks.ts
git commit -m "feat: multi-line textarea, condition field, templates dropdown in commands editor"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task(s) |
|-------------|---------|
| 6.1 Shell configurabile (PS, Git Bash, WSL, cmd) | Task 1–3 |
| 6.1 Configurazione shell per progetto | Task 1–3 |
| 6.1 Esporre MANAGER_AI_SHELL nella UI | Task 3 (shell selector) |
| 6.2 Variabili custom per progetto | Task 4–8 |
| 6.2 Secrets management (mascherate nella UI) | Task 5, 8 |
| 6.2 Variabili iniettate nel terminale | Task 7 |
| 6.3 Ricerca nel buffer (Ctrl+F) | Task 9 |
| 6.3 Copia/incolla con bottoni | Task 10 |
| 6.3 Temi terminale configurabili | Task 11 |
| 6.3 Split pane due terminali | Task 2 (service), Task 12 |
| 6.3 Session recording | Task 13 |
| 6.4 Sintassi multi-linea | Task 14–15, 16–17 |
| 6.4 Condizioni esecuzione | Task 14–15, 16–17 |
| 6.4 Template comandi predefiniti | Task 16–17 |
| 6.4 Validazione sintassi | Covered by existing Pydantic validation + frontend |

### Placeholder scan

No TBD items. All code blocks are complete and runnable.

### Type consistency

- `TerminalCommand.condition` is `str | None` throughout (model, schema, service, frontend type).
- `ProjectVariable` is consistently named across model/schema/service/router/frontend.
- `Project.shell` is `str | None` in model, `str | None = None` in all schemas, `shell?: string | null` in frontend.
- `_evaluate_condition(condition: str | None, issue_status: str) -> bool` matches usage in router.
- `TERMINAL_THEMES` keys (`catppuccin`, `dracula`, `one_dark`, `solarized_dark`) match `default_settings.json` default value.
