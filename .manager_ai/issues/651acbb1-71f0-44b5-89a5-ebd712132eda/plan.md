# Favorite Projects — Implementation Plan

**Goal:** Add a star/favorite toggle on each project in the ProjectSidebar. Favorited projects sort to the top (most recent first), then non-favorites alphabetically.

**Approach:** Add `favorited_at` (nullable datetime) to the projects table. Reuse existing `PUT /api/projects/{id}` for toggling. Frontend uses `SidebarMenuAction` with `showOnHover` + `Star` icon from lucide-react. Backend sorts `favorited_at DESC NULLS LAST`, then `lower(name) ASC`.

**Tech Stack:** Python FastAPI + SQLAlchemy async + Alembic migrations. React + Vite + shadcn/ui sidebar + lucide-react icons + TanStack React Query.

---

## Task 1: Add `favorited_at` to Project model + migration

**Files:**
- Modify: `backend/app/models/project.py` (add column)
- Create: migration via alembic

Add `favorited_at: Mapped[datetime | None]` column after `archived_at`. Run `alembic revision --autogenerate` to create migration.

## Task 2: Update Project schemas

**File:** `backend/app/schemas/project.py`

Add `favorited_at: datetime | None = None` to `ProjectUpdate` (so frontend can toggle it) and `ProjectResponse`.

## Task 3: Update sort order in ProjectService

**File:** `backend/app/services/project_service.py`

Change `list_all` sort from `func.lower(Project.name).asc()` to:
```python
stmt = stmt.order_by(
    Project.favorited_at.is_not(None).desc(),
    Project.favorited_at.desc(),
    func.lower(Project.name).asc(),
)
```

## Task 4: Frontend types

**File:** `frontend/src/shared/types/index.ts`

Add `favorited_at?: string | null;` to both `Project` and `ProjectUpdate` interfaces.

## Task 5: Star toggle in ProjectSidebar

**File:** `frontend/src/shared/components/project-sidebar.tsx`

- Import `Star` from lucide-react, `SidebarMenuAction` from sidebar UI, `useUpdateProject` from hooks
- Add `SidebarMenuAction` with `showOnHover` inside each project's `SidebarMenuItem`, containing a `Star` icon
- Filled star (`fill="currentColor" text-yellow-400`) when `project.favorited_at` is non-null, outline otherwise
- Click handler calls `updateProject.mutate({ favorited_at: project.favorited_at ? null : new Date().toISOString() })`
- Wrap in a local `ToggleStar` component or inline it per project