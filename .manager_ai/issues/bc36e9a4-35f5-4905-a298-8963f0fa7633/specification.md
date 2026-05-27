# Kanban Finished issues disappear after navigation

## Root cause

`frontend/src/features/issues/components/kanban-board.tsx` line 51 calls `useIssues(...)` to paginate the Finished column, but `useIssues` is not imported. The import on line 8 only brings in `useUpdateIssueStatus`.

This causes a `ReferenceError` when the component mounts — the Finished column renders nothing, and all finished issues (including the default first page) are missing.

The bug is most visible after navigating to an issue detail and back, because the component remounts and the hook call fails again. But it also affects the initial page load — the missing import means the Finished column never loads any issues.

## Fix

Add `useIssues` to the existing import from `@/features/issues/hooks` on line 8 of `kanban-board.tsx`:

```
- import { useUpdateIssueStatus } from "@/features/issues/hooks";
+ import { useUpdateIssueStatus, useIssues } from "@/features/issues/hooks";
```

## Why it was not caught

The parent `IssuesPage` imports `useIssues` from the same module, so the import exists in the bundle. The missing import in `kanban-board.tsx` is a module-scope error — each file must import its own dependencies. No lint error because the project's ESLint config may not enforce `no-undef` for hook calls, or the rule is not configured to catch this pattern.

## Behavior after fix

- First load: Finished column loads first page (10 issues) via `useIssues`
- "Load more": increments offset, appends next page to `allFinished` state
- Navigate away and back: component remounts, `finishedOffset` resets to 0, React Query returns cached first page from query cache → first page displays immediately
- Previously loaded "load more" pages are not restored (local state limitation, not part of this fix)
