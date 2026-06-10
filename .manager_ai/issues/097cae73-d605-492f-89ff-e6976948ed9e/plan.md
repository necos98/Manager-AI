## Implementation Plan

### Task 1: Backend guard in `terminal_operations.py:create_terminal()`
Add an HTTP 409 guard in `create_terminal()` that checks `service.list_active(project_id, issue_id)` before creating a new terminal. If active terminals exist, raise `HTTPException(409, ...)`. This is the primary defence against duplicate terminals.

### Task 2: Backend guard in `run_issue_service.py:run_issue()`
Add the same guard in `run_issue()` for the MCP code path (`run_issue` MCP tool → `shared_tools.py:run_issue` → `run_issue_service.py:run_issue`). The MCP path creates a terminal directly via `terminal_service.create()` with no prior check.

### Task 3: Frontend — disable "Run Issue" button when terminal exists
In `issue-actions.tsx`, import and use `useTerminals` to check if the issue already has active terminals. Disable the button when `terminals.length > 0`. This provides immediate visual feedback in the UI.

### Task 4: Verify with curl + frontend check
- Start the backend
- Run an issue via curl POST /api/terminals
- Verify a second POST returns 409
- Verify frontend button is disabled after a terminal appears
