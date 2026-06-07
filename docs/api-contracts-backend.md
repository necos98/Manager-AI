# API Contracts — Backend

**Part:** backend
**Project Type:** Python/FastAPI
**Generated:** 2026-06-07
**Total Endpoints:** 67+

## API Overview

Base URL: `http://localhost:8000/api`

| Prefix | Router File | Endpoints |
|--------|------------|-----------|
| `/api/projects` | projects.py | 10 |
| `/api/projects/{id}/issues` | issues.py | 12 |
| `/api/projects/{id}/tasks` | tasks.py | 5 |
| `/api/projects/{id}/activity` | activity.py | 1 |
| `/api/projects/{id}/files` | files.py | 8 |
| `/api/projects/{id}/settings` | project_settings.py | 3 |
| `/api/projects/{id}/skills` | project_skills.py | 3 |
| `/api/projects/{id}/links` | project_links.py | 4 |
| `/api/projects/{id}/templates` | project_templates.py | 4 |
| `/api/projects/{id}/plugins` | plugins.py | 7 |
| `/api/projects/{id}/credentials` | credentials.py | 4 |
| `/api/terminals` | terminals.py | 10 |
| `/api/terminal-commands` | terminal_commands.py | 6 |
| `/api/agents` | agents.py | 10 |
| `/api/pipelines` | pipelines.py | 15 |
| `/api/pipeline-runs` | pipeline_runs.py | 6 |
| `/api/events` | events.py | 1 REST + 1 WS |
| `/api/settings` | settings.py | 3 |
| `/api/questions` | questions.py | 4 |
| `/api/memories` | memories.py | — |
| `/api/projects/{id}/memories` | memories.py | — |
| `/api/issues/{id}/relations` | issue_relations.py | 3 |
| `/api/library` | library.py | 4 |
| `/api/project-variables` | project_variables.py | 5 |
| `/api/credentials-editor` | credentials_editor.py | 6 |
| `/api/system` | system.py | 1 |
| `/api/import` | import_export.py | 2 |
| `/api/network` | network.py | 1 |

## Projects

### `POST /api/projects`
- **Status:** 201
- **Response:** `ProjectResponse`
- **Description:** Create new project

### `GET /api/projects`
- **Response:** `list[ProjectResponse]`
- **Description:** List all projects

### `GET /api/projects/{project_id}`
- **Response:** `ProjectResponse`

### `PUT /api/projects/{project_id}`
- **Response:** `ProjectResponse`
- **Body:** `ProjectUpdate`

### `POST /api/projects/{project_id}/archive`
- **Response:** `ProjectResponse`

### `POST /api/projects/{project_id}/unarchive`
- **Response:** `ProjectResponse`

### `DELETE /api/projects/{project_id}`
- **Status:** 204
- **Description:** Delete project

### `POST /api/projects/{project_id}/install-manager-json`
- **Status:** 200

### `POST /api/projects/{project_id}/install-claude-resources`
- **Status:** 200

### `GET /api/projects/{project_id}/health`
- **Description:** Health check for project's MCP server

### `POST /api/projects/{project_id}/rebuild-index`
- **Description:** Rebuild project index

### `POST /api/projects/{project_id}/install-mcp`
- **Status:** 201
- **Response:** `TerminalResponse`
- **Description:** Install MCP in a terminal session

### `POST /api/projects/{project_id}/install-playwright-mcp`
- **Status:** 201
- **Response:** `TerminalResponse`

## Issues

**Prefix:** `/api/projects/{project_id}/issues`

### `POST ""`
- **Status:** 201
- **Response:** `IssueResponse`
- **Body:** `IssueCreate` (description, priority, category, tags, source_issue_id)

### `GET ""`
- **Response:** `list[IssueResponse]`
- **Query:** status, search, tag, limit, offset

### `GET /tags`
- **Response:** `list[str]`

### `GET /{issue_id}`
- **Response:** `IssueResponse`

### `PUT /{issue_id}`
- **Response:** `IssueResponse`
- **Body:** `IssueUpdate`

