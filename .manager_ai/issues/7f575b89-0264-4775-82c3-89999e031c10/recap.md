## What was implemented

Built-in MCP Plugin Catalog system that replaces manual plugin configuration. Developers add plugin manifests to `backend/plugins/<key>/plugin.yaml`. End users browse available plugins, configure options, and toggle enable/disable.

### New files
- `backend/app/mcp/catalog.py` — CatalogPlugin/OptionDef Pydantic models + CatalogLoader singleton. Scans `backend/plugins/*/plugin.yaml` at startup, caches manifests, provides `build_runtime_config()` to merge catalog def + user config into PluginConfig.
- `backend/plugins/filesystem/plugin.yaml` — Sample manifest for @modelcontextprotocol/server-filesystem
- `backend/plugins/memory/plugin.yaml` — Sample manifest for @modelcontextprotocol/server-memory
- `backend/tests/test_catalog.py` — 15 tests covering CatalogPlugin validation, CatalogLoader, and build_runtime_config

### Modified files
- `backend/app/mcp/plugin_config.py` — Added ProjectPluginConfig model. PluginsFile v2 stores only `enabled` + `config`. load_plugins handles v1→v2 migration. Added set_plugin_config helper.
- `backend/app/mcp/plugin_manager.py` — start_plugins_for_project uses catalog_loader.build_runtime_config(). enable_plugin accepts config dict, requires catalog entry. restart_plugin rebuilds from catalog + stored config.
- `backend/app/routers/plugins.py` — New GET /api/plugins/catalog endpoint on catalog_router. GET list_plugins enriched with catalog metadata (name, description, options). PUT validates catalog key, accepts {enabled, config}. Legacy plugins shown as read-only.
- `backend/app/mcp/server.py` — MCP list_plugins returns catalog metadata + catalog_available. enable_plugin validates against catalog with helpful error. get_plugin_config returns catalog metadata + user config.
- `backend/app/main.py` — Import catalog_loader, call load() at startup. Register catalog_router.
- `backend/app/services/manager_ai_watcher.py` — _reload_plugins simplified for v2 schema (enable/disable toggles only).
- `frontend/src/features/settings/api-plugins.ts` — Added CatalogPlugin, PluginOption types, fetchCatalog(), updated PluginInfo.
- `frontend/src/features/settings/hooks-plugins.ts` — Added useCatalog hook, updated useUpsertPlugin mutation signature.
- `frontend/src/features/settings/components/plugins-panel.tsx` — Full rewrite: catalog grid, ConfigModal with dynamic form from options schema (string/secret/number/boolean/select), enabled plugins list with status, legacy section. Removed "Add Plugin" free-form dialog.
- `backend/tests/test_plugin_manager.py` — Updated for v2 schema + catalog injection.

### Architecture decisions
- Plugin key = catalog directory name. No `catalog_key` indirection needed.
- CatalogLoader is a singleton. build_runtime_config() returns existing PluginConfig — PluginManager internals unchanged.
- V1 plugins.yaml auto-migrated on load (env → config, enabled preserved).
- Catalog-only: PUT rejects keys not in catalog (400 error).
- Catalog endpoint on separate router (/api/plugins/catalog, no project_id) since catalog is global.
- PluginManager.enable_plugin accepts optional `config` dict (defaults to {}).

### Test results
- 23/23 plugin manager tests pass
- 15/15 catalog tests pass
- Backend starts clean, loads 2 catalog plugins (filesystem, memory)
- Other test failures (projects/templates/variables/tasks) are pre-existing and unrelated