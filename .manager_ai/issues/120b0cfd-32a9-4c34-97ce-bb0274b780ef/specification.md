# Specification: Pipeline Terminal Missing Issue Context

## Problem

When a pipeline run creates a terminal (via `pipeline_run_service.py`), the terminal is correctly associated with the issue via `issue_id` in the backend. However, no WebSocket event is emitted to notify the frontend. The frontend's `useTerminals` query cache is never invalidated, so the terminal does not appear on the Issue detail page. When the user navigates away and returns, the query may or may not re-fetch depending on React Query cache state — resulting in an apparently "orphan" terminal visible only on the global Terminals page.

## Root Cause

`backend/app/services/pipeline_run_service.py` calls `terminal_service.create(issue_id=run.issue_id, ...)` but never emits a `terminal_created` WebSocket event afterward. The frontend already has the handler for this event (`event-context.tsx:190`) which invalidates the `["terminals"]` query key, but the event is never fired.

## Solution

### Backend: Emit `terminal_created` WebSocket Event

**File:** `backend/app/services/pipeline_run_service.py`

After terminal creation succeeds (after line 148, inside `_execute()`), emit a `terminal_created` event:

```python
await event_service.emit({
    "type": "terminal_created",
    "terminal_id": term_id,
    "issue_id": run.issue_id,
    "project_id": project_id,
})
```

The existing frontend handler (`event-context.tsx` line 190) catches this event and calls:
```js
queryClient.invalidateQueries({ queryKey: ["terminals"] });
```

This invalidates all terminal queries — both the global Terminals page list and the issue-filtered query `["terminals", undefined, issueId]` used by the Issue detail page.

### Frontend: Add Polling to useTerminals

**File:** `frontend/src/features/terminals/hooks.ts`

Add `refetchInterval: 3000` (3 seconds) to the `useQuery` options in `useTerminals`. This provides defense-in-depth: if a WebSocket event is missed (network blip, tab backgrounded, etc.), the terminal list is still eventually consistent.

This matches the existing pattern used by `usePipelineRuns` which already polls at 2-3 second intervals.

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/pipeline_run_service.py` | Emit `terminal_created` event after terminal creation |
| `frontend/src/features/terminals/hooks.ts` | Add `refetchInterval: 3000` to `useTerminals` |

## Acceptance Criteria

1. When a pipeline run creates a terminal, the terminal appears on the Issue detail page within 3 seconds without manual refresh.
2. The terminal remains visible when navigating away from and back to the Issue detail page.
3. The terminal is also visible on the global Terminals page.
4. Existing terminal creation flows (Run Issue button, Open Terminal button) continue to work as before.
5. No regression in pipeline run execution or terminal functionality.
