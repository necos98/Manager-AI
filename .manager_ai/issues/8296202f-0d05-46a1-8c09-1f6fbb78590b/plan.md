## Implementation Plan

**Goal:** Remove duplicate Agents sidebar entry from `project-sidebar.tsx`.

**Architecture:** Single-file UI cleanup. Delete the duplicate `<SidebarMenuItem>` block (lines 182-192) between Questions and Pipelines. No logic changes, no new dependencies.

### Task 1: Remove duplicate Agents entry

**Files:**
- Modify: `frontend/src/shared/components/project-sidebar.tsx` — remove lines 182-192

**Steps:**
1. Delete the duplicate Agents `<SidebarMenuItem>` block (second occurrence, after Questions, before Pipelines)
2. Verify the file parses correctly (no JSX errors)
3. Run `npm run lint` to ensure no lint errors