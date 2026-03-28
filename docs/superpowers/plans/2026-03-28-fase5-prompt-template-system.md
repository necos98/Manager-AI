# Fase 5 — Prompt & Template System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendere configurabili i prompt di Claude, le skill/agent per progetto, e le descrizioni dei tool MCP, tramite una skill library su filesystem e override per-progetto in DB.

**Architecture:** Tre layer indipendenti: (1) SkillLibraryService legge `claude_library/` dal filesystem e copia file in `<project>/.claude/skills/`; (2) PromptTemplateService risolve template con priority override DB → file default; (3) McpToolDescriptionResolver legge override da ProjectSettings. Tutti i hook handler delegano la costruzione del prompt a PromptTemplateService.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, Alembic, Pydantic v2, React/TypeScript, TanStack Query, TanStack Router

---

## File Map

**Create (backend):**
- `backend/app/models/prompt_template.py`
- `backend/app/models/project_skill.py`
- `backend/app/services/prompt_template_service.py`
- `backend/app/services/skill_library_service.py`
- `backend/app/schemas/library.py`
- `backend/app/schemas/prompt_template.py`
- `backend/app/routers/library.py`
- `backend/app/routers/project_skills.py`
- `backend/app/routers/project_templates.py`
- `backend/alembic/versions/XXXX_add_prompt_templates_project_skills.py`
- `backend/tests/test_routers_library.py`
- `backend/tests/test_routers_project_skills.py`
- `backend/tests/test_routers_project_templates.py`

**Create (claude_library):**
- `claude_library/templates/workflow.md`
- `claude_library/templates/implementation.md`
- `claude_library/templates/recap.md`
- `claude_library/templates/spec.md`
- `claude_library/templates/plan.md`
- `claude_library/templates/enrich.md`
- `claude_library/skills/laravel-12.md`
- `claude_library/skills/react-19.md`
- `claude_library/skills/django.md`
- `claude_library/skills/fastapi.md`
- `claude_library/skills/nestjs.md`
- `claude_library/skills/crm.md`
- `claude_library/skills/saas.md`
- `claude_library/agents/backend-architect.md`
- `claude_library/agents/frontend-expert.md`
- `claude_library/agents/fullstack.md`

**Create (frontend):**
- `frontend/src/features/library/api.ts`
- `frontend/src/features/library/hooks.ts`
- `frontend/src/features/projects/api-skills.ts`
- `frontend/src/features/projects/hooks-skills.ts`
- `frontend/src/features/projects/api-templates.ts`
- `frontend/src/features/projects/hooks-templates.ts`
- `frontend/src/features/projects/components/library-tab.tsx`
- `frontend/src/routes/library.tsx`
- `frontend/src/routes/projects/$projectId/library.tsx`

**Modify:**
- `backend/app/models/__init__.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/hooks/handlers/auto_start_workflow.py`
- `backend/app/hooks/handlers/auto_start_implementation.py`
- `backend/app/hooks/handlers/auto_completion.py`
- `backend/app/hooks/handlers/start_analysis.py`
- `backend/tests/conftest.py`
- `frontend/src/shared/types/index.ts`
- `frontend/src/routes/__root.tsx` (or sidebar nav component)

---

## Task 1: DB Models

**Files:**
- Create: `backend/app/models/prompt_template.py`
- Create: `backend/app/models/project_skill.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create PromptTemplate model**

```python
# backend/app/models/prompt_template.py
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: Create ProjectSkill model**

```python
# backend/app/models/project_skill.py
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectSkill(Base):
    __tablename__ = "project_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # "skill" | "agent"
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Update `__init__.py`**

```python
# backend/app/models/__init__.py
from app.database import Base
from app.models.activity_log import ActivityLog
from app.models.issue import Issue
from app.models.issue_feedback import IssueFeedback
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.project_skill import ProjectSkill
from app.models.prompt_template import PromptTemplate
from app.models.setting import Setting
from app.models.task import Task
from app.models.terminal_command import TerminalCommand

__all__ = [
    "ActivityLog", "Base", "Issue", "IssueFeedback", "Project", "ProjectFile",
    "ProjectSkill", "PromptTemplate", "Setting", "Task", "TerminalCommand",
]
```

- [ ] **Step 4: Update conftest.py to import new models**

```python
# backend/tests/conftest.py — replace the import line
from app.models import (  # noqa: F401
    ActivityLog, Issue, IssueFeedback, Project, ProjectSkill,
    PromptTemplate, Setting, Task, TerminalCommand,
)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/prompt_template.py backend/app/models/project_skill.py \
        backend/app/models/__init__.py backend/tests/conftest.py
