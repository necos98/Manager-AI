# Mobile Sidebar Hamburger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mobile-only top bar with a hamburger button that opens the existing slide-in sidebar on viewports < 768px.

**Architecture:** A single `<header>` element with `md:hidden` is inserted into `SidebarInset` in `__root.tsx`. It renders `SidebarTrigger` (already exported from the shadcn sidebar component) which calls `toggleSidebar()` → sets `openMobile = true` → opens the existing `Sheet` slide-in. No other files change.

**Tech Stack:** React, TailwindCSS, shadcn/ui sidebar (`SidebarTrigger`), TanStack Router

---

### Task 1: Add mobile header with hamburger to root layout

**Files:**
- Modify: `frontend/src/routes/__root.tsx`

> Note: This is a pure layout/visual change. There is no business logic to unit test. Verification is done by visual inspection in the browser at a narrow viewport.

- [ ] **Step 1: Read the current file**

Read `frontend/src/routes/__root.tsx` to confirm current structure before editing.

- [ ] **Step 2: Add `SidebarTrigger` import**

In `frontend/src/routes/__root.tsx`, update the sidebar import line from:

```tsx
import { SidebarInset, SidebarProvider } from "@/shared/components/ui/sidebar";
```

to:

```tsx
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/shared/components/ui/sidebar";
```

- [ ] **Step 3: Add mobile header inside `SidebarInset`**

Replace the `SidebarInset` block in `RootLayout`:

```tsx
<SidebarInset className="min-w-0">
  <main className="flex-1 overflow-y-auto overflow-x-hidden">
    <Outlet />
  </main>
</SidebarInset>
```

with:

```tsx
<SidebarInset className="min-w-0 flex flex-col">
  <header className="md:hidden flex h-12 items-center px-4 border-b bg-background shrink-0">
    <SidebarTrigger />
  </header>
  <main className="flex-1 overflow-y-auto overflow-x-hidden">
    <Outlet />
  </main>
</SidebarInset>
```

- [ ] **Step 4: Verify in browser**

Start the dev server if not running:
```bash
python start.py
```

Open the app in a browser and use DevTools to simulate a mobile viewport (< 768px width, e.g. iPhone 390px).

Expected:
- A thin top bar appears with a `☰` (panel-left) icon button
- Clicking it opens the sidebar as a slide-in sheet from the left
- On desktop (≥ 768px), the top bar is invisible and layout is unchanged

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/__root.tsx
git commit -m "feat: add mobile hamburger button to open sidebar"
```
