## Recap

**Problem:** Pipeline-created terminals were invisible on the Issue detail page. The backend correctly associated terminals with `issue_id`, but no WebSocket event notified the frontend to refresh its query cache.

**Fix:** Two changes:

1. **Backend** (`pipeline_run_service.py:162-167`): Emit `terminal_created` WebSocket event after terminal creation in the pipeline `_execute()` method. The frontend handler at `event-context.tsx:315-317` already exists and invalidates `["terminals"]` queries on receipt.

2. **Frontend** (`hooks.ts:24`): Added `refetchInterval: 3000` to `useTerminals` hook as defense-in-depth, ensuring eventual consistency even if WebSocket events are missed (network blip, tab backgrounded).

**Changes:** 2 files, 4 lines added.
