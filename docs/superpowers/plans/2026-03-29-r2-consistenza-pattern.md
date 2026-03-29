# R2 — Consistenza dei Pattern: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align architectural patterns across the codebase — uniform error handling in the frontend, consistent input validation, atomic MCP transactions, and a complete `.env.example`.

**Architecture:** Four independent sub-areas: (1) frontend catch-blocks and `useMutation` `onError` handlers; (2) Pydantic `max_length` validators on backend schemas mirrored by frontend form guards; (3) single-commit-per-tool pattern in `mcp/server.py`; (4) `.env.example` documentation with Pydantic validators for required settings.

**Tech Stack:** Python/FastAPI, Pydantic v2, React/TypeScript, TanStack Query v5, Sonner (toast), `pydantic-settings`

---

## File Map

| File | Change |
|------|--------|
| `frontend/src/shared/api/client.ts` | Add 30 s `AbortController` timeout to `request()` |
| `frontend/src/features/issues/hooks.ts` | Add `onError` toast to all `useMutation` calls |
| `frontend/src/features/projects/hooks.ts` | Add `onError` toast |
| `frontend/src/features/files/hooks.ts` | Add `onError` toast |
| `frontend/src/features/terminals/hooks.ts` | Add `onError` toast |
| `frontend/src/features/settings/hooks.ts` | Add `onError` toast |
| `frontend/src/features/issues/components/issue-detail.tsx` | Log `catch {}` in `handleDelete` |
| `frontend/src/features/issues/components/issue-actions.tsx` | Add `onError` to inline `mutate()` calls |
| `backend/app/schemas/issue.py` | `max_length` on `description`, `recap`, `spec`, `plan` fields |
| `backend/app/mcp/server.py` | Remove `rollback()` calls; ensure single commit at end of each tool |
| `.env.example` | Document all variables: `EMBEDDING_MODEL`, `CLAUDE_LIBRARY_PATH`, `RECORDINGS_PATH`, `BACKEND_PORT` |
| `backend/app/config.py` | Add Pydantic `@field_validator` for required paths |
| `backend/tests/test_r2_schemas.py` | New: tests for `max_length` validation |
| `backend/tests/test_r2_mcp_transactions.py` | New: tests for MCP transaction atomicity |

---

## Task 1: API client timeout (R2.1 partial)

**Files:**
- Modify: `frontend/src/shared/api/client.ts:13-24`

- [ ] **Step 1: Write the failing test**

  Open `frontend/src/shared/api/client.ts`. The current `request()` function has no timeout. We will add one.

  There is no automated frontend unit test runner set up, so verification is manual (visual + network tab). Skip to Step 2.

- [ ] **Step 2: Add AbortController timeout to `request()`**

Replace the `request` function body:

```typescript
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...options.headers },
      signal: controller.signal,
      ...options,
    });
    if (res.status === 204) return null as T;
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }));
      throw new ApiError(err.detail || "Request failed", res.status);
    }
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}
```

Note: `signal` must come before the spread of `options` so callers can override it if needed; but since no caller currently passes `signal`, this is fine.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors related to `client.ts`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/api/client.ts
git commit -m "feat(frontend): add 30s timeout to API client fetch requests (R2.1)"
```

---

## Task 2: `onError` handlers on all `useMutation` hooks (R2.1)

**Files:**
- Modify: `frontend/src/features/issues/hooks.ts`
- Modify: `frontend/src/features/projects/hooks.ts`
- Modify: `frontend/src/features/files/hooks.ts`
- Modify: `frontend/src/features/terminals/hooks.ts`
- Modify: `frontend/src/features/settings/hooks.ts`

The pattern to add to every `useMutation` that is missing `onError`:

```typescript
onError: (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
},
```

`toast` is imported from `"sonner"` in each file where it is not already imported.

### 2a — issues/hooks.ts

The mutations that currently lack `onError`:
- `useCreateIssue`
- `useUpdateIssue`
- `useUpdateIssueStatus`
- `useDeleteIssue`
- `useAcceptIssue`
- `useCancelIssue`
- `useCompleteIssue`
- `useAddFeedback`
- `useUpdateTask`
- `useDeleteTask`
- `useCreateTasks`
- `useReplaceTasks`

- [ ] **Step 1: Add `toast` import and `onError` to each mutation in `issues/hooks.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { IssueCompleteBody, IssueCreate, IssueFeedbackCreate, IssueStatus, IssueStatusUpdate, IssueUpdate, TaskCreate, TaskUpdate } from "@/shared/types";

