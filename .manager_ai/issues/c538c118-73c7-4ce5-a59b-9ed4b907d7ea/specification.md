# Claude Code credentials.json Editor

## Overview
A dedicated tool/page to edit the `env` section of Claude Code's `credentials.json` file (`~/.claude/credentials.json`). Users can view, edit, add, and remove environment variables, and save/reuse named presets (templates) for quick switching between API provider configurations.

## Functional Requirements

### 1. View & Edit credentials.json env
- Read the current `env` object from `~/.claude/credentials.json`
- Display all env variables as editable key-value fields
- Support adding new env variables (key + value)
- Support removing env variables (with confirmation for non-empty values)
- Save changes back to `credentials.json` with atomic write (temp file + rename)

### 2. Preset Management
- **Save preset**: Name the current set of env variables and persist as a preset
- **Load/Apply preset**: Replace current env variables with a preset's values, then write to credentials.json
- **Delete preset**: Remove a saved preset
- **Update preset**: Overwrite an existing preset with the current values
- Presets are stored project-locally (in Manager AI's database)

### 3. Security
- Values marked as sensitive (containing `KEY`, `SECRET`, `TOKEN` in the key name) are masked by default with a reveal toggle
- API keys and secrets stored in presets are encrypted at rest (Fernet, same as existing credential system)

### 4. UI Structure
- New global route: `/tools/credentials-editor`
- Layout: two-column
  - Left: presets list (saved configurations)
  - Right: env variable editor form

## Backend Endpoints

All endpoints live at `/api/credentials-editor`:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/credentials-editor` | Read current credentials.json env vars |
| PUT | `/api/credentials-editor` | Write env vars to credentials.json |
| GET | `/api/credentials-editor/presets` | List all saved presets |
| POST | `/api/credentials-editor/presets` | Create a new preset |
| PUT | `/api/credentials-editor/presets/{preset_id}` | Update an existing preset |
| DELETE | `/api/credentials-editor/presets/{preset_id}` | Delete a preset |
| POST | `/api/credentials-editor/presets/{preset_id}/apply` | Apply a preset to credentials.json |

## Data Model

### New Table: `credential_presets`
- `id`: UUID string (PK)
- `name`: String, user-given label
- `variables`: Text (JSON dict of env key-value pairs)
- `encrypted_fields`: Text (JSON dict of sensitive values, Fernet-encrypted)
- `created_at`: DateTime
- `updated_at`: DateTime

## Technical Constraints
- Windows-first: `credentials.json` path is `%USERPROFILE%\.claude\credentials.json`
- Backup: Before writing, create a `.bak` copy of the current credentials.json
- Atomic write: Write to temp file, then rename over target
- Preserve all non-env keys in credentials.json (read whole file, modify only `env`, write back)