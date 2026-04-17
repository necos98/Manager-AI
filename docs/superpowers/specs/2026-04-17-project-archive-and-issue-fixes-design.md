# Project Archive, Issue List Refresh Bug, and Alphabetical Project Sort

**Date:** 2026-04-17
**Status:** Draft

## Overview

Three independent changes bundled into one spec:

1. **Bug fix:** After creating a new issue, the issue list is not refreshed because the `useCreateIssue` invalidation key does not match the `useIssues` query key.
2. **Feature:** Archive / unarchive projects. Archived projects are hidden from the sidebar, dropdown, and dashboard; they are managed on a dedicated `/projects/archived` page (Option C from brainstorming).
3. **Feature:** Sort the project dropdown (and all other project lists) alphabetically by name, case-insensitive.

The three items are scoped together because they are all small, relate to the projects/issues surface, and ship as a single cohesive update to the left-hand navigation area.

## 1. Issue list refresh bug

### Root cause

`useIssues` uses the query key `["issues", projectId, status, search]` (frontend/src/features/issues/hooks.ts:18).

Mutations such as `useCreateIssue`, `useUpdateIssue`, `useDeleteIssue`, `useAcceptIssue`, `useCancelIssue`, and `useCompleteIssue` invalidate `issueKeys.all(projectId)` which is `["projects", projectId, "issues"]` (hooks.ts:11). These prefixes do not match, so the list cache is never invalidated after a mutation.

`useUpdateIssueStatus` invalidates `["issues", projectId]` which does match the list prefix but is inconsistent with the other helpers.

### Fix

Unify the list key under the `issueKeys` namespace so all invalidations match via prefix.

Change `useIssues` in `frontend/src/features/issues/hooks.ts`:

```ts
export function useIssues(projectId: string, status?: IssueStatus, search?: string) {
  return useQuery({
    queryKey: [...issueKeys.all(projectId), "list", { status, search }],
    queryFn: () => api.fetchIssues(projectId, status, search),
  });
}
```

Any mutation that calls `queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) })` now invalidates the list cache by prefix.

Change `useUpdateIssueStatus` to use `issueKeys.all(projectId)` instead of `["issues", projectId]` for consistency.

No other consumer relies on the old key shape — the `useIssues` signature is unchanged.

### Tests

- Backend: none (no backend change).
- Frontend: existing tests for `useIssues` / `useCreateIssue` must still pass. Add a React Query test that mounts `useIssues`, runs the mutation from `useCreateIssue`, and verifies the list query is re-fetched. If the existing test harness does not cover this area, a lightweight Vitest + React Testing Library test is sufficient.

## 2. Archive / unarchive projects

### Data model

Add a single nullable timestamp column `archived_at` to `projects` (backend/app/models/project.py).

- `archived_at IS NULL` → project is active.
- `archived_at IS NOT NULL` → project is archived; the value is the timestamp at which it was archived.

Using a timestamp rather than a boolean gives us a free "recently archived" sort on the archived page and costs nothing.

Alembic migration:
- `op.add_column("projects", sa.Column("archived_at", sa.DateTime(), nullable=True))`
- Downgrade drops the column.

### Backend API

All under `/api/projects` (backend/app/routers/projects.py).

- `GET /api/projects` — unchanged signature, now filters `WHERE archived_at IS NULL` by default.
- `GET /api/projects?archived=true` — returns archived projects only (`WHERE archived_at IS NOT NULL`).
- `POST /api/projects/{id}/archive` — sets `archived_at = func.now()`. 204 on success. Idempotent (archiving an already-archived project is a no-op, returns 204).
- `POST /api/projects/{id}/unarchive` — sets `archived_at = NULL`. 204 on success. Idempotent.

Both endpoints return 404 if the project does not exist.

Dashboard (`GET /api/dashboard`) excludes archived projects. This falls out naturally from changing `ProjectService.list_all` to accept an `archived: bool | None = False` filter.

### Active resources during archive

Archive is reversible, so:
- Active terminals are **not** killed. They keep running; the user just cannot see the project in the sidebar until unarchived.
- Issues are untouched. Hooks continue to fire normally.
- MCP tools that target the project by ID still work (no filtering added there — the archive filter is a UI-level concern).