### `PATCH /{issue_id}/status`
- **Response:** `IssueResponse`
- **Body:** `IssueStatusUpdate`
- **Description:** Transition issue status

### `DELETE /{issue_id}`
- **Status:** 204

### `POST /{issue_id}/accept`
- **Response:** `IssueResponse`

### `POST /{issue_id}/cancel`
- **Response:** `IssueResponse`

### `POST /{issue_id}/complete`
- **Response:** `IssueResponse`

### `POST /{issue_id}/force-finish`
- **Response:** `IssueResponse`

### `GET /{issue_id}/feedback`
- **Response:** `list[IssueFeedbackResponse]`

### `POST /{issue_id}/feedback`
- **Status:** 201
- **Response:** `IssueFeedbackResponse`

## Tasks

**Prefix:** `/api/projects/{project_id}/issues/{issue_id}/tasks`

### `POST ""`
- **Status:** 201
- **Response:** `list[TaskResponse]`

### `GET ""`
- **Response:** `list[TaskResponse]`

### `PATCH /{task_id}`
- **Response:** `TaskResponse`

### `DELETE /{task_id}`
- **Status:** 204

### `PUT ""`
- **Response:** `list[TaskResponse]`
- **Description:** Batch update/reorder tasks

## Terminals

**Prefix:** `/api/terminals`

### `POST ""`
- **Status:** 201
- **Response:** `TerminalResponse`
- **Body:** `TerminalCreate`

### `POST /ask`
- **Status:** 201
- **Response:** `TerminalResponse`
- **Body:** `AskTerminalCreate`

### `POST /manage-agent`
- **Status:** 201
- **Response:** `TerminalResponse`

### `POST /log`
- **Status:** 201
- **Response:** `TerminalResponse`

### `GET /ask`
- **Response:** `list[TerminalListResponse]`

### `GET /manage-agent`
- **Response:** `list[TerminalListResponse]`

### `GET /config`
- **Description:** Get terminal configuration

### `GET ""`
- **Response:** `list[TerminalListResponse]`

### `GET /count`

### `GET /{terminal_id}/recording`

### `DELETE /{terminal_id}`
- **Status:** 204

### `WS /{terminal_id}/ws`
- **Description:** WebSocket for terminal I/O streaming

## Agents

**Prefix:** `/api/agents`

### `GET ""`
- **Response:** `list[AgentResponse]`

### `POST ""`
- **Status:** 201
- **Response:** `AgentResponse`

### `POST /seed`
- **Status:** 201
- **Response:** `list[AgentResponse]`

### `GET /export`
- **Description:** Export all agents

### `POST /export/batch`

### `GET /export/{agent_id}`

### `POST /import/preview`
- **Response:** `ImportPreviewResponse`

### `POST /import/confirm`
- **Response:** `ImportConfirmResponse`

### `GET /{agent_id}`
- **Response:** `AgentResponse`

### `PUT /{agent_id}`
- **Response:** `AgentResponse`

### `DELETE /{agent_id}`
- **Status:** 204

## Pipelines

**Prefix:** `/api/pipelines`

### `GET ""`
- **Response:** `list[PipelineResponse]`

### `POST ""`
- **Status:** 201
- **Response:** `PipelineResponse`

### `POST /seed`
- **Status:** 201
- **Response:** `PipelineResponse`

### `GET /export`

### `POST /export/batch`

### `GET /export/{pipeline_id}`

### `POST /import/preview`
- **Response:** `PipelineImportPreviewResponse`

### `POST /import/confirm`
- **Response:** `ImportConfirmResponse`

### `GET /{pipeline_id}`
- **Response:** `PipelineResponse`

### `PUT /{pipeline_id}`
- **Response:** `PipelineResponse`

### `DELETE /{pipeline_id}`
- **Status:** 204

### `POST /{pipeline_id}/run`
- **Status:** 202
- **Response:** `PipelineRunResponse`

### `DELETE /{pipeline_id}/steps/{step_id}`
- **Status:** 204

### `PUT /{pipeline_id}/steps/reorder`

### `GET /{pipeline_id}/steps/{step_id}/runs`

### `POST /{pipeline_id}/steps/{step_id}/runs`

