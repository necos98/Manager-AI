# Implementation Plan: Group Terminals by Project

## Files to Modify
- **`frontend/src/features/terminals/components/terminal-grid.tsx`** — Core change: group terminals by `project_id`, render per-project sections with headers
- **`frontend/src/routes/terminals.tsx`** — Minor: adjust page header text if needed

## Task 1: Group terminals in TerminalGrid

**File:** `frontend/src/features/terminals/components/terminal-grid.tsx`

Group incoming terminals by `project_id`. For each group:
1. Compute `Map<project_id, TerminalListItem[]>` sorted by project name
2. Render a small project header (`text-sm font-medium text-muted-foreground`) with project name and terminal count
3. Render the group's terminals in the existing responsive grid below the header
4. Reuse `getGridClass(count)` per group for responsive layout
5. Fallback for null `project_name`: "Unknown Project"

Empty state (0 terminals) stays unchanged.

## Task 2: Verify and clean up

**File:** `frontend/src/routes/terminals.tsx`

- Verify the page-level `h1` ("Terminali Attivi") and soft-limit counter still work correctly
- Manual test: open multiple terminals from different projects, verify grouping on /terminals page