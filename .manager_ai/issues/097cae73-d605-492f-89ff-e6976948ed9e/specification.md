## Problem

The "Run Issue" button in the issue detail page (`issue-actions.tsx`) is always enabled when the issue is not in a terminal state (Finished/Canceled). A user can click it multiple times, creating multiple PTY terminals for the same issue simultaneously. There is no backend check preventing duplicate terminals per issue, and no frontend check disabling the button when a terminal already exists.

## Current Behavior

### Frontend (`issue-actions.tsx:143-152`)
```tsx
<Button
  size="sm"
  variant="outline"
  onClick={handleRunIssue}
  disabled={isPending || createTerminal.isPending}
  aria-label="Run issue in terminal"
>
```
The only disables are:
- `isPending` — while any other mutation (accept, cancel, complete, force-finish) is processing
- `createTerminal.isPending` — while the terminal creation mutation itself is in flight

There is no check whether a terminal already exists for this issue. The page-level `useTerminalLayout` hook already fetches `useTerminals(undefined, issueId)` and exposes `hasAny`, but `IssueActions` doesn't use it.

### Backend (`terminal_operations.py:126-137`)
`create_terminal()`:
- Validates the project exists
- Creates a PTY with no check for existing terminals for the same issue_id
- Writes provider commands into the PTY
- Returns the terminal dict

`run_issue_service.py:run_issue()`:
- Similarly creates a terminal via `terminal_service.create()` with no prior check
- No reference to `terminal_service.list_active(issue_id=issue_id)` anywhere

The `TerminalService.list_active(project_id=, issue_id=)` method already exists and can filter by issue_id. It's used for reaping (deleting old terminals before creating new ones) in `create_ask_terminal` and `create_terminal_base`, but not for preventing duplicate runs.

## Solution

### 1. Backend guard (primary) — `terminal_operations.py:create_terminal()`
Before creating a new terminal, check if the issue already has an active terminal:
```python
existing = service.list_active(project_id=data.project_id, issue_id=data.issue_id)
if existing:
    raise HTTPException(
        status_code=409,
        detail=f"Issue {data.issue_id} already has an active terminal ({existing[0]['id']})"
    )
```
This prevents duplicate terminal creation at the API level regardless of frontend state.

Also add the same guard in `run_issue_service.py:run_issue()` for the MCP path.

### 2. Frontend guard (UX) — `issue-actions.tsx`
Pass terminal info or use `useTerminals` hook to disable the button when there's already an active terminal:

**Option A** (cleaner, more reactive): Use the `useTerminals` hook directly:
```tsx
const { data: terminals } = useTerminals(projectId, issue.id);
const hasActiveTerminal = (terminals?.length ?? 0) > 0;

// In button:
disabled={isPending || createTerminal.isPending || hasActiveTerminal}
```
This reacts automatically when terminals are created/killed via the 3-second refetchInterval.

**Option B**: Pass terminal info via props from the page (`issue-detail.tsx` already receives `terminalId`).

### 3. Pipeline Run consideration
The "Run Issue" button is distinct from `PipelineRunButton`. The guard should only block the "Run Issue" button based on direct terminals, not pipeline runs. Pipeline runs use a separate terminal via the pipeline step system.

## Verification

1. Open an issue detail page with no terminal → "Run Issue" should be enabled
2. Click "Run Issue" → button should show "Opening..." then become disabled when terminal appears
3. Kill the terminal → button should become re-enabled
4. Try POST /api/terminals with same issue_id twice via curl → second call should return 409
