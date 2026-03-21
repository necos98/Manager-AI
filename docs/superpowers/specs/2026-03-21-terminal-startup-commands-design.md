# Terminal Startup Commands

## Summary

Add a system for configuring startup commands that execute automatically when a terminal is opened. Commands can be configured globally (apply to all projects as fallback) or per-project (override globals). When a project has its own commands, only those run; otherwise, global commands run.

## Database

New table `terminal_commands`:

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer, PK, autoincrement | |
| `command` | Text, NOT NULL | The command to execute |
| `sort_order` | Integer, NOT NULL | Execution order (0, 1, 2...) |
| `project_id` | String, FK → projects.id, nullable | NULL = global, set = per-project |
| `created_at` | DateTime | Creation timestamp |

Fallback logic: when opening a terminal for a project, the backend looks for commands with that `project_id` first. If none found, it falls back to commands with `project_id = NULL` (global).

## API Endpoints

REST endpoints under `/api/terminal-commands`:

| Method | Path | Description |
|--------|------|-------------|
| `GET /api/terminal-commands` | `?project_id=X` (optional) | List commands. No project_id → global. With project_id → project-specific |
| `POST /api/terminal-commands` | Body: `{command, sort_order, project_id?}` | Create a new command |
| `PUT /api/terminal-commands/{id}` | Body: `{command?, sort_order?}` | Update command text or order |
| `PUT /api/terminal-commands/reorder` | Body: `{commands: [{id, sort_order}, ...]}` | Bulk reorder |
| `DELETE /api/terminal-commands/{id}` | Delete a command |

## Terminal Execution Flow

In `TerminalService.create()`, after spawning the PTY:

1. Query commands for the terminal's `project_id`, ordered by `sort_order`
2. If no results, query global commands (`project_id = NULL`), ordered by `sort_order`
3. If commands exist, concatenate with ` && ` and write to PTY followed by `\n`

This happens before the frontend WebSocket connects, so the user sees the commands already executing.

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

## Unchanged

- WebSocket flow: no changes
- TerminalPanel component: no changes
- `terminal_soft_limit` setting: stays in the existing settings system

## Testing

- Backend unit tests for the service layer (CRUD, fallback logic global/project)
- Backend API tests for all endpoints
- Verify startup commands are written to PTY on terminal creation
