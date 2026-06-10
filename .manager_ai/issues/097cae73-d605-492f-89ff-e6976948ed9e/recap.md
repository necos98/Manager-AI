## Recap

Fixed "Run Issue" button being clickable when the issue already has a running terminal.

### Changes made

**1. Backend guard — `terminal_operations.py:create_terminal()`**
Added a check at the top of `create_terminal()` that calls `service.list_active(project_id, issue_id)` before creating a new terminal. If an active terminal already exists for that issue, it raises `HTTPException(409, ...)` with the existing terminal ID. This is the primary defence — it blocks duplicate terminal creation at the API level regardless of frontend state.

**2. Backend guard — `run_issue_service.py:run_issue()`**
Added the same check in the MCP code path (`run_issue` tool). Uses `terminal_service.list_active(project_id, issue_id)` and returns `{"error": "..."}` instead of creating a second terminal.

**3. Frontend guard — `issue-actions.tsx`**
Added `useTerminals(projectId, issue.id)` hook call and `hasActiveTerminal` derived state. The "Run Issue" button is now disabled when `isPending || createTerminal.isPending || hasActiveTerminal`. Since `useTerminals` refetches every 3 seconds, the button state reacts automatically when a terminal is created or killed.

### Files modified
- `backend/app/services/terminal_operations.py` — HTTP 409 guard in `create_terminal()`
- `backend/app/services/run_issue_service.py` — Error guard in `run_issue()` (MCP path)
- `frontend/src/features/issues/components/issue-actions.tsx` — Button disabled state

### Verification
- 218 existing tests still pass
- TypeScript compilation passes with no errors
- Module imports verified: `python -c "from app.services.terminal_operations import create_terminal; from app.services.run_issue_service import run_issue; print('OK')"`