---
project_name: 'manager_ai'
user_name: 'Jacob'
date: '2026-06-07'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'style_rules', 'workflow_rules', 'architecture_decisions', 'critical_rules']
status: 'complete'
rule_count: 42
optimized_for_llm: true
existing_patterns_found: 28
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Backend (Python/FastAPI)
- **Runtime:** Python >=3.12, <3.15 (Windows primary target; 3.14 may break pythonnet)
- **Framework:** FastAPI 0.115.12 with Uvicorn 0.34.2
- **ORM:** SQLAlchemy 2.0+ (async) + aiosqlite 0.21.0
- **Migrations:** Alembic 1.15.2
- **Validation:** Pydantic v2.11+ (BaseModel, BaseSettings) — `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`, `@field_validator` not `@validator`, `from_attributes=True` not `orm_mode=True`
- **MCP:** FastMCP (mcp[cli] 1.9.2) — **PIN exact version**, API changes between releases
- **Auth/Crypto:** cryptography 47.0.0 (Fernet)
- **Testing:** pytest 8.3.5 + pytest-asyncio 0.25.3 — `asyncio_mode = "auto"`, do NOT add `@pytest.mark.asyncio`
- **HTTP Client:** httpx 0.28.1
- **Config:** python-dotenv 1.1.0
- **Serialization:** PyYAML 6.0.2
- **File Parsing:** pypdf 5.1.0, python-docx 1.1.2, openpyxl 3.1.5
- **Desktop:** pywebview 5.0+, pythonnet (Windows only; handle ImportError gracefully)
- **Speech:** openai-whisper (latest) — load model ON-DEMAND only, not at startup
- **Terminal:** pywinpty (Windows-only; Linux uses built-in pty module)

### Frontend (React/TypeScript)
- **UI Library:** React 19.2.4 + React DOM 19.2.4 — `forwardRef` deprecated, ref passes as prop directly
- **Language:** TypeScript 6.0.2 (strict mode with `noUncheckedIndexedAccess`)
- **Build Tool:** Vite 5.4.0
- **Routing:** @tanstack/react-router 1.168.7 (file-based in `/src/routes/`)
- **Server State:** @tanstack/react-query 5.95.2
- **CSS:** Tailwind CSS 4.2.1 — CSS-first config, NO `tailwind.config.js`, plugin via `@plugin` directive
- **UI Components:** Radix UI 1.4.3
- **Icons:** lucide-react 1.7.0
- **Toasts:** sonner 2.0.7
- **Terminal:** Xterm.js 5.3.0 + @xterm/addon-fit/search/web-links
- **Drag & Drop:** @dnd-kit 6.3.1/10.0.0
- **Graph/Diagrams:** reactflow 11.11.4, @dagrejs/dagre 3.0.0
- **Markdown:** react-markdown 10.1.0
- **Dates:** date-fns 4.1.0
- **QR:** react-qr-code 2.0.18
- **Styling Utils:** class-variance-authority 0.7.1, clsx 2.1.1, tailwind-merge 3.5.0
- **Linting:** ESLint 9.39.4 + react-hooks plugin + react-refresh plugin
- **Dev Tools:** @tanstack/router-devtools, @tanstack/router-plugin

### Stack Constraints (Critical - AI Agents Must Know)
- **SQLite + asyncio:** DO NOT use Uvicorn `--workers > 1` with aiosqlite — all writes serialize. Single-process only.
- **No Redis/Postgres:** Stack uses SQLite + WriteQueue. Do NOT propose Redis-based or Postgres-specific solutions.
- **No Docker Compose in production:** `start.py` manages everything. Do NOT assume containerization.
- **Windows-only deps:** `pywinpty`, `pythonnet` — Linux/Mac devs cannot test terminal service locally.
- **MCP version:** Pin `mcp==1.9.2`. Do NOT upgrade without full StreamableHTTP + session manager testing.
- **Python version range:** Keep `>=3.12, <3.15` — pythonnet RC may break on 3.14 stable.

## Critical Implementation Rules

### Language-Specific Rules

