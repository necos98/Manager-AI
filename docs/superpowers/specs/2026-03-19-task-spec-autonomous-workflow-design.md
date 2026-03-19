# Task Specification & Autonomous Claude Workflow — Design

**Date:** 2026-03-19
**Status:** Draft

---

## Overview

Shift the task management workflow from a GUI-driven approval loop to a fully autonomous Claude-driven flow. Claude Code manages task selection, writes specifications and plans, and transitions task states via MCP tools. The frontend becomes a read-only dashboard.

---

## Motivation

Previously, Claude submitted a plan and blocked execution waiting for the user to click Accept/Decline in the frontend. The new model puts Claude in charge of interpreting user intent from conversation and calling the appropriate MCP tools to advance the task state. This removes friction, eliminates UI-blocking calls, and introduces a `specification` phase before planning.

---

## New Task State Machine

```
New ──────────────────► Reasoning ──► Planned ──► Accepted ──► Finished
                            ▲
Declined ───────────────────┘

Any state ──────────────────────────────────────────────────► Canceled
```

### States

| State | Description |
|-------|-------------|
| `New` | Task created by user, not yet analyzed |
| `Reasoning` | Claude has written a specification; user reviewing in conversation |
| `Planned` | Claude has written an implementation plan |
| `Accepted` | User approved plan in conversation; Claude begins work |
| `Finished` | Claude completed the task |
| `Canceled` | Task discarded from any state |
| `Declined` | Kept in enum for backward compatibility; transitions to Reasoning via create_task_spec |

### Valid Transitions

| From | To | Triggered by |
|------|----|--------------|
| New / Declined | Reasoning | `create_task_spec` |
| Reasoning | Planned | `create_task_plan` |
| Planned | Accepted | `accept_task` |
| Accepted | Finished | `complete_task` |
| Any | Canceled | `cancel_task` |
| Reasoning | Reasoning | `edit_task_spec` (no state change) |
| Planned | Planned | `edit_task_plan` (no state change) |

**Note — `Reasoning` is MCP-only:** The transitions `New → Reasoning` and `Declined → Reasoning` are **not** added to `VALID_TRANSITIONS` in `task_service.py`. Instead, the new service methods (`create_spec`, `edit_spec`, `create_plan`, `edit_plan`, `accept_task`, `cancel_task`) perform their own status validation and call `update_fields()` directly to set status, bypassing `update_status()`. Only `(REASONING, PLANNED)` is added to `VALID_TRANSITIONS` because `create_plan` (Reasoning → Planned) follows the normal pattern. This approach ensures the REST `PATCH /{task_id}/status` endpoint can never transition a task into or out of `Reasoning` — no additional REST-layer guard is needed.

**Error behavior:** All new service methods must validate the incoming task status before proceeding. If the status is invalid, raise a `ValueError` with a descriptive message. The MCP tool handler catches `ValueError` and returns `{"error": "<message>"}`. This is consistent with the existing `save_plan` pattern. Expected error messages:
- `edit_task_spec`: `"Task must be in Reasoning status to edit spec"`
- `edit_task_plan`: `"Task must be in Planned status to edit plan"`

---

## Database Changes

### New column: `tasks.specification`

```sql
ALTER TABLE tasks ADD COLUMN specification TEXT NULL;
```

- Type: `TEXT`, nullable
- Stores the markdown specification document written by Claude
- Added via a new Alembic migration

### TaskStatus enum: add `Reasoning`

```python
class TaskStatus(str, enum.Enum):
    NEW = "New"
    REASONING = "Reasoning"   # NEW
    PLANNED = "Planned"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    FINISHED = "Finished"
    CANCELED = "Canceled"
```

---

## MCP Tools

### Commented out (disabled)

| Tool | Reason |
|------|--------|
| `get_next_task` | Claude Code selects tasks autonomously; user directs via conversation |
| `save_task_plan` | Replaced by `create_task_plan` + `edit_task_plan` |

