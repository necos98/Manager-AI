# Ask & Brainstorming — Design Spec

**Date:** 2026-03-29
**Status:** Approved

## Overview

A dedicated section in Manager AI that lets the user open an interactive Claude Code session for free-form conversation, ideation, and architectural decisions about the active project. Claude starts in listening mode, uses MCP tools to access project context, and can optionally create issues on request.

## Goals

- Open a Claude Code terminal session pre-loaded with a brainstorming prompt in one click
- Give Claude access to the project via MCP tools (context, semantic search, issue creation)
- Allow the user to fully customize the startup command from the Settings page
- Embed the terminal inline in the Ask & Brainstorming page; terminal also visible in /terminals

## Architecture

Four pieces are created. No existing code is modified.

### 1. Command file: `claude_resources/commands/ask-and-brainstorm.md`

A Claude Code slash command invoked as `/ask-and-brainstorm <project_id>`. Written in English. Instructs Claude to:

1. Call `get_project_context($ARGUMENTS)` to load project metadata
2. Optionally call `search_project_context` to retrieve relevant docs/issues if useful
3. Enter listening mode: present itself briefly, then wait for user input
4. For each user message: reason collaboratively, surface trade-offs, suggest directions
5. Issue creation (optional): only when the user explicitly asks. Claude verifies it has a clear name, description, and context before calling `create_issue`. Confirms to the user after creation.
6. Never act autonomously — listening mode only.

### 2. Backend: new setting key

**File:** `backend/app/mcp/default_settings.json`

New key added:
```json
"ask_brainstorm_command": "claude --mcp-config $mcp_config_path /ask-and-brainstorm $project_id"
```

- `$project_id` and `$mcp_config_path` are resolved at runtime by the endpoint
- Editable from the global Settings page like any other setting
- Default uses the same MCP config path convention as other terminal commands

### 3. Backend: `POST /api/terminals/ask`

**File:** `backend/app/routers/terminals.py` (new route added to existing router)

**Schema** (new, in `backend/app/schemas/terminal.py`):
```python
class AskTerminalCreate(BaseModel):
    project_id: str
```

**Behavior:**
1. Look up project path and shell from DB (same as existing `create_terminal`)
2. Spawn PTY via `terminal_service.create(issue_id="", project_id=..., project_path=..., shell=...)`
3. Inject standard env vars: `MANAGER_AI_PROJECT_ID`, `MANAGER_AI_BASE_URL`, `MANAGER_AI_TERMINAL_ID`
4. Inject project custom variables (same as existing endpoint)
5. Read `ask_brainstorm_command` from `SettingsService`, resolve `$project_id` and `$mcp_config_path`
6. Write resolved command to PTY
7. Return `TerminalResponse`

The terminal is registered in `terminal_service` with an empty `issue_id` so it appears in `GET /api/terminals` and in the /terminals page.

### 4. Frontend

**New route:** `frontend/src/routes/projects/$projectId/ask.tsx`

**States:**
- **Idle** (no active terminal): centered layout with title "Ask & Brainstorming", short description, and a "Start conversation" button
- **Active** (terminal running): renders `<TerminalPanel terminalId={id} />` filling the available space. A "New conversation" button allows starting a fresh session.

**API hook:** `useCreateAskTerminal` in `frontend/src/features/terminals/hooks.ts` — calls `POST /api/terminals/ask`.

**Sidebar:** New nav item "Ask & Brainstorming" in the Project section of `app-sidebar.tsx`, positioned between "Activity" and "Library". Uses the `MessageSquare` icon from lucide-react.

**Route registration:** Added to `frontend/src/routeTree.gen.ts` and the router config.

## Data Flow

```
User clicks "Start conversation"
  → POST /api/terminals/ask { project_id }
  → Backend resolves ask_brainstorm_command from settings
  → PTY spawned, command injected: claude --mcp-config <path> /ask-and-brainstorm <project_id>
  → Claude reads ask-and-brainstorm.md, calls get_project_context via MCP
  → Claude enters listening mode
  → TerminalPanel connects via WebSocket, renders inline
  → Terminal also visible in /terminals list
```

## What is NOT in scope

- Persisting conversation history (terminal recording already handles this)
- Multiple simultaneous brainstorming sessions per project (user can open a new one manually)
- Custom skills for the brainstorming workflow (the command file is self-contained)
- Extractors for .docx/.xlsx (separate gap, not related to this feature)
