## Implementation Plan

One-line change in `frontend/src/shared/context/event-context.tsx`.

**File to modify:** `frontend/src/shared/context/event-context.tsx:178`

**Change:** Add `"issue_updated"` and `"file_updated"` to the existing case block that silences `memory_*` and `project_updated` events.

**Before:**
```typescript
case "project_updated":
case "memory_created":
case "memory_updated":
case "memory_deleted":
case "memory_linked":
case "memory_unlinked":
  return { title: "", message: "", variant: "default", silent: true };
```

**After:**
```typescript
case "project_updated":
case "issue_updated":
case "file_updated":
case "memory_created":
case "memory_updated":
case "memory_deleted":
case "memory_linked":
case "memory_unlinked":
  return { title: "", message: "", variant: "default", silent: true };
```

**Verification:** After change, filesystem watcher events (`issue_updated`, `file_updated`) still trigger cache invalidation in `ws.onmessage` but produce no toast and no sound.