**Sequencing note:** Comment out the `@mcp.tool()` decorator and function body in `server.py` **first**, then remove the corresponding keys from `default_settings.json`. The server reads these keys at startup to register tool descriptions; removing them while the tool registration code is still active will cause a `KeyError` crash.

The corresponding keys in `default_settings.json` (`tool.get_next_task.description`, `tool.save_task_plan.description`, `tool.save_task_plan.response_message`) should be **removed** from the JSON file since those tools are no longer registered. The `TaskService.get_next_task()` service method may be retained as dead code (no runtime risk since the MCP tool is disabled).

### Updated tools

#### `get_task_details(project_id, task_id)`
- **Change:** Return dict now includes the `specification` field
- Implementation: add `"specification": task.specification` to the return dict in `server.py`
- The `tool.get_task_details.description` entry in `default_settings.json` must be updated to mention that the response includes a `specification` field (markdown, may be null)

### New tools

#### `create_task_spec(project_id, task_id, spec)`
- Saves the specification markdown to `tasks.specification`
- Transitions status: `New` / `Declined` → `Reasoning`
- Raises `ValueError` if status is not `New` or `Declined`
- Returns: `{"id": ..., "status": "Reasoning", "specification": ...}`
- `default_settings.json` key: `tool.create_task_spec.description`

#### `edit_task_spec(project_id, task_id, spec)`
- Updates `tasks.specification` without changing status
- Valid only when status is `Reasoning`; raises `ValueError` otherwise
- Returns: `{"id": ..., "status": "Reasoning", "specification": ...}`
- `default_settings.json` key: `tool.edit_task_spec.description`

#### `create_task_plan(project_id, task_id, plan)`
- Saves the implementation plan markdown to `tasks.plan`
- Transitions status: `Reasoning` → `Planned`
- Raises `ValueError` if status is not `Reasoning`
- Returns: `{"id": ..., "status": "Planned", "plan": ...}`
- `default_settings.json` key: `tool.create_task_plan.description`

#### `edit_task_plan(project_id, task_id, plan)`
- Updates `tasks.plan` without changing status
- Valid only when status is `Planned`; raises `ValueError` otherwise
- Returns: `{"id": ..., "status": "Planned", "plan": ...}`
- `default_settings.json` key: `tool.edit_task_plan.description`

#### `accept_task(project_id, task_id)`
- Transitions status: `Planned` → `Accepted`
- Raises `ValueError` if status is not `Planned`
- Called by Claude after user confirms in conversation
- Returns: `{"id": ..., "status": "Accepted"}`
- `default_settings.json` key: `tool.accept_task.description`

#### `cancel_task(project_id, task_id)`
- Transitions status: any → `Canceled`
- Called by Claude when user says to discard the task
- Returns: `{"id": ..., "status": "Canceled"}` — only `id` and `status`; no content fields included (intentional)
- `default_settings.json` key: `tool.cancel_task.description`

### Existing tools (fully unchanged)

| Tool | Notes |
|------|-------|
| `get_task_status` | Unchanged |
| `get_project_context` | Unchanged |
| `set_task_name` | Unchanged |
| `complete_task` | Unchanged (Accepted → Finished) |

---

## Backend Changes

### Model (`backend/app/models/task.py`)
- Add `specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)`

### Schema (`backend/app/schemas/task.py`)
- Add `specification: Optional[str] = None` to `TaskResponse`
- Add `REASONING = "Reasoning"` to `TaskStatus` enum

