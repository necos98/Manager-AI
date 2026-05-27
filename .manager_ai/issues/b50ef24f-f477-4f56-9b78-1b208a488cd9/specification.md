# Double Sidebar Layout — Specification

## Summary

Split current single sidebar into two independent sidebars: a left **ProjectSidebar** (all projects + global nav) and a right **AppSidebar** (project-specific nav, visible only when a project is selected).

## Motivation

Current single sidebar mixes project-scoped and global navigation. User must use a dropdown to switch projects, losing context. Double sidebar is a proven pattern (Slack, Discord, Linear, Notion) that provides persistent project visibility and cleaner separation of concerns.

## Architecture

### Two SidebarProviders

Nested `SidebarProvider` components in `__root.tsx`:

```
<SidebarProvider>              ← outer (project sidebar, ~220px)
  <ProjectSidebar />
  <SidebarInset>
    <SidebarProvider>          ← inner (project nav sidebar, ~260px)
      {activeProject && <AppSidebar />}
      <SidebarInset>           ← main content
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  </SidebarInset>
</SidebarProvider>
```

### Three-column layout when project is active:
```
┌──────────────┬────────────┬──────────────────────────┐
│ Project      │ Project    │ Main Content             │
│ Sidebar      │ Nav        │ (Outlet)                 │
│ (~220px)     │ Sidebar    │                          │
│              │ (~260px)   │                          │
│ - Projects   │            │                          │
│   list       │ - Issues   │                          │
│ - Global     │ - Files    │                          │
│   nav        │ - Activity │                          │
│ - Footer     │ - etc.     │                          │
└──────────────┴────────────┴──────────────────────────┘
```

### Two-column layout (no project selected):
```
┌──────────────┬────────────────────────────────────────┐
│ Project      │ Main Content                           │
│ Sidebar      │ (Outlet)                               │
│ (~220px)     │                                        │
└──────────────┴────────────────────────────────────────┘
```

## Component Changes

### 1. New: `frontend/src/shared/components/project-sidebar.tsx`

Left sidebar. Contents migrated from current `AppSidebar`:

- **Header**: "Manager AI" brand label
- **Projects list**: All projects fetched via `useProjects()`. Each project shown with name + active indicator. Click navigates to `/projects/$projectId/issues`. Active project highlighted.
- **Separator**
- **Global nav group**: Dashboard, Terminals, Questions, Settings (unchanged from current)
- **Footer**: Smartphone QR, Theme toggle (unchanged)

### 2. Modified: `frontend/src/shared/components/app-sidebar.tsx`

Right sidebar — stripped down to project-scoped nav only:

- **Header**: Active project name
- **Project nav items**: Issues, Files, Activity, Memories, Ask & Brainstorming, Health, Edit Project, MCP Plugins, MCP Setup (unchanged)
- Renders `null` when `activeProject` is falsy
- Removed: ProjectSwitcher dropdown, global nav group, footer (moved to ProjectSidebar)

### 3. Modified: `frontend/src/routes/__root.tsx`

- Import and render `ProjectSidebar` as first sidebar
- Nest second `SidebarProvider` + `AppSidebar` + `SidebarInset` inside first `SidebarInset`
- `AppSidebar` only rendered when `activeProject` is non-null

### 4. Removed: `ProjectSwitcher` in header replaced by direct project list in ProjectSidebar

The `project-switcher.tsx` dropdown component is no longer needed as a primary navigation element. May be kept for mobile fallback but removed from desktop layout.

## Sidebar Widths

- ProjectSidebar (left): `--project-sidebar-width: 220px`
- AppSidebar (right): `--sidebar-width: 260px` (unchanged)

## Behaviors

- Both sidebars collapsible independently via `Ctrl+B` (or separate shortcuts)
- Left sidebar collapse → icon-only mode (project initials/avatars, tooltips on hover)
- Right sidebar collapse → existing icon mode behavior
- On mobile: both sidebars use Sheet overlay pattern
- Active route highlighting preserved via existing `matchRoute` fuzzy matching

## What Does NOT Change

- Routes, route structure, and URL patterns
- Backend API — projects list endpoint already exists
- All project pages remain identical
- Global pages (Dashboard, Terminals, Questions, Settings) unchanged
- Theme toggle, smartphone QR functionality unchanged

## Edge Cases

- **No projects**: ProjectSidebar shows empty project list with "Create Project" link
- **Archived projects**: Shown in separate collapsible section or excluded (use existing archived page pattern)
- **Long project names**: Truncated with ellipsis + tooltip
- **Many projects**: Scrollable project list within sidebar content area