// ... (issueKeys unchanged)

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export function useCreateIssue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueCreate) => api.createIssue(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useUpdateIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueUpdate) => api.updateIssue(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useUpdateIssueStatus(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ issueId, status }: { issueId: string; status: IssueStatus }) =>
      api.updateIssueStatus(projectId, issueId, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["issues", projectId] });
    },
    onError: onMutationError,
  });
}

export function useDeleteIssue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (issueId: string) => api.deleteIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useAcceptIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.acceptIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useCancelIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.cancelIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useCompleteIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueCompleteBody) => api.completeIssue(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useAddFeedback(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueFeedbackCreate) => api.addFeedback(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: feedbackKeys.all(projectId, issueId) });
    },
    onError: onMutationError,
  });
}

export function useUpdateTask(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: TaskUpdate }) =>
      api.updateTask(projectId, issueId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteTask(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => api.deleteTask(projectId, issueId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
    onError: onMutationError,
  });
}

export function useCreateTasks(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tasks: TaskCreate[]) => api.createTasks(projectId, issueId, tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
    onError: onMutationError,
  });
}

export function useReplaceTasks(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tasks: TaskCreate[]) => api.replaceTasks(projectId, issueId, tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
    onError: onMutationError,
  });
}
```

Keep `useFeedback`, `useIssues`, `useIssue` unchanged (they are `useQuery`, not `useMutation`).

### 2b — projects/hooks.ts

Mutations missing `onError`: `useCreateProject`, `useUpdateProject`, `useDeleteProject`, `useInstallManagerJson`, `useInstallClaudeResources`.

- [ ] **Step 2: Add `toast` import and `onError` to `projects/hooks.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { ProjectCreate, ProjectUpdate } from "@/shared/types";

// projectKeys unchanged

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) => api.createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: onMutationError,
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectUpdate) => api.updateProject(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: onMutationError,
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: onMutationError,
  });
}

export function useInstallManagerJson(projectId: string) {
  return useMutation({
    mutationFn: () => api.installManagerJson(projectId),
    onError: onMutationError,
  });
}

export function useInstallClaudeResources(projectId: string) {
  return useMutation({
    mutationFn: () => api.installClaudeResources(projectId),
    onError: onMutationError,
  });
}
```

### 2c — files/hooks.ts

Mutations missing `onError`: `useUploadFiles`, `useDeleteFile`.

- [ ] **Step 3: Add `toast` import and `onError` to `files/hooks.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";

