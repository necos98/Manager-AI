# Mobile Sidebar — Design Spec

**Date:** 2026-03-29

## Problem

On mobile (viewport < 768px) the sidebar is hidden with no way to open it. The shadcn `Sidebar` component already renders a `Sheet` slide-in on mobile via `useIsMobile()`, but no trigger button exists in the UI.

## Solution

Add a minimal top bar visible only on mobile that contains a single hamburger button (`SidebarTrigger`) to open the sidebar.

## Architecture

**Single file change:** `frontend/src/routes/__root.tsx`

Inside `RootLayout`, wrap the existing `<main>` with a flex column container and prepend a mobile-only `<header>`:

```
SidebarInset
  └── div.flex.flex-col.min-h-svh
        ├── <header class="md:hidden flex h-12 items-center px-4 border-b bg-background">
        │     └── SidebarTrigger   (PanelLeft icon, calls toggleSidebar → opens Sheet)
        └── <main class="flex-1 overflow-y-auto overflow-x-hidden">
              └── <Outlet />
```

## Behavior

- Header is hidden on `md` and above (≥ 768px) — desktop layout unchanged.
- On mobile, tapping the hamburger calls `toggleSidebar()` which sets `openMobile = true`.
- The `Sheet` slide-in (already implemented in `sidebar.tsx`) opens with the full sidebar content.
- No changes to `app-sidebar.tsx`, individual route files, or any other component.

## Components Used

- `SidebarTrigger` — already exported from `@/shared/components/ui/sidebar`, uses `PanelLeftIcon` from lucide-react and calls `useSidebar().toggleSidebar()`.

## Out of Scope

- Page title in the header
- Project name display
- Any desktop layout changes
