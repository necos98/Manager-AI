# Implementation Plan: Built-in MCP Plugin Catalog

## Architecture Overview

**Catalog layer** (new): `backend/plugins/<key>/plugin.yaml` — developer-defined manifests with name, description, transport, command, access_level, and config options schema.

**Translation layer** (new): `CatalogLoader` reads manifests → `build_runtime_config()` merges catalog def + user config → produces existing `PluginConfig` for PluginManager.

**Storage layer** (modified): `plugins.yaml` v2 stores only `enabled` + user `config` per plugin key. Plugin key = catalog key.

**Runtime layer** (mostly unchanged): `PluginManager` receives `PluginConfig` same as before. Merge happens upstream before calling `_start_one`.

## Files to Create

| File | Responsibility |
|------|---------------|
| `backend/app/mcp/catalog.py` | `CatalogPlugin`, `OptionDef` Pydantic models + `CatalogLoader` class |
| `backend/plugins/filesystem/plugin.yaml` | Sample manifest: filesystem MCP server |
| `backend/plugins/memory/plugin.yaml` | Sample manifest: memory MCP server |

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/mcp/plugin_config.py` | v2 schema: `ProjectPluginConfig`, `PluginsFile` v2, migration helper |
| `backend/app/mcp/plugin_manager.py` | `enable_plugin` accepts optional `config` dict; `start_plugins_for_project` merges catalog |
| `backend/app/routers/plugins.py` | New `GET /catalog` endpoint; `PUT` validates catalog key; `GET` enriches with catalog metadata |
| `backend/app/mcp/server.py` | `list_plugins` returns catalog info; `enable_plugin` accepts config |
| `backend/app/services/manager_ai_watcher.py` | Update `_reload_plugins` for v2 merge logic |
| `frontend/src/features/settings/api-plugins.ts` | Add `fetchCatalog`, update `PluginInfo` type |
| `frontend/src/features/settings/hooks-plugins.ts` | Add `useCatalog` hook, update mutations |
| `frontend/src/features/settings/components/plugins-panel.tsx` | Full rewrite: catalog grid + config modal + enabled list |

---

### Task 1: Catalog models + CatalogLoader

**Files:**
- Create: `backend/app/mcp/catalog.py`

**What:** Define `OptionDef`, `CatalogPlugin` Pydantic models. Implement `CatalogLoader` that scans `backend/plugins/*/plugin.yaml`, validates manifests, caches in memory.

```python
# backend/app/mcp/catalog.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from app.mcp.plugin_config import PluginTransport, AccessLevel

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent / "plugins"


class OptionChoice(BaseModel):
    value: str
    label: str


class OptionDef(BaseModel):
    key: str
    label: str
    type: Literal["string", "secret", "number", "boolean", "select"] = "string"
    required: bool = False
    default: str = ""
    placeholder: str = ""
    choices: list[OptionChoice] = Field(default_factory=list)


class CatalogPlugin(BaseModel):
    key: str  # set from directory name, not in YAML
    name: str
    description: str = ""
    transport: PluginTransport = PluginTransport.stdio
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    access_level: AccessLevel = AccessLevel.read_only
    timeout: int = 30
    options: list[OptionDef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_transport(self) -> "CatalogPlugin":
        if self.transport == PluginTransport.stdio and not self.command:
            raise ValueError("stdio transport requires 'command'")
        if self.transport == PluginTransport.http and not self.url:
            raise ValueError("http transport requires 'url'")
        return self


class CatalogLoader:
    def __init__(self) -> None:
        self._plugins: dict[str, CatalogPlugin] = {}
        self._loaded = False

    @property
    def plugins(self) -> dict[str, CatalogPlugin]:
        return dict(self._plugins)

    def get(self, key: str) -> CatalogPlugin | None:
        return self._plugins.get(key)

    def load(self) -> None:
        self._plugins.clear()
        if not PLUGINS_DIR.is_dir():
            logger.warning("Plugins directory not found: %s", PLUGINS_DIR)
            self._loaded = True
            return
        for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
            if not plugin_dir.is_dir():
                continue
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                logger.warning("No plugin.yaml in %s, skipping", plugin_dir)
                continue
            try:
                raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                raw["key"] = plugin_dir.name
                plugin = CatalogPlugin(**raw)
                self._plugins[plugin.key] = plugin
                logger.info("Loaded catalog plugin: %s", plugin.key)
            except Exception as exc:
                logger.warning("Failed to load plugin %s: %s", plugin_dir.name, exc)
        self._loaded = True

    def build_runtime_config(
        self, catalog_key: str, enabled: bool, user_config: dict[str, str]
    ) -> "PluginConfig | None":
        """Merge catalog definition + user config into a PluginConfig for PluginManager."""
        from app.mcp.plugin_config import PluginConfig

        cat = self.get(catalog_key)
        if cat is None:
            return None
        return PluginConfig(
            name=cat.name,
            enabled=enabled,
            transport=cat.transport,
            command=cat.command,
            args=cat.args,
            url=cat.url,
            env=user_config,
            access_level=cat.access_level,
            timeout=cat.timeout,
        )


catalog_loader = CatalogLoader()
```

- [ ] **Step 1: Create `backend/app/mcp/catalog.py`** with code above
- [ ] **Step 2: Create `backend/plugins/` directory** with `__init__.py` (empty)
- [ ] **Step 3: Wire catalog load into app startup** — add `catalog_loader.load()` to `main.py` lifespan before `start_plugins_for_project`
- [ ] **Step 4: Run backend to verify catalog loads without errors**

---

### Task 2: Plugin config v2 schema + migration

**Files:**
- Modify: `backend/app/mcp/plugin_config.py`

**What:** Add `ProjectPluginConfig` (v2 per-plugin config: `enabled` + `config` dict). Bump `PluginsFile.schema_version` to 2. Modify `load_plugins` to handle both v1 and v2. V1 plugins are wrapped as legacy.

Changes to `plugin_config.py`:

```python
# Add after existing PluginConfig class:

class ProjectPluginConfig(BaseModel):
    """Per-project plugin instance config (v2). References catalog by key."""
    enabled: bool = False
    config: dict[str, str] = Field(default_factory=dict)


# Modify PluginsFile:
class PluginsFile(BaseModel):
    schema_version: int = 2
    plugins: dict[str, ProjectPluginConfig] = Field(default_factory=dict)


# Modify load_plugins to handle v1 and v2:
def load_plugins(project_path: str) -> PluginsFile:
    path = _plugins_yaml_path(project_path)
    raw = atomic.read_yaml(path) or {}
    if not raw:
        return PluginsFile()
    version = raw.get("schema_version", 1)
    plugins_raw = raw.get("plugins", {}) or {}
    plugins: dict[str, ProjectPluginConfig] = {}
    for key, cfg in plugins_raw.items():
        try:
            if version >= 2:
                plugins[key] = ProjectPluginConfig(**cfg)
            else:
                # V1: PluginConfig has enabled field, migrate to v2 format
                v1 = PluginConfig(**cfg)
                plugins[key] = ProjectPluginConfig(
                    enabled=v1.enabled,
                    config=v1.env,
                )
        except Exception:
            pass
    return PluginsFile(plugins=plugins)


# Replace set_plugin_enabled:
def set_plugin_enabled(project_path: str, plugin_name: str, enabled: bool) -> bool:
    pf = load_plugins(project_path)
    cfg = pf.plugins.get(plugin_name)
    if cfg is None:
        return False
    cfg.enabled = enabled
    save_plugins(project_path, pf)
    return True


# Add helper:
def set_plugin_config(project_path: str, plugin_name: str, enabled: bool, config: dict[str, str]) -> bool:
    pf = load_plugins(project_path)
    cfg = pf.plugins.get(plugin_name)
    if cfg is None:
        pf.plugins[plugin_name] = ProjectPluginConfig(enabled=enabled, config=config)
    else:
        cfg.enabled = enabled
        cfg.config = config
    save_plugins(project_path, pf)
    return True
```

`save_plugins` stays the same (uses `.model_dump(mode="json")` on each plugin config).

- [ ] **Step 1: Add `ProjectPluginConfig` model and modify `PluginsFile`**
- [ ] **Step 2: Update `load_plugins`** to handle v1→v2 migration
- [ ] **Step 3: Add `set_plugin_config`** helper
- [ ] **Step 4: Run existing plugin tests** to verify backward compat

---

### Task 3: PluginManager merge logic

**Files:**
- Modify: `backend/app/mcp/plugin_manager.py`

**What:** `start_plugins_for_project` and `enable_plugin` use `catalog_loader.build_runtime_config()` to merge catalog + user config before passing to `_start_one`. `_start_one` unchanged (still takes `PluginConfig`).

Key changes:

```python
# In start_plugins_for_project, replace the for loop:
for key, proj_cfg in plugins_file.plugins.items():
    if not proj_cfg.enabled:
        continue
    if key in existing:
        continue
    runtime_cfg = catalog_loader.build_runtime_config(key, True, proj_cfg.config)
    if runtime_cfg is None:
        logger.warning("Plugin %s not in catalog, running as legacy", key)
        # Legacy v1: reconstruct PluginConfig from old format
        # (only path for manually-created plugins that predate catalog)
        continue  # skip if no catalog entry, legacy handled separately
    await self._start_one(project_id, project_path, key, runtime_cfg, mcp_instance)


# Modify enable_plugin signature:
async def enable_plugin(
    self,
    project_id: str,
    project_path: str,
    plugin_key: str,
    mcp_instance: FastMCP,
    config: dict[str, str] | None = None,
) -> bool:
    cat = catalog_loader.get(plugin_key)
    if cat is None:
        return False  # must be in catalog
    if not set_plugin_config(project_path, plugin_key, True, config or {}):
        # create new entry
        set_plugin_config(project_path, plugin_key, True, config or {})
    runtime_cfg = catalog_loader.build_runtime_config(plugin_key, True, config or {})
    if runtime_cfg is None:
        return False
    await self._start_one(project_id, project_path, plugin_key, runtime_cfg, mcp_instance)
    return True
```

- [ ] **Step 1: Update `start_plugins_for_project`** to use `catalog_loader.build_runtime_config()`
- [ ] **Step 2: Update `enable_plugin`** to accept `config` dict and require catalog entry
- [ ] **Step 3: Update `restart_plugin`** to rebuild runtime config from catalog + stored user config
- [ ] **Step 4: Run plugin manager tests**

---

### Task 4: API endpoints — catalog + modified plugins

**Files:**
- Modify: `backend/app/routers/plugins.py`

**What:** New `GET /api/plugins/catalog` endpoint. Modify `GET /api/projects/{id}/plugins` to enrich with catalog metadata. Modify `PUT` to validate catalog key and accept config.

```python
# New endpoint:
@router.get("/catalog")
async def get_catalog():
    """List all available plugins in the built-in catalog."""
    return [
        {
            "key": p.key,
            "name": p.name,
            "description": p.description,
            "transport": p.transport.value,
            "access_level": p.access_level.value,
            "options": [
                {
                    "key": o.key,
                    "label": o.label,
                    "type": o.type,
                    "required": o.required,
                    "default": o.default,
                    "placeholder": o.placeholder,
                    "choices": [{"value": c.value, "label": c.label} for c in o.choices],
                }
                for o in p.options
            ],
        }
        for p in catalog_loader.plugins.values()
    ]


# Modified list_plugins — enrich with catalog metadata:
@router.get("")
async def list_plugins(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    statuses = plugin_manager.get_status(project_id)
    config = load_plugins(project.path)
    
    # Catalog plugins (enabled or not)
    result = []
    seen = set()
    for key, cat in catalog_loader.plugins.items():
        proj_cfg = config.plugins.get(key)
        running = next((s for s in statuses if s["name"] == key), None)
        result.append({
            "key": key,
            "name": cat.name,
            "description": cat.description,
            "enabled": proj_cfg.enabled if proj_cfg else False,
            "transport": cat.transport.value,
            "access_level": cat.access_level.value,
            "connected": running["connected"] if running else False,
            "tool_count": running["tool_count"] if running else 0,
            "configured": proj_cfg is not None,
            "config": proj_cfg.config if proj_cfg else {},
            "catalog": True,
        })
        seen.add(key)
    
    # Legacy plugins (from v1, not in catalog)
    for key, proj_cfg in config.plugins.items():
        if key not in seen:
            running = next((s for s in statuses if s["name"] == key), None)
            result.append({
                "key": key,
                "name": key,
                "description": "Legacy plugin (no catalog entry)",
                "enabled": proj_cfg.enabled,
                "transport": "unknown",
                "access_level": "unknown",
                "connected": running["connected"] if running else False,
                "tool_count": running["tool_count"] if running else 0,
                "configured": True,
                "config": proj_cfg.config,
                "catalog": False,
                "legacy": True,
            })
    
    return result


# Modified PUT — catalog-key only, config-driven:
@router.put("/{plugin_key}")
async def upsert_plugin(project_id: str, plugin_key: str, data: dict, db: AsyncSession = Depends(get_db)):
    cat = catalog_loader.get(plugin_key)
    if cat is None:
        raise HTTPException(status_code=400, detail=f"Plugin '{plugin_key}' not found in catalog")
    
    project = await ProjectService(db).get_by_id(project_id)
    enabled = data.get("enabled", True)
    config = data.get("config", {})
    
    set_plugin_config(project.path, plugin_key, enabled, config)
    
    # If enabling, start it; if disabling, stop it
    if enabled:
        await plugin_manager.enable_plugin(project_id, project.path, plugin_key, mcp, config)
    else:
        await plugin_manager.disable_plugin(project_id, project.path, plugin_key, mcp)
    
    return {"key": plugin_key, "name": cat.name, "enabled": enabled, "config": config}
```

Note: catalog endpoint must be defined BEFORE the `/{plugin_key}` routes to avoid path conflicts. Place it right after the router definition, before `@router.get("")`.

- [ ] **Step 1: Add `GET /catalog` endpoint** (before parameterized routes)
- [ ] **Step 2: Modify `GET /` to enrich with catalog metadata**
- [ ] **Step 3: Modify `PUT /{plugin_key}` to validate catalog key and accept config**
- [ ] **Step 4: Modify `GET /{plugin_key}` to use catalog for metadata**
- [ ] **Step 5: Update `DELETE /{plugin_key}`** — no change needed (already works)
- [ ] **Step 6: Test all endpoints manually with curl/httpie**

---

### Task 5: MCP tool updates

**Files:**
- Modify: `backend/app/mcp/server.py` (lines 732-791)

**What:** `list_plugins` returns catalog info. `enable_plugin` accepts optional config. `get_plugin_config` returns catalog metadata + user config.

```python
@mcp.tool(description=_desc["tool.list_plugins.description"])
async def list_plugins(project_id: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
    
    statuses = plugin_manager.get_status(project_id)
    config = load_plugins(project.path) if project else PluginsFile()
    
    plugins = []
    for key, cat in catalog_loader.plugins.items():
        proj_cfg = config.plugins.get(key)
        running = next((s for s in statuses if s["name"] == key), None)
        plugins.append({
            "name": key,
            "display_name": cat.name,
            "description": cat.description,
            "enabled": proj_cfg.enabled if proj_cfg else False,
            "connected": running["connected"] if running else False,
            "tool_count": running["tool_count"] if running else 0,
            "access_level": cat.access_level.value,
            "catalog": True,
        })
    
    return {
        "plugins": plugins,
        "catalog_available": [
            k for k in catalog_loader.plugins
            if k not in config.plugins or not config.plugins[k].enabled
        ],
    }


@mcp.tool(description=_desc["tool.enable_plugin.description"])
async def enable_plugin(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
    
    cat = catalog_loader.get(plugin_name)
    if cat is None:
        return {"error": f"Plugin '{plugin_name}' not found in catalog. Available: {list(catalog_loader.plugins.keys())}"}
    
    success = await plugin_manager.enable_plugin(
        project_id, project.path, plugin_name, mcp
    )
    return {"success": success}
```

- [ ] **Step 1: Update `list_plugins`** to return catalog metadata
- [ ] **Step 2: Update `enable_plugin`** with catalog validation and helpful error message
- [ ] **Step 3: Update `get_plugin_config`** to include catalog metadata + user config
- [ ] **Step 4: Test MCP tools via Claude Code or manual invocation**

---

### Task 6: Sample plugin manifests

**Files:**
- Create: `backend/plugins/filesystem/plugin.yaml`
- Create: `backend/plugins/memory/plugin.yaml`

```yaml
# backend/plugins/filesystem/plugin.yaml
name: "Filesystem"
description: "Read, write, and manage files on the local filesystem via MCP"
transport: stdio
command: "npx"
args:
  - "-y"
  - "@modelcontextprotocol/server-filesystem"
  - "/path/to/allowed/dir"
access_level: read_write
timeout: 30
options:
  - key: ALLOWED_DIR
    label: "Allowed directory"
    type: string
    required: true
    placeholder: "/path/to/allowed/directory"
```

```yaml
# backend/plugins/memory/plugin.yaml
name: "Memory"
description: "Knowledge graph memory system for persistent context across sessions"
transport: stdio
command: "npx"
args:
  - "-y"
  - "@modelcontextprotocol/server-memory"
access_level: read_write
timeout: 30
options: []
```

- [ ] **Step 1: Create `backend/plugins/filesystem/plugin.yaml`**
- [ ] **Step 2: Create `backend/plugins/memory/plugin.yaml`**
- [ ] **Step 3: Verify catalog loader picks them up at startup**

---

### Task 7: Watcher integration

**Files:**
- Modify: `backend/app/services/manager_ai_watcher.py` (lines 103-159, `_reload_plugins`)

**What:** On `plugins.yaml` change, `_reload_plugins` must use catalog merge logic. Currently reads `PluginConfig` directly — change to use `catalog_loader.build_runtime_config()` for catalog plugins, skip legacy plugins without catalog entry.

- [ ] **Step 1: Update `_reload_plugins`** to use catalog merge for starting/restarting
- [ ] **Step 2: Test by editing plugins.yaml while app is running**

---

### Task 8: Frontend — API client + types

**Files:**
- Modify: `frontend/src/features/settings/api-plugins.ts`

**What:** Add `fetchCatalog()`, update `PluginInfo` type to include catalog metadata.

```typescript
// New types
export interface CatalogPlugin {
  key: string;
  name: string;
  description: string;
  transport: string;
  access_level: string;
  options: PluginOption[];
}

export interface PluginOption {
  key: string;
  label: string;
  type: "string" | "secret" | "number" | "boolean" | "select";
  required: boolean;
  default: string;
  placeholder: string;
  choices?: { value: string; label: string }[];
}

// Updated PluginInfo
export interface PluginInfo {
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  transport: string;
  access_level: string;
  connected: boolean;
  tool_count: number;
  configured: boolean;
  config: Record<string, string>;
  catalog: boolean;
  legacy?: boolean;
}

// New function
export function fetchCatalog(): Promise<CatalogPlugin[]> {
  return apiGet<CatalogPlugin[]>("/plugins/catalog");
}
```

- [ ] **Step 1: Add `CatalogPlugin`, `PluginOption` types and `fetchCatalog`**
- [ ] **Step 2: Update `PluginInfo`** to match new API response shape

---

### Task 9: Frontend — React Query hooks

**Files:**
- Modify: `frontend/src/features/settings/hooks-plugins.ts`

**What:** Add `useCatalog` hook. Update `useUpsertPlugin` to accept config. Update cache invalidation.

- [ ] **Step 1: Add `useCatalog` hook**
- [ ] **Step 2: Update `useUpsertPlugin` mutation** to send `{ catalog: true, config, enabled }`
- [ ] **Step 3: Update cache keys** for catalog invalidation

---

### Task 10: Frontend — Plugin catalog UI rewrite

**Files:**
- Modify: `frontend/src/features/settings/components/plugins-panel.tsx`

**What:** Full rewrite. Three sections:
1. **Enabled plugins** — cards showing connected plugins with status, quick toggle, click to configure
2. **Available catalog** — grid of catalog plugins not yet enabled, with "Configure" button
3. **Legacy plugins** (if any) — read-only with delete button

Config modal for each plugin renders form fields based on options schema.

Key component structure:
```
<PluginsPanel>
  <EnabledPlugins />     // currently enabled, with status
  <CatalogGrid />        // available but not enabled
  <LegacyPlugins />      // if any exist
  <ConfigModal />        // opened for any plugin
</PluginsPanel>
```

Remove: "Add Plugin" button, free-form creation dialog, manual command/URL/args input fields.

- [ ] **Step 1: Build catalog grid component** — card per plugin with name, description, transport icon, access badge, "Configure" button
- [ ] **Step 2: Build config modal** — enable toggle + form fields rendered from options schema (string→Input, secret→password Input, number→number Input, boolean→Checkbox, select→Select)
- [ ] **Step 3: Build enabled plugins list** — status indicator, tool count, quick disable, click to reconfigure
- [ ] **Step 4: Build legacy section** — read-only display, delete button only
- [ ] **Step 5: Remove "Add Plugin" button and free-form creation dialog**
- [ ] **Step 6: Handle loading/empty/error states** for catalog fetch

---

### Task 11: Startup wiring

**Files:**
- Modify: `backend/app/main.py`

**What:** Import `catalog_loader` and call `catalog_loader.load()` in lifespan before `start_plugins_for_project`.

- [ ] **Step 1: Import catalog_loader in main.py**
- [ ] **Step 2: Call catalog_loader.load()** before plugin startup loop
- [ ] **Step 3: Verify full stack starts without errors**

---

### Task 12: Tests

**Files:**
- Create: `backend/tests/test_catalog.py`
- Modify: `backend/tests/test_plugin_manager.py` (if needed)

**What:** Test catalog loading, v1→v2 migration, merge logic, API endpoints.

- [ ] **Step 1: Test `CatalogLoader.load()`** with temp plugin dirs
- [ ] **Step 2: Test `build_runtime_config()`** merge produces correct PluginConfig
- [ ] **Step 3: Test v1→v2 migration** in `load_plugins`
- [ ] **Step 4: Test `GET /api/plugins/catalog`** returns manifest data
- [ ] **Step 5: Test `PUT /api/projects/{id}/plugins/{key}`** validates catalog key
- [ ] **Step 6: Run full test suite**

---

### Task 13: Cleanup + final verification

- [ ] **Step 1: Remove unused imports** across modified files
- [ ] **Step 2: Run backend linting** (if any)
- [ ] **Step 3: Run frontend linting** (`npm run lint`)
- [ ] **Step 4: Full stack smoke test** — start app, browse catalog, configure + enable a plugin
- [ ] **Step 5: Verify enable/disable toggle** works end-to-end