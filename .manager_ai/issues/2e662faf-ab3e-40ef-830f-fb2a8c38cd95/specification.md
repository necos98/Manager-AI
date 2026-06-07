## Bug: Duplicate ISSUE_COMPLETED Hook Fire

### Problem
`backend/app/mcp/server.py` `complete_issue` tool fires `HookEvent.ISSUE_COMPLETED` twice:

1. **Via service layer** (line 135): `issue_service.complete_issue()` calls `hook_registry.fire(HookEvent.ISSUE_COMPLETED, ...)` at `issue_service.py:367`.
2. **Via MCP tool** (lines 162-178): The same hook fires again with near-identical metadata.

Result: any hook listener runs twice per completion — duplicate notifications, side effects, potential race conditions.

### Scope
Remove the redundant hook fire in `mcp/server.py` lines 162-178.

### Acceptance Criteria
- `HookEvent.ISSUE_COMPLETED` fires exactly once per `complete_issue` call.
- The event service emit (lines 153-160) remains — that's a real-time WebSocket notification, not a hook.
- `force_finish_issue` is unaffected (BugHunter confirmed it does NOT have this bug).

### Non-goals
- No changes to `issue_service.py` — it correctly fires the hook.
- No changes to hook registry, event service, or other MCP tools.
- No refactoring of the `complete_issue` tool beyond removing the redundant block.

### Constraints
- Remove lines 162-178 only. Preserve all other logic including the `try/except` structure and the return statement.
- The import `from app.hooks.registry import HookContext, HookEvent, hook_registry` may become unused — check and remove if so.
