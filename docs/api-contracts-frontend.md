# API Contracts — Frontend

**Part:** frontend
**Project Type:** React/TypeScript (Web)
**Generated:** 2026-06-07
**API Client:** `src/shared/api/client.ts` — custom fetch wrapper (not Axios)

## Architecture

- **Base URL:** Proxied via Vite (`/api` → `http://localhost:8000`)
- **Client:** Thin fetch wrapper in `src/shared/api/client.ts`
- **State Mgmt:** TanStack Query for server state (caching, invalidation, mutations)
- **Real-time:** WebSocket via EventProvider context

## API Modules (per feature)

| Feature | API File | Domain |
|---------|----------|--------|
| issues | `src/features/issues/` | Issue CRUD, status transitions |
| projects | `src/features/projects/` | Project CRUD, archive, MCP install |
| terminals | `src/features/terminals/` | Terminal CRUD, WebSocket I/O |
| agents | `src/features/agents/` | Agent CRUD, import/export |
| pipelines | `src/features/pipelines/` | Pipeline CRUD, runs, event rules |
| pipeline-runs | `src/features/pipeline-runs/` | Run monitoring, messages |
| files | `src/features/files/` | File upload, list, preview, search |
| settings | `src/features/settings/` | App settings CRUD |
| credentials | `src/features/credentials-editor/` | Credential presets |
| memories | `src/features/memories/` | Memory CRUD |
| library | `src/features/library/` | Skill library |
| questions | `src/features/questions/` | Agent questions |
| system | `src/features/system/` | System info |
| import | `src/features/import/` | Data import |

## Query Key Factory Pattern

All features follow `featureKeys.all`, `featureKeys.detail(id)`, `featureKeys.tasks` pattern for TanStack Query key management.

## Frontend-Specific Patterns

- **Mutations:** Use `onMutationError` helper (toast.error pattern), never inline console.error/alert
- **Real-time:** EventProvider in context listens to WebSocket for live updates
- **File Upload:** Custom multipart/form-data handling
- **Terminal:** WebSocket-based PTY I/O streaming via Xterm.js
