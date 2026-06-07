## Problem

`backend/app/main.py:509-515` configures CORS with `allow_origins=["*"]` and `allow_credentials=True`. This combination is **invalid per CORS spec** — browsers reject credentialed requests (`Authorization` headers, cookies) when the server responds with `Access-Control-Allow-Origin: *`. The app cannot authenticate requests from the frontend when credentials are required.

## Scope

Replace the hardcoded wildcard origin with a configurable list of specific origins, defaulting to the Vite dev server ports.

### In Scope

1. **Settings field**: Add `cors_origins: str` to the `Settings` class in `backend/app/config.py` with default `"http://localhost:5173,http://127.0.0.1:5173"`
2. **Middleware registration**: Replace `allow_origins=["*"]` in `backend/app/main.py:511` with `settings.cors_origins.split(",")`
3. **Env example**: Add a `# --- CORS ---` section to `.env.example` with the `CORS_ORIGINS` variable commented out
4. **All origins accept `*`**: If user sets `CORS_ORIGINS=*`, it should restore the wildcard behavior (this is valid when credentials aren't used, or for non-credentialed CORS)

### Out of Scope

- No changes to CORS methods, headers, or other middleware settings
- No refactoring of the middleware setup (keep it as `add_middleware` call)
- No changes to `allow_credentials` behavior
- No frontend changes
- No adding a new dependency or library

## Constraints

- Must follow existing `pydantic_settings.BaseSettings` pattern (env file, no new loading mechanism)
- `settings` is already imported in `main.py:13` — no import changes needed
- `.env.example` comments use `# VAR=value` format — keep consistent
- The change must be minimal: ~2 lines of code changed, ~3 lines in `.env.example`
- Existing default (wildcard + credentials) is broken; new defaults must work out of the box for local development

## Acceptance Criteria

1. `Settings.cors_origins` defaults to `"http://localhost:5173,http://127.0.0.1:5173"` when no env var is set
2. `allow_origins` in middleware resolves to `["http://localhost:5173", "http://127.0.0.1:5173"]` by default
3. Setting `CORS_ORIGINS=http://example.com` in `.env` results in `allow_origins=["http://example.com"]`
4. Setting `CORS_ORIGINS=*` restores wildcard behavior (`allow_origins=["*"]`)
5. `.env.example` documents the new `CORS_ORIGINS` variable under a `# --- CORS ---` section header
6. Backend starts without errors with both default and custom `CORS_ORIGINS` values
7. Credentialed requests (cookies, Authorization headers) from allowed origins succeed

## Non-Goals

- Not fixing or changing `allow_credentials=True` — it stays as-is (only the origin list is wrong)
- Not adding a separate `allow_origins_regex` or per-environment config
- Not adding validation for origin format (invalid origins just won't match, which is harmless)
- Not modifying any frontend or test code
