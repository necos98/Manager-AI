# Implementation Plan

## Files

- **Modify:** `frontend/src/features/issues/components/kanban-board.tsx` — add missing `useIssues` import

## Tasks

### Task 1: Fix missing import

- Add `useIssues` to the existing import from `@/features/issues/hooks` on line 8
- Verify the app compiles and Finished column loads issues

### Task 2: Verify fix

- Run the frontend dev server and confirm Finished column shows issues after page load and after navigating back from an issue detail