### Service (`backend/app/services/task_service.py`)
- Add `create_spec(task_id, project_id, spec)` — validates New/Declined, raises `ValueError` if `spec` is blank, writes `task.specification` directly (not via `update_fields()`), sets `task.status = REASONING`, flushes to DB
- Add `edit_spec(task_id, project_id, spec)` — validates Reasoning, raises `ValueError` if `spec` is blank, writes `task.specification` directly
- Add `create_plan(task_id, project_id, plan)` — validates Reasoning, raises `ValueError` if `plan` is blank, writes `task.plan` directly, transitions → Planned via `update_status()`
- Add `edit_plan(task_id, project_id, plan)` — validates Planned, raises `ValueError` if `plan` is blank, writes `task.plan` directly
- Add `accept_task(task_id, project_id)` — validates Planned, transitions → Accepted via `update_status()`
- Add `cancel_task(task_id, project_id)` — transitions any → Canceled via `update_status()`
- **Do not use `update_fields()` for `specification` or `plan` writes** — `update_fields()` silently skips `None` values; direct attribute assignment prevents a silent no-op if an empty or falsy value is passed
- Update `VALID_TRANSITIONS` to add only: `(REASONING, PLANNED)` — the other new transitions (`NEW → REASONING`, `DECLINED → REASONING`) are handled inside the new service methods directly (see "Valid Transitions" note above)

### MCP Server (`backend/app/mcp/server.py`)
- Comment out `get_next_task` function and its `@mcp.tool()` decorator
- Comment out `save_task_plan` function and its `@mcp.tool()` decorator
- Update `get_task_details` return dict to include `"specification": task.specification`
- Add 6 new `@mcp.tool()` functions: `create_task_spec`, `edit_task_spec`, `create_task_plan`, `edit_task_plan`, `accept_task`, `cancel_task`

### Settings (`backend/app/mcp/default_settings.json`)
- Remove keys: `tool.get_next_task.description`, `tool.save_task_plan.description`, `tool.save_task_plan.response_message`
- Update key: `tool.get_task_details.description` (mention `specification` field)
- Add keys for all 6 new tools: `tool.create_task_spec.description`, `tool.edit_task_spec.description`, `tool.create_task_plan.description`, `tool.edit_task_plan.description`, `tool.accept_task.description`, `tool.cancel_task.description`

### Migration (`backend/alembic/versions/`)
- New migration file: adds `specification TEXT NULL` column to `tasks`
- The `TaskStatus` enum change in Python is reflected automatically (SQLite stores enums as strings)

---

## Frontend Changes

The frontend becomes **read-only**. No user-initiated state transitions on tasks.

### `frontend/src/pages/TaskDetailPage.jsx`
- Remove **Accept**, **Decline**, **Cancel** action buttons and their click handlers
- Remove the Decline feedback form (`showDeclineForm` state, `feedback` state, the textarea and submit button — lines 111-138 approximately)
- Add **Specification** section: render `task.specification` as markdown (using existing `MarkdownViewer` component), shown only if `task.specification` is not null, placed above the Plan section
- **`decline_feedback` display block (lines 77-82 approximately):** retain as read-only for backward compatibility with existing task data — no removal required. The `decline_feedback` column stays in the database and `TaskResponse` continues to expose it; no data migration needed.

### `frontend/src/components/StatusBadge.jsx`
- Add `Reasoning` badge with color: indigo/purple (consistent with "thinking/analysis" connotation)

### `frontend/src/pages/ProjectDetailPage.jsx`
- Add `"Reasoning"` to the `STATUSES` array (the filter buttons list for task status filtering)

### `frontend/src/api/client.js`
- No changes needed (REST endpoints already return full `TaskResponse` which will include `specification`)

---

## Workflow Example

```
User: "I need a task to add dark mode support"
  → User creates task in frontend (New)

Claude: reads task description via get_task_details
Claude: calls create_task_spec → task moves to Reasoning
  spec: "Feature: dark mode toggle in settings page. Acceptance: ..."

User: "add auto-detect based on OS preference too"
Claude: calls edit_task_spec → spec updated, still Reasoning

User: "ok proceed"
Claude: calls create_task_plan → task moves to Planned
  plan: "1. Add useColorScheme hook. 2. Store in localStorage. ..."

User: "perfect, go ahead"
Claude: calls accept_task → task moves to Accepted
Claude: implements feature
Claude: calls complete_task → task moves to Finished
```

---

## Out of Scope

- Task creation via MCP (user still creates tasks in frontend)
- Multi-agent task assignment
- Spec/plan diffing or version history
- `edit_task_plan` from `Accepted` status (plan is locked once accepted)
