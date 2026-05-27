# Favorite Projects in Sidebar

## Summary

Allow users to mark projects as favorites via a star icon in the ProjectSidebar. Favorited projects sort to the top of the list, followed by non-favorites in alphabetical order.

## Motivation

Users with many projects want quick access to the ones they use most. A favorites mechanism avoids scrolling and searching through a long flat project list.

## Design

### Data Model

Add `favorited_at` (nullable datetime) to the `projects` table. Timestamp over boolean because:
- Natural ordering: most recently favorited first
- No separate sort column needed
- `null` = not favorited, non-null = favorited at that time

### Sort Order

Favorites first (most recent first), then non-favorites alphabetically:
```sql
ORDER BY favorited_at IS NOT NULL DESC, favorited_at DESC, lower(name) ASC
```

### API

Reuse existing `PUT /api/projects/{id}`. The `ProjectUpdate` schema gains `favorited_at: datetime | None`. Frontend sends current timestamp to favorite, `null` to unfavorite. No new endpoints needed.

### Frontend

- Star icon (lucide-react `Star`) on each project row in ProjectSidebar
- Filled star (`fill="currentColor"`) when favorited, outline when not
- Click toggles via `useUpdateProject` with optimistic update
- No visual separation between favorites and rest — just sort order

## Files Changed

| Layer | File | Change |
|---|---|---|
| DB | `backend/app/models/project.py` | Add `favorited_at` column |
| DB | Migration | `alembic revision --autogenerate` |
| API | `backend/app/schemas/project.py` | Add `favorited_at` to response + update schemas |
| API | `backend/app/services/project_service.py` | Update `list_all` sort order |
| UI | `frontend/src/shared/types/index.ts` | Add `favorited_at` to Project type |
| UI | `frontend/src/shared/components/project-sidebar.tsx` | Add star toggle per project row |

## Constraints

- Favorites stored per-project, not per-user (Manager AI has no multi-user concept)
- Star button uses existing `SidebarMenuAction` with `showOnHover` for clean default appearance
- Must support dark mode (use existing shadcn CSS variables)
