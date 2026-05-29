## Plan

### Fix 1: Filter manage-agent terminals from global listing

**File:** `backend/app/routers/terminals.py` — `list_terminals` endpoint

Add filter: exclude terminals where `project_id=""` AND `issue_id=""`. These are section-internal manage-agent terminals, not project terminals. They should only appear via the `/terminals/manage-agent` endpoint.

Change: after `list_active()`, filter out manage-agent entries before enriching with project/issue names.

### Fix 2: Fix manage-agent terminal cleanup on create

**File:** `backend/app/routers/terminals.py` — `create_manage_agent_terminal` endpoint

Current code uses `_to_response()` output which strips `pty` field. Fix by checking the internal `_terminals` dict directly. Since manage-agent terminals always have PTY, simplify: always tear down existing terminals when creating a new one.

### Fix 3: Add loading guard to AgentsTab reconnection

**File:** `frontend/src/features/agents/components/AgentsTab.tsx`

Current reconnection `useEffect` has no loading state guard — if React Query cache is empty (GC'd), data is `undefined` on render, effect skips until query resolves. Add `isPending` from `useManageAgentTerminals` as a guard: wait for initial load before attempting reconnection.

### Scope

3 changes, all small. No new files. No tests needed — this fixes existing behavior. Backend: filter + cleanup fix. Frontend: loading guard.