### Service layer

`ProjectService.list_all(archived: bool | None = False)`:
- `archived=False` (default) → `WHERE archived_at IS NULL`.
- `archived=True` → `WHERE archived_at IS NOT NULL`.
- `archived=None` → no filter (used nowhere today but reserved for future admin views).

New methods:
- `ProjectService.archive(project_id: str) -> Project`
- `ProjectService.unarchive(project_id: str) -> Project`

### Frontend

Routes:
- New route `/projects/archived` (`frontend/src/routes/projects/archived.tsx`): shows a list/card view of archived projects. Each row shows name, path, `archived_at` formatted relative (e.g. "archived 3 days ago"), and an "Unarchive" button. Empty state: "No archived projects."

Hooks (frontend/src/features/projects/hooks.ts):
- `useProjects()` — unchanged.
- `useArchivedProjects()` — new. Query key `[...projectKeys.all, "archived"]`.
- `useArchiveProject(projectId)` — new mutation. On success, invalidate `projectKeys.all` and the archived list key.
- `useUnarchiveProject(projectId)` — symmetric.

API client (frontend/src/features/projects/api.ts):
- `fetchProjects(archived?: boolean)` → `GET /api/projects?archived=true` when set.
- `archiveProject(id)`, `unarchiveProject(id)`.

UI surfaces:
- **Project switcher dropdown** (`frontend/src/features/projects/components/project-switcher.tsx`): add a `View archived` menu item below the existing `New Project` item. Clicking it navigates to `/projects/archived`.
- **Project settings dialog** (`frontend/src/features/projects/components/project-settings-dialog.tsx`): append a destructive section at the bottom (after the codebase index block, before the cancel/save buttons). The section contains a single "Archive project" outline button in a destructive color, with a short helper text: "Hides the project from sidebar and dashboard. You can restore it from the archived page."
- **Active project redirect:** if the user archives the currently-open project, redirect to `/` after the mutation resolves. The sidebar would otherwise display a stale selection.

Archived page behavior:
- Route shows the `ProjectSwitcher` sidebar as normal so the user can jump back to an active project.
- Unarchiving from the list triggers `useUnarchiveProject`, invalidates both lists, shows a toast "Project restored". The row disappears from the archived list and re-appears in the switcher.

### Tests

- Backend: new tests in `backend/tests/test_routers_projects.py`:
  - `GET /api/projects` excludes archived.
  - `GET /api/projects?archived=true` returns only archived.
  - Archive / unarchive endpoints toggle the field and return 204.
  - Archive of unknown id returns 404.
  - Dashboard excludes archived.
- Frontend: component test that the "Archive project" button triggers the mutation and the dialog closes / redirect fires.

## 3. Alphabetical project sort

Change `ProjectService.list_all` in `backend/app/services/project_service.py` to order by lower-cased name ascending:

```python
stmt = select(Project)
if archived is False:
    stmt = stmt.where(Project.archived_at.is_(None))
elif archived is True:
    stmt = stmt.where(Project.archived_at.is_not(None))
stmt = stmt.order_by(func.lower(Project.name).asc())
result = await self.session.execute(stmt)
```

This applies to every consumer of `list_all`: the project switcher, the dashboard, the archived page, and any future admin views. No frontend sort is required.

### Tests

- Backend: add a case to `test_routers_projects.py` that inserts three projects with mixed-case names and verifies they come back alphabetically.

## Out of scope

- Bulk archive / unarchive (one at a time is sufficient).
- Soft-delete semantics for issues inside archived projects.
- Archiving MCP behavior changes (archived projects remain addressable via MCP).
- Search / filter on the archived page (small expected volume).
- Changing the creation-date ordering available elsewhere — all existing `list_all` consumers want projects by name once we ship this.

## Build order

1. Backend model + migration + service filter + endpoints + tests.
2. Alphabetical ORDER BY (same PR as backend — one line change).
3. Frontend query invalidation bug fix (independent, can land first or last).
4. Frontend hooks, api client, archive button in settings dialog, archived route, dropdown link.
5. Manual smoke test in the browser: create issue → list updates; archive active project → redirect + hidden; unarchive from page → reappears; dropdown sorted A→Z.
