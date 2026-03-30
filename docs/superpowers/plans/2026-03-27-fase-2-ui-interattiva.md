# Fase 2 — UI Interattiva Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform `IssueDetailPage` from a read-only view to a fully interactive UI where users can trigger state transitions, give feedback on plans, manage tasks, and edit issue fields inline.

**Architecture:** The backend exposes dedicated action endpoints (`/accept`, `/cancel`, `/complete`, `/start-analysis`) that fire hooks where needed, plus a new `IssueFeedback` model for plan feedback. The frontend adds new components (`IssueActions`, `PlanFeedback`, `EditableTaskList`, `InlineEditField`) that are integrated into the existing `IssueDetail` component without breaking its current structure.

**Tech Stack:** Python/FastAPI (backend), React 19 + TanStack Query + TanStack Router (frontend), SQLAlchemy async (ORM), Alembic (migrations), shadcn/ui + Radix UI (components), @dnd-kit/sortable (drag-and-drop), Tailwind CSS

---

## File Map

**Backend — create:**
- `backend/app/models/issue_feedback.py` — IssueFeedback ORM model
- `backend/app/hooks/handlers/start_analysis.py` — hook that spawns Claude to write spec+plan
- `backend/alembic/versions/a1b2c3d4e5f6_add_issue_feedback.py` — migration

**Backend — modify:**
- `backend/app/hooks/registry.py` — add `ISSUE_ANALYSIS_STARTED` to `HookEvent`
- `backend/app/hooks/handlers/__init__.py` — import start_analysis for autodiscovery
- `backend/app/models/__init__.py` — export `IssueFeedback`
- `backend/app/schemas/issue.py` — add `name` to `IssueUpdate`, add `IssueCompleteBody`, `IssueFeedbackCreate`, `IssueFeedbackResponse`
- `backend/app/services/issue_service.py` — add `add_feedback`, `list_feedback`, `start_analysis` methods
- `backend/app/routers/issues.py` — add `/accept`, `/cancel`, `/complete`, `/start-analysis`, `/feedback` (GET+POST) endpoints
- `backend/tests/conftest.py` — import `IssueFeedback` so SQLite test DB creates the table

**Frontend — create:**
- `frontend/src/features/issues/components/issue-actions.tsx` — state-based action buttons with confirmation modals
- `frontend/src/features/issues/components/plan-feedback.tsx` — feedback textarea + history
- `frontend/src/features/issues/components/editable-task-list.tsx` — checkboxes, add/delete, drag-to-reorder
- `frontend/src/features/issues/components/inline-edit-field.tsx` — click-to-edit primitive

**Frontend — modify:**
- `frontend/src/shared/types/index.ts` — add `IssueFeedback`, `IssueFeedbackCreate`, `name` to `IssueUpdate`
- `frontend/src/features/issues/api.ts` — add `acceptIssue`, `cancelIssue`, `completeIssue`, `startAnalysis`, `addFeedback`, `fetchFeedback`
- `frontend/src/features/issues/hooks.ts` — add mutations/queries for new API calls
- `frontend/src/features/issues/components/issue-detail.tsx` — integrate all new components

---

## Task 1: Backend — Hook Event + Start-Analysis Endpoint

**Files:**
- Modify: `backend/app/hooks/registry.py:17-21`
- Create: `backend/app/hooks/handlers/start_analysis.py`
- Modify: `backend/app/hooks/handlers/__init__.py:3`
- Modify: `backend/app/routers/issues.py`

- [ ] **Step 1: Add `ISSUE_ANALYSIS_STARTED` to `HookEvent` enum**

In `backend/app/hooks/registry.py`, change the `HookEvent` class:

```python
class HookEvent(str, Enum):
    ISSUE_COMPLETED = "issue_completed"
    ISSUE_ACCEPTED = "issue_accepted"
    ISSUE_CANCELLED = "issue_cancelled"
    ISSUE_ANALYSIS_STARTED = "issue_analysis_started"
```

- [ ] **Step 2: Write the failing test for start-analysis hook**

Create `backend/tests/test_issue_actions.py`:

```python
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.exceptions import InvalidTransitionError
from app.models.issue import IssueStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test", path="/tmp/test")


@pytest_asyncio.fixture
async def issue(db_session, project):
    service = IssueService(db_session)
    return await service.create(project_id=project.id, description="Test issue")


async def test_start_analysis_fires_hook(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        result = await service.start_analysis(issue.id, project.id)
        assert result.id == issue.id
        assert result.status == IssueStatus.NEW  # state unchanged
        mock_registry.fire.assert_called_once()
        call_args = mock_registry.fire.call_args
        from app.hooks.registry import HookEvent
        assert call_args[0][0] == HookEvent.ISSUE_ANALYSIS_STARTED


async def test_start_analysis_requires_new_status(db_session, issue, project):
    service = IssueService(db_session)
    # Manually move to REASONING
    issue.status = IssueStatus.REASONING
    await db_session.flush()
    with pytest.raises(InvalidTransitionError):
        await service.start_analysis(issue.id, project.id)


async def test_accept_issue_via_service(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        issue.status = IssueStatus.PLANNED
        await db_session.flush()
        result = await service.accept_issue(issue.id, project.id)
        assert result.status == IssueStatus.ACCEPTED


async def test_cancel_issue_via_service(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        result = await service.cancel_issue(issue.id, project.id)
        assert result.status == IssueStatus.CANCELED
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_issue_actions.py -v
```

Expected: `FAILED` — `IssueService` has no `start_analysis` method.

- [ ] **Step 4: Add `start_analysis` method to `IssueService`**

In `backend/app/services/issue_service.py`, add this import at the top (already present):
```python
from app.services.project_service import ProjectService
```

Then add the method after `cancel_issue`:

