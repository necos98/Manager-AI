## Root Cause

In `frontend/src/routes/queue.tsx`, the `QueuePage` component has a **conditional React hook call**. The hook `useSetAutoProcess()` is declared at line 70, **after** an early return for the loading state (lines 56-64):

```tsx
// Line 54
const isLoading = queueLoading && runningLoading;

// Lines 56-64 — EARLY RETURN when loading
if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    );
  }

// Line 70 — HOOK CALL (skipped during loading renders!)
const setAutoProcess = useSetAutoProcess();
```

### Why it breaks

1. **First render** (page loads, queries fetching): `isLoading = true` → early return → `useSetAutoProcess()` is **never called** → React records N hooks.

2. **Second render** (data arrives, `isLoading = false`): proceeds past early return → `useSetAutoProcess()` IS called → React sees N+1 hooks → **"Rendered more hooks than during the previous render"** error.

3. **"Try Again" works** because after the error, on re-render with cached data, `isLoading` is never `true` → early return never triggers → hooks are consistent from mount.

### Fix

Move the `useSetAutoProcess()` hook call from line 70 to the top of the component function, grouping it with the other unconditional hook calls (lines 27-33). This ensures the hook is called on EVERY render, regardless of the loading state.

### File changed

- `frontend/src/routes/queue.tsx` — move `const setAutoProcess = useSetAutoProcess();` before the early return block

### Verification

1. Navigate to `/queue` for the first time (no cached data) — should load without "Rendered more hooks" error
2. Verify the Auto-process toggle still works (toggle enabled/disabled state reflects correctly)
