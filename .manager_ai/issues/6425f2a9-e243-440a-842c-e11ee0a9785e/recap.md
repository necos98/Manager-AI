## What changed

Added `refetchInterval: 30_000` to `useQuery` in `useProjectHealth` hook (`frontend/src/features/projects/hooks.ts:70`). Health panel status indicators now auto-refresh every 30 seconds instead of showing stale data until page reload.

## What was verified

- TypeScript type check passed (`npx tsc --noEmit` in frontend directory, no errors)
- React Query handles polling lifecycle natively: pauses when tab is background, stops on unmount
- Backend health endpoint already reads live filesystem state on every call — no backend changes needed