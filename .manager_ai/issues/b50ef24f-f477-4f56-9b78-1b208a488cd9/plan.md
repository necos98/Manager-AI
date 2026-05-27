# Double Sidebar — Implementation Plan

## Files

| Action | File |
|--------|------|
| Create | `frontend/src/shared/components/project-sidebar.tsx` |
| Modify | `frontend/src/shared/components/app-sidebar.tsx` |
| Modify | `frontend/src/routes/__root.tsx` |

## Approach

Nested `SidebarProvider` components. Outer provider handles project list + global nav sidebar. Inner provider handles project-scoped nav sidebar. Each has its own `--sidebar-width` CSS variable via the `style` prop on `SidebarProvider`. The existing `sidebar.tsx` uses `peer` + gap div for layout — nesting two creates cumulative gaps (220px + 260px = 480px offset for main content when both visible).

When no project is selected, `AppSidebar` returns `null` (no gap created), and the inner `SidebarInset` fills the remaining space.

## Task 1: Create ProjectSidebar component

**File:** Create `frontend/src/shared/components/project-sidebar.tsx`

New component containing:
- Header: "Manager AI" label (simple text, not a dropdown)
- Project list: `useProjects()` fetches all projects, each clickable, active one highlighted via `matchRoute`
- Separator
- Global nav: Dashboard, Terminals, Questions, Settings (same as current AppSidebar global group)
- Footer: Smartphone QR dialog + ThemeToggle (same as current AppSidebar footer)
- Dialogs rendered inline: `SmartphoneQrDialog`

Props: `activeProject: Project | null`

## Task 2: Modify AppSidebar → project-nav only

**File:** Modify `frontend/src/shared/components/app-sidebar.tsx`

Changes:
- Remove: `ProjectSwitcher` import and usage (line 32, line 105)
- Remove: Global nav group (Dashboard, Terminals, Questions, Settings) — lines 159-215
- Remove: Footer (SmartphoneQR, ThemeToggle) — lines 218-230
- Remove: `SmartphoneQrDialog`, its state, and import (lines 35, 54, 249-252)
- Remove: `useTerminalCount`, `usePendingCount` imports (lines 37-38) if no longer used
- Remove: `ThemeToggle` import (line 36) if no longer used
- Remove: `SidebarFooter` import if unused
- Add early return: `if (!activeProject) return null;` at top of component
- Keep: Project settings dialog, MCP setup dialog, and their state
- Keep: `projectNav` array and its rendering
- Keep: `SidebarHeader`, `SidebarContent`, `SidebarGroup`, `SidebarMenu` for project nav

## Task 3: Update __root.tsx with nested sidebar layout

**File:** Modify `frontend/src/routes/__root.tsx`

Changes:
- Import `ProjectSidebar` from `@/shared/components/project-sidebar`
- Current structure:
```tsx
<SidebarProvider>
  <AppSidebar activeProject={activeProject} />
  <SidebarInset>
    <header /><main><Outlet /></main>
  </SidebarInset>
</SidebarProvider>
```
- New structure:
```tsx
<SidebarProvider style={{ "--sidebar-width": "220px" } as React.CSSProperties}>
  <ProjectSidebar activeProject={activeProject} />
  <SidebarInset>
    <SidebarProvider>
      {activeProject && <AppSidebar activeProject={activeProject} />}
      <SidebarInset>
        <header className="md:hidden ..."><SidebarTrigger /></header>
        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <ErrorBoundary><Outlet /></ErrorBoundary>
        </main>
      </SidebarInset>
    </SidebarProvider>
  </SidebarInset>
</SidebarProvider>
```
- Note: `<SidebarTrigger />` moved to inner SidebarInset header (controls inner sidebar collapse)
- Note: `activeProject &&` guard keeps AppSidebar from rendering when no project selected
