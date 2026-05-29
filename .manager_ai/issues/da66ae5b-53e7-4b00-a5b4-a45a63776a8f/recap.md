Root cause: 3 bugs causing manage-agent terminals to only appear in global Terminals page instead of AGENTS section.

**Fix 1** (backend): `list_terminals` returned ALL terminals including manage-agent ones (project_id="", issue_id=""). Added filter to exclude them — only project-associated terminals appear in global view.

**Fix 2** (backend): `create_manage_agent_terminal` cleanup was broken — `_to_response()` strips `pty` field, so `existing.get("pty", None)` was always None, preventing teardown of old terminals. Removed dead PTY check, always tear down.

**Fix 3** (frontend): AgentsTab reconnection `useEffect` had no loading state guard — if React Query cache was GC'd, `manageAgentTerminals` was undefined on mount and effect skipped. Added `isPending` guard to wait for initial load before reconnecting.