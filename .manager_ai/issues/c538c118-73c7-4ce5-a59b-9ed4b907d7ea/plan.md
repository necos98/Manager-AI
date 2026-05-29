# Implementation Plan: Claude Code credentials.json Editor

## Overview
Build a tool page to edit `~/.claude/credentials.json` env vars with preset management. Model/schema/migration already done — focus is service, router, frontend.

## Phase 1: Backend — CredentialEditorService
**File: `backend/app/services/credential_editor_service.py`**

`CredentialEditorService(db: AsyncSession)`:
- `_get_credentials_path() -> Path` — resolve `%USERPROFILE%\.claude\credentials.json` (Windows) or `~/.claude/credentials.json` (other)
- `read_env() -> dict[str, str]` — read file, return `env` dict or `{}` if missing/invalid JSON
- `write_env(variables: dict[str, str])` — read full JSON, backup as `.bak`, modify `env` key, atomic write via temp file + os.replace
- **Preset CRUD**: `list_presets()`, `create_preset(name, vars)`, `update_preset(id, name, vars)`, `delete_preset(id)`, `get_preset(id)`, `apply_preset(id)`
- `_is_sensitive_key(key) -> bool` — case-insensitive check for KEY/SECRET/TOKEN
- Encryption via `CredentialService._get_fernet()` (reuse existing static method). Split variables into plain (visible) and encrypted (sensitive) dicts on write, recombine on read.

### Pattern reference
- Service pattern: `backend/app/services/credential_service.py` (AsyncSession, Fernet)

## Phase 2: Backend — Router
**File: `backend/app/routers/credentials_editor.py`**

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/api/credentials-editor` | Read current env | - | `{"variables": {...}}` |
| PUT | `/api/credentials-editor` | Write env vars | `{"variables": {...}}` | `{"variables": {...}}` |
| GET | `/api/credentials-editor/presets` | List presets | - | `PresetOut[]` |
| POST | `/api/credentials-editor/presets` | Create preset | `{"name": "...", "variables": {...}}` | `PresetOut` |
| PUT | `/api/credentials-editor/presets/{id}` | Update preset | `{"name": "...", "variables": {...}}` | `PresetOut` |
| DELETE | `/api/credentials-editor/presets/{id}` | Delete preset | - | 204 |
| POST | `/api/credentials-editor/presets/{id}/apply` | Apply preset | - | `{"variables": {...}}` |

**Register:** Add `credentials_editor` to router imports in `backend/app/main.py` line 29 (`from app.routers import ...`) + `app.include_router(credentials_editor.router)`.

Router pattern: `backend/app/routers/credentials.py` (Depends(get_db), async, commit).

## Phase 3: Frontend — API Client + Hooks
**File: `frontend/src/features/credentials-editor/api.ts`**
- `fetchEnv()`, `updateEnv(variables)`, `fetchPresets()`, `createPreset(data)`, `updatePreset(id, data)`, `deletePreset(id)`, `applyPreset(id)`
- Shared API client: `@/shared/api/client` (apiGet, apiPut, apiPost, apiDelete)

**File: `frontend/src/features/credentials-editor/hooks.ts`**
- `useCredentialsEnv()` — query
- `useUpdateEnv()` — mutation with env invalidation
- `usePresets()` — query
- `useCreatePreset()`, `useUpdatePreset()`, `useDeletePreset()`, `useApplyPreset()` — mutations with presets invalidation
- Toast notifications on mutation errors (pattern from `hooks-credentials.ts`)

## Phase 4: Frontend — Components
**File: `frontend/src/features/credentials-editor/components/env-editor.tsx`**
- Key-value form listing current env variables
- "Add Variable" button → new empty row
- Remove button per row (confirm if value non-empty)
- Sensitive key detection (KEY/SECRET/TOKEN) → show `****` + reveal toggle
- "Save" button to persist

**File: `frontend/src/features/credentials-editor/components/presets-panel.tsx`**
- Left column: list saved presets with name, edit/delete/apply buttons
- "Save Current as Preset" button → dialog for name input
- Apply confirmation dialog

**File: `frontend/src/features/credentials-editor/components/credentials-editor.tsx`**
- Main two-column layout (left: presets, right: env editor)
- Fetches env + presets on mount
- Orchestrates apply/load interactions between panels

## Phase 5: Frontend — Route + Sidebar
**File: `frontend/src/routes/tools/credentials-editor.tsx`** (new `tools/` route group)
- `createFileRoute('/tools/credentials-editor')` with TanStack Router
- Renders CredentialsEditor component

**File: `frontend/src/shared/components/project-sidebar.tsx`**
- Add "Credentials" nav item under **Global** section (after Pipelines or Settings)
- Import `Key` from lucide-react
- Link to `/tools/credentials-editor`
- Pattern: follow existing nav items in the Global group (e.g., Settings at line 193-203)

TanStack Router auto-generates route tree — no manual route tree edit.

## Build Order
1. Backend: CredentialEditorService
2. Backend: credentials_editor router + main.py registration
3. Frontend: API client + hooks
4. Frontend: env-editor component
5. Frontend: presets-panel component
6. Frontend: credentials-editor container + route + sidebar link
