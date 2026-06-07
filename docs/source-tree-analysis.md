# Source Tree Analysis

**Generated:** 2026-06-07
**Repository Type:** Monorepo (2 parts: backend, frontend)

## Root Structure

```
manager_ai/
├── backend/              # Python/FastAPI API server (Part: backend)
│   ├── app/              # Application package
│   │   ├── hooks/        # Event-driven hook system → Call claude CLI
│   │   ├── mcp/          # FastMCP server mounted at /mcp
│   │   ├── middleware/   # FastAPI middleware
│   │   ├── migration/    # Data migration utilities
│   │   ├── models/       # SQLAlchemy ORM models (24 tables)
│   │   ├── routers/      # REST API route handlers (25 routers)
│   │   ├── schemas/      # Pydantic v2 request/response schemas
│   │   ├── services/     # Business logic layer
│   │   ├── storage/      # File-backed storage + cache
│   │   ├── main.py       # FastAPI app entry point
│   │   └── database.py   # AsyncSession + engine setup
│   ├── tests/            # Pytest test suite
│   ├── scripts/          # Utility scripts
│   ├── alembic/          # DB migration versions
│   ├── requirements.txt  # Python dependencies
│   └── pyproject.toml    # Pytest config
│
├── frontend/             # React/TypeScript SPA (Part: frontend)
│   ├── src/
│   │   ├── features/     # Feature modules (16 features)
│   │   │   ├── issues/       # Issue CRUD + status flow
│   │   │   ├── projects/     # Project dashboard
│   │   │   ├── terminals/    # Terminal emulator (Xterm.js)
│   │   │   ├── agents/       # Agent config
│   │   │   ├── pipelines/    # Pipeline builder
│   │   │   ├── pipeline-runs/# Run monitoring
│   │   │   ├── files/        # File gallery + preview
│   │   │   ├── settings/     # App settings
│   │   │   ├── credentials-editor/ # Credential presets
│   │   │   ├── memories/     # Memory graph
│   │   │   ├── library/      # Skill library
│   │   │   ├── questions/    # Agent Q&A
│   │   │   ├── activity/     # Activity log
│   │   │   ├── system/       # System info
│   │   │   ├── conflicts/    # Conflict resolution
│   │   │   └── import/       # Data import
│   │   ├── routes/       # File-based TanStack Router routes
│   │   ├── shared/
│   │   │   ├── api/          # HTTP client (fetch wrapper)
│   │   │   ├── components/   # Shared + UI primitives
│   │   │   │   └── ui/       # Radix UI wrappers (18 components)
│   │   │   ├── context/      # EventProvider (WebSocket)
│   │   │   ├── hooks/        # Custom hooks
│   │   │   ├── lib/          # Utility libraries
│   │   │   ├── types/        # TypeScript type definitions
│   │   │   └── utils/        # Helper functions
│   │   ├── main.jsx      # React entry point
│   │   └── App.jsx       # Router + providers
│   ├── package.json      # Node dependencies
│   ├── vite.config.ts    # Vite config + proxy
│   ├── tsconfig.json     # TypeScript strict config
│   └── eslint.config.js  # ESLint flat config
│
├── docs/                 # Project documentation output
│   ├── plugins/          # Plugin docs
│   ├── superpowers/      # Historical specs & plans (~60 files)
│   ├── api-contracts-backend.md    # (generated)
│   ├── api-contracts-frontend.md   # (generated)
│   ├── data-models-backend.md      # (generated)
│   ├── data-models-frontend.md     # (generated)
│   ├── component-inventory-frontend.md  # (generated)
│   ├── agent-pipeline-architecture.md   # (existing)
│   ├── wsl-setup.md                    # (existing)
│   └── project-scan-report.json        # (generated)
│
├── data/                 # SQLite DB + LanceDB vectors
├── .claude/              # Claude Code config + skills
├── _bmad/                # BMAD workflow config
├── _bmad-output/         # BMAD generated artifacts
│
├── start.py              # Full-stack orchestrator (venv/deps/migrations)
├── start.bat             # Windows batch launcher
├── start.sh              # Unix shell launcher
├── CLAUDE.md             # AI agent instructions
├── manager.json          # Project ID config
└── .env                  # Environment variables
```

## Critical Directories

### backend/app/hooks/
Event-driven hooks that fire on issue state transitions. `HookRegistry` manages registration; `ClaudeCodeExecutor` spawns `claude` CLI. Hooks execute async via `asyncio.create_task`.

### backend/app/mcp/
FastMCP server exposing tools to Claude Code (get/update issue, specs, plans, project context). Mounted at `/mcp` via `streamable_http_app()`.

### backend/app/services/
Business logic: ProjectService, IssueService, TaskService, TerminalService, AgentService, PipelineService, MemoryService, etc. Instantiated per-request with AsyncSession.

### frontend/src/features/
16 feature modules, each colocating api/hooks/components. No cross-feature relative imports — use `@/` alias.

### frontend/src/shared/components/ui/
18 Radix UI wrappers following consistent pattern (Radix primitives + Tailwind + cn() utility).

## Entry Points

| Purpose | File |
|---------|------|
| Backend server | `backend/app/main.py` — FastAPI `create_app()` |
| Frontend SPA | `frontend/src/main.jsx` → `App.jsx` |
| App launcher | `start.py` — Starts both backend + frontend |
| MCP server | `backend/app/mcp/server.py` — FastMCP tools |

## Integration Points (backend ↔ frontend)

- **REST API:** Frontend → `/api/*` (proxied via Vite) → Backend routers
- **WebSocket:** Frontend EventProvider ← `/api/events/ws` → Backend event bus
- **Terminal I/O:** Frontend Xterm.js ← WS `/api/terminals/{id}/ws` → Backend PTY
- **MCP:** Claude Code CLI ← `/mcp` → Backend FastMCP tools
