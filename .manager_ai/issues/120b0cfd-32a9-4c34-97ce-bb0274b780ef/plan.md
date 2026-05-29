# Implementation Plan: Pipeline Terminal Missing Issue Context

## Files

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/services/pipeline_run_service.py:148-160` | Emit `terminal_created` WebSocket event after terminal creation |
| Modify | `frontend/src/features/terminals/hooks.ts:20-25` | Add `refetchInterval: 3000` to `useTerminals` hook |

---

### Task 1: Backend — Emit `terminal_created` event in pipeline

**File:** `backend/app/services/pipeline_run_service.py`

After `agent_step_started` event emission (line 160), add `terminal_created` event emission:

```python
await event_service.emit({
    "type": "terminal_created",
    "terminal_id": term_id,
    "issue_id": run.issue_id,
    "project_id": project_id,
})
```

This triggers the existing frontend handler (`event-context.tsx:315-317`) which invalidates `["terminals"]` queries, causing the issue detail page to re-fetch and display the new terminal.

**Placement:** Between the `agent_step_started` event emission and the `try:` block that executes the agent step.

**No new imports needed** — `event_service` is already imported and used in the same function.

---

### Task 2: Frontend — Add `refetchInterval` to `useTerminals`

**File:** `frontend/src/features/terminals/hooks.ts`

Add `refetchInterval: 3000` to the `useQuery` options in `useTerminals`:

```typescript
export function useTerminals(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: [...terminalKeys.all, projectId, issueId] as const,
    queryFn: () => api.fetchTerminals(projectId, issueId),
    refetchInterval: 3000,
  });
}
```

This provides defense-in-depth: if a WebSocket event is missed (network blip, tab backgrounded), the terminal list is still eventually consistent within 3 seconds. Matches the existing pattern used by `useTerminalCount` (`refetchInterval: 5_000`) and `usePipelineRuns` (`refetchInterval: 3000`).

---

## Execution Order

1. Task 1: Backend event emission
2. Task 2: Frontend polling fallback

## Verification

1. Start backend, run pipeline on an issue
2. Confirm `terminal_created` WebSocket event appears in browser network tab
3. Confirm terminal appears on issue detail page within ~3 seconds
4. Navigate away and back — terminal still visible
5. Run Issue button still creates terminals correctly
