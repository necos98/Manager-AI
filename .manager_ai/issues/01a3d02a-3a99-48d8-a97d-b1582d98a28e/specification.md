# Exclude Archived Projects From All Operations

## Problem

Projects on remote/unavailable storage cause the system to hang during cache/index rebuilds and cross-project lookups. The system iterates over all projects — including archived ones — and reads their `.manager_ai/` directories. When that directory is on an unreachable network server, filesystem access blocks.

## Goal

Archived projects must be excluded from **every** operation that iterates over project directories: cache rebuilds, index rebuilds, cross-project ID lookups, and MCP tool calls.

## Design

### 1. Service layer — cross-project scans (core fix)

Five locations call `ProjectService.list_all(archived=None)`, which returns both active and archived projects. Each then iterates over returned projects and reads their `.manager_ai/` directories. Change all to `archived=False`:

| File | Line(s) | Method(s) |
|------|---------|-----------|
| `app/services/issue_service.py` | 92 | `get_by_id()` |
| `app/services/memory_service.py` | 37 | `_locate_memory()` |
| `app/services/task_service.py` | 31, 77, 85, 109 | `_project_path_for_issue()`, `get_by_id()`, `update()`, `delete()` |
| `app/services/issue_relation_service.py` | 42, 145 | `_all_paths()`, `_detect_cycle()` |
| `app/mcp/server.py` | 389, 445, 476 | `update_task_status()`, `update_task_name()`, `delete_task()` |

### 2. Rebuild-index endpoint guard

`app/routers/projects.py` `POST /{project_id}/rebuild-index` — add an archived check. If `project.archived_at is not None`, return HTTP 400 with message "Cannot rebuild index for archived project."

### 3. No changes needed

- `main.py` startup: already filters `archived_at.is_(None)`
- `watcher.start_project()`: already checks `_is_archived()`
- `archive_project` endpoint: already stops watcher + plugins
- Migration script: already filters `archived_at.is_(None)`

## Impact

- Cross-project lookups skip archived projects
- Items in archived projects are invisible to cross-project queries
- Unarchiving restarts watcher and restores visibility
- No schema changes, no migration