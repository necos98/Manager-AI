## Problem

When user clicks "Start Conversation" in AGENTS section (`/agents`), manage-agent terminal doesn't stay attached to AGENTS section. Terminal is only visible in global Terminals page (`/terminals`). User expects the terminal to be visible/accessible from AGENTS section.

## Root Causes

### RC1: Global Terminals page includes manage-agent terminals
`GET /api/terminals` with no filters returns ALL active terminals from `TerminalService.list_active(project_id=None, issue_id=None)`. Manage-agent terminals have `project_id=""` and `issue_id=""` but no filter excludes them. In `terminal-grid.tsx`, they render with:
- Blank issue name (empty string, null project_name)
- Broken Issue link to `/projects//issues/` (empty params)
- No visual indication they belong to AGENTS section

User sees orphaned terminal in global list, not in AGENTS.

### RC2: Manage-agent terminal cleanup is broken
`backend/app/routers/terminals.py:355-358`:
```python
for existing in service.list_active(project_id="", issue_id=""):
    existing_pty = existing.get("pty", None)
    if existing_pty is not None:
        await _teardown_terminal(existing["id"], service)
```
`existing` comes from `_to_response()` which does NOT include `pty` field. So `existing.get("pty", None)` is ALWAYS None → tear-down is NEVER executed. Multiple manage-agent terminals accumulate.

### RC3: AgentsTab reconnection has no loading guard
`frontend/src/features/agents/components/AgentsTab.tsx:159-167` — reconnection `useEffect` runs on mount to reattach existing manage-agent terminal. But it has no `isPending` guard: if React Query cache is GC'd (5+ min away), data is `undefined` on initial render and effect skips. Works eventually when query resolves, but one render cycle delay.

## Fix Plan

1. **Filter manage-agent terminals from global listing**: In `list_terminals` endpoint, exclude terminals where both `project_id=""` and `issue_id=""` (manage-agent signature). These are section-internal terminals, not project terminals.

2. **Fix cleanup logic**: Instead of `to_response` output (strips pty), access internal `_terminals` dict entry directly to check for PTY. Or simply always tear down since manage-agent terminals always have PTY.

3. **Add loading guard to reconnection**: Use `isPending` from `useManageAgentTerminals` query to wait for data before attempting reconnection.

## Files to Change

- **backend/app/routers/terminals.py**: Fix `list_terminals` filter + `create_manage_agent_terminal` cleanup
- **frontend/src/features/agents/components/AgentsTab.tsx**: Add loading guard to reconnection effect
