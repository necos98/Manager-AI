# Implementation Plan: Claude Code credentials.json Editor

## 1. Backend: Data Model & Migration

### New file: `backend/app/models/credential_preset.py`
- SQLAlchemy model `CredentialPreset`
- Columns: `id` (UUID PK), `name` (String not null), `variables` (Text, JSON), `encrypted_fields` (Text, Fernet-encrypted JSON), `created_at`, `updated_at`
- Follow existing model patterns (use `uuid4().hex` for id, `datetime.utcnow` for timestamps)

### New migration
- Run alembic autogenerate to create `credential_presets` table

## 2. Backend: Schema

### New file: `backend/app/schemas/credential_preset.py`
- `CredentialPresetCreate`: `name` (str), `variables` (dict[str, str])
- `CredentialPresetUpdate`: `name` (str | None), `variables` (dict[str, str] | None)
- `CredentialPresetOut`: `id`, `name`, `variables` (with secrets masked), `has_secrets` (bool), `created_at`, `updated_at`
- `CredentialPresetDetail`: like Out but with all values revealed (for apply)
- `CredentialsEnvOut`: dict[str, str] — current env vars from credentials.json
- `CredentialsEnvUpdate`: dict[str, str] — env vars to write

## 3. Backend: Service

### New file: `backend/app/services/credential_editor_service.py`
- `CredentialEditorService` class
  - `__init__(db: AsyncSession, secret_key: bytes | None)`
  - `get_credentials_path() -> Path` — resolves `%USERPROFILE%\.claude\credentials.json`
  - `read_env() -> dict[str, str]` — reads file, returns `env` object (or `{}` if missing)
  - `write_env(variables: dict[str, str])` — atomic write (temp + rename), backup as `.bak` first
  - **Preset CRUD**: `list_presets()`, `create_preset(name, vars)`, `update_preset(id, name, vars)`, `delete_preset(id)`, `get_preset(id)` — encrypt values with sensitive keys before storing
  - `apply_preset(preset_id)` — get preset, decrypt, write to credentials.json
  - `_is_sensitive_key(key: str) -> bool` — checks if key name contains KEY/SECRET/TOKEN
  - `_mask_value(key, value) -> str` — returns masked value for sensitive keys

## 4. Backend: Router

### New file: `backend/app/routers/credentials_editor.py`
- Prefix: `/api/credentials-editor`
- Endpoints matching spec table above
- Register in `app/main.py`

## 5. Frontend: Route & Page

### New route: `frontend/src/routes/tools/credentials-editor.tsx`
- Create `tools/` directory under routes (new route group)
- Page component with two-column layout

### New feature module: `frontend/src/features/credentials-editor/`
- `api.ts` — API client functions matching backend endpoints
- `hooks.ts` — React Query hooks (`useCredentialsEnv`, `useUpdateEnv`, `usePresets`, `useCreatePreset`, etc.)
- `components/`
  - `credentials-editor.tsx` — main container with two-column layout
  - `presets-panel.tsx` — left column: list presets, create/delete/apply actions
  - `env-editor.tsx` — right column: key-value form with add/remove/reveal

## 6. Frontend: Navigation

### Update `frontend/src/shared/components/app-sidebar.tsx`
- Add link to `/tools/credentials-editor` under a "Tools" section (or as top-level nav item)

## 7. Frontend: Route Tree Update
- TanStack Router auto-generates route tree — no manual edit needed for file-based routes

## Build Order
1. Backend model + migration
2. Backend schema + service
3. Backend router + register in main.py
4. Frontend API + hooks
5. Frontend components
6. Frontend route + navigation link
7. Manual test with real credentials.json