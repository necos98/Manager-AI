## Summary

Added ability to mark projects as favorites via a star icon in the ProjectSidebar. Favorited projects sort to the top of the list (most recently favorited first), followed by non-favorites alphabetically.

## Changes Made

### Backend
- **`backend/app/models/project.py`**: Added `favorited_at` (nullable DateTime) column to Project model
- **Alembic migration**: `e3b028c8b53a_add_favorited_at_to_projects.py` — adds `favorited_at` to `projects` table
- **`backend/app/schemas/project.py`**: Added `favorited_at: datetime | None = None` to `ProjectUpdate` and `ProjectResponse`
- **`backend/app/services/project_service.py`**: Updated `list_all` sort order — favorites first (`favorited_at IS NOT NULL DESC, favorited_at DESC`), then alphabetical (`lower(name) ASC`)

### Frontend
- **`frontend/src/shared/types/index.ts`**: Added `favorited_at?: string | null` to `Project` and `ProjectUpdate` interfaces
- **`frontend/src/shared/components/project-sidebar.tsx`**: 
  - Extracted `ProjectSidebarItem` component using `useUpdateProject` hook
  - Added star toggle via `SidebarMenuAction` with `showOnHover`
  - Star icon from lucide-react: filled yellow when favorited, outline when not
  - Click toggles favorited state with optimistic update via React Query

## Architecture Decisions
- Timestamp over boolean for `favorited_at` — gives free ordering without separate sort column
- Reused existing `PUT /api/projects/{id}` rather than adding dedicated endpoints
- Extracted `ProjectSidebarItem` instead of inline hook call (React hooks-in-map rule)