git commit -m "feat: add PromptTemplate and ProjectSkill models"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/XXXX_add_prompt_templates_project_skills.py`

- [ ] **Step 1: Generate migration**

```bash
cd backend
python -m alembic revision --autogenerate -m "add_prompt_templates_project_skills"
```

Expected: creates a file in `alembic/versions/` with `upgrade()` and `downgrade()`.

- [ ] **Step 2: Verify the generated migration contains both tables**

Open the generated file and confirm `upgrade()` has `op.create_table("prompt_templates", ...)` and `op.create_table("project_skills", ...)`. If autogenerate missed columns, add them manually:

```python
def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_templates_project_id", "prompt_templates", ["project_id"])

    op.create_table(
        "project_skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_skills_project_id", "project_skills", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_skills_project_id", "project_skills")
    op.drop_table("project_skills")
    op.drop_index("ix_prompt_templates_project_id", "prompt_templates")
    op.drop_table("prompt_templates")
```

- [ ] **Step 3: Apply migration**

```bash
cd backend
python -m alembic upgrade head
```

Expected: `Running upgrade ... -> XXXX, add_prompt_templates_project_skills`

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: migration — add prompt_templates and project_skills tables"
```

---

## Task 3: `claude_library/` Structure and Config

**Files:**
- Create: `claude_library/templates/*.md` (6 files)
- Create: `claude_library/skills/*.md` (8 files)
- Create: `claude_library/agents/*.md` (3 files)
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add `claude_library_path` to config**

```python
# backend/app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    lancedb_path: str = str(_PROJECT_ROOT / "data" / "lancedb")
    backend_port: int = 8000
    embedding_driver: str = "sentence_transformer"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50
    claude_library_path: str = str(_PROJECT_ROOT / "claude_library")

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 2: Create default workflow template**

```markdown
<!-- claude_library/templates/workflow.md -->
---
type: workflow
description: Template per auto-start workflow (spec + piano + task)
---
Sei il project manager di "{{project_name}}".

È stata creata una nuova issue con questa descrizione:
{{issue_description}}

Contesto del progetto:
{{project_description}}
Tech stack: {{tech_stack}}
{{skills_context}}

Il tuo compito:
1. Usa `create_issue_spec` per scrivere una specifica tecnica dettagliata
2. Usa `create_issue_plan` per scrivere un piano di implementazione step-by-step
3. Usa `create_plan_tasks` per creare i task atomici del piano
4. Usa `send_notification` per notificare l'utente che il piano è pronto per la review

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Lavora in sequenza, non saltare passi.
```

- [ ] **Step 3: Create default implementation template**

```markdown
<!-- claude_library/templates/implementation.md -->
---
type: implementation
description: Template per auto-start implementazione
---
Sei il developer assegnato all'issue "{{issue_name}}" nel progetto "{{project_name}}".

Contesto del progetto:
{{project_description}}
Tech stack: {{tech_stack}}
{{skills_context}}

Specifica dell'issue:
{{issue_spec}}

Piano di implementazione:
{{issue_plan}}

Il tuo compito è implementare il piano passo per passo:
1. Usa `get_plan_tasks` per ottenere la lista dei task
2. Per ogni task, in ordine:
   a. Usa `update_task_status` per marcarlo "In Progress"
   b. Implementa il task nel codice del progetto
   c. Usa `update_task_status` per marcarlo "Completed"
3. Quando tutti i task sono completati, usa `complete_issue` con un recap dettagliato

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Lavora metodicamente. Non saltare task.
```

- [ ] **Step 4: Create default recap template**

```markdown
<!-- claude_library/templates/recap.md -->
---
type: recap
description: Template per auto-completamento con recap
---
Tutti i task dell'issue "{{issue_name}}" sono stati completati.
{{skills_context}}

Il tuo compito:
1. Usa `get_issue_details` per leggere il piano e i task completati
2. Usa `complete_issue` con un recap dettagliato che descrive cosa è stato implementato

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Il recap deve essere completo e basato sul piano effettivamente eseguito.
```

- [ ] **Step 5: Create remaining templates (spec, plan, enrich)**

```markdown
<!-- claude_library/templates/spec.md -->
---
type: spec
description: Template per scrittura specifica tecnica
---
Scrivi una specifica tecnica dettagliata per l'issue descritta di seguito.

Progetto: {{project_name}}
Stack: {{tech_stack}}
{{skills_context}}

Descrizione issue:
{{issue_description}}

La specifica deve coprire: obiettivo, requisiti funzionali, requisiti tecnici, edge case.
```

```markdown
<!-- claude_library/templates/plan.md -->
---
type: plan
description: Template per scrittura piano di implementazione
---
Scrivi un piano di implementazione step-by-step per la seguente specifica.

Progetto: {{project_name}}
Stack: {{tech_stack}}
{{skills_context}}

Specifica:
{{issue_spec}}

Il piano deve essere atomico: ogni step deve essere un'azione singola e verificabile.
```

```markdown
<!-- claude_library/templates/enrich.md -->
---
type: enrich
description: Template per arricchimento contesto RAG
---
Analizza il seguente contenuto e arricchiscilo con contesto aggiuntivo rilevante per il progetto.

Progetto: {{project_name}}
Stack: {{tech_stack}}
{{skills_context}}

Contenuto da analizzare:
{{issue_description}}
```

- [ ] **Step 6: Create built-in skill files**

```markdown
<!-- claude_library/skills/laravel-12.md -->
---
name: laravel-12
category: tech
description: Patterns, conventions, Eloquent, Pest for Laravel 12
built_in: true
---
# Laravel 12 Conventions

## Architecture
- Use Repository pattern for data access layer
- Service classes for business logic (inject via constructor)
- Form Requests for validation
- API Resources for response transformation

## Models & Eloquent
- Define `$fillable` explicitly, never use `$guarded = []`
- Use typed properties in models
- Relationships: `hasMany`, `belongsTo`, `belongsToMany` with explicit foreign keys
- Scopes for reusable query logic

## Testing
- Use Pest PHP for all tests
- `RefreshDatabase` trait for database tests
- Factory-based test data, never raw inserts
- Feature tests in `tests/Feature/`, unit tests in `tests/Unit/`

## API
- RESTful routes in `api.php`, versioned under `/api/v1/`
- Return `JsonResource` or `ResourceCollection`, never raw arrays
- HTTP status codes: 201 for creation, 204 for deletion, 422 for validation errors

## Naming
- Controllers: `PascalCase`, suffix `Controller`
- Migrations: snake_case descriptive names (`create_users_table`)
- Events: past tense (`UserRegistered`, `OrderShipped`)
```

```markdown
<!-- claude_library/skills/react-19.md -->
---
name: react-19
category: tech
description: React 19 patterns, hooks, TypeScript conventions
built_in: true
---
# React 19 Conventions

## Components
- Functional components only, no class components
- TypeScript interfaces for all props, never `any`
- Co-locate component, types, and hooks in feature folders

## State & Data
- TanStack Query for server state (never fetch in useEffect)
- `useState` only for pure UI state (modals, toggles)
- Avoid prop drilling beyond 2 levels — use context or query cache

## Hooks
- Custom hooks prefixed `use`, return typed objects not arrays
- No business logic in components — extract to custom hooks

## Styling
- Tailwind CSS utility classes
- Shadcn/ui components as base
- `cn()` for conditional class merging

## Performance
- `useMemo`/`useCallback` only when profiling shows a problem
- Lazy load routes with `React.lazy`
```

```markdown
<!-- claude_library/skills/django.md -->
---
name: django
category: tech
description: Django patterns, ORM, DRF conventions
built_in: true
---
# Django Conventions

## Structure
- Fat models, thin views
- Managers for complex querysets
- `select_related` / `prefetch_related` to avoid N+1

## API (DRF)
- ViewSets with routers for CRUD
- Serializer validation, never validate in views
- `IsAuthenticated` as default permission class

## Testing
- pytest-django, `@pytest.mark.django_db`
- `baker` (model_bakery) for test data
- Test serializers and views separately

## Naming
- Models: singular PascalCase
- URLs: kebab-case
- Apps: plural snake_case
```

```markdown
<!-- claude_library/skills/fastapi.md -->
---
name: fastapi
category: tech
description: FastAPI patterns, async SQLAlchemy, Pydantic v2
built_in: true
---
# FastAPI Conventions

## Structure
- Routers are thin: no business logic, only HTTP wiring
- Services hold all business logic, accept AsyncSession
- Pydantic v2 schemas for request/response validation
- Custom exception hierarchy with global handler

## Database
- SQLAlchemy async ORM with `AsyncSession`
- `Mapped` typed columns, never use old-style `Column()`
- Migrations with Alembic

## Testing
- pytest-asyncio with `asyncio_mode = "auto"`
- In-memory SQLite for tests
- httpx `AsyncClient` with `ASGITransport`

## Error Handling
- Raise custom `AppError` subclasses in services
- Global exception handler in FastAPI maps to HTTP responses
- Never catch exceptions in routers
```

```markdown
<!-- claude_library/skills/nestjs.md -->
---
name: nestjs
category: tech
description: NestJS modules, decorators, TypeORM conventions
built_in: true
---
# NestJS Conventions

## Structure
- Feature modules: controller + service + module + entity
- DTOs with class-validator decorators for all inputs
- Repositories via TypeORM `@InjectRepository`

## Patterns
- Guards for auth, Pipes for validation, Interceptors for transformation
- Exception filters for consistent error responses
- `ConfigModule` for environment variables

## Testing
- Jest for unit tests, supertest for e2e
- `Test.createTestingModule` for unit test setup
- Mock services explicitly, never mock repositories in e2e
```

```markdown
<!-- claude_library/skills/crm.md -->
---
name: crm
category: domain
description: CRM domain patterns, contact management, pipeline, integrations
built_in: true
---
# CRM Domain Patterns

## Core Entities
- Contact (person), Account (company), Deal (opportunity)
- Activities: call, email, meeting — always linked to Contact or Deal
- Pipeline: stages with probability, expected close date

## Business Rules
- A Contact belongs to at most one Account (B2B CRM)
- Deals move through pipeline stages, never skip backward
- All activities must be logged — never delete, only mark completed/cancelled
- Duplicate detection on email and phone before creating Contact

## Integrations
- Email sync: always use IMAP/SMTP, store sent emails as Activities
- Calendar sync: bidirectional, avoid event duplication
- Webhooks for outbound notifications on stage changes

## Reporting
- Conversion rate = Deals won / Deals created in period
- Average deal cycle = days from creation to close
- Funnel view by stage counts and values
```

```markdown
<!-- claude_library/skills/saas.md -->
---
name: saas
category: domain
description: SaaS patterns, multi-tenancy, subscriptions, billing
built_in: true
---
# SaaS Domain Patterns

## Multi-tenancy
- Row-level tenancy: every table has `tenant_id` (or `organization_id`)
- Middleware enforces tenant isolation on every request
- Never expose cross-tenant data in API responses

## Subscriptions & Billing
- Plans: free, starter, pro, enterprise — always extendable
- Subscription state machine: trial → active → past_due → cancelled
- Billing via Stripe: webhook-driven state updates, never trust client
- Metered usage: record events, aggregate on billing cycle

## Onboarding
- Setup wizard captures org name, invites teammates, seeds initial data
- Trial period: 14 days, no credit card required

## Feature Flags
- Gate premium features by subscription plan
- Never hard-code plan checks — use feature flag service
```

- [ ] **Step 7: Create built-in agent files**

```markdown
<!-- claude_library/agents/backend-architect.md -->
---
name: backend-architect
category: architecture
description: Senior backend architect perspective — API design, DB schema, performance
built_in: true
---
# Backend Architect Agent

You are a senior backend architect reviewing and implementing this feature.

## Your Perspective
- Design APIs contract-first: define endpoints and schemas before implementation
- Database schema decisions are hard to reverse — think about indexing, normalization, and future queries upfront
- Question every N+1 query. Use query analysis tools to verify.
- Prefer explicit over implicit: no magic, no hidden side effects

## When Reviewing Plans
- Does the schema support the required queries efficiently?
- Are there missing indexes on foreign keys and filter columns?
- Is the transaction boundary correct?
- What happens when this endpoint is called concurrently 100 times?

## When Implementing
- Write migrations that are reversible
- Add indexes for every FK and every column used in WHERE/ORDER BY
- Document non-obvious schema decisions with comments
```

```markdown
<!-- claude_library/agents/frontend-expert.md -->
---
name: frontend-expert
category: architecture
description: Senior frontend engineer — UX, performance, accessibility
built_in: true
---
# Frontend Expert Agent

You are a senior frontend engineer implementing this feature.

## Your Perspective
- Every user interaction should feel instant — optimistic updates, skeleton states, no blank screens
- Accessibility is not optional: keyboard nav, ARIA labels, focus management
- Mobile-first: design for small screens, enhance for large

## When Reviewing Plans
- Is loading state handled for every async operation?
- Are error states user-friendly (not just "An error occurred")?
- Does the component tree make sense? Is state at the right level?

## When Implementing
- Use TanStack Query `isLoading`/`isError` for every fetch
- `useMutation` with `onSuccess` invalidation for writes
- Accessible form labels and ARIA where needed
```

```markdown
<!-- claude_library/agents/fullstack.md -->
---
name: fullstack
category: architecture
description: Fullstack engineer — end-to-end feature implementation, API + UI coherence
built_in: true
---
# Fullstack Agent

You are a fullstack engineer implementing this feature end-to-end.

## Your Perspective
- API contract first: define the API shape before writing frontend or backend code
- Keep frontend types in sync with backend schemas — no manual drift
- Test the full flow: create → read → update → delete

## When Implementing
- Backend first: models → service → router → tests
- Frontend second: types → API client → hooks → components
- Verify the API works with curl/httpx before wiring the UI
- One commit per layer: backend commit, then frontend commit
```

- [ ] **Step 8: Commit library structure**

```bash
git add claude_library/ backend/app/config.py
git commit -m "feat: claude_library structure with built-in skills, agents, and default templates"
```

---

## Task 4: SkillLibraryService

**Files:**
- Create: `backend/app/schemas/library.py`
- Create: `backend/app/services/skill_library_service.py`

- [ ] **Step 1: Create library schemas**

```python
# backend/app/schemas/library.py
from pydantic import BaseModel


class SkillMeta(BaseModel):
    name: str
    category: str
    description: str
    built_in: bool
    type: str  # "skill" | "agent"


class SkillCreate(BaseModel):
    name: str
    category: str
    description: str
    content: str


class SkillDetail(SkillMeta):
    content: str


class ProjectSkillOut(BaseModel):
    id: int
    project_id: str
    name: str
    type: str
    assigned_at: str


class ProjectSkillAssign(BaseModel):
    name: str
    type: str  # "skill" | "agent"
```

- [ ] **Step 2: Create SkillLibraryService**

```python
# backend/app/services/skill_library_service.py
from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AppError, NotFoundError
from app.models.project_skill import ProjectSkill
from app.schemas.library import SkillCreate, SkillDetail, SkillMeta


MANAGER_AI_MARKER_BEGIN = "<!-- MANAGER AI BEGIN -->"
MANAGER_AI_MARKER_END = "<!-- MANAGER AI END -->"


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a markdown file."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}
    return meta, parts[2].lstrip("\n")


class SkillLibraryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._library_path = Path(settings.claude_library_path)

    def _dir(self, type: str) -> Path:
        return self._library_path / ("skills" if type == "skill" else "agents")

    def list_available(self, type: str = "skill") -> list[SkillMeta]:
        """Read skill/agent files from the filesystem library."""
        directory = self._dir(type)
        if not directory.exists():
            return []
        result = []
        for path in sorted(directory.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            meta, _ = _parse_frontmatter(content)
            result.append(
                SkillMeta(
                    name=meta.get("name", path.stem),
                    category=meta.get("category", ""),
                    description=meta.get("description", ""),
                    built_in=bool(meta.get("built_in", False)),
                    type=type,
                )
            )
        return result

    def get_content(self, name: str, type: str) -> SkillDetail:
        """Return full skill detail including content."""
        path = self._dir(type) / f"{name}.md"
        if not path.exists():
            raise NotFoundError(f"{type} '{name}' not found in library")
        content = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        return SkillDetail(
            name=meta.get("name", path.stem),
            category=meta.get("category", ""),
            description=meta.get("description", ""),
            built_in=bool(meta.get("built_in", False)),
            type=type,
            content=body,
        )

    def create(self, data: SkillCreate, type: str) -> SkillMeta:
        """Create a new user-defined skill/agent file."""
        directory = self._dir(type)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{data.name}.md"
        if path.exists():
            raise AppError(f"{type} '{data.name}' already exists", status_code=409)
        frontmatter = (
            f"---\nname: {data.name}\ncategory: {data.category}\n"
            f"description: {data.description}\nbuilt_in: false\n---\n"
        )
        path.write_text(frontmatter + data.content, encoding="utf-8")
        return SkillMeta(
            name=data.name,
            category=data.category,
            description=data.description,
            built_in=False,
            type=type,
        )

    def update_content(self, name: str, type: str, content: str) -> None:
        """Update the body of a user-created skill (preserves frontmatter)."""
        path = self._dir(type) / f"{name}.md"
        if not path.exists():
            raise NotFoundError(f"{type} '{name}' not found")
        existing = path.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(existing)
        if meta.get("built_in"):
            raise AppError(f"Built-in {type} '{name}' cannot be edited via API", status_code=403)
        frontmatter = (
            f"---\nname: {meta.get('name', name)}\ncategory: {meta.get('category', '')}\n"
            f"description: {meta.get('description', '')}\nbuilt_in: false\n---\n"
        )
        path.write_text(frontmatter + content, encoding="utf-8")

    async def list_assigned(self, project_id: str) -> list[ProjectSkill]:
        result = await self.session.execute(
            select(ProjectSkill).where(ProjectSkill.project_id == project_id)
        )
        return list(result.scalars().all())

    async def assign(self, project_id: str, project_path: str, name: str, type: str) -> ProjectSkill:
        """Assign a skill to a project: DB record + file copy + CLAUDE.md update."""
        # Check skill exists in library
        src = self._dir(type) / f"{name}.md"
        if not src.exists():
            raise NotFoundError(f"{type} '{name}' not found in library")

        # Check not already assigned
        existing = await self.session.execute(
            select(ProjectSkill).where(
                ProjectSkill.project_id == project_id,
                ProjectSkill.name == name,
                ProjectSkill.type == type,
            )
        )
        if existing.scalar_one_or_none():
            raise AppError(f"{type} '{name}' already assigned to this project", status_code=409)

        # Copy file
        dest_dir = Path(project_path) / ".claude" / ("skills" if type == "skill" else "agents")
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_dir / f"{name}.md")

        # Update CLAUDE.md
        self._update_claude_md(project_path, project_id)

        # DB record
        skill = ProjectSkill(project_id=project_id, name=name, type=type)
        self.session.add(skill)
        await self.session.flush()
        return skill

    async def unassign(self, project_id: str, project_path: str, name: str, type: str) -> None:
        """Remove skill assignment: delete DB record + file + update CLAUDE.md."""
        result = await self.session.execute(
            select(ProjectSkill).where(
                ProjectSkill.project_id == project_id,
                ProjectSkill.name == name,
                ProjectSkill.type == type,
            )
        )
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError(f"{type} '{name}' not assigned to this project")

        # Remove file
        dest = Path(project_path) / ".claude" / ("skills" if type == "skill" else "agents") / f"{name}.md"
        if dest.exists():
            dest.unlink()

        await self.session.delete(skill)
        await self.session.flush()

        # Update CLAUDE.md
        self._update_claude_md(project_path, project_id)

    def _update_claude_md(self, project_path: str, project_id: str) -> None:
        """Rewrite the Manager AI section of the project's CLAUDE.md."""
        # Build new section content synchronously (no DB call — called after flush)
        claude_md = Path(project_path) / "CLAUDE.md"

        # We can't do an async DB query here, so read files from disk instead
        skills_dir = Path(project_path) / ".claude" / "skills"
        agents_dir = Path(project_path) / ".claude" / "agents"

        skill_lines = []
        if skills_dir.exists():
            for f in sorted(skills_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                desc = meta.get("description", "")
                skill_lines.append(f"- {f.stem}: {desc}")

        agent_lines = []
        if agents_dir.exists():
            for f in sorted(agents_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                desc = meta.get("description", "")
                agent_lines.append(f"- {f.stem}: {desc}")

        section_parts = []
        if skill_lines:
            section_parts.append("## Active Skills\n" + "\n".join(skill_lines))
        if agent_lines:
            section_parts.append("## Active Agents\n" + "\n".join(agent_lines))

        if section_parts:
            new_section = (
                f"{MANAGER_AI_MARKER_BEGIN}\n"
                + "\n\n".join(section_parts)
                + "\n\nUse the Skill tool to invoke any of the above when relevant.\n"
                + MANAGER_AI_MARKER_END
            )
        else:
            new_section = ""

        if claude_md.exists():
            existing = claude_md.read_text(encoding="utf-8")
            if MANAGER_AI_MARKER_BEGIN in existing:
                start = existing.index(MANAGER_AI_MARKER_BEGIN)
                end = existing.index(MANAGER_AI_MARKER_END) + len(MANAGER_AI_MARKER_END)
                before = existing[:start].rstrip("\n")
                after = existing[end:].lstrip("\n")
                if new_section:
                    updated = before + ("\n\n" if before else "") + new_section + ("\n\n" + after if after else "")
                else:
                    updated = before + ("\n\n" + after if after else "")
                claude_md.write_text(updated.strip() + "\n", encoding="utf-8")
            else:
                if new_section:
                    claude_md.write_text(existing.rstrip("\n") + "\n\n" + new_section + "\n", encoding="utf-8")
        else:
            if new_section:
                claude_md.write_text(new_section + "\n", encoding="utf-8")

    def get_skills_context(self, project_path: str) -> str:
        """Return a summary string of active skills for use in prompt templates."""
        skills_dir = Path(project_path) / ".claude" / "skills"
        agents_dir = Path(project_path) / ".claude" / "agents"
        lines = []

        if skills_dir.exists():
            for f in sorted(skills_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                lines.append(f"- Skill '{f.stem}': {meta.get('description', '')}")

        if agents_dir.exists():
            for f in sorted(agents_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                lines.append(f"- Agent '{f.stem}': {meta.get('description', '')}")

        if not lines:
            return ""
        return "\nActive project skills and agents:\n" + "\n".join(lines)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/library.py backend/app/services/skill_library_service.py
git commit -m "feat: SkillLibraryService — filesystem library + project assignment + CLAUDE.md management"
```

---

## Task 5: Library and Project Skills REST Endpoints

**Files:**
- Create: `backend/app/routers/library.py`
- Create: `backend/app/routers/project_skills.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create library router**

```python
# backend/app/routers/library.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.library import SkillCreate, SkillDetail, SkillMeta
from app.services.skill_library_service import SkillLibraryService

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/skills", response_model=list[SkillMeta])
async def list_skills(db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).list_available("skill")


@router.get("/agents", response_model=list[SkillMeta])
async def list_agents(db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).list_available("agent")


@router.get("/skills/{name}", response_model=SkillDetail)
async def get_skill(name: str, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).get_content(name, "skill")


@router.get("/agents/{name}", response_model=SkillDetail)
async def get_agent(name: str, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).get_content(name, "agent")


@router.post("/skills", response_model=SkillMeta, status_code=201)
async def create_skill(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).create(data, "skill")


@router.post("/agents", response_model=SkillMeta, status_code=201)
async def create_agent(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).create(data, "agent")


@router.put("/skills/{name}", status_code=204)
async def update_skill(name: str, data: SkillCreate, db: AsyncSession = Depends(get_db)):
    SkillLibraryService(db).update_content(name, "skill", data.content)


@router.put("/agents/{name}", status_code=204)
async def update_agent(name: str, data: SkillCreate, db: AsyncSession = Depends(get_db)):
    SkillLibraryService(db).update_content(name, "agent", data.content)
```

- [ ] **Step 2: Create project skills router**

```python
# backend/app/routers/project_skills.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError
from app.schemas.library import ProjectSkillAssign, ProjectSkillOut
from app.services.project_service import ProjectService
from app.services.skill_library_service import SkillLibraryService

router = APIRouter(prefix="/api/projects/{project_id}/skills", tags=["project-skills"])


@router.get("", response_model=list[ProjectSkillOut])
async def list_project_skills(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = SkillLibraryService(db)
    skills = await svc.list_assigned(project_id)
    return [
        ProjectSkillOut(
            id=s.id,
            project_id=s.project_id,
            name=s.name,
            type=s.type,
            assigned_at=s.assigned_at.isoformat(),
        )
        for s in skills
    ]


@router.post("", response_model=ProjectSkillOut, status_code=201)
async def assign_skill(
    project_id: str, data: ProjectSkillAssign, db: AsyncSession = Depends(get_db)
):
    project = await ProjectService(db).get_by_id(project_id)
    svc = SkillLibraryService(db)
    skill = await svc.assign(project_id, project.path, data.name, data.type)
    await db.commit()
    return ProjectSkillOut(
        id=skill.id,
        project_id=skill.project_id,
        name=skill.name,
        type=skill.type,
        assigned_at=skill.assigned_at.isoformat(),
    )


@router.delete("/{type}/{name}", status_code=204)
async def unassign_skill(
    project_id: str, type: str, name: str, db: AsyncSession = Depends(get_db)
):
    project = await ProjectService(db).get_by_id(project_id)
    svc = SkillLibraryService(db)
    await svc.unassign(project_id, project.path, name, type)
    await db.commit()
```

- [ ] **Step 3: Register routers in main.py**

```python
# backend/app/main.py — add to imports
from app.routers import (
    activity, events, files, issues, library, project_settings, project_skills,
    project_templates, projects, settings as settings_router, tasks, terminals, terminal_commands,
)

# add after existing include_router calls:
app.include_router(library.router)
app.include_router(project_skills.router)
app.include_router(project_templates.router)
```

- [ ] **Step 4: Write tests**

```python
# backend/tests/test_routers_library.py
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


@pytest.mark.asyncio
async def test_list_skills_returns_list(client):
    response = await client.get("/api/library/skills")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_agents_returns_list(client):
    response = await client.get("/api/library/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_skill_not_found(client):
    response = await client.get("/api/library/skills/nonexistent-skill-xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_skill(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "claude_library_path", str(tmp_path))

    response = await client.post("/api/library/skills", json={
        "name": "test-skill",
        "category": "tech",
        "description": "A test skill",
        "content": "# Test\nSome content",
    })
    assert response.status_code == 201
    assert response.json()["name"] == "test-skill"

    get_resp = await client.get("/api/library/skills/test-skill")
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == "# Test\nSome content"
```

- [ ] **Step 5: Run tests**

```bash
cd backend
python -m pytest tests/test_routers_library.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/library.py backend/app/routers/project_skills.py \
        backend/tests/test_routers_library.py
git commit -m "feat: library and project-skills REST endpoints"
```

---

## Task 6: PromptTemplateService

**Files:**
- Create: `backend/app/schemas/prompt_template.py`
- Create: `backend/app/services/prompt_template_service.py`

- [ ] **Step 1: Create prompt template schemas**

```python
# backend/app/schemas/prompt_template.py
from pydantic import BaseModel


class TemplateInfo(BaseModel):
    type: str
    content: str
    is_overridden: bool


class TemplateSave(BaseModel):
    content: str
```

- [ ] **Step 2: Write failing test**

```python
# backend/tests/test_prompt_template_service.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event

from app.database import Base
from app.models import PromptTemplate  # noqa: F401


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_resolve_falls_back_to_file(session, tmp_path):
    from app.config import settings
    from app.services.prompt_template_service import PromptTemplateService

    # Create a template file
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "workflow.md").write_text(
        "---\ntype: workflow\n---\nHello {{project_name}}", encoding="utf-8"
    )

    svc = PromptTemplateService(session, library_path=str(tmp_path))
    result = await svc.resolve("workflow", "proj-1", {"project_name": "MyApp"})
    assert result == "Hello MyApp"


@pytest.mark.asyncio
async def test_db_override_takes_priority(session, tmp_path):
    from app.models.prompt_template import PromptTemplate
    from app.services.prompt_template_service import PromptTemplateService

    # Add a file fallback
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "workflow.md").write_text("---\ntype: workflow\n---\nFile content", encoding="utf-8")

    # Add DB override
    session.add(PromptTemplate(project_id="proj-1", type="workflow", content="DB override {{project_name}}"))
    await session.flush()

    svc = PromptTemplateService(session, library_path=str(tmp_path))
    result = await svc.resolve("workflow", "proj-1", {"project_name": "X"})
    assert result == "DB override X"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_prompt_template_service.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 4: Implement PromptTemplateService**

```python
# backend/app/services/prompt_template_service.py
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.prompt_template import PromptTemplate
from app.schemas.prompt_template import TemplateInfo


def _parse_template_file(path: Path) -> str:
    """Read template file, strip YAML frontmatter, return body."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) >= 3 else content


TEMPLATE_TYPES = ["spec", "plan", "recap", "enrich", "workflow", "implementation"]


class PromptTemplateService:
    def __init__(self, session: AsyncSession, library_path: str | None = None):
        self.session = session
        self._library = Path(library_path or settings.claude_library_path)

    async def resolve(
        self, type: str, project_id: str, variables: dict[str, str]
    ) -> str:
        """Resolve template with variable substitution.

        Priority: DB override → file default → empty string fallback.
        """
        content = await self._get_raw(type, project_id)
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

    async def get_template_info(self, type: str, project_id: str) -> TemplateInfo:
        row = await self._get_db_override(type, project_id)
        if row:
            return TemplateInfo(type=type, content=row.content, is_overridden=True)
        file_content = self._read_file(type)
        return TemplateInfo(type=type, content=file_content, is_overridden=False)

    async def list_for_project(self, project_id: str) -> list[TemplateInfo]:
        return [
            await self.get_template_info(t, project_id) for t in TEMPLATE_TYPES
        ]

    async def save_override(self, type: str, project_id: str, content: str) -> None:
        row = await self._get_db_override(type, project_id)
        if row:
            row.content = content
        else:
            self.session.add(
                PromptTemplate(project_id=project_id, type=type, content=content)
            )
        await self.session.flush()

    async def delete_override(self, type: str, project_id: str) -> None:
        row = await self._get_db_override(type, project_id)
        if row:
            await self.session.delete(row)
            await self.session.flush()

    # ── private ──────────────────────────────────────────────────────────────

    async def _get_raw(self, type: str, project_id: str) -> str:
        row = await self._get_db_override(type, project_id)
        if row:
            return row.content
        return self._read_file(type)

    async def _get_db_override(self, type: str, project_id: str) -> PromptTemplate | None:
        result = await self.session.execute(
            select(PromptTemplate).where(
                PromptTemplate.project_id == project_id,
                PromptTemplate.type == type,
            )
        )
        return result.scalar_one_or_none()

    def _read_file(self, type: str) -> str:
        path = self._library / "templates" / f"{type}.md"
        if not path.exists():
            return ""
        return _parse_template_file(path)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_prompt_template_service.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/prompt_template.py \
        backend/app/services/prompt_template_service.py \
        backend/tests/test_prompt_template_service.py
git commit -m "feat: PromptTemplateService — DB override + file fallback with variable resolution"
```

---

## Task 7: Project Templates REST Endpoints

**Files:**
- Create: `backend/app/routers/project_templates.py`
- Create: `backend/tests/test_routers_project_templates.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_routers_project_templates.py
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
async def project_id(client):
    resp = await client.post("/api/projects", json={"name": "P", "path": "/tmp/p"})
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_templates_returns_all_types(client, project_id):
    response = await client.get(f"/api/projects/{project_id}/templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    types = {item["type"] for item in data}
    assert "workflow" in types
    assert "implementation" in types


@pytest.mark.asyncio
async def test_save_and_retrieve_override(client, project_id):
    resp = await client.put(
        f"/api/projects/{project_id}/templates/workflow",
        json={"content": "Custom prompt {{project_name}}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_overridden"] is True

    get_resp = await client.get(f"/api/projects/{project_id}/templates/workflow")
    assert get_resp.json()["content"] == "Custom prompt {{project_name}}"


@pytest.mark.asyncio
async def test_delete_override_restores_default(client, project_id):
    await client.put(
        f"/api/projects/{project_id}/templates/workflow",
        json={"content": "Override"},
    )
    del_resp = await client.delete(f"/api/projects/{project_id}/templates/workflow")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/projects/{project_id}/templates/workflow")
    assert get_resp.json()["is_overridden"] is False
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
python -m pytest tests/test_routers_project_templates.py -v
```

Expected: FAIL (router not found / 404).

- [ ] **Step 3: Create project templates router**

```python
# backend/app/routers/project_templates.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.prompt_template import TemplateInfo, TemplateSave
from app.services.prompt_template_service import PromptTemplateService

router = APIRouter(prefix="/api/projects/{project_id}/templates", tags=["project-templates"])


@router.get("", response_model=list[TemplateInfo])
async def list_templates(project_id: str, db: AsyncSession = Depends(get_db)):
    return await PromptTemplateService(db).list_for_project(project_id)


@router.get("/{type}", response_model=TemplateInfo)
async def get_template(project_id: str, type: str, db: AsyncSession = Depends(get_db)):
    return await PromptTemplateService(db).get_template_info(type, project_id)


@router.put("/{type}", response_model=TemplateInfo)
async def save_template_override(
    project_id: str, type: str, data: TemplateSave, db: AsyncSession = Depends(get_db)
):
    svc = PromptTemplateService(db)
    await svc.save_override(type, project_id, data.content)
    await db.commit()
    return await svc.get_template_info(type, project_id)


@router.delete("/{type}", status_code=204)
async def delete_template_override(
    project_id: str, type: str, db: AsyncSession = Depends(get_db)
):
    svc = PromptTemplateService(db)
    await svc.delete_override(type, project_id)
    await db.commit()
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd backend
python -m pytest tests/test_routers_project_templates.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/project_templates.py \
        backend/tests/test_routers_project_templates.py
git commit -m "feat: project templates REST endpoints (GET/PUT/DELETE)"
```

---

## Task 8: Hook Migration

**Files:**
- Modify: `backend/app/hooks/handlers/auto_start_workflow.py`
- Modify: `backend/app/hooks/handlers/auto_start_implementation.py`
- Modify: `backend/app/hooks/handlers/auto_completion.py`
- Modify: `backend/app/hooks/handlers/start_analysis.py`

- [ ] **Step 1: Update auto_start_workflow.py**

Replace the entire file:

```python
# backend/app/hooks/handlers/auto_start_workflow.py
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService
from app.services.prompt_template_service import PromptTemplateService
from app.services.settings_service import SettingsService
from app.services.skill_library_service import SkillLibraryService


@hook(event=HookEvent.ISSUE_CREATED)
class AutoStartWorkflow(BaseHook):
    name = "auto_start_workflow"
    description = "Avvia automaticamente spec+piano+task quando viene creata una issue"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            enabled = await svc.get(context.project_id, "auto_workflow_enabled", default="false")
            if enabled != "true":
                return HookResult(success=True, output="auto_workflow disabled for this project")
            legacy_prompt = await svc.get(context.project_id, "auto_workflow_prompt", default="")
            timeout_str = await svc.get(context.project_id, "auto_workflow_timeout", default="600")
            paused = await SettingsService(session).get("work_queue_paused")

        if paused == "true":
            return HookResult(success=True, output="work queue is paused")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 600

        project_path = context.metadata.get("project_path", "")

        # Build variables dict
        variables = {
            "issue_description": context.metadata.get("issue_description", ""),
            "project_name": context.metadata.get("project_name", ""),
            "project_description": context.metadata.get("project_description", ""),
            "tech_stack": context.metadata.get("tech_stack", ""),
            "skills_context": SkillLibraryService(None).get_skills_context(project_path),
        }

        # Legacy override takes priority over DB templates for backwards compatibility
        if legacy_prompt:
            prompt = legacy_prompt
            for key, value in variables.items():
                prompt = prompt.replace(f"{{{{{key}}}}}", value)
        else:
            async with async_session() as session:
                prompt = await PromptTemplateService(session).resolve(
                    "workflow", context.project_id, variables
                )

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": context.project_id,
                "MANAGER_AI_ISSUE_ID": context.issue_id,
            },
            timeout=timeout,
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
```

- [ ] **Step 2: Update auto_start_implementation.py**

Replace the entire file:

```python
# backend/app/hooks/handlers/auto_start_implementation.py
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService
from app.services.prompt_template_service import PromptTemplateService
from app.services.settings_service import SettingsService
from app.services.skill_library_service import SkillLibraryService


@hook(event=HookEvent.ISSUE_ACCEPTED)
class AutoStartImplementation(BaseHook):
    name = "auto_start_implementation"
    description = "Avvia automaticamente l'implementazione quando una issue viene accettata"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            enabled = await svc.get(context.project_id, "auto_implementation_enabled", default="false")
            if enabled != "true":
                return HookResult(success=True, output="auto_implementation disabled for this project")
            timeout_str = await svc.get(context.project_id, "auto_implementation_timeout", default="900")
            paused = await SettingsService(session).get("work_queue_paused")

        if paused == "true":
            return HookResult(success=True, output="work queue is paused")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 900

        project_path = context.metadata.get("project_path", "")

        variables = {
            "issue_name": context.metadata.get("issue_name", ""),
            "project_name": context.metadata.get("project_name", ""),
            "project_description": context.metadata.get("project_description", ""),
            "tech_stack": context.metadata.get("tech_stack", ""),
            "issue_spec": context.metadata.get("specification", ""),
            "issue_plan": context.metadata.get("plan", ""),
            "skills_context": SkillLibraryService(None).get_skills_context(project_path),
        }

        async with async_session() as session:
            prompt = await PromptTemplateService(session).resolve(
                "implementation", context.project_id, variables
            )

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": context.project_id,
                "MANAGER_AI_ISSUE_ID": context.issue_id,
            },
            timeout=timeout,
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
```

- [ ] **Step 3: Update auto_completion.py**

Replace only the `auto` mode prompt block in `execute()`:

```python
        if mode == "auto":
            project_path = context.metadata.get("project_path", "")
            variables = {
                "issue_name": issue_name,
                "skills_context": SkillLibraryService(None).get_skills_context(project_path),
            }
            async with async_session() as session:
                prompt = await PromptTemplateService(session).resolve(
                    "recap", context.project_id, variables
                )
```

Add imports at top of file:
```python
from app.services.prompt_template_service import PromptTemplateService
from app.services.skill_library_service import SkillLibraryService
```

- [ ] **Step 4: Update start_analysis.py**

Replace entire file:

```python
# backend/app/hooks/handlers/start_analysis.py
from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.prompt_template_service import PromptTemplateService
from app.services.skill_library_service import SkillLibraryService


@hook(event=HookEvent.ISSUE_ANALYSIS_STARTED)
class StartAnalysis(BaseHook):
    name = "start_analysis"
    description = "Avvia Claude Code per scrivere spec, piano e task della issue"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        project_path = context.metadata.get("project_path", "")

        variables = {
            "issue_description": context.metadata.get("issue_description", ""),
            "project_name": context.metadata.get("project_name", ""),
            "project_description": context.metadata.get("project_description", ""),
            "tech_stack": context.metadata.get("tech_stack", ""),
            "skills_context": SkillLibraryService(None).get_skills_context(project_path),
        }

        async with async_session() as session:
            prompt = await PromptTemplateService(session).resolve(
                "workflow", context.project_id, variables
            )

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": context.project_id,
                "MANAGER_AI_ISSUE_ID": context.issue_id,
            },
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
```

- [ ] **Step 5: Run existing tests to verify nothing broken**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all existing tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/hooks/handlers/
git commit -m "feat: hook handlers use PromptTemplateService for prompt resolution"
```

---

## Task 9: MCP Tool Description Resolver (5.3)

**Files:**
- Create: `backend/app/services/mcp_tool_description_service.py`
- Modify: `backend/app/hooks/executor.py`

- [ ] **Step 1: Create McpToolDescriptionService**

```python
# backend/app/services/mcp_tool_description_service.py
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.project_setting_service import ProjectSettingService

_MCP_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "mcp" / "default_settings.json"
_TOOL_DESC_PREFIX = "mcp_tool_desc."


class McpToolDescriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._defaults: dict[str, str] = self._load_defaults()

    def _load_defaults(self) -> dict[str, str]:
        if not _MCP_SETTINGS_PATH.exists():
            return {}
        data = json.loads(_MCP_SETTINGS_PATH.read_text(encoding="utf-8"))
        return {
            k.removeprefix("tool.").removesuffix(".description"): v
            for k, v in data.items()
            if k.startswith("tool.") and k.endswith(".description")
        }

    async def get_project_overrides(self, project_id: str) -> dict[str, str]:
        """Return {tool_name: custom_description} for all overrides on this project."""
        svc = ProjectSettingService(self.session)
        all_settings = await svc.get_all_for_project(project_id)
        return {
            k.removeprefix(_TOOL_DESC_PREFIX): v
            for k, v in all_settings.items()
            if k.startswith(_TOOL_DESC_PREFIX)
        }

    async def build_tool_guidance(self, project_id: str) -> str:
        """Build a [Tool guidance] block to inject into prompts, if any overrides exist."""
        overrides = await self.get_project_overrides(project_id)
        if not overrides:
            return ""
        lines = ["[Tool guidance for this project]"]
        for tool, desc in overrides.items():
            lines.append(f"{tool}: {desc}")
        return "\n".join(lines)
```

- [ ] **Step 2: Inject tool guidance in executor**

Modify `ClaudeCodeExecutor.run()` to accept an optional `tool_guidance` param and prepend it to the prompt:

```python
# backend/app/hooks/executor.py — update run() signature and body
    async def run(
        self,
        prompt: str,
        project_path: str,
        env_vars: dict | None = None,
        timeout: int = 300,
        tool_guidance: str = "",
    ) -> ExecutorResult:
        if tool_guidance:
            prompt = tool_guidance + "\n\n" + prompt
        # ... rest unchanged
```

- [ ] **Step 3: Update hook handlers to pass tool guidance**

In each hook handler (`auto_start_workflow`, `auto_start_implementation`, `start_analysis`), add before `executor.run()`:

```python
        async with async_session() as session:
            from app.services.mcp_tool_description_service import McpToolDescriptionService
            tool_guidance = await McpToolDescriptionService(session).build_tool_guidance(
                context.project_id
            )

        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={...},
            timeout=timeout,
            tool_guidance=tool_guidance,
        )
```

- [ ] **Step 4: Run tests**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mcp_tool_description_service.py \
        backend/app/hooks/executor.py \
        backend/app/hooks/handlers/
git commit -m "feat: MCP tool description overrides injected into hook prompts (5.3)"
```

---

## Task 10: Frontend — Types and API Layer

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Create: `frontend/src/features/library/api.ts`
- Create: `frontend/src/features/library/hooks.ts`
- Create: `frontend/src/features/projects/api-skills.ts`
- Create: `frontend/src/features/projects/hooks-skills.ts`
- Create: `frontend/src/features/projects/api-templates.ts`
- Create: `frontend/src/features/projects/hooks-templates.ts`

- [ ] **Step 1: Add types to shared/types/index.ts**

Append to the end of the file:

```typescript
// ── Library ──

export interface SkillMeta {
  name: string;
  category: string;
  description: string;
  built_in: boolean;
  type: "skill" | "agent";
}

export interface SkillDetail extends SkillMeta {
  content: string;
}

export interface SkillCreate {
  name: string;
  category: string;
  description: string;
  content: string;
}

export interface ProjectSkill {
  id: number;
  project_id: string;
  name: string;
  type: "skill" | "agent";
  assigned_at: string;
}

export interface ProjectSkillAssign {
  name: string;
  type: "skill" | "agent";
}

// ── Prompt Templates ──

export interface TemplateInfo {
  type: string;
  content: string;
  is_overridden: boolean;
}

export interface TemplateSave {
  content: string;
}
```

- [ ] **Step 2: Create library API**

```typescript
// frontend/src/features/library/api.ts
import { request } from "@/shared/api/client";
import type { SkillCreate, SkillDetail, SkillMeta } from "@/shared/types";

export function fetchSkills(): Promise<SkillMeta[]> {
  return request("/library/skills");
}

export function fetchAgents(): Promise<SkillMeta[]> {
  return request("/library/agents");
}

export function fetchSkill(name: string): Promise<SkillDetail> {
  return request(`/library/skills/${name}`);
}

export function fetchAgent(name: string): Promise<SkillDetail> {
  return request(`/library/agents/${name}`);
}

export function createSkill(data: SkillCreate): Promise<SkillMeta> {
  return request("/library/skills", { method: "POST", body: JSON.stringify(data) });
}

export function createAgent(data: SkillCreate): Promise<SkillMeta> {
  return request("/library/agents", { method: "POST", body: JSON.stringify(data) });
}

export function updateSkill(name: string, data: SkillCreate): Promise<null> {
  return request(`/library/skills/${name}`, { method: "PUT", body: JSON.stringify(data) });
}
```

- [ ] **Step 3: Create library hooks**

```typescript
// frontend/src/features/library/hooks.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { SkillCreate } from "@/shared/types";

export const libraryKeys = {
  skills: ["library", "skills"] as const,
  agents: ["library", "agents"] as const,
  skill: (name: string) => ["library", "skills", name] as const,
  agent: (name: string) => ["library", "agents", name] as const,
};

export function useSkills() {
  return useQuery({ queryKey: libraryKeys.skills, queryFn: api.fetchSkills });
}

export function useAgents() {
  return useQuery({ queryKey: libraryKeys.agents, queryFn: api.fetchAgents });
}

export function useSkillDetail(name: string) {
  return useQuery({
    queryKey: libraryKeys.skill(name),
    queryFn: () => api.fetchSkill(name),
    enabled: !!name,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillCreate) => api.createSkill(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: libraryKeys.skills }),
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillCreate) => api.createAgent(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: libraryKeys.agents }),
  });
}
```

- [ ] **Step 4: Create project skills API and hooks**

```typescript
// frontend/src/features/projects/api-skills.ts
import { request } from "@/shared/api/client";
import type { ProjectSkill, ProjectSkillAssign } from "@/shared/types";

export function fetchProjectSkills(projectId: string): Promise<ProjectSkill[]> {
  return request(`/projects/${projectId}/skills`);
}

export function assignSkill(projectId: string, data: ProjectSkillAssign): Promise<ProjectSkill> {
  return request(`/projects/${projectId}/skills`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function unassignSkill(projectId: string, type: string, name: string): Promise<null> {
  return request(`/projects/${projectId}/skills/${type}/${name}`, { method: "DELETE" });
}
```

```typescript
// frontend/src/features/projects/hooks-skills.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-skills";
import type { ProjectSkillAssign } from "@/shared/types";

export const skillKeys = {
  project: (id: string) => ["projects", id, "skills"] as const,
};

export function useProjectSkills(projectId: string) {
  return useQuery({
    queryKey: skillKeys.project(projectId),
    queryFn: () => api.fetchProjectSkills(projectId),
    enabled: !!projectId,
  });
}

export function useAssignSkill(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectSkillAssign) => api.assignSkill(projectId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: skillKeys.project(projectId) }),
  });
}

export function useUnassignSkill(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, name }: { type: string; name: string }) =>
      api.unassignSkill(projectId, type, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: skillKeys.project(projectId) }),
  });
}
```

- [ ] **Step 5: Create project templates API and hooks**

```typescript
// frontend/src/features/projects/api-templates.ts
import { request } from "@/shared/api/client";
import type { TemplateInfo, TemplateSave } from "@/shared/types";

export function fetchProjectTemplates(projectId: string): Promise<TemplateInfo[]> {
  return request(`/projects/${projectId}/templates`);
}

export function fetchProjectTemplate(projectId: string, type: string): Promise<TemplateInfo> {
  return request(`/projects/${projectId}/templates/${type}`);
}

export function saveTemplateOverride(
  projectId: string,
  type: string,
  data: TemplateSave,
): Promise<TemplateInfo> {
  return request(`/projects/${projectId}/templates/${type}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteTemplateOverride(projectId: string, type: string): Promise<null> {
  return request(`/projects/${projectId}/templates/${type}`, { method: "DELETE" });
}
```

```typescript
// frontend/src/features/projects/hooks-templates.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-templates";

export const templateKeys = {
  project: (id: string) => ["projects", id, "templates"] as const,
};

export function useProjectTemplates(projectId: string) {
  return useQuery({
    queryKey: templateKeys.project(projectId),
    queryFn: () => api.fetchProjectTemplates(projectId),
    enabled: !!projectId,
  });
}

export function useSaveTemplate(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, content }: { type: string; content: string }) =>
      api.saveTemplateOverride(projectId, type, { content }),
    onSuccess: () => qc.invalidateQueries({ queryKey: templateKeys.project(projectId) }),
  });
}

export function useDeleteTemplate(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (type: string) => api.deleteTemplateOverride(projectId, type),
    onSuccess: () => qc.invalidateQueries({ queryKey: templateKeys.project(projectId) }),
  });
}
```

- [ ] **Step 6: Lint check**

```bash
cd frontend
npm run lint
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/shared/types/index.ts \
        frontend/src/features/library/ \
        frontend/src/features/projects/api-skills.ts \
        frontend/src/features/projects/hooks-skills.ts \
        frontend/src/features/projects/api-templates.ts \
        frontend/src/features/projects/hooks-templates.ts
git commit -m "feat: frontend types and API layer for library, project skills, templates"
```

---

## Task 11: Frontend — Library Page (`/library`)

**Files:**
- Create: `frontend/src/routes/library.tsx`

- [ ] **Step 1: Create the library route**

```tsx
// frontend/src/routes/library.tsx
import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useSkills, useAgents, useCreateSkill, useCreateAgent } from "@/features/library/hooks";
import { useSkillDetail } from "@/features/library/hooks";
import type { SkillMeta } from "@/shared/types";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Input } from "@/shared/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";

export const Route = createFileRoute("/library")({
  component: LibraryPage,
});

function SkillCard({
  skill,
  onSelect,
}: {
  skill: SkillMeta;
  onSelect: (skill: SkillMeta) => void;
}) {
  return (
    <div
      className="border rounded-lg p-4 cursor-pointer hover:border-primary transition-colors"
      onClick={() => onSelect(skill)}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="font-medium text-sm">{skill.name}</span>
        <div className="flex gap-1 shrink-0">
          <Badge variant="outline" className="text-xs">{skill.category}</Badge>
          {skill.built_in && (
            <Badge variant="secondary" className="text-xs">Built-in</Badge>
          )}
          {!skill.built_in && (
            <Badge className="text-xs">Custom</Badge>
          )}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{skill.description}</p>
    </div>
  );
}

function CreateSkillDialog({
  open,
  type,
  onClose,
  onCreate,
}: {
  open: boolean;
  type: "skill" | "agent";
  onClose: () => void;
  onCreate: (data: { name: string; category: string; description: string; content: string }) => void;
}) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");

  const handleSubmit = () => {
    if (!name || !category) return;
    onCreate({ name, category, description, content });
    setName(""); setCategory(""); setDescription(""); setContent("");
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>New {type === "skill" ? "Skill" : "Agent"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input placeholder="name (e.g. my-framework)" value={name} onChange={e => setName(e.target.value)} />
          <Input placeholder="category (tech / domain / architecture)" value={category} onChange={e => setCategory(e.target.value)} />
          <Input placeholder="short description" value={description} onChange={e => setDescription(e.target.value)} />
          <Textarea
            placeholder="Markdown content..."
            value={content}
            onChange={e => setContent(e.target.value)}
            rows={12}
            className="font-mono text-xs"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={!name || !category}>Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LibraryPage() {
  const { data: skills = [] } = useSkills();
  const { data: agents = [] } = useAgents();
  const createSkill = useCreateSkill();
  const createAgent = useCreateAgent();
  const [selected, setSelected] = useState<SkillMeta | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createType, setCreateType] = useState<"skill" | "agent">("skill");
  const [filter, setFilter] = useState<"all" | "tech" | "domain" | "architecture">("all");

  const { data: detail } = useSkillDetail(
    selected?.type === "skill" ? selected.name : ""
  );

  const allItems = [
    ...skills.map(s => ({ ...s, type: "skill" as const })),
    ...agents.map(a => ({ ...a, type: "agent" as const })),
  ];
  const filtered = filter === "all" ? allItems : allItems.filter(s => s.category === filter);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Library</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Skills and agents available for assignment to projects
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => { setCreateType("skill"); setCreateOpen(true); }}>
            + New Skill
          </Button>
          <Button variant="outline" size="sm" onClick={() => { setCreateType("agent"); setCreateOpen(true); }}>
            + New Agent
          </Button>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {(["all", "tech", "domain", "architecture"] as const).map(f => (
          <Button
            key={f}
            variant={filter === f ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(f)}
          >
            {f}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-1 space-y-2">
          {filtered.map(skill => (
            <SkillCard key={`${skill.type}-${skill.name}`} skill={skill} onSelect={setSelected} />
          ))}
          {filtered.length === 0 && (
            <p className="text-sm text-muted-foreground">No items found.</p>
          )}
        </div>

        <div className="col-span-2">
          {selected ? (
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <h2 className="font-semibold">{selected.name}</h2>
                <Badge variant="outline">{selected.category}</Badge>
                <Badge variant={selected.built_in ? "secondary" : "default"}>
                  {selected.built_in ? "Built-in" : "Custom"}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-4">{selected.description}</p>
              {detail && (
                <pre className="text-xs bg-muted rounded p-3 overflow-auto max-h-96 whitespace-pre-wrap">
                  {detail.content}
                </pre>
              )}
            </div>
          ) : (
            <div className="border rounded-lg p-8 flex items-center justify-center text-muted-foreground text-sm">
              Select a skill or agent to preview its content
            </div>
          )}
        </div>
      </div>

      <CreateSkillDialog
        open={createOpen}
        type={createType}
        onClose={() => setCreateOpen(false)}
        onCreate={data =>
          createType === "skill"
            ? createSkill.mutate(data)
            : createAgent.mutate(data)
        }
      />
    </div>
  );
}
```

- [ ] **Step 2: Lint check**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/library.tsx frontend/src/features/library/
git commit -m "feat: global /library page with skill/agent browser and creation"
```

---

## Task 12: Frontend — ProjectDetailPage Library Tab

**Files:**
- Create: `frontend/src/routes/projects/$projectId/library.tsx`
- Create: `frontend/src/features/projects/components/library-tab.tsx`

- [ ] **Step 1: Create the library-tab component**

```tsx
// frontend/src/features/projects/components/library-tab.tsx
import { useState } from "react";
import { useSkills, useAgents } from "@/features/library/hooks";
import { useProjectSkills, useAssignSkill, useUnassignSkill } from "@/features/projects/hooks-skills";
import { useProjectTemplates, useSaveTemplate, useDeleteTemplate } from "@/features/projects/hooks-templates";
import type { SkillMeta, TemplateInfo } from "@/shared/types";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";

// ── Skills Section ────────────────────────────────────────────────────────────

function SkillsSection({ projectId }: { projectId: string }) {
  const { data: allSkills = [] } = useSkills();
  const { data: allAgents = [] } = useAgents();
  const { data: assigned = [] } = useProjectSkills(projectId);
  const assign = useAssignSkill(projectId);
  const unassign = useUnassignSkill(projectId);

  const assignedNames = new Set(assigned.map(s => `${s.type}:${s.name}`));

  const available = [
    ...allSkills.map(s => ({ ...s, type: "skill" as const })),
    ...allAgents.map(a => ({ ...a, type: "agent" as const })),
  ];

  const assignedItems = assigned.map(a => {
    const meta = available.find(s => s.name === a.name && s.type === a.type);
    return { ...a, description: meta?.description ?? "", category: meta?.category ?? "" };
  });

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Skills &amp; Agents</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-muted-foreground mb-2">Available in library</p>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {available.map(skill => {
              const key = `${skill.type}:${skill.name}`;
              const isAssigned = assignedNames.has(key);
              return (
                <div key={key} className="flex items-start justify-between border rounded p-2 gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1">
                      <span className="text-xs font-medium truncate">{skill.name}</span>
                      <Badge variant="outline" className="text-xs shrink-0">{skill.category}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{skill.description}</p>
                  </div>
                  <Button
                    size="sm"
                    variant={isAssigned ? "secondary" : "outline"}
                    className="text-xs shrink-0"
                    disabled={isAssigned || assign.isPending}
                    onClick={() => assign.mutate({ name: skill.name, type: skill.type })}
                  >
                    {isAssigned ? "Active" : "Add"}
                  </Button>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <p className="text-xs text-muted-foreground mb-2">Active in this project</p>
          {assignedItems.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">No skills assigned yet.</p>
          ) : (
            <div className="space-y-2">
              {assignedItems.map(skill => (
                <div key={`${skill.type}:${skill.name}`} className="flex items-start justify-between border rounded p-2 border-primary/30 bg-primary/5 gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1">
                      <span className="text-xs font-medium truncate">{skill.name}</span>
                      <Badge variant="outline" className="text-xs shrink-0">{skill.category}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{skill.description}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-xs text-destructive shrink-0"
                    disabled={unassign.isPending}
                    onClick={() => unassign.mutate({ type: skill.type, name: skill.name })}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Templates Section ─────────────────────────────────────────────────────────

const TEMPLATE_LABELS: Record<string, string> = {
  workflow: "Workflow (spec + plan + tasks)",
  implementation: "Implementation",
  recap: "Recap (auto-completion)",
  spec: "Specification",
  plan: "Plan",
  enrich: "Context Enrichment",
};

const TEMPLATE_VARS = "{{issue_description}} {{issue_spec}} {{issue_plan}} {{project_name}} {{project_description}} {{tech_stack}} {{skills_context}}";

function TemplateRow({ tpl, projectId }: { tpl: TemplateInfo; projectId: string }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(tpl.content);
  const save = useSaveTemplate(projectId);
  const del = useDeleteTemplate(projectId);

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{TEMPLATE_LABELS[tpl.type] ?? tpl.type}</span>
          <Badge variant={tpl.is_overridden ? "default" : "secondary"} className="text-xs">
            {tpl.is_overridden ? "Custom" : "Default"}
          </Badge>
        </div>
        <div className="flex gap-1">
          {!editing && (
            <Button size="sm" variant="outline" className="text-xs" onClick={() => { setDraft(tpl.content); setEditing(true); }}>
              Edit
            </Button>
          )}
          {tpl.is_overridden && !editing && (
            <Button size="sm" variant="ghost" className="text-xs text-destructive" onClick={() => del.mutate(tpl.type)}>
              Reset
            </Button>
          )}
        </div>
      </div>

      {editing ? (
        <div className="space-y-2">
          <Textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={8}
            className="font-mono text-xs"
          />
          <p className="text-xs text-muted-foreground">Variables: {TEMPLATE_VARS}</p>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => { save.mutate({ type: tpl.type, content: draft }); setEditing(false); }}>
              Save
            </Button>
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </div>
      ) : (
        <pre className="text-xs bg-muted rounded p-2 max-h-24 overflow-hidden whitespace-pre-wrap text-muted-foreground">
          {tpl.content.slice(0, 200)}{tpl.content.length > 200 ? "…" : ""}
        </pre>
      )}
    </div>
  );
}

function TemplatesSection({ projectId }: { projectId: string }) {
  const { data: templates = [] } = useProjectTemplates(projectId);

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">Prompt Templates</h3>
      {templates.map(tpl => (
        <TemplateRow key={tpl.type} tpl={tpl} projectId={projectId} />
      ))}
    </div>
  );
}

// ── Main Export ───────────────────────────────────────────────────────────────

export function LibraryTab({ projectId }: { projectId: string }) {
  const [section, setSection] = useState<"skills" | "templates">("skills");

  return (
    <div className="space-y-6">
      <div className="flex gap-2 border-b pb-2">
        <Button
          variant={section === "skills" ? "default" : "ghost"}
          size="sm"
          onClick={() => setSection("skills")}
        >
          Skills &amp; Agents
        </Button>
        <Button
          variant={section === "templates" ? "default" : "ghost"}
          size="sm"
          onClick={() => setSection("templates")}
        >
          Prompt Templates
        </Button>
      </div>

      {section === "skills" && <SkillsSection projectId={projectId} />}
      {section === "templates" && <TemplatesSection projectId={projectId} />}
    </div>
  );
}
```

- [ ] **Step 2: Create the library route for a project**

```tsx
// frontend/src/routes/projects/$projectId/library.tsx
import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { LibraryTab } from "@/features/projects/components/library-tab";

export const Route = createFileRoute("/projects/$projectId/library")({
  component: ProjectLibraryPage,
});

function ProjectLibraryPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Library - ${project.name}` : "Library";
  }, [project]);

  return (
    <div className="p-6">
      {project && (
        <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
      )}
      <h1 className="text-xl font-semibold mb-6">Library</h1>
      <div className="max-w-4xl">
        <LibraryTab projectId={projectId} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Lint check**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/projects/\$projectId/library.tsx \
        frontend/src/features/projects/components/library-tab.tsx
git commit -m "feat: ProjectDetailPage Library tab — skills assignment and template editing"
```

---

## Task 13: Frontend — Navigation

**Files:**
- Modify: `frontend/src/shared/components/app-sidebar.tsx`

- [ ] **Step 1: Add `BookOpen` to lucide-react import**

```tsx
import {
  Activity,
  BookOpen,
  CircleDot,
  Download,
  FileText,
  FolderSync,
  MoreHorizontal,
  Pencil,
  Plug,
  Settings,
  SquareTerminal,
  Terminal,
  Zap,
} from "lucide-react";
```

- [ ] **Step 2: Add Library to `projectNav` array (after Automation)**

```tsx
        {
          label: "Automation",
          to: "/projects/$projectId/automation" as const,
          params: { projectId },
          icon: Zap,
        },
        {
          label: "Library",
          to: "/projects/$projectId/library" as const,
          params: { projectId },
          icon: BookOpen,
        },
```

- [ ] **Step 3: Add global Library to Global SidebarGroup (between Terminals and Settings)**

```tsx
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/library", fuzzy: true })}
                  >
                    <Link to="/library">
                      <BookOpen />
                      <span>Library</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
```

Insert this block between the Terminals `SidebarMenuItem` and the Settings `SidebarMenuItem`.

- [ ] **Step 4: Lint check**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/components/app-sidebar.tsx
git commit -m "feat: Library navigation links in sidebar (project tab + global)"
```

---

## Task 14: Final Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: all tests PASS, no failures.

- [ ] **Step 2: Start full stack and manual smoke test**

```bash
python start.py
```

Verify in browser:
1. `/library` loads and shows built-in skills (laravel-12, crm, etc.)
2. Creating a project and navigating to its Library tab shows Skills & Agents + Templates sections
3. Assigning `laravel-12` to a project creates the file at `<project_path>/.claude/skills/laravel-12.md`
4. Editing a template override saves and shows "Custom" badge
5. Resetting a template override restores "Default" badge

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Fase 5 — Prompt & Template System complete"
```
