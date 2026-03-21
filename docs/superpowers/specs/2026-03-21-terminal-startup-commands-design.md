# Terminal Startup Commands

## Summary

Add a system for configuring startup commands that execute automatically when a terminal is opened. Commands can be configured globally (apply to all projects as fallback) or per-project (override globals). When a project has its own commands, only those run; otherwise, global commands run.

## Database

New table `terminal_commands`:

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer, PK, autoincrement | |
| `command` | Text, NOT NULL | The command to execute. Must be non-empty, no newlines allowed. |
| `sort_order` | Integer, NOT NULL | Execution order (0, 1, 2...) |
| `project_id` | String, FK → projects.id ON DELETE CASCADE, nullable | NULL = global, set = per-project |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Auto-updated on modification |

Unique constraint on `(project_id, sort_order)` to prevent ambiguous ordering.

Requires a new Alembic migration.

Fallback logic: when opening a terminal for a project, the backend looks for commands with that `project_id` first. If none found, it falls back to commands with `project_id = NULL` (global).

## Schemas

New file `backend/app/schemas/terminal_command.py`:

- `TerminalCommandCreate`: `command` (str, non-empty), `sort_order` (int), `project_id` (str, optional)
- `TerminalCommandUpdate`: `command` (str, optional), `sort_order` (int, optional)
- `TerminalCommandOut`: all fields from the DB model
- `TerminalCommandReorder`: `commands` (list of `{id, sort_order}`)

## Service Layer

New file `backend/app/services/terminal_command_service.py` with `TerminalCommandService`:

- `list(project_id: str | None)` → list commands filtered by project_id (NULL = global)
- `resolve(project_id: str)` → return project commands if any exist, otherwise global commands (implements fallback)
- `create(command, sort_order, project_id?)` → create a command
- `update(id, command?, sort_order?)` → update a command
- `reorder(commands: list[{id, sort_order}])` → bulk reorder
- `delete(id)` → delete a command

This is a DB-backed service, separate from the in-memory `TerminalService`.

## API Endpoints

REST endpoints under `/api/terminal-commands`.

**Important:** The `/reorder` route MUST be declared before `/{id}` to avoid FastAPI matching "reorder" as an id parameter.

| Method | Path | Description |
|--------|------|-------------|
| `GET /api/terminal-commands` | `?project_id=X` (optional) | List commands. No project_id → global. With project_id → project-specific |
| `POST /api/terminal-commands` | Body: `{command, sort_order, project_id?}` | Create a new command |
| `PUT /api/terminal-commands/reorder` | Body: `{commands: [{id, sort_order}, ...]}` | Bulk reorder (declared before /{id}) |
| `PUT /api/terminal-commands/{id}` | Body: `{command?, sort_order?}` | Update command text or order |
| `DELETE /api/terminal-commands/{id}` | Delete a command |

## Terminal Execution Flow

In the `create_terminal` router endpoint (`terminals.py`), after calling `service.create()`:

1. Use `TerminalCommandService.resolve(project_id)` to get the effective commands
2. If commands exist, concatenate with ` && ` and write to PTY followed by `\n`
3. This is fail-fast: if a command fails, subsequent commands do not run

This happens at the router level (which has DB access), not inside `TerminalService` (which is in-memory only). The commands are written before the frontend WebSocket connects, so the user sees them already executing.

## Frontend — Settings Page (Global Commands)

In the existing `SettingsPage.jsx`, add a new **"Terminal"** tab alongside existing tabs (Server, Tool Descriptions, Response Messages).

Contents:
- Explanatory text: *"These commands run automatically when opening a terminal. They apply only when a project has no project-specific commands."*
- Ordered list of commands, each with:
  - Text input field with the command
  - Up/down arrows to reorder
  - Delete button (X)
- "Add Command" button at the bottom
- Changes save immediately (on blur for text edits, on click for reorder/delete)

## Frontend — ProjectDetailPage (Per-Project Commands)

In `ProjectDetailPage.jsx`, add a **"Terminal Settings"** section.

Contents:
- Explanatory text: *"These commands run when opening a terminal for this project. When set, they override the global terminal commands."*
- Same UI as global: ordered list + arrows + delete + add
- When empty: *"No project commands configured. Global commands will be used."*

## Frontend — API Client

New methods in `client.js`:
- `listTerminalCommands(projectId?)` → GET
- `createTerminalCommand(data)` → POST
- `updateTerminalCommand(id, data)` → PUT
- `reorderTerminalCommands(commands)` → PUT /reorder
- `deleteTerminalCommand(id)` → DELETE

## Unchanged

- WebSocket flow: no changes
- TerminalPanel component: no changes
- `terminal_soft_limit` setting: stays in the existing settings system

## Testing

- Backend unit tests for `TerminalCommandService` (CRUD, fallback logic global/project, cascade delete)
- Backend API tests for all endpoints (including route ordering for /reorder vs /{id})
- Verify startup commands are written to PTY on terminal creation
