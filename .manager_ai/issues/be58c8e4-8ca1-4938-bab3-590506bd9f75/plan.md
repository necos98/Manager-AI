## Agent Terminal Not Attached — Implementation Plan

**Goal:** Fix terminal panel not rendering in Agents section after "Start Conversation"

**Architecture:** 3 independent fixes: CSS layout in AgentsTab (primary), query cache invalidation in hooks, backend filter logic in TerminalService.

**Tech Stack:** React/Tailwind, React Query, Python/FastAPI

---

### Task 1: Fix CSS height chain in AgentsTab terminal wrapper

**Files:** `frontend/src/features/agents/components/AgentsTab.tsx`

- [ ] **Step 1: Change terminal wrapper div to flex column**

Change from:
```tsx
{chatTerminalId && (
  <div className="border rounded-lg overflow-hidden min-h-[400px]">
    <TerminalPanel
      terminalId={chatTerminalId}
      projectId={_projectId}
      onSessionEnd={handleEndChat}
    />
  </div>
)}
```

To:
```tsx
{chatTerminalId && (
  <div className="border rounded-lg overflow-hidden min-h-[400px] flex flex-col">
    <div className="flex-1 min-h-0">
      <TerminalPanel
        terminalId={chatTerminalId}
        projectId={_projectId}
        onSessionEnd={handleEndChat}
      />
    </div>
  </div>
)}
```

The `flex flex-col` creates flex formatting context. The inner `flex-1 min-h-0` div gets definite height from parent's `min-h-[400px]` via flex distribution. TerminalPanel's `h-full` now resolves against this definite height instead of 0.

---

### Task 2: Add manageAgent query invalidation

**Files:** `frontend/src/features/terminals/hooks.ts`

- [ ] **Step 1: Add manageAgent invalidation to useCreateManageAgentTerminal**

In `useCreateManageAgentTerminal`, add `terminalKeys.manageAgent` to `onSuccess` invalidations:

```tsx
export function useCreateManageAgentTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ManageAgentTerminalCreate) => api.createManageAgentTerminal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
      queryClient.invalidateQueries({ queryKey: terminalKeys.manageAgent });  // ADD
    },
    onError: onMutationError,
  });
}
```

This ensures `useManageAgentTerminals` consumers (AgentsTab reconnection effect) get fresh data after terminal creation.

---

### Task 3: Fix list_active empty-string filter in backend

**Files:** `backend/app/services/terminal_service.py`

- [ ] **Step 1: Change truthiness checks to explicit None checks**

In `list_active` method, around line 214-222:

```python
def list_active(
    self,
    project_id: str | None = None,
    issue_id: str | None = None,
) -> list[dict]:
    results = []
    for term in self._terminals.values():
        if term["status"] != "active":
            continue
        if project_id is not None and term["project_id"] != project_id:  # CHANGED
            continue
        if issue_id is not None and term["issue_id"] != issue_id:        # CHANGED
            continue
        results.append(self._to_response(term))
    return results
```

Empty string `""` is falsy in Python. `if project_id and term["project_id"] != project_id` treats `""` as no filter. Callers passing `project_id=""` (manage-agent: `list_active(project_id="", issue_id="")`) get ALL terminals instead of just empty-project_id ones. Using `is not None` fixes this.

Note: `issue_id` was already correct (used `is not None` in condition `if issue_id is not None`). Only `project_id` needed the fix. But align both for consistency.
