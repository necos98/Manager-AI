# Health Panel Auto-Refresh

## Problem

The Health panel (`frontend/src/features/projects/components/health-panel.tsx`) shows MCP Server, manager.json, and Claude Resources installation status. The `useProjectHealth` hook uses React Query's `useQuery` without a `refetchInterval`, so data is fetched once on mount and never auto-refreshes. Users see stale status indicators and think they need to restart the backend.

## Solution

Add `refetchInterval: 30_000` (30 seconds) to `useQuery` in the `useProjectHealth` hook (`frontend/src/features/projects/hooks.ts`).

React Query handles polling natively: auto-pauses when browser tab is in background, stops on unmount. The existing `queryClient.invalidateQueries` calls after install/reinstall mutations still trigger immediate refetch — no change needed there.

## Backend

No backend changes needed. `GET /api/projects/{id}/health` already checks live filesystem state on every call (reads actual files/directories, no caching).

## Testing

Manual: open Health page, observe status indicators refresh every 30s. Existing tests cover the hook structure.