```python
async def start_analysis(self, issue_id: str, project_id: str) -> Issue:
    issue = await self.get_for_project(issue_id, project_id)
    if issue.status != IssueStatus.NEW:
        raise InvalidTransitionError(
            f"Can only start analysis for issues in New status, got {issue.status.value}"
        )
    project_service = ProjectService(self.session)
    project = await project_service.get_by_id(project_id)
    await hook_registry.fire(
        HookEvent.ISSUE_ANALYSIS_STARTED,
        HookContext(
            project_id=project_id,
            issue_id=issue_id,
            event=HookEvent.ISSUE_ANALYSIS_STARTED,
            metadata={
                "issue_description": issue.description,
                "project_name": project.name if project else "",
                "project_path": project.path if project else "",
                "project_description": project.description if project else "",
                "tech_stack": project.tech_stack if project else "",
            },
        ),
    )
    return issue
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_issue_actions.py -v
```

Expected: All 4 tests `PASSED`.

- [ ] **Step 6: Create the start_analysis hook handler**

Create `backend/app/hooks/handlers/start_analysis.py`:

```python
"""StartAnalysis hook: spawns Claude Code to write spec, plan, and tasks for a new issue."""

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook


@hook(event=HookEvent.ISSUE_ANALYSIS_STARTED)
class StartAnalysis(BaseHook):
    name = "start_analysis"
    description = "Avvia Claude Code per scrivere spec, piano e task della issue"

    async def execute(self, context: HookContext) -> HookResult:
        issue_description = context.metadata.get("issue_description", "")
        project_name = context.metadata.get("project_name", "")
        project_path = context.metadata.get("project_path", "")
        project_description = context.metadata.get("project_description", "")
        tech_stack = context.metadata.get("tech_stack", "")

        prompt = f"""Sei il project manager di "{project_name}".

È stata creata una nuova issue con questa descrizione:
{issue_description}

Contesto del progetto:
{project_description}
Tech stack: {tech_stack}

Il tuo compito:
1. Usa `create_issue_spec` per scrivere una specifica tecnica dettagliata basata sulla descrizione
2. Usa `create_issue_plan` per scrivere un piano di implementazione step-by-step
3. Usa `create_plan_tasks` per creare i task atomici del piano (usa replace=true)
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
        )

        return HookResult(
            success=result.success,
            output=result.output,
            error=result.error,
        )
```

- [ ] **Step 7: Register the new handler**

In `backend/app/hooks/handlers/__init__.py`:

```python
"""Hook handlers package: import modules here to trigger @hook decorator autodiscovery."""

from app.hooks.handlers import enrich_context  # noqa: F401
from app.hooks.handlers import start_analysis  # noqa: F401
```

- [ ] **Step 8: Add action endpoints to the issues router**

In `backend/app/routers/issues.py`, add these imports at the top:

```python
from app.exceptions import InvalidTransitionError
from app.hooks.registry import HookContext, HookEvent, hook_registry
from app.schemas.issue import IssueCompleteBody
from app.services.project_service import ProjectService
```

Then append these endpoints to the file (after the existing `delete_issue`):

```python
@router.post("/{issue_id}/start-analysis", response_model=IssueResponse)
async def start_analysis(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.start_analysis(issue_id, project_id)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.post("/{issue_id}/accept", response_model=IssueResponse)
async def accept_issue(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.accept_issue(issue_id, project_id)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.post("/{issue_id}/cancel", response_model=IssueResponse)
async def cancel_issue_endpoint(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.cancel_issue(issue_id, project_id)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.post("/{issue_id}/complete", response_model=IssueResponse)
async def complete_issue(
    project_id: str, issue_id: str, data: IssueCompleteBody, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.complete_issue(issue_id, project_id, recap=data.recap)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)
```

- [ ] **Step 9: Add `IssueCompleteBody` schema**

In `backend/app/schemas/issue.py`, add:

```python
class IssueCompleteBody(BaseModel):
    recap: str = Field(..., min_length=1)
```

- [ ] **Step 10: Run all backend tests**

```bash
cd backend && python -m pytest tests/test_issue_actions.py -v
```

Expected: All `PASSED`.

- [ ] **Step 11: Commit**

```bash
git add backend/app/hooks/registry.py \
        backend/app/hooks/handlers/start_analysis.py \
        backend/app/hooks/handlers/__init__.py \
        backend/app/services/issue_service.py \
        backend/app/routers/issues.py \
        backend/app/schemas/issue.py \
        backend/tests/test_issue_actions.py
git commit -m "feat: add issue action endpoints (accept, cancel, complete, start-analysis)"
```

---

## Task 2: Backend — IssueFeedback Model, Migration, API

**Files:**
- Create: `backend/app/models/issue_feedback.py`
- Create: `backend/alembic/versions/a1b2c3d4e5f6_add_issue_feedback.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/issue.py`
- Modify: `backend/app/services/issue_service.py`
- Modify: `backend/app/routers/issues.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_issue_feedback.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_issue_feedback.py`:

```python
import pytest
import pytest_asyncio

from app.exceptions import NotFoundError
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test", path="/tmp/test")


@pytest_asyncio.fixture
async def issue(db_session, project):
    service = IssueService(db_session)
    return await service.create(project_id=project.id, description="Test issue")


async def test_add_feedback(db_session, issue, project):
    service = IssueService(db_session)
    fb = await service.add_feedback(issue.id, project.id, "The plan needs more detail on tests")
    assert fb.id is not None
    assert fb.issue_id == issue.id
    assert fb.content == "The plan needs more detail on tests"


async def test_list_feedback_ordered(db_session, issue, project):
    service = IssueService(db_session)
    await service.add_feedback(issue.id, project.id, "First comment")
    await service.add_feedback(issue.id, project.id, "Second comment")
    feedbacks = await service.list_feedback(issue.id, project.id)
    assert len(feedbacks) == 2
    assert feedbacks[0].content == "First comment"
    assert feedbacks[1].content == "Second comment"


async def test_add_feedback_issue_not_found(db_session, project):
    service = IssueService(db_session)
    with pytest.raises(NotFoundError):
        await service.add_feedback("nonexistent-id", project.id, "feedback")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_issue_feedback.py -v
```

