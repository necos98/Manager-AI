## Root cause

`kanban-board.tsx:51` called `useIssues(...)` to paginate the Finished column, but the import on line 8 only imported `useUpdateIssueStatus`. `useIssues` was missing, causing a `ReferenceError` at runtime.

The parent `IssuesPage` imported `useIssues` from the same module, masking the error during development (the symbol existed in the bundle). But ES modules are file-scoped — each file must import its own dependencies.

## Fix

One-line change to `frontend/src/features/issues/components/kanban-board.tsx:8`:

```diff
- import { useUpdateIssueStatus } from "@/features/issues/hooks";
+ import { useUpdateIssueStatus, useIssues } from "@/features/issues/hooks";
```

## Verification

Frontend production build passes (2767 modules, no errors).
