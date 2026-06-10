## Recap

**Issue**: Queue page crashes on first load with "Rendered more hooks than during the previous render."

**Root cause**: In `frontend/src/routes/queue.tsx`, the `useSetAutoProcess()` hook was called AFTER a conditional early return for the loading state. On the first render (loading), the hook was skipped. On the second render (data arrived), it was called — React detected N+1 hooks and threw the error. "Try Again" worked because subsequent renders used cached data where `isLoading` was never `true`.

**Fix**: Moved `const setAutoProcess = useSetAutoProcess();` from line 70 (after the early return) to line 34 (grouped with the other unconditional hooks before the early return).

**Files changed**: `frontend/src/routes/queue.tsx` — 1 line moved, 1 line removed.

**Verification**: TypeScript compilation passes with no errors on `queue.tsx`. Lint shows only pre-existing parsing errors from other files (unrelated).