**TypeScript (frontend):**
- `noUncheckedIndexedAccess` strict — every `array[i]` / `obj[key]` returns `T | undefined`. Always use optional chaining (`?.`), never assume indexed access is safe.
- Path alias `@/*` maps to `./src/*`. Use absolute `@/shared/...` imports, never relative paths across features.
- Named function exports (`export function Foo`), NOT `export default` for components.
- React 19: `forwardRef` deprecated — pass `ref` as a regular prop. `ReactNode` includes `Promise<ReactNode>`.
- TanStack Router: file-based in `src/routes/`. Dynamic params use `$param` convention. Do NOT create routes manually with `createRoute`.
- Query key factory pattern: `{feature}Keys.all/detail/tasks` standard.

**Python (backend):**
- Pydantic v2: use `model_dump()` (not `dict()`), `model_validate()` (not `parse_obj()`), `@field_validator` (not `@validator`). Config via `from_attributes=True` in `model_config`, NOT `orm_mode=True`.
- Services receive `AsyncSession` in `__init__`. Database commit happens at router level, NEVER inside service methods.
- Errors use `AppError` base exception with `status_code` + `message`. Centralized handler in `main.py`.
- Type hints: `Mapped[...]` for SQLAlchemy columns, `| None` for optional, `list[X]` not `List[X]`.
- File-backed storage: issue/memory/file operations read/write `.manager_ai/` directory, not the database directly.
- MCP: FastMCP mounted via `mcp.streamable_http_app()`. Mounted app MUST use `_noop_lifespan` to prevent session manager conflicts.

### Framework-Specific Rules

**React (frontend):**
- Custom hooks in `src/shared/hooks/` (global) or `src/features/{name}/hooks.ts` (feature-scoped).
- Components: named function exports, PascalCase filenames (`.tsx`), feature components in `src/features/{name}/components/`, shared components in `src/shared/components/`, UI primitives in `src/shared/components/ui/` (Radix UI wrappers).
- TanStack Query: mutation error handler pattern — `const onMutationError = (e: unknown) => { toast.error(e instanceof Error ? e.message : "Operation failed"); };` — must NOT use inline alert/console.error.
- EventProvider in `src/context/` for WebSocket realtime events.
- Query key factory pattern: `{feature}Keys.all/detail/tasks` with `invalidateQueries` on mutation success.

**FastAPI (backend):**
- Router pattern: `APIRouter(prefix="/api/...", tags=["..."])`, session via `Depends(get_db)`.
- Service instantiation inside endpoint: `service = IssueService(db)`. Then call methods, then `await db.commit()`.
- Response via `from_record()` classmethod on Pydantic schema — never return ORM objects directly.
- Error handling: `AppError` exceptions with `status_code` + `message`, caught by global handler in `main.py`.
- Startup lifecycle: decomposed into `_startup_*` helper functions called inside `lifespan()`.

**TanStack Router:**
- File-based routing in `src/routes/`. `__root.tsx` for root layout. Dynamic path segments use `$` prefix.
- Do NOT use `createRoute()` manually — route tree is auto-generated via `@tanstack/router-plugin`.

### Testing Rules

- **pytest-asyncio** with `asyncio_mode = "auto"` — every `async def test_*` is auto-detected as async. Do NOT add `@pytest.mark.asyncio` (causes warnings/errors).
- **SQLite in-memory:** Async in-memory SQLite for tests. Vector columns (LanceDB) must be stripped from test schema — SQLite cannot handle them.
- **Test files:** Named `test_*.py` alongside source or in `backend/tests/`. Use async fixtures for DB session.
- **CLI:** `cd backend && python -m pytest` or `python -m pytest tests/test_file.py::test_func -v` for single tests.
- **Mutation error handling:** Use `onMutationError` helper (toast.error pattern). Never use inline `console.error` or `alert()` in React code.

## Coding Conventions

