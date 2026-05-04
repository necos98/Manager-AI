# Health Panel Auto-Refresh Implementation Plan

**Goal:** Add 30-second polling to Health panel so status indicators auto-refresh without page reload.

**Architecture:** One-line change to add `refetchInterval: 30_000` to existing `useQuery` in `useProjectHealth` hook. React Query handles polling lifecycle (pause on background, stop on unmount). No backend changes.

**Tech Stack:** React, React Query

---

### Task 1: Add refetchInterval to useProjectHealth

**Files:**
- Modify: `frontend/src/features/projects/hooks.ts:65-71`

- [ ] Add `refetchInterval: 30_000` to `useQuery` options in `useProjectHealth`

```typescript
export function useProjectHealth(projectId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "health"] as const,
    queryFn: () => api.fetchProjectHealth(projectId),
    enabled: !!projectId,
    refetchInterval: 30_000,
  });
}
```

- [ ] Verify frontend builds: `cd frontend && npm run build` (or `npx tsc --noEmit`)

- [ ] Commit