Expected: `FAILED` — `IssueService` has no `add_feedback` method.

- [ ] **Step 3: Create the IssueFeedback model**

Create `backend/app/models/issue_feedback.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IssueFeedback(Base):
    __tablename__ = "issue_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    issue = relationship("Issue", back_populates="feedback")
```

- [ ] **Step 4: Add `feedback` relationship to Issue model**

In `backend/app/models/issue.py`, add the import and relationship:

```python
# Add to existing imports — no change needed since relationship is lazy

# In the Issue class, add after the tasks relationship:
    feedback = relationship("IssueFeedback", back_populates="issue", cascade="all, delete-orphan", order_by="IssueFeedback.created_at")
```

The full updated `Issue` model bottom section:

```python
    project = relationship("Project", back_populates="issues")
    tasks = relationship("Task", back_populates="issue", cascade="all, delete-orphan", order_by="Task.order")
    feedback = relationship("IssueFeedback", back_populates="issue", cascade="all, delete-orphan", order_by="IssueFeedback.created_at")
```

- [ ] **Step 5: Export IssueFeedback from models package**

In `backend/app/models/__init__.py`:

```python
from app.database import Base
from app.models.issue import Issue
from app.models.issue_feedback import IssueFeedback
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.setting import Setting
from app.models.task import Task
from app.models.terminal_command import TerminalCommand

__all__ = ["Base", "Issue", "IssueFeedback", "Project", "ProjectFile", "Setting", "Task", "TerminalCommand"]
```

- [ ] **Step 6: Import IssueFeedback in conftest so test DB creates the table**

In `backend/tests/conftest.py`, update the models import line:

```python
from app.models import Issue, IssueFeedback, Project, Setting, Task, TerminalCommand  # noqa: F401
```

- [ ] **Step 7: Add feedback schemas**

In `backend/app/schemas/issue.py`, add at the end:

```python
class IssueFeedbackCreate(BaseModel):
    content: str = Field(..., min_length=1)


class IssueFeedbackResponse(BaseModel):
    id: str
    issue_id: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 8: Add feedback service methods to IssueService**

In `backend/app/services/issue_service.py`, add these imports at the top:

```python
from app.models.issue_feedback import IssueFeedback
```

Then add these methods to `IssueService` (after `delete`):

```python
async def add_feedback(self, issue_id: str, project_id: str, content: str) -> IssueFeedback:
    await self.get_for_project(issue_id, project_id)  # validates ownership
    fb = IssueFeedback(issue_id=issue_id, content=content)
    self.session.add(fb)
    await self.session.flush()
    return fb

async def list_feedback(self, issue_id: str, project_id: str) -> list[IssueFeedback]:
    await self.get_for_project(issue_id, project_id)  # validates ownership
    result = await self.session.execute(
        select(IssueFeedback)
        .where(IssueFeedback.issue_id == issue_id)
        .order_by(IssueFeedback.created_at.asc())
    )
    return list(result.scalars().all())
