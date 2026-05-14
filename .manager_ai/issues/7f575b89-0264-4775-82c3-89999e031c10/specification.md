# Built-in MCP Plugin Catalog — Specification

## Goal

Replace manual plugin configuration with a built-in catalog. Developers add plugin definitions to the codebase. End users browse available plugins, configure plugin-specific options, and toggle enable/disable. No manual command/URL entry required.

## Current State

Users create plugins by filling in a free-form "Add Plugin" dialog: key, name, transport type, command or URL, args, env vars, access level. All fields typed manually. This requires knowing the exact MCP server command, its arguments, and available tools — too technical for end users.

## Desired State

1. Plugin definitions live in `backend/plugins/<plugin-key>/plugin.yaml`
2. Backend loads catalog at startup, exposes available plugins list
3. Frontend shows catalog as browsable grid of plugin cards
4. User clicks a plugin, sees description + config form (rendered from manifest options schema)
5. User fills config fields (host, port, API keys, etc.), toggles enable
6. Backend merges catalog definition + user config, writes to project `plugins.yaml`
7. PluginManager starts the plugin with merged config
8. Manual "Add Plugin" form removed — catalog is the only path

## Plugin Manifest Format

Each plugin is a directory under `backend/plugins/` with a `plugin.yaml`:

```yaml
name: "Plugin Display Name"
description: "What this plugin does"
transport: stdio          # stdio | http
command: "uvx"            # required for stdio
args:                     # required for stdio
  - "mcp-server-name"
  - "--flag"
url: ""                   # required for http
access_level: read_only   # read_only | read_write | admin
timeout: 30               # optional, default 30
options:                  # user-configurable fields
  - key: ENV_VAR_NAME
    label: "Human-readable field label"
    type: string          # string | secret | number | boolean | select
    required: true
    default: "optional default"
    placeholder: "placeholder text"
    choices:              # only for type: select
      - value: "val1"
        label: "Label 1"
```

**Option types:**
- `string` — text input
- `secret` — password input (masked in UI, stored encrypted)
- `number` — numeric input
- `boolean` — checkbox
- `select` — dropdown with `choices`

**Transport rules:**
- `stdio` requires `command` + `args`
- `http` requires `url`

## File Structure

```
backend/plugins/
├── mysql/
│   └── plugin.yaml
├── slack/
│   └── plugin.yaml
├── filesystem/
│   └── plugin.yaml
└── ... (one folder per plugin)
```

## Catalog Loading

- `CatalogLoader` class reads `backend/plugins/*/plugin.yaml` at startup
- Validates manifests against Pydantic schema
- Caches parsed catalog in memory
- Exposes via new API endpoint `GET /api/plugins/catalog`
- Returns list of available plugins with: key, name, description, transport, access_level, options (schema only, no values)

## Project plugins.yaml — Schema v2

Current format (v1) stores full plugin config including command/transport. New format (v2) references catalog entry + user config:

```yaml
schema_version: 2
plugins:
  mysql:
    catalog_key: mysql
    enabled: true
    config:
      MYSQL_HOST: "10.0.1.5"
      MYSQL_PORT: "3306"
      MYSQL_USER: "admin"
      MYSQL_PASSWORD: ""  # secret values handled via credential system
```

PluginManager merges at runtime: catalog `command` + `args` + `transport` + user `config` (injected as env vars).

## Migration

- On startup, detect v1 `plugins.yaml`
- V1 plugins without `catalog_key`: keep running but mark as "legacy" in API
- Legacy plugins: read-only in UI, can be disabled/deleted, cannot be edited
- New plugins only createable via catalog
- Migration is one-way — no downgrade

## API Changes

### New endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/plugins/catalog` | List all available plugins in catalog |

### Modified endpoints

| Method | Path | Change |
|--------|------|--------|
| `PUT` | `/api/projects/{id}/plugins/{key}` | Accept catalog_key + config instead of raw command/url |
| `GET` | `/api/projects/{id}/plugins` | Include catalog metadata (name, description, options schema) |

### Removed functionality

- Creating plugins with manual command/URL (server-side validation rejects non-catalog keys)

## Frontend Changes

### Plugins page rewrite

1. **Catalog grid** — card per available plugin showing:
   - Plugin name
   - Description (2-line clamp)
   - Access level badge
   - Transport icon
   - "Configure" button (opens config modal)

2. **Config modal** — for selected plugin:
   - Enable/disable toggle at top
   - Rendered form fields from options schema
   - Save button (saves config + enable state)
   - Cancel button

3. **Enabled plugins list** — summary of currently enabled plugins:
   - Plugin name + config summary
   - Connection status indicator
   - Quick disable toggle
   - Click to reconfigure

4. **Legacy plugins section** (if any exist):
   - Read-only display
   - Delete button only

### Removed

- "Add Plugin" button and free-form creation dialog
- Manual command/URL/args input fields

## MCP Tools

Existing tools (`list_plugins`, `get_plugin_config`, `enable_plugin`, `disable_plugin`) remain with same signatures. `list_plugins` additionally returns `catalog_available` field listing plugins in catalog but not yet enabled.

## Edge Cases

1. **Plugin removed from catalog but enabled in project** → plugin still runs, shown as "legacy" with warning
2. **Plugin catalog definition updated** → running plugins restart on config change (existing watchdog behavior)
3. **Catalog plugin with no required options** → enable toggle works immediately, no config form needed
4. **Duplicate catalog keys** → startup error, catalog load fails with clear message
5. **Invalid plugin.yaml** → skipped on load, logged as warning, doesn't break other plugins

## Out of Scope

- Plugin versioning / upgrade management
- Remote catalog fetching
- Plugin dependency resolution
- Per-user plugin configuration (project-scoped only)