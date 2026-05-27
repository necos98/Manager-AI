## Changes

Created double sidebar layout with three files:

1. **Created** `frontend/src/shared/components/project-sidebar.tsx` — Left sidebar (~220px) with project list, global nav (Dashboard, Terminals, Questions, Settings), Smartphone QR, and ThemeToggle.
2. **Modified** `frontend/src/shared/components/app-sidebar.tsx` — Stripped to project-scoped nav only. Returns null when no active project. Removed ProjectSwitcher, global nav, footer.
3. **Modified** `frontend/src/routes/__root.tsx` — Nested two SidebarProviders: outer (220px) for ProjectSidebar, inner (260px default) for conditional AppSidebar.

## Architecture

Nested `SidebarProvider` components with CSS variable override for outer sidebar width. When a project is selected: three-column layout (ProjectSidebar | AppSidebar | Content). When no project: two-column layout (ProjectSidebar | Content). Inner AppSidebar renders null when `activeProject` is falsy, so no gap is created.

## Verification

- TypeScript: `tsc --noEmit` passes clean
- Build: `vite build` passes (2767 modules, 7.65s)
- No other files depend on removed imports