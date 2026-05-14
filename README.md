# Manager AI

AI-powered project management with Claude Code integration. Issue tracking, terminal emulation, real-time events, and an MCP server that exposes tools to Claude Code — all in a local desktop app.

## Architecture

```
manager-ai/
├── backend/          # FastAPI + SQLAlchemy async (Python)
│   ├── app/
│   │   ├── mcp/      # MCP server, plugin system, catalog
│   │   ├── routers/  # REST endpoints
│   │   ├── services/ # Business logic
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic v2 validation
│   │   ├── hooks/    # Event-driven hook system
│   │   └── storage/  # File/memory stores
│   └── plugins/      # Built-in MCP plugin catalog
│       ├── filesystem/
│       ├── memory/
│       └── mysql/
├── frontend/         # React + Vite + Tailwind
│   └── src/
│       ├── features/ # Domain modules (issues, terminals, memories...)
│       ├── routes/   # TanStack Router pages
│       └── shared/   # UI components, contexts
└── start.py          # Launcher: venv bootstrap, deps, desktop window
```

**Stack:** FastAPI (Python) | React + Vite + Tailwind (TypeScript) | SQLite + aiosqlite | pywebview (desktop)

## Features

### Issue Lifecycle & Kanban
Issues flow through a defined state machine: **NEW → REASONING → PLANNED → ACCEPTED/DECLINED → FINISHED**. Each issue holds a specification, implementation plan, task breakdown, and recap. A drag-and-drop Kanban board visualizes the pipeline.

### Claude Code Integration (MCP Server)
A FastMCP server exposes tools to Claude Code: `get_issue_details`, `get_issue_status`, `get_project_context`, memory search, and more. Claude can inspect project state, read specs, and act on issues directly from its CLI.

### MCP Plugin System
Pluggable MCP servers per project. Built-in catalog includes read-only **filesystem**, **memory**, and **MySQL** plugins. Supports stdio and HTTP transports with per-plugin configuration. Plugins are started/stopped with project lifecycle.

### Integrated Terminal
Multi-tab PTY terminal (pywinpty on Windows) with WebSocket streaming. Supports variable resolution (`$issue_id`, `$project_id`), predefined command templates, environment injection, and **WSL** distro selection (`wsl.exe -d <distro>`).

### Voice & Transcription
Built-in speech-to-text: record audio from the browser, transcribe via backend, and insert text into terminals or issue fields.

### Memory System
Project-scoped persistent memory stored as markdown files under `.manager_ai/memories/`. Hierarchical, graph-linked, full-text searchable. Memories survive across sessions and are written/queried via MCP tools.

### Project Links
Cross-reference projects — link related repositories together and navigate between them.

### Real-Time Events
WebSocket-based event stream (`EventProvider` context). Activity timeline shows issue state changes, hook executions, memory updates.

### Health Checks
Built-in health dashboard detects resource consistency issues (e.g., `project_id` mismatches between `manager.json` and the database).

### Desktop App
Wrapped in a native desktop window via pywebview (1400×900). Single `python start.py` launches everything.

## Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js + npm**
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview)** (for AI features)

### 1. Launch

```bash
python start.py
```

This bootstraps a venv, installs backend/frontend dependencies, runs database migrations, builds the frontend, and opens the desktop window. Backend runs on `http://localhost:8000`, frontend on `http://localhost:4173`.

### 2. Create a Project

From the main interface, create a new project pointing to a local directory.

### 3. Set Up Claude Resources

In the project **Summary** tab, run these in order:

1. **Install manager.json** — writes project config into the target repo
2. **Install Claude Resources** — copies CLAUDE.md and skills into the project
3. **MCP Setup** — generates the MCP connection command

### 4. Connect Claude Code

Copy the MCP command shown in the setup dialog and run it in your project's terminal:

```bash
claude mcp add --transport http ManagerAi http://localhost:8000/mcp/
```

Claude can now call Manager AI tools to read/write issues, search memories, and inspect project state.

### 5. Configure the Terminal (Optional)

In **Settings → Terminal**, add a command like:

```
claude "/run-issue $issue_id" --dangerously-skip-permissions
```

Select an issue, click this command, and Claude starts working on it in the integrated terminal.

## Development

```bash
# Backend only (with hot reload)
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend only (with HMR)
cd frontend
npm run dev

# Run tests
cd backend
python -m pytest
```

### Database Migrations

```bash
cd backend
python -m alembic upgrade head              # Apply
python -m alembic revision --autogenerate -m "description"  # Create new
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | `8000` | Backend listen port |
| `FRONTEND_PORT` | `4173` | Frontend dev server port |
| `MANAGER_AI_DEV` | _(empty)_ | Set to `1` for debug mode (webview devtools) |

Copy `.env.example` to `.env` to customize.

## Plugins

Built-in MCP plugin catalog lives in `backend/plugins/`. Each plugin is a directory with a `plugin.yaml`:

```yaml
name: MySQL (read-only)
description: Query MySQL databases with read-only access
transport: stdio
command: npx
args: ["-y", "mysql-mcp-server"]
access_level: read_only
options:
  - key: MYSQL_HOST
    label: Host
    required: true
```

Plugins are configurable per project from the **Plugins** panel.

## License

MIT — see `LICENSE`.
