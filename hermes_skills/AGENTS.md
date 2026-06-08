# AGENTS.md — Hermes Agent Guidance for Manager AI Projects

This file is loaded by Hermes when operating in this project directory.
It provides project-specific context, conventions, and instructions.

## MCP Connection

Manager AI runs locally at `http://localhost:8000`.
The MCP server is at `http://localhost:8000/mcp`.

To connect Hermes:

```bash
hermes mcp add manager-ai --url http://localhost:8000/mcp
```

Verify: `hermes mcp list` should show `manager-ai` with tools.

## Project ID

The project ID is stored at the repo root in `manager.json`.
Load it before calling any MCP tool that requires `project_id`:

```bash
cat manager.json
# → {"project_id": "abc-123-def"}
```

## Memory Protocol

- **READ**: Search the filesystem: `grep -ri "<keywords>" .manager_ai/memories/`
  or use MCP: `memory_search(project_id=..., query="...")`
- **WRITE**: Use MCP tools `memory_create` / `memory_update` — do NOT edit
  `.md` files directly

## Key Skills

| Skill | When to use |
|-------|-------------|
| `manager-ai-orchestrator` | Orchestrating pipeline runs, creating issues, managing projects |
| `manager-ai-issue-worker` | Executing a single pipeline step (reading issue, implementing, signalling completion) |

Load a skill: `/skill manager-ai-orchestrator`

## Conventions

- Always read project context before acting
- Write memories for every completed issue
- Use `get_next_issue` to find workable issues
- Autonomous decisions preferred — use `ask_user_question` only when blocked
