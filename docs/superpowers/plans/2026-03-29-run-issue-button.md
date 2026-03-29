# Run Issue Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the "Open Terminal" button into two distinct actions — "Run Issue" (with startup commands, near Cancel Issue) and "Open Terminal" (bare terminal, in top bar).

**Architecture:** Add a `run_commands: bool = True` flag to `TerminalCreate` schema on the backend. The terminals POST endpoint already injects startup commands; when `run_commands=False` it skips that block. On the frontend, the existing top-bar "Open Terminal" button passes `run_commands: false`, while a new "Run Issue" button inside `IssueActions` calls with the default (commands enabled).

**Tech Stack:** FastAPI/Pydantic (backend), React/TypeScript/TanStack Query (frontend)

---

## Files

| File | Change |
|------|--------|
| `backend/app/schemas/terminal.py` | Add `run_commands: bool = True` field to `TerminalCreate` |
| `backend/app/routers/terminals.py` | Gate startup-commands injection on `data.run_commands` |
| `frontend/src/shared/types/index.ts` | Add optional `run_commands?: boolean` to `TerminalCreate` interface |
| `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` | Pass `run_commands: false` in top-bar "Open Terminal" calls |
| `frontend/src/features/issues/components/issue-actions.tsx` | Add "Run Issue" button that opens terminal with commands |

---

### Task 1: Backend schema — add `run_commands` flag

**Files:**
- Modify: `backend/app/schemas/terminal.py`

- [ ] **Step 1: Add the field**

```python
class TerminalCreate(BaseModel):
    issue_id: str
    project_id: str
    run_commands: bool = True
```

- [ ] **Step 2: Gate startup commands in the router**

In `backend/app/routers/terminals.py`, find the block starting with `# Inject startup commands into the PTY` (lines ~124–153) and wrap it:

```python
    # Inject startup commands into the PTY
    if data.run_commands:
        try:
            from app.models.issue import Issue
            issue = await db.get(Issue, data.issue_id)
            issue_status = issue.status.value if issue else ""

            cmd_service = TerminalCommandService(db)
            commands = await cmd_service.resolve(data.project_id)
            if commands:
                pty = service.get_pty(terminal["id"])
                variables = {
                    "$issue_id": data.issue_id,
                    "$project_id": data.project_id,
                    "$project_path": project_path,
                }
                for c in commands:
                    if not _evaluate_condition(c.condition, issue_status):
                        continue
                    cmd_text = c.command
                    for var, val in variables.items():
                        cmd_text = cmd_text.replace(var, val)
                    for line in cmd_text.split("\n"):
                        line = line.strip()
                        if line:
                            pty.write(line + "\r\n")
        except Exception:
            logger.warning("Failed to inject startup commands for terminal %s", terminal["id"], exc_info=True)
```

(The env vars and custom variable injection blocks above remain unconditional — they always run.)

- [ ] **Step 3: Verify backend starts without errors**

```bash
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: server starts, no import errors. Ctrl+C to stop.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/terminal.py backend/app/routers/terminals.py
git commit -m "feat: add run_commands flag to TerminalCreate to skip startup command injection"
```

---

### Task 2: Frontend types — expose `run_commands`

**Files:**
- Modify: `frontend/src/shared/types/index.ts`

- [ ] **Step 1: Add optional field**

```typescript
export interface TerminalCreate {
  issue_id: string;
  project_id: string;
  run_commands?: boolean;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | head -30
```

Expected: build succeeds (or only pre-existing errors, no new ones about `TerminalCreate`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/shared/types/index.ts
git commit -m "feat: add optional run_commands field to TerminalCreate type"
```

---

### Task 3: Top-bar "Open Terminal" — bare terminal (no commands)

**Files:**
- Modify: `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`

- [ ] **Step 1: Update `doOpenTerminal` to pass `run_commands: false`**

Current:
```typescript
await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId });
```

Change to:
```typescript
await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId, run_commands: false });
```

This affects the single `doOpenTerminal` function (line ~55), which is called by both the direct button and the "Open Anyway" limit-bypass path.

- [ ] **Step 2: Verify in browser**

Open an issue, click "Open Terminal" in the top bar — terminal should open without auto-running any pre-configured startup commands.

- [ ] **Step 3: Commit**

```bash
git add "frontend/src/routes/projects/\$projectId/issues/\$issueId.tsx"
git commit -m "feat: top-bar Open Terminal opens bare terminal without startup commands"
```

---

### Task 4: Add "Run Issue" button to IssueActions

**Files:**
- Modify: `frontend/src/features/issues/components/issue-actions.tsx`

- [ ] **Step 1: Add props and import**

`IssueActions` needs to know `projectId` (already present) and `issueId` (already present via `issue.id`). Add the terminal hook and a handler.

Add imports at the top:
```typescript
import { Play, XCircle, CheckCircle, Loader2 } from "lucide-react";
import { useCreateTerminal } from "@/features/terminals/hooks";
import { toast } from "sonner";
```

(Replace the existing `XCircle` import line — merge it with the new `Play` icon.)

- [ ] **Step 2: Add `useCreateTerminal` hook and handler inside the component**

Inside `IssueActions`, after the existing hooks:
```typescript
const createTerminal = useCreateTerminal();

const handleRunIssue = async () => {
  try {
    await createTerminal.mutateAsync({ issue_id: issue.id, project_id: projectId });
  } catch (err) {
    toast.error("Failed to open terminal: " + (err instanceof Error ? err.message : "Unknown error"));
  }
};
```

- [ ] **Step 3: Add "Run Issue" button next to "Cancel Issue"**

In the `<div className="flex items-center gap-2 flex-wrap">`, add the button right before the "Cancel Issue" button:

```tsx
<Button
  size="sm"
  variant="outline"
  onClick={handleRunIssue}
  disabled={isPending || createTerminal.isPending}
>
  <Play className="size-4 mr-1" />
  {createTerminal.isPending ? "Opening..." : "Run Issue"}
</Button>
```

Full updated buttons section:
```tsx
<div className="flex items-center gap-2 flex-wrap">
  {issue.status === "Planned" && (
    <Button size="sm" onClick={() => setConfirmAction("accept")} disabled={isPending}>
      <CheckCircle className="size-4 mr-1" />
      Accept Plan
    </Button>
  )}
  {issue.status === "Accepted" && (
    <Button size="sm" onClick={() => setConfirmAction("complete")} disabled={isPending}>
      <CheckCircle className="size-4 mr-1" />
      Mark as Complete
    </Button>
  )}
  <Button
    size="sm"
    variant="outline"
    onClick={handleRunIssue}
    disabled={isPending || createTerminal.isPending}
  >
    <Play className="size-4 mr-1" />
    {createTerminal.isPending ? "Opening..." : "Run Issue"}
  </Button>
  <Button
    size="sm"
    variant="outline"
    className="text-destructive hover:text-destructive"
    onClick={() => setConfirmAction("cancel")}
    disabled={isPending}
  >
    <XCircle className="size-4 mr-1" />
    Cancel Issue
  </Button>
</div>
```

- [ ] **Step 4: Verify in browser**

Open an issue in a non-terminal state. The action area should now show:
- "Accept Plan" or "Mark as Complete" (contextual)
- "Run Issue" (opens terminal with startup commands)
- "Cancel Issue" (unchanged)

Clicking "Run Issue" should open a terminal and run configured startup commands.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/issues/components/issue-actions.tsx
git commit -m "feat: add Run Issue button to IssueActions that opens terminal with startup commands"
```