### `DELETE /{pipeline_id}/steps/{step_id}/event-rules/{rule_id}`
- **Status:** 204

## Pipeline Runs

**Prefix:** `/api/pipeline-runs`

### `POST ""`
- **Status:** 201
- **Response:** `PipelineRunResponse`

### `GET /active-by-project`
- **Response:** `list[PipelineRunResponse]`

### `GET ""`
- **Response:** `list[PipelineRunResponse]`

### `GET /{run_id}`
- **Response:** `PipelineRunResponse`

### `DELETE /{run_id}`
- **Status:** 204

### `GET /{run_id}/messages`
- **Response:** `list[PipelineMessageResponse]`

### `POST /{run_id}/messages`
- **Description:** Add message to pipeline run

## Events

### `GET /api/events` (WebSocket upgrade at `/api/events/ws`)
- **Description:** Real-time event streaming via WebSocket

### `POST /api/events`
- **Description:** Dispatch custom event

## Other Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/{id}/activity` | Activity log |
| GET/POST/PUT/DELETE | `/api/projects/{id}/plugins` | Plugin management |
| GET/POST/PUT/DELETE | `/api/projects/{id}/links` | Project links |
| GET/PUT/DELETE | `/api/projects/{id}/settings/{key}` | Project settings |
| GET/POST/DELETE | `/api/projects/{id}/skills` | Project skills |
| GET/PUT/DELETE | `/api/projects/{id}/templates` | Prompt templates |
| POST | `/api/projects/{id}/files` | File upload |
| GET/DELETE | `/api/projects/{id}/files` | File listing/deletion |
| GET | `/api/projects/{id}/files/{id}/download` | File download |
| GET | `/api/projects/{id}/files/{id}/preview` | File preview |
| GET | `/api/projects/{id}/files/{id}/content` | File content |
| POST | `/api/projects/{id}/files/{id}/reextract` | Re-extract file |
| GET | `/api/projects/{id}/files/search` | File search |
| GET/POST | `/api/projects/{id}/credentials` | Credential management |
| DELETE | `/api/projects/{id}/credentials/{role}` | Delete credential |
| GET/PUT | `/api/credentials-editor` | Credential editor |
| GET/POST/PUT/DELETE | `/api/credentials-editor/presets` | Credential presets |
| POST | `/api/credentials-editor/presets/{id}/apply` | Apply preset |
| GET/POST | `/api/memories` | Flat memories |
| GET/POST | `/api/projects/{id}/memories` | Project-scoped memories |
| GET/POST/DELETE | `/api/issues/{id}/relations` | Issue relations |
| GET/POST/PUT | `/api/library/skills` | Skill library |
| GET/POST/PUT/DELETE | `/api/project-variables` | Project variables |
| GET/PUT/DELETE | `/api/settings` | App settings |
| GET/POST/PUT/DELETE | `/api/terminal-commands` | Terminal command templates |
| GET | `/api/terminal-commands/variables` | Available variables |
| GET | `/api/terminal-commands/templates` | Command templates |
| PUT | `/api/terminal-commands/reorder` | Reorder commands |
| GET/POST | `/api/questions` | Questions |
| GET | `/api/questions/pending` | Pending questions |
| GET | `/api/questions/count` | Question count |
| POST | `/api/questions/{id}/answer` | Answer question |
| GET | `/api/system/info` | System info (WSL, distros) |
| POST | `/api/import` | Import data |
| POST | `/api/import/resolve` | Resolve import conflicts |
| GET | `/api/network-info` | Network information |

## Authentication

- **Type:** None built-in (manage externally)
- **CORS:** Configured via `settings.cors_origins` (default: `http://localhost:5173`)
- **Secret Key:** Fernet key auto-generated at `data/secret.key`

## Common Patterns

- **Response Format:** Pydantic v2 schemas with `from_record()` classmethods
- **Error Handling:** `AppError` exceptions with `status_code` + `message`, caught by global handler
- **Database:** AsyncSession from `get_db()` dependency injection
- **Service Layer:** Service classes instantiated per-request, commit at router level