```

Also add `IssueFeedback` to the existing `select` import at the top (it's already there from sqlalchemy).

- [ ] **Step 9: Run feedback tests**

```bash
cd backend && python -m pytest tests/test_issue_feedback.py -v
```

Expected: All `PASSED`.

- [ ] **Step 10: Add feedback endpoints to the issues router**

In `backend/app/routers/issues.py`, add these imports:

```python
from app.schemas.issue import IssueFeedbackCreate, IssueFeedbackResponse
```

Then add these endpoints at the end of the file:

```python
@router.get("/{issue_id}/feedback", response_model=list[IssueFeedbackResponse])
async def list_feedback(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    return await service.list_feedback(issue_id, project_id)


@router.post("/{issue_id}/feedback", response_model=IssueFeedbackResponse, status_code=201)
async def add_feedback(
    project_id: str, issue_id: str, data: IssueFeedbackCreate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    fb = await service.add_feedback(issue_id, project_id, data.content)
    await db.commit()
    await db.refresh(fb)
    return fb
```

- [ ] **Step 11: Create the Alembic migration**

```bash
cd backend && python -m alembic revision --autogenerate -m "add_issue_feedback"
```

Review the generated file in `backend/alembic/versions/` to confirm it creates the `issue_feedback` table. It should look like:

```python
def upgrade() -> None:
    op.create_table(
        "issue_feedback",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("issue_id", sa.String(36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("issue_feedback")
```

- [ ] **Step 12: Apply the migration**

```bash
cd backend && python -m alembic upgrade head
```

Expected: No errors, migration applied.

- [ ] **Step 13: Run all backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All `PASSED`.

- [ ] **Step 14: Commit**

```bash
git add backend/app/models/issue_feedback.py \
        backend/app/models/issue.py \
        backend/app/models/__init__.py \
        backend/app/schemas/issue.py \
        backend/app/services/issue_service.py \
        backend/app/routers/issues.py \
        backend/tests/conftest.py \
        backend/tests/test_issue_feedback.py \
        backend/alembic/versions/
git commit -m "feat: add IssueFeedback model, service methods, and API endpoints"
```

---

## Task 3: Backend — Add `name` to IssueUpdate

**Files:**
- Modify: `backend/app/schemas/issue.py`
- Modify: `backend/app/routers/issues.py`

- [ ] **Step 1: Write failing test**

In `backend/tests/test_issue_actions.py`, add:

```python
async def test_update_issue_name(db_session, issue, project):
    service = IssueService(db_session)
    updated = await service.set_name(issue.id, project.id, "New name")
    assert updated.name == "New name"


async def test_update_issue_name_too_long(db_session, issue, project):
    service = IssueService(db_session)
    from app.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await service.set_name(issue.id, project.id, "x" * 501)
```

- [ ] **Step 2: Run tests to verify they pass (service already has set_name)**

```bash
cd backend && python -m pytest tests/test_issue_actions.py::test_update_issue_name tests/test_issue_actions.py::test_update_issue_name_too_long -v
```

Expected: Both `PASSED` — `set_name` already exists in `IssueService`.

- [ ] **Step 3: Add `name` to `IssueUpdate` schema**

In `backend/app/schemas/issue.py`, update `IssueUpdate`:

```python
class IssueUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, min_length=1)
    priority: int | None = Field(None, ge=1, le=5)
```

- [ ] **Step 4: Handle `name` in the update router**

In `backend/app/routers/issues.py`, update the `update_issue` endpoint:

```python
@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    project_id: str, issue_id: str, data: IssueUpdate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload:
        await service.set_name(issue_id, project_id, payload.pop("name"))
    if payload:
        await service.update_fields(issue_id, project_id, **payload)
    await db.commit()
    return await _reload_with_tasks(db, issue_id)
```

- [ ] **Step 5: Run all backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/issue.py backend/app/routers/issues.py backend/tests/test_issue_actions.py
git commit -m "feat: add name field to IssueUpdate schema and router"
```

---

## Task 4: Frontend — Types, API Functions, React Query Hooks

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/features/issues/api.ts`
- Modify: `frontend/src/features/issues/hooks.ts`

- [ ] **Step 1: Add new types to `types/index.ts`**

In `frontend/src/shared/types/index.ts`, update `IssueUpdate` and add feedback types:

```typescript
export interface IssueUpdate {
  name?: string;
  description?: string;
  priority?: number;
}

export interface IssueCompleteBody {
  recap: string;
}

export interface IssueFeedback {
  id: string;
  issue_id: string;
  content: string;
  created_at: string;
}

export interface IssueFeedbackCreate {
  content: string;
}
```

- [ ] **Step 2: Add API functions to `api.ts`**

In `frontend/src/features/issues/api.ts`, update the import line and add new functions:

```typescript
import { request } from "@/shared/api/client";
import type {
  Issue,
  IssueCreate,
  IssueCompleteBody,
  IssueFeedback,
  IssueFeedbackCreate,
  IssueStatus,
  IssueStatusUpdate,
  IssueUpdate,
  Task,
  TaskCreate,
  TaskUpdate,
} from "@/shared/types";

// ... existing functions unchanged ...

export function startAnalysis(projectId: string, issueId: string): Promise<Issue> {
  return request(`/projects/${projectId}/issues/${issueId}/start-analysis`, { method: "POST" });
}

export function acceptIssue(projectId: string, issueId: string): Promise<Issue> {
  return request(`/projects/${projectId}/issues/${issueId}/accept`, { method: "POST" });
}

export function cancelIssue(projectId: string, issueId: string): Promise<Issue> {
  return request(`/projects/${projectId}/issues/${issueId}/cancel`, { method: "POST" });
}

export function completeIssue(projectId: string, issueId: string, data: IssueCompleteBody): Promise<Issue> {
  return request(`/projects/${projectId}/issues/${issueId}/complete`, { method: "POST", body: JSON.stringify(data) });
}

export function fetchFeedback(projectId: string, issueId: string): Promise<IssueFeedback[]> {
  return request(`/projects/${projectId}/issues/${issueId}/feedback`);
}

export function addFeedback(projectId: string, issueId: string, data: IssueFeedbackCreate): Promise<IssueFeedback> {
  return request(`/projects/${projectId}/issues/${issueId}/feedback`, { method: "POST", body: JSON.stringify(data) });
}
```

- [ ] **Step 3: Add React Query hooks to `hooks.ts`**

In `frontend/src/features/issues/hooks.ts`, add to the existing file:

```typescript
// Add to imports
import type { IssueCompleteBody, IssueFeedbackCreate } from "@/shared/types";

// Add these hooks after the existing ones

export function useStartAnalysis(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.startAnalysis(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}

export function useAcceptIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.acceptIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useCancelIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.cancelIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useCompleteIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueCompleteBody) => api.completeIssue(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export const feedbackKeys = {
  all: (projectId: string, issueId: string) =>
    ["projects", projectId, "issues", issueId, "feedback"] as const,
};

export function useFeedback(projectId: string, issueId: string) {
  return useQuery({
    queryKey: feedbackKeys.all(projectId, issueId),
    queryFn: () => api.fetchFeedback(projectId, issueId),
  });
}

export function useAddFeedback(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueFeedbackCreate) => api.addFeedback(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: feedbackKeys.all(projectId, issueId) });
    },
  });
}

export function useUpdateTask(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: import("@/shared/types").TaskUpdate }) =>
      api.updateTask(projectId, issueId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}