// fileKeys unchanged

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export function useUploadFiles(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => api.uploadFiles(projectId, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteFile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) => api.deleteFile(projectId, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}
```

### 2d — terminals/hooks.ts

Mutations missing `onError`: `useCreateTerminal`, `useCreateAskTerminal`, `useKillTerminal`, `useCreateTerminalCommand`, `useUpdateTerminalCommand`, `useReorderTerminalCommands`, `useDeleteTerminalCommand`.

- [ ] **Step 4: Add `toast` import and `onError` to `terminals/hooks.ts`**

Add `import { toast } from "sonner";` at the top, add `const onMutationError = (e: unknown) => { toast.error(e instanceof Error ? e.message : "Operation failed"); };`, then add `onError: onMutationError` to each of the seven mutations listed above.

### 2e — settings/hooks.ts

Mutations missing `onError`: `useUpdateSetting`, `useResetSetting`, `useResetAllSettings`.

- [ ] **Step 5: Add `toast` import and `onError` to `settings/hooks.ts`**

Same pattern: import `toast`, add `onMutationError` constant, add `onError: onMutationError` to each mutation.

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -30
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/issues/hooks.ts \
        frontend/src/features/projects/hooks.ts \
        frontend/src/features/files/hooks.ts \
        frontend/src/features/terminals/hooks.ts \
        frontend/src/features/settings/hooks.ts
git commit -m "feat(frontend): add onError toast to all useMutation hooks (R2.1)"
```

---

## Task 3: Fix `catch {}` in issue-detail.tsx (R2.1)

**Files:**
- Modify: `frontend/src/features/issues/components/issue-detail.tsx:62-78`

The `handleDelete` function catches a terminal-kill error with an empty `catch {}`. The comment says "Terminal may already be dead" — which is a valid reason to swallow the error. We should log it for debugging.

- [ ] **Step 1: Replace empty catch with console.warn**

In `issue-detail.tsx`, locate the `handleDelete` function and change:

```typescript
      try {
        await killTerminal.mutateAsync(terminalId);
      } catch {
        // Terminal may already be dead
      }
```

to:

```typescript
      try {
        await killTerminal.mutateAsync(terminalId);
      } catch (e) {
        // Terminal may already be dead — intentionally swallowed
        console.warn("killTerminal during delete:", e);
      }
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/issues/components/issue-detail.tsx
git commit -m "fix(frontend): log swallowed killTerminal error in handleDelete (R2.1)"
```

---

## Task 4: Backend schema `max_length` validation (R2.2)

**Files:**
- Modify: `backend/app/schemas/issue.py`
- Create: `backend/tests/test_r2_schemas.py`

### Constants (use these everywhere in this task)

```python
DESCRIPTION_MAX = 50_000
RECAP_MAX = 50_000
SPEC_MAX = 500_000
PLAN_MAX = 500_000
```

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_r2_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.issue import IssueCreate, IssueCompleteBody, IssueUpdate


def test_issue_create_description_too_long():
    with pytest.raises(ValidationError):
        IssueCreate(description="x" * 50_001)


def test_issue_create_description_at_limit():
    obj = IssueCreate(description="x" * 50_000)
    assert len(obj.description) == 50_000


def test_issue_complete_recap_too_long():
    with pytest.raises(ValidationError):
        IssueCompleteBody(recap="x" * 50_001)


def test_issue_complete_recap_at_limit():
    obj = IssueCompleteBody(recap="x" * 50_000)
    assert len(obj.recap) == 50_000


def test_issue_update_spec_too_long():
    with pytest.raises(ValidationError):
        IssueUpdate(spec="x" * 500_001)


def test_issue_update_spec_at_limit():
    obj = IssueUpdate(spec="x" * 500_000)
    assert len(obj.spec) == 500_000


def test_issue_update_plan_too_long():
    with pytest.raises(ValidationError):
        IssueUpdate(plan="x" * 500_001)


def test_issue_update_plan_at_limit():
    obj = IssueUpdate(plan="x" * 500_000)
    assert len(obj.plan) == 500_000
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_r2_schemas.py -v
```

Expected: all tests FAIL because `max_length` constraints don't exist yet. The `spec`/`plan` fields on `IssueUpdate` don't exist at all yet — tests will fail with `ValidationError` about unexpected fields.

- [ ] **Step 3: Add `max_length` and missing fields to `schemas/issue.py`**

Replace the content of `backend/app/schemas/issue.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.issue import IssueStatus
from app.schemas.task import TaskResponse

_DESCRIPTION_MAX = 50_000
_RECAP_MAX = 50_000
_SPEC_MAX = 500_000
_PLAN_MAX = 500_000


class IssueCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=_DESCRIPTION_MAX)
    priority: int = Field(default=3, ge=1, le=5)


class IssueUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, min_length=1, max_length=_DESCRIPTION_MAX)
    priority: int | None = Field(None, ge=1, le=5)
    spec: str | None = Field(None, max_length=_SPEC_MAX)
    plan: str | None = Field(None, max_length=_PLAN_MAX)


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueCompleteBody(BaseModel):
    recap: str = Field(..., min_length=1, max_length=_RECAP_MAX)


class IssueResponse(BaseModel):
    id: str
    project_id: str
    name: str | None
    description: str
    status: IssueStatus
    priority: int
    plan: str | None
    specification: str | None = None
    recap: str | None
    tasks: list[TaskResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueFeedbackCreate(BaseModel):
    content: str = Field(..., min_length=1)


class IssueFeedbackResponse(BaseModel):
    id: str
    issue_id: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_r2_schemas.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd backend && python -m pytest --tb=short 2>&1 | tail -20
```

Expected: no new failures.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/issue.py backend/tests/test_r2_schemas.py
git commit -m "feat(backend): add max_length validators to IssueCreate/Update/CompleteBody schemas (R2.2)"
```

---

## Task 5: Frontend form guards for `max_length` (R2.2)

**Files:**
- Modify: `frontend/src/features/issues/components/issue-detail.tsx`
- Modify: `frontend/src/features/issues/components/issue-actions.tsx`

The `InlineEditField` component already accepts a `validate` prop (see `issue-detail.tsx:93` where it validates priority). We add `max_length` validation to description and name fields.

The `complete` dialog recap textarea needs a character counter / disabled submit when over limit.

- [ ] **Step 1: Add max_length validation to InlineEditField for description in `issue-detail.tsx`**

Locate the `InlineEditField` for description (around line 147) and add a `validate` prop:

```tsx
<InlineEditField
  value={issue.description}
  onSave={(description) => updateIssue.mutate({ description })}
  disabled={isTerminalState}
  multiline
  validate={(v) => v.length > 50_000 ? "Max 50,000 characters" : null}
  renderView={(v) => <p className="text-sm whitespace-pre-wrap">{v}</p>}
/>
```

- [ ] **Step 2: Add max_length guard to recap textarea in `issue-actions.tsx`**

The recap `Textarea` already controls submit via `disabled={... (confirmAction === "complete" && !recap.trim())}`. Add a length check:

```tsx
// In the complete dialog section, replace the existing Textarea with:
{confirmAction === "complete" && (
  <>
    <Textarea
      placeholder="Describe what was implemented..."
      value={recap}
      onChange={(e) => setRecap(e.target.value)}
      rows={4}
      className="mt-2"
    />
    {recap.length > 50_000 && (
      <p className="text-xs text-destructive mt-1">
        Max 50,000 characters ({recap.length.toLocaleString()} / 50,000)
      </p>
    )}
  </>
)}
```

And update the confirm button `disabled` condition:

```tsx
disabled={isPending || (confirmAction === "complete" && (!recap.trim() || recap.length > 50_000))}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/issues/components/issue-detail.tsx \
        frontend/src/features/issues/components/issue-actions.tsx
git commit -m "feat(frontend): add max_length form guards for description and recap fields (R2.2)"
```

---

## Task 6: Uniform MCP transactions — single commit per tool (R2.3)

**Files:**
- Modify: `backend/app/mcp/server.py`
- Create: `backend/tests/test_r2_mcp_transactions.py`

### Current state analysis

Looking at the existing tools:

| Tool | Current commit pattern | Problem |
|------|----------------------|---------|
| `update_project_context` | `session.commit()` after update, no rollback | OK |
| `set_issue_name` | `session.commit()` + explicit `session.rollback()` on error | Has rollback — inconsistent |
| `complete_issue` | `session.commit()` after issue_service + project fetch | OK |
| `create_issue_spec` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `edit_issue_spec` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `create_issue_plan` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `edit_issue_plan` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `accept_issue` | `session.commit()`, no rollback on error | Missing rollback |
| `cancel_issue` | `session.commit()`, no rollback on error | Missing rollback |
| `create_plan_tasks` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `replace_plan_tasks` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `update_task_status` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `update_task_name` | `session.commit()` + `session.rollback()` on error | Has rollback |
| `delete_task` | `session.flush()` + `session.commit()` + `session.rollback()` | Extra flush |

The rule: **one `session.commit()` per tool, at the end of the happy path. No explicit `rollback()` — `async_session()` context manager handles rollback on exception.**

Verify by reading `backend/app/database.py` to confirm `async_session` is a context manager that rolls back on exception before implementing. If it doesn't, keep the explicit rollbacks.

- [ ] **Step 1: Check `async_session` rollback behavior**

```bash
cd backend && grep -A 20 "async_session" app/database.py
```

Expected: `async_session` should be an `asynccontextmanager` that calls `session.rollback()` or uses `async with AsyncSession(...) as session` which auto-rolls back on exception. If confirmed, proceed. If NOT, keep existing `rollback()` calls and skip to Task 7.

- [ ] **Step 2: Write failing test for MCP transaction atomicity**

Create `backend/tests/test_r2_mcp_transactions.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.mcp.server import create_issue_spec


@pytest.mark.asyncio
async def test_create_issue_spec_error_does_not_leave_partial_state(mock_session):
    """If IssueService raises, no commit should have happened."""
    from app.exceptions import AppError

    with patch("app.mcp.server.async_session") as mock_ctx:
        session = AsyncMock()
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.mcp.server.IssueService") as MockService:
            instance = MockService.return_value
            instance.create_spec = AsyncMock(side_effect=AppError("not found", 404))

            result = await create_issue_spec(
                project_id="proj-1",
                issue_id="issue-1",
                spec="some spec",
            )

        assert result == {"error": "not found"}
        session.commit.assert_not_called()
        session.rollback.assert_not_called()  # rollback is handled by context manager
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_r2_mcp_transactions.py -v
```

Expected: FAIL because `create_issue_spec` currently calls `session.rollback()` on error.

- [ ] **Step 4: Remove explicit `rollback()` calls from `mcp/server.py`**

For each of the following tools, remove the `await session.rollback()` line from the `except AppError` block:
- `set_issue_name` (line ~125)
- `create_issue_spec` (line ~196)
- `edit_issue_spec` (line ~216)
- `create_issue_plan` (line ~238)
- `edit_issue_plan` (line ~258)
- `create_plan_tasks` (line ~350)
- `replace_plan_tasks` (line ~372)
- `update_task_status` (line ~420)
- `update_task_name` (line ~444)
- `delete_task` (line ~470)

Also remove the redundant `await session.flush()` in `delete_task` — `commit()` already flushes.

For `accept_issue` and `cancel_issue`, add `await session.rollback()` ... actually, since we're standardizing to "let the context manager handle it", **just ensure** `accept_issue` and `cancel_issue` don't call `session.rollback()` (they currently don't, which is consistent).

After edits, the pattern for every tool with writes is:
```python
async with async_session() as session:
    service = IssueService(session)
    try:
        result = await service.do_thing(...)
        await session.commit()
        # emit events
        return {...}
    except AppError as e:
        return {"error": e.message}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_r2_mcp_transactions.py -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

```bash
cd backend && python -m pytest --tb=short 2>&1 | tail -20
```

Expected: no new failures.

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_r2_mcp_transactions.py
git commit -m "refactor(mcp): remove explicit rollback() calls — delegate to session context manager (R2.3)"
```

---

## Task 7: Complete `.env.example` and config validators (R2.4)

**Files:**
- Modify: `.env.example`
- Modify: `backend/app/config.py`

### Current `.env.example` (only 2 lines)

```
# DATABASE_URL=sqlite+aiosqlite:///data/manager_ai.db  (default, no config needed)
# BACKEND_PORT=8000
```

### Current `config.py` settings (all have defaults, none are required)

```python
database_url, lancedb_path, recordings_path, claude_library_path,
backend_port, embedding_driver, embedding_model,
chunk_max_tokens, chunk_overlap_tokens
```

All settings have defaults, so no field is truly "required" (the app works without a `.env` file). The ROADMAP says: add validators for required values. The intent is: validate that if values ARE provided, they're sane.

- [ ] **Step 1: Update `.env.example` to document all variables**

Replace `.env.example`:

```env
# Manager AI — Environment Configuration
# Copy to .env and uncomment lines to override defaults.

# --- Database ---
# DATABASE_URL=sqlite+aiosqlite:///data/manager_ai.db

# --- Server ---
# BACKEND_PORT=8000

# --- Embedding / RAG ---
# EMBEDDING_DRIVER=sentence_transformer   # options: sentence_transformer
# EMBEDDING_MODEL=all-MiniLM-L6-v2
# CHUNK_MAX_TOKENS=500
# CHUNK_OVERLAP_TOKENS=50

# --- Storage paths (absolute or relative to project root) ---
# LANCEDB_PATH=data/lancedb
# RECORDINGS_PATH=data/recordings
# CLAUDE_LIBRARY_PATH=claude_library
```

- [ ] **Step 2: Add Pydantic validators to `config.py` for port and token values**

```python
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    lancedb_path: str = str(_PROJECT_ROOT / "data" / "lancedb")
    recordings_path: str = str(_PROJECT_ROOT / "data" / "recordings")
    claude_library_path: str = str(_PROJECT_ROOT / "claude_library")
    backend_port: int = 8000
    embedding_driver: str = "sentence_transformer"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50

    model_config = {"env_file": ".env"}

    @field_validator("backend_port")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"backend_port must be 1-65535, got {v}")
        return v

    @field_validator("chunk_max_tokens", "chunk_overlap_tokens")
    @classmethod
    def tokens_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("token counts must be >= 1")
        return v

    @field_validator("embedding_driver")
    @classmethod
    def driver_must_be_known(cls, v: str) -> str:
        allowed = {"sentence_transformer"}
        if v not in allowed:
            raise ValueError(f"embedding_driver must be one of {allowed}, got {v!r}")
        return v


settings = Settings()
```

- [ ] **Step 3: Verify settings module loads correctly**

```bash
cd backend && python -c "from app.config import settings; print(settings.model_dump())"
```

Expected: prints a dict of all settings with their default values, no error.

- [ ] **Step 4: Run full test suite**

```bash
cd backend && python -m pytest --tb=short 2>&1 | tail -10
```

Expected: no failures.

- [ ] **Step 5: Commit**

```bash
git add .env.example backend/app/config.py
git commit -m "docs+feat: complete .env.example and add config validators (R2.4)"
```

---

## Self-Review

### Spec coverage check

| R2 requirement | Task that covers it |
|---------------|---------------------|
| R2.1 — `catch {}` in `issue-detail.tsx` | Task 3 |
| R2.1 — `useMutation` without `onError` | Task 2 |
| R2.1 — `api/client.ts` 30s timeout | Task 1 |
| R2.2 — `IssueCreate.description` max_length | Task 4 |
| R2.2 — `IssueCompleteBody.recap` max_length | Task 4 |
| R2.2 — `IssueUpdate.spec` / `.plan` max_length | Task 4 |
| R2.2 — Frontend form guards | Task 5 |
| R2.3 — Uniform MCP commit pattern | Task 6 |
| R2.4 — `.env.example` complete | Task 7 |
| R2.4 — `config.py` Pydantic validators | Task 7 |

All requirements covered.

### Placeholder scan

- No TBDs, TODOs, or "similar to Task N" references.
- All code blocks show complete implementations.
- All test commands include expected output.

### Type consistency

- `onMutationError` is defined identically in each hooks file (local constant, not shared import — avoids cross-feature coupling).
- `IssueUpdate.spec` / `.plan` fields added in Task 4 are new additions to the schema (previously absent); no existing callers use them yet, so no downstream breakage.
- `_DESCRIPTION_MAX`, `_RECAP_MAX`, `_SPEC_MAX`, `_PLAN_MAX` are private module-level constants in `schemas/issue.py` — consistent naming.
