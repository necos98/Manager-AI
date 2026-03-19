# Task Specification & Autonomous Claude Workflow — Design

**Date:** 2026-03-19
**Status:** Approved

---

## Overview

Shift the task management workflow from a GUI-driven approval loop to a fully autonomous Claude-driven flow. Claude Code manages task selection, writes specifications and plans, and transitions task states via MCP tools. The frontend becomes a read-only dashboard.

---

## Motivation

Previously, Claude submitted a plan and blocked execution waiting for the user to click Accept/Decline in the frontend. The new model puts Claude in charge of interpreting user intent from conversation and calling the appropriate MCP tools to advance the task state. This removes friction, eliminates UI-blocking calls, and introduces a `specification` phase before planning.

---

## New Task State Machine

```
New ──► Reasoning ──► Planned ──► Accepted ──► Finished
 ▲           │             │
 └─Declined  └─────────────┴──────────────────► Canceled (from any state)
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
| `Declined` | Kept in enum for backward compatibility; no longer exposed in UI |

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

### New tools

#### `create_task_spec(project_id, task_id, spec)`
- Saves the specification markdown to `tasks.specification`
- Transitions status: `New` / `Declined` → `Reasoning`
- Returns: `id`, `status`, `specification`

#### `edit_task_spec(project_id, task_id, spec)`
- Updates `tasks.specification` without changing status
- Valid when status is `Reasoning` (or any, for flexibility during iteration)
- Returns: `id`, `status`, `specification`

#### `create_task_plan(project_id, task_id, plan)`
- Saves the implementation plan markdown to `tasks.plan`
- Transitions status: `Reasoning` → `Planned`
- Returns: `id`, `status`, `plan`

#### `edit_task_plan(project_id, task_id, plan)`
- Updates `tasks.plan` without changing status
- Valid when status is `Planned`
- Returns: `id`, `status`, `plan`

#### `accept_task(project_id, task_id)`
- Transitions status: `Planned` → `Accepted`
- Called by Claude after user confirms in conversation
- Returns: `id`, `status`

#### `cancel_task(project_id, task_id)`
- Transitions status: any → `Canceled`
- Called by Claude when user says to discard the task
- Returns: `id`, `status`

### Existing tools (unchanged)

| Tool | Notes |
|------|-------|
| `get_task_details` | Now also returns `specification` field |
| `get_task_status` | Unchanged |
| `get_project_context` | Unchanged |
| `set_task_name` | Unchanged |
| `complete_task` | Unchanged (Accepted → Finished) |

---

## Backend Changes

### Model (`backend/app/models/task.py`)
- Add `specification: Optional[str]` column

### Schema (`backend/app/schemas/task.py`)
- Add `specification: Optional[str]` to `TaskResponse`
- Add `Reasoning` to `TaskStatus` enum

### Service (`backend/app/services/task_service.py`)
- Add `create_spec(task_id, project_id, spec)` — saves spec, transitions → Reasoning
- Add `edit_spec(task_id, project_id, spec)` — updates spec only
- Add `create_plan(task_id, project_id, plan)` — saves plan, transitions → Planned
- Add `edit_plan(task_id, project_id, plan)` — updates plan only
- Add `accept_task(task_id, project_id)` — transitions → Accepted
- Add `cancel_task(task_id, project_id)` — transitions → Canceled
- Update `VALID_TRANSITIONS` to include `Reasoning`

### MCP Server (`backend/app/mcp/server.py`)
- Comment out `get_next_task` and `save_task_plan`
- Add 6 new tool functions (delegating to service methods)

### Migration (`backend/alembic/versions/`)
- New migration: add `specification TEXT NULL` to `tasks`
- Update `TaskStatus` enum check constraint to include `Reasoning`

---

## Frontend Changes

The frontend becomes **read-only**. No user-initiated state transitions.

### `TaskDetailPage.jsx`
- Remove **Accept**, **Decline**, **Cancel** action buttons
- Add **Specification** section (rendered as markdown, above Plan section)
- Show specification only if not null

### `StatusBadge.jsx`
- Add `Reasoning` badge with an appropriate color (e.g., purple/indigo)

### `TaskList.jsx`
- Add `Reasoning` to status filter options

### `api/client.js`
- No changes needed (REST endpoints already return full `TaskResponse`)

---

## Workflow Example

```
User: "I need a task to add dark mode support"
  → User creates task in frontend (New)

Claude: reads task description via get_task_details
Claude: calls create_task_spec → task moves to Reasoning
  spec: "Feature: dark mode toggle in settings page. Acceptance criteria: ..."

User: "looks good, add an auto-detect based on OS preference too"
Claude: calls edit_task_spec → spec updated, still Reasoning

User: "ok proceed"
Claude: calls create_task_plan → task moves to Planned
  plan: "1. Add useColorScheme hook. 2. Store preference in localStorage. ..."

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