export function useDeleteTask(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => api.deleteTask(projectId, issueId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}

export function useCreateTasks(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tasks: import("@/shared/types").TaskCreate[]) =>
      api.createTasks(projectId, issueId, tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}

export function useReplaceTasks(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tasks: import("@/shared/types").TaskCreate[]) =>
      api.replaceTasks(projectId, issueId, tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/types/index.ts \
        frontend/src/features/issues/api.ts \
        frontend/src/features/issues/hooks.ts
git commit -m "feat: add frontend types, API functions and hooks for issue actions and feedback"
```

---

## Task 5: Frontend — IssueActions Component (2.1)

**Files:**
- Create: `frontend/src/features/issues/components/issue-actions.tsx`

- [ ] **Step 1: Install no new dependencies**

All UI components (Button, Dialog) already exist in shadcn/ui. No new packages needed.

- [ ] **Step 2: Create `issue-actions.tsx`**

Create `frontend/src/features/issues/components/issue-actions.tsx`:

```tsx
import { useState } from "react";
import { PlayCircle, CheckCircle, XCircle, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  useStartAnalysis,
  useAcceptIssue,
  useCancelIssue,
  useCompleteIssue,
} from "@/features/issues/hooks";
import type { Issue } from "@/shared/types";

interface IssueActionsProps {
  issue: Issue;
  projectId: string;
}

export function IssueActions({ issue, projectId }: IssueActionsProps) {
  const [confirmAction, setConfirmAction] = useState<
    "start-analysis" | "accept" | "cancel" | "complete" | null
  >(null);
  const [recap, setRecap] = useState("");

  const startAnalysis = useStartAnalysis(projectId, issue.id);
  const acceptIssue = useAcceptIssue(projectId, issue.id);
  const cancelIssue = useCancelIssue(projectId, issue.id);
  const completeIssue = useCompleteIssue(projectId, issue.id);

  const isPending =
    startAnalysis.isPending ||
    acceptIssue.isPending ||
    cancelIssue.isPending ||
    completeIssue.isPending;

  const handleConfirm = () => {
    if (confirmAction === "start-analysis") {
      startAnalysis.mutate(undefined, { onSuccess: () => setConfirmAction(null) });
    } else if (confirmAction === "accept") {
      acceptIssue.mutate(undefined, { onSuccess: () => setConfirmAction(null) });
    } else if (confirmAction === "cancel") {
      cancelIssue.mutate(undefined, { onSuccess: () => setConfirmAction(null) });
    } else if (confirmAction === "complete") {
      completeIssue.mutate({ recap }, { onSuccess: () => { setConfirmAction(null); setRecap(""); } });
    }
  };

  const isTerminalState = issue.status === "Finished" || issue.status === "Canceled";

  const CONFIRM_COPY: Record<string, { title: string; description: string; confirm: string }> = {
    "start-analysis": {
      title: "Avvia Analisi",
      description: "Claude analizzerà la descrizione e scriverà spec, piano e task. Questo potrebbe richiedere qualche minuto.",
      confirm: "Avvia",
    },
    accept: {
      title: "Accetta Piano",
      description: "Accettare il piano trasferisce l'issue in stato Accepted e avvia il workflow di implementazione.",
      confirm: "Accetta",
    },
    cancel: {
      title: "Cancella Issue",
      description: "Questa azione non può essere annullata. L'issue verrà marcata come Canceled.",
      confirm: "Cancella",
    },
    complete: {
      title: "Segna come Completata",
      description: "Tutti i task devono essere completati. Inserisci un recap di cosa è stato fatto.",
      confirm: "Completa",
    },
  };

  if (isTerminalState) return null;

  return (
    <>
      <div className="flex items-center gap-2 flex-wrap">
        {issue.status === "New" && (
          <Button
            size="sm"
            onClick={() => setConfirmAction("start-analysis")}
            disabled={isPending}
          >
            <PlayCircle className="size-4 mr-1" />
            Avvia Analisi
          </Button>
        )}

        {issue.status === "Planned" && (
          <Button
            size="sm"
            variant="default"
            onClick={() => setConfirmAction("accept")}
            disabled={isPending}
          >
            <CheckCircle className="size-4 mr-1" />
            Accetta Piano
          </Button>
        )}

        {issue.status === "Accepted" && (
          <Button
            size="sm"
            variant="default"
            onClick={() => setConfirmAction("complete")}
            disabled={isPending}
          >
            <CheckCircle className="size-4 mr-1" />
            Segna come Completata
          </Button>
        )}

        <Button
          size="sm"
          variant="outline"
          className="text-destructive hover:text-destructive"
          onClick={() => setConfirmAction("cancel")}
          disabled={isPending}
        >
          <XCircle className="size-4 mr-1" />
          Cancella Issue
        </Button>
      </div>

      {confirmAction && CONFIRM_COPY[confirmAction] && (
        <Dialog open onOpenChange={() => setConfirmAction(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{CONFIRM_COPY[confirmAction].title}</DialogTitle>
              <DialogDescription>{CONFIRM_COPY[confirmAction].description}</DialogDescription>
            </DialogHeader>

            {confirmAction === "complete" && (
              <Textarea
                placeholder="Descrivi cosa è stato implementato..."
                value={recap}
                onChange={(e) => setRecap(e.target.value)}
                rows={4}
                className="mt-2"
              />
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmAction(null)}>
                Annulla
              </Button>
              <Button
                variant={confirmAction === "cancel" ? "destructive" : "default"}
                onClick={handleConfirm}
                disabled={isPending || (confirmAction === "complete" && !recap.trim())}
              >
                {isPending ? (
                  <Loader2 className="size-4 mr-1 animate-spin" />
                ) : (
                  <AlertCircle className="size-4 mr-1" />
                )}
                {isPending ? "In corso..." : CONFIRM_COPY[confirmAction].confirm}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
```

- [ ] **Step 3: Check that `Textarea` is available in shadcn/ui**

```bash
ls frontend/src/shared/components/ui/ | grep textarea
```

If it's not present, create `frontend/src/shared/components/ui/textarea.tsx`:

```tsx
import * as React from "react";
import { cn } from "@/shared/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/issues/components/issue-actions.tsx \
        frontend/src/shared/components/ui/textarea.tsx
git commit -m "feat: add IssueActions component with state transition buttons and confirmation modals"
```

---

## Task 6: Frontend — PlanFeedback Component (2.2)

**Files:**
- Create: `frontend/src/features/issues/components/plan-feedback.tsx`

- [ ] **Step 1: Create `plan-feedback.tsx`**

Create `frontend/src/features/issues/components/plan-feedback.tsx`:

```tsx
import { useState } from "react";
import { MessageSquare, Send, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { useFeedback, useAddFeedback } from "@/features/issues/hooks";

interface PlanFeedbackProps {
  projectId: string;
  issueId: string;
}

export function PlanFeedback({ projectId, issueId }: PlanFeedbackProps) {
  const [text, setText] = useState("");
  const { data: feedbacks = [] } = useFeedback(projectId, issueId);
  const addFeedback = useAddFeedback(projectId, issueId);

  const handleSubmit = () => {
    if (!text.trim()) return;
    addFeedback.mutate(
      { content: text.trim() },
      { onSuccess: () => setText("") }
    );
  };

  return (
    <div className="space-y-4 mt-4 border-t pt-4">
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <MessageSquare className="size-4" />
        Feedback per Claude
      </div>

      {feedbacks.length > 0 && (
        <div className="space-y-2">
          {feedbacks.map((fb) => (
            <div key={fb.id} className="rounded-md bg-muted px-3 py-2 text-sm">
              <p className="whitespace-pre-wrap">{fb.content}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {new Date(fb.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <Textarea
          placeholder="Dai feedback a Claude sul piano (es: aggiungi test per X, considera Y)..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          className="flex-1"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSubmit();
          }}
        />
        <Button
          size="sm"
          onClick={handleSubmit}
          disabled={!text.trim() || addFeedback.isPending}
          className="self-end"
        >
          {addFeedback.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Send className="size-4" />
          )}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">Ctrl+Enter per inviare</p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/issues/components/plan-feedback.tsx
git commit -m "feat: add PlanFeedback component for plan review comments"
```

---

## Task 7: Frontend — EditableTaskList with Drag-and-Drop (2.3)

**Files:**
- Install: `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`
- Create: `frontend/src/features/issues/components/editable-task-list.tsx`

- [ ] **Step 1: Install drag-and-drop library**

```bash
cd frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

Expected output: packages added to `node_modules`.

- [ ] **Step 2: Create `editable-task-list.tsx`**

Create `frontend/src/features/issues/components/editable-task-list.tsx`:

```tsx
import { useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Trash2, Plus, Loader2, Check, Circle, Clock } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import {
  useUpdateTask,
  useDeleteTask,
  useCreateTasks,
  useReplaceTasks,
} from "@/features/issues/hooks";
import type { Task, TaskStatus } from "@/shared/types";

interface SortableTaskItemProps {
  task: Task;
  onToggle: (task: Task) => void;
  onDelete: (taskId: string) => void;
  isToggling: boolean;
  isDeleting: boolean;
}

function SortableTaskItem({ task, onToggle, onDelete, isToggling, isDeleting }: SortableTaskItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const statusIcon = {
    Pending: <Circle className="size-4 text-slate-400" />,
    "In Progress": <Clock className="size-4 text-amber-500" />,
    Completed: <Check className="size-4 text-emerald-500" />,
  }[task.status as TaskStatus];

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 p-2 rounded-md border bg-card hover:bg-accent/50 group"
    >
      <button
        className="cursor-grab touch-none text-muted-foreground"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-4" />
      </button>

      <button
        onClick={() => onToggle(task)}
        disabled={isToggling || task.status === "Completed"}
        className="shrink-0 disabled:opacity-50"
        title={task.status === "Completed" ? "Completato" : "Segna come completato"}
      >
        {isToggling ? <Loader2 className="size-4 animate-spin" /> : statusIcon}
      </button>

      <span
        className={`flex-1 text-sm ${
          task.status === "Completed" ? "line-through text-muted-foreground" : ""
        }`}
      >
        {task.name}
      </span>

      <button
        onClick={() => onDelete(task.id)}
        disabled={isDeleting}
        className="opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive/80 disabled:opacity-50"
      >
        {isDeleting ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
      </button>
    </div>
  );
}

interface EditableTaskListProps {
  tasks: Task[];
  projectId: string;
  issueId: string;
}

export function EditableTaskList({ tasks, projectId, issueId }: EditableTaskListProps) {
  const [newTaskName, setNewTaskName] = useState("");
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const updateTask = useUpdateTask(projectId, issueId);
  const deleteTask = useDeleteTask(projectId, issueId);
  const createTasks = useCreateTasks(projectId, issueId);
  const replaceTasks = useReplaceTasks(projectId, issueId);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleToggle = async (task: Task) => {
    setTogglingId(task.id);
    try {
      if (task.status === "Pending") {
        // Two-step: Pending → In Progress → Completed
        await updateTask.mutateAsync({ taskId: task.id, data: { status: "In Progress" } });
        await updateTask.mutateAsync({ taskId: task.id, data: { status: "Completed" } });
      } else if (task.status === "In Progress") {
        await updateTask.mutateAsync({ taskId: task.id, data: { status: "Completed" } });
      }
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async (taskId: string) => {
    setDeletingId(taskId);
    try {
      await deleteTask.mutateAsync(taskId);
    } finally {
      setDeletingId(null);
    }
  };

  const handleAddTask = () => {
    if (!newTaskName.trim()) return;
    createTasks.mutate([{ name: newTaskName.trim() }], {
      onSuccess: () => setNewTaskName(""),
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = tasks.findIndex((t) => t.id === active.id);
    const newIndex = tasks.findIndex((t) => t.id === over.id);
    const reordered = arrayMove(tasks, oldIndex, newIndex);

    replaceTasks.mutate(reordered.map((t) => ({ name: t.name })));
  };

  return (
    <div className="space-y-2">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <SortableTaskItem
              key={task.id}
              task={task}
              onToggle={handleToggle}
              onDelete={handleDelete}
              isToggling={togglingId === task.id}
              isDeleting={deletingId === task.id}
            />
          ))}
        </SortableContext>
      </DndContext>

      {tasks.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-4">
          Nessun task. Aggiungine uno qui sotto.
        </p>
      )}

      <div className="flex gap-2 mt-3">
        <Input
          placeholder="Aggiungi task..."
          value={newTaskName}
          onChange={(e) => setNewTaskName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAddTask();
          }}
          className="flex-1"
        />
        <Button
          size="sm"
          onClick={handleAddTask}
          disabled={!newTaskName.trim() || createTasks.isPending}
        >
          {createTasks.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Plus className="size-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify Input component exists**

```bash
ls frontend/src/shared/components/ui/ | grep input
```

If missing, create `frontend/src/shared/components/ui/input.tsx`:

```tsx
import * as React from "react";
import { cn } from "@/shared/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/issues/components/editable-task-list.tsx \
        frontend/src/shared/components/ui/input.tsx \
        frontend/package.json \
        frontend/package-lock.json
git commit -m "feat: add EditableTaskList with checkbox toggle, add/delete, and drag-to-reorder"
```

---

## Task 8: Frontend — InlineEditField Component (2.4)

**Files:**
- Create: `frontend/src/features/issues/components/inline-edit-field.tsx`

- [ ] **Step 1: Create `inline-edit-field.tsx`**

Create `frontend/src/features/issues/components/inline-edit-field.tsx`:

```tsx
import { useState, useRef, useEffect } from "react";
import { Pencil, Check, X } from "lucide-react";
import { cn } from "@/shared/utils";

interface InlineEditFieldProps {
  value: string;
  onSave: (value: string) => void;
  className?: string;
  inputClassName?: string;
  renderView?: (value: string) => React.ReactNode;
  validate?: (value: string) => string | null; // returns error message or null
  multiline?: boolean;
  disabled?: boolean;
}

export function InlineEditField({
  value,
  onSave,
  className,
  inputClassName,
  renderView,
  validate,
  multiline = false,
  disabled = false,
}: InlineEditFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement & HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing) {
      setDraft(value);
      setError(null);
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing, value]);

  const handleSave = () => {
    const trimmed = draft.trim();
    if (!trimmed) {
      setError("Il campo non può essere vuoto");
      return;
    }
    if (validate) {
      const err = validate(trimmed);
      if (err) { setError(err); return; }
    }
    onSave(trimmed);
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(value);
    setError(null);
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !multiline) { e.preventDefault(); handleSave(); }
    if (e.key === "Escape") handleCancel();
    if (e.key === "Enter" && multiline && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleSave(); }
  };

  if (editing) {
    const sharedProps = {
      ref: inputRef as never,
      value: draft,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setDraft(e.target.value);
        setError(null);
      },
      onKeyDown: handleKeyDown,
      onBlur: handleSave,
      className: cn(
        "w-full rounded border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring",
        inputClassName
      ),
    };

    return (
      <div className={cn("relative", className)}>
        {multiline ? (
          <textarea {...sharedProps} rows={3} />
        ) : (
          <input {...sharedProps} />
        )}
        {error && <p className="text-xs text-destructive mt-1">{error}</p>}
        <div className="flex gap-1 mt-1">
          <button onClick={handleSave} className="text-emerald-600 hover:text-emerald-700">
            <Check className="size-3.5" />
          </button>
          <button onClick={handleCancel} className="text-muted-foreground hover:text-foreground">
            <X className="size-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group flex items-start gap-1",
        !disabled && "cursor-pointer",
        className
      )}
      onClick={() => !disabled && setEditing(true)}
      title={disabled ? undefined : "Clicca per modificare"}
    >
      {renderView ? renderView(value) : <span className="text-sm">{value}</span>}
      {!disabled && (
        <Pencil className="size-3 mt-0.5 opacity-0 group-hover:opacity-60 shrink-0 text-muted-foreground" />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/issues/components/inline-edit-field.tsx
git commit -m "feat: add InlineEditField click-to-edit component"
```

---

## Task 9: Frontend — Wire Everything into IssueDetail

**Files:**
- Modify: `frontend/src/features/issues/components/issue-detail.tsx`

- [ ] **Step 1: Update `issue-detail.tsx` with all new components**

Replace the entire content of `frontend/src/features/issues/components/issue-detail.tsx` with:

```tsx
import { useState, useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { MarkdownViewer } from "@/shared/components/markdown-viewer";
import { StatusBadge } from "./status-badge";
import { IssueActions } from "./issue-actions";
import { PlanFeedback } from "./plan-feedback";
import { EditableTaskList } from "./editable-task-list";
import { InlineEditField } from "./inline-edit-field";
import { useDeleteIssue, useUpdateIssue } from "@/features/issues/hooks";
import { useKillTerminal } from "@/features/terminals/hooks";
import type { Issue } from "@/shared/types";

interface IssueDetailProps {
  issue: Issue;
  projectId: string;
  terminalId: string | null;
}

interface TabDef {
  value: string;
  label: string;
  available: boolean;
}

export function IssueDetail({ issue, projectId, terminalId }: IssueDetailProps) {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const deleteIssue = useDeleteIssue(projectId);
  const killTerminal = useKillTerminal();
  const updateIssue = useUpdateIssue(projectId, issue.id);

  const tabs = useMemo<TabDef[]>(() => [
    { value: "description", label: "Description", available: true },
    { value: "specification", label: "Specification", available: !!issue.specification },
    { value: "plan", label: "Plan", available: !!issue.plan },
    { value: "tasks", label: "Tasks", available: true },
    { value: "recap", label: "Recap", available: !!issue.recap },
  ], [issue.specification, issue.plan, issue.recap]);

  const availableTabs = tabs.filter((t) => t.available);
  const defaultTab = availableTabs[0]?.value ?? "description";

  const handleDelete = async () => {
    if (terminalId) {
      try { await killTerminal.mutateAsync(terminalId); } catch { /* Terminal may already be dead */ }
    }
    deleteIssue.mutate(issue.id, {
      onSuccess: () => navigate({ to: "/projects/$projectId/issues", params: { projectId } }),
    });
  };

  const isTerminalState = issue.status === "Finished" || issue.status === "Canceled";

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <InlineEditField
            value={issue.name || "Untitled Issue"}
            onSave={(name) => updateIssue.mutate({ name })}
            disabled={isTerminalState}
            validate={(v) => v.length > 500 ? "Max 500 caratteri" : null}
            renderView={(v) => <h1 className="text-xl font-bold">{v}</h1>}
          />
          <div className="flex items-center gap-3 mt-1">
            <InlineEditField
              value={String(issue.priority)}
              onSave={(v) => {
                const n = parseInt(v, 10);
                if (n >= 1 && n <= 5) updateIssue.mutate({ priority: n });
              }}
              disabled={isTerminalState}
              validate={(v) => {
                const n = parseInt(v, 10);
                return isNaN(n) || n < 1 || n > 5 ? "Priorità deve essere 1-5" : null;
              }}
              renderView={(v) => (
                <span className="text-sm text-muted-foreground">Priority: {v}</span>
              )}
            />
            <StatusBadge status={issue.status} />
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive shrink-0"
          onClick={() => setShowDeleteConfirm(true)}
        >
          <Trash2 className="size-4 mr-1" />
          Delete
        </Button>
      </div>

      {/* Action buttons */}
      <IssueActions issue={issue} projectId={projectId} />

      {/* Tabbed content */}
      <Tabs defaultValue={defaultTab} className="w-full">
        <TabsList>
          {availableTabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
              {tab.value === "tasks" && issue.tasks.length > 0 && (
                <span className="ml-1 text-xs text-muted-foreground">
                  ({issue.tasks.filter((t) => t.status === "Completed").length}/{issue.tasks.length})
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="description" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <InlineEditField
                value={issue.description}
                onSave={(description) => updateIssue.mutate({ description })}
                disabled={isTerminalState}
                multiline
                renderView={(v) => <p className="text-sm whitespace-pre-wrap">{v}</p>}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {issue.specification && (
          <TabsContent value="specification" className="mt-4">
            <Card>
              <CardContent className="pt-6">
                <MarkdownViewer content={issue.specification} />
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {issue.plan && (
          <TabsContent value="plan" className="mt-4">
            <Card>
              <CardContent className="pt-6">
                <MarkdownViewer content={issue.plan} />
                {issue.status === "Planned" && (
                  <PlanFeedback projectId={projectId} issueId={issue.id} />
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        <TabsContent value="tasks" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <EditableTaskList
                tasks={issue.tasks}
                projectId={projectId}
                issueId={issue.id}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {issue.recap && (
          <TabsContent value="recap" className="mt-4">
            <Card>
              <CardContent className="pt-6">
                <MarkdownViewer content={issue.recap} />
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      {/* Delete confirmation */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Issue?</DialogTitle>
            <DialogDescription>
              This will permanently delete this issue and all its tasks. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteIssue.isPending}
            >
              {deleteIssue.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 2: Verify the app builds without errors**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no TypeScript or import errors.

If there are errors:
- Missing `cn` import: check path is `@/shared/utils` (look in `frontend/src/shared/` for a `utils.ts` that exports `cn`)
- Missing component: verify each component file was created in previous tasks

- [ ] **Step 3: Run ESLint**

```bash
cd frontend && npm run lint
```

Expected: No errors.

- [ ] **Step 4: Run all backend tests one final time**

```bash
cd backend && python -m pytest -v
```

Expected: All `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/issues/components/issue-detail.tsx
git commit -m "feat: wire IssueActions, PlanFeedback, EditableTaskList, InlineEditField into IssueDetail"
```

---

## Self-Review Checklist

### Spec Coverage

| Requirement | Task |
|---|---|
| 2.1 — Bottoni transizione stato (NEW→start, PLANNED→accept, ACCEPTED→complete) | Task 1 (backend), Task 5 (UI) |
| 2.1 — Modale di conferma per ogni transizione | Task 5 (`IssueActions`) |
| 2.1 — "Cancella Issue" qualsiasi stato | Task 1 (cancel endpoint), Task 5 |
| 2.1 — StatusBadge cliccabile con dropdown | **Not covered** — the roadmap says "cliccabile con dropdown"; the plan uses explicit buttons in the header instead. The buttons approach is simpler and clearer UX. If a dropdown badge is required, a `DropdownMenu` on the `StatusBadge` could be added separately. |
| 2.2 — Campo feedback PLANNED state | Task 6 (`PlanFeedback`) |
| 2.2 — Feedback salvato, storico visibile | Task 2 (DB), Task 6 (UI) |
| 2.3 — Lista task editabile (checkbox) | Task 7 |
| 2.3 — Aggiunta/rimozione task manuali | Task 7 |
| 2.3 — Drag-and-drop riordino | Task 7 (`@dnd-kit`) |
| 2.4 — Modifica nome, descrizione, priorità inline | Task 8, Task 9 |

### Gap: StatusBadge dropdown

The plan implements explicit action buttons in the issue header instead of a clickable `StatusBadge` dropdown. This covers all the same actions but through a different (arguably clearer) UX. If the dropdown badge is preferred, add a `DropdownMenu` wrapper around `StatusBadge` in `issue-actions.tsx` — the mutations are already in place.

### Placeholder Scan

No TBD, TODO, or vague steps found.

### Type Consistency

- `Task.status` typed as `TaskStatus = "Pending" | "In Progress" | "Completed"` — consistent in `SortableTaskItem` switch
- `Issue.status` typed as `IssueStatus` — `isTerminalState` check uses `"Finished" | "Canceled"` matching the enum
- `updateTask` mutation signature `{ taskId, data }` — consistent across hook definition and `EditableTaskList` call site
- `IssueUpdate.name` added in Task 3 schema and used in Task 9 via `updateIssue.mutate({ name })`