- **Frontend file naming:** PascalCase for `.tsx` components, kebab-case for utility/config files.
- **Backend file naming:** snake_case for `.py` files. Classes PascalCase, functions/variables snake_case.
- **Enum pattern:** `class IssueStatus(str, enum.Enum)` with string values matching UI display text.
- **Router filenames:** Plural form (`issues.py`, `agents.py`, `terminals.py`).
- **Test files:** `test_` prefix for all test files and test functions.
- **Imports (frontend):** Use `@/` path alias. Group: React/external → TanStack → local.
- **Imports (backend):** Standard library → third-party → app package. Use `from __future__ import annotations` at top.
- **ESLint:** Flat config (`eslint.config.js`). Rule: `no-unused-vars` with `varsIgnorePattern: '^[A-Z_]'` for interface names.
- **CSS:** Tailwind CSS 4 with `@tailwindcss/vite` plugin. NO `tailwind.config.js`. Class merging via `cn()` utility (clsx + tailwind-merge).

## Architecture Decisions

### Key Architecture Decisions

- **SQLite over Postgres:** Deliberate choice for zero-config deployment. Acceptable up to ~1GB data. No Postgres-specific SQL (JSONB, array columns, `ON CONFLICT` variations).
- **File-backed storage:** Issues, memories, and file metadata stored in `.manager_ai/` directory per project, not in database directly. DB holds only project registry and relational links.
- **No Redis/ORM cache:** WriteQueue + BackgroundWriter pattern for async I/O instead. Every query is a direct SQLite round-trip. Agents must avoid N+1 queries.
- **Single-process Uvicorn:** SQLite + aiosqlite serializes writes — `--workers > 1` causes write collisions. Use `--workers 1` always.
- **MCP StreamableHTTP:** FastMCP mounted at `/mcp` via `streamable_http_app()`. The mounted app uses `_noop_lifespan` to prevent session manager conflicts. This is fragile — test thoroughly on MCP version upgrades.
- **Windows-first:** pywinpty for terminal PTY, ProactorEventLoopPolicy for subprocesses. Linux uses built-in PTY module. All terminal service changes must be tested on Windows.
- **Feature-based frontend:** `src/features/{name}/` with colocated api/hooks/components. Shared code in `src/shared/`. No cross-feature relative imports — use `@/` alias.
- **Layered backend:** Router (HTTP) → Service (business logic) → Schema/Model (data). Services take `AsyncSession` in constructor. Commit in router only.

## Critical Don't-Miss Rules

### Anti-Patterns to Avoid
- ❌ Do NOT propose Redis/Postgres — stack uses SQLite + WriteQueue for async I/O.
- ❌ Do NOT use `--workers > 1` with aiosqlite — writes collide. Always `--workers 1`.
- ❌ Do NOT import `whisper` at module level — load model on-demand only (~3GB model).
- ❌ Do NOT use `export default` for React components — use named function exports.
- ❌ Do NOT create `tailwind.config.js` — Tailwind v4 is CSS-first, configure via `@plugin` directives.
- ❌ Do NOT use Pydantic v1 APIs — `dict()`, `parse_obj()`, `@validator`, `orm_mode` are removed in v2.
- ❌ Do NOT use `createRoute()` manually — TanStack Router uses file-based routing via `@tanstack/router-plugin`.
- ❌ Do NOT add `@pytest.mark.asyncio` — `asyncio_mode = "auto"` detects async tests automatically.
- ❌ Do NOT use `forwardRef` — React 19 passes `ref` as a regular prop.

### Edge Cases
- Windows `ProactorEventLoopPolicy` required for MCP stdio subprocesses. Startup patch via `.pth` file, fallback in `main.py`.
- `aiosqlite` requires `check_same_thread=False` + NullPool to avoid deadlocks.
- Client disconnects during MCP StreamableHTTP are normal — suppressed via `_SuppressClientDisconnectFilter`.
- Windows IOCP accept noise (WinError 64, 121, 995, 1236) demoted to DEBUG level.
- Orphaned pipeline runs marked FAILED on startup — always handle `PipelineRunStatus.RUNNING` at startup.
- `pythonnet>=3.1.0rc0` is experimental on Python 3.14+ Windows — wrap `import clr` in try/except.

### Security Rules
- Fernet secret key auto-generated to `data/secret.key`. Loaded into `MANAGER_AI_SECRET_KEY` env var at startup.
- CORS configured via `settings.cors_origins` (default: `http://localhost:5173`).
- No built-in authentication — manage externally if needed.
- Sanitize all inputs passed to `pythonnet`/`pywebview` desktop APIs — they introduce local attack surface.

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

*Last Updated: 2026-06-07*
