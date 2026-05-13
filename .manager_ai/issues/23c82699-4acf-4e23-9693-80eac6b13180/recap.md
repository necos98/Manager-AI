## Feasibility Analysis & Implementation: MCP Plugin System

### Verdict: Feasible and Implemented

The MCP plugin system was analyzed, designed, and implemented across backend and frontend.

### What was built

**Backend (5 new files, 4 modified):**
- `app/mcp/plugin_config.py` — Pydantic models for plugin config, YAML load/save to `.manager_ai/plugins.yaml`
- `app/mcp/plugin_client.py` — MCP client wrapper (stdio subprocess + HTTP/SSE), tool discovery, tool invocation
- `app/mcp/plugin_proxy.py` — Dynamic tool proxy registration on FastMCP with `{plugin}__` prefix
- `app/mcp/plugin_manager.py` — Lifecycle orchestrator: start/stop/enable/disable plugins, retry logic (max 3 in 60s, then 5min cooldown), event emission
- `app/routers/plugins.py` — REST API for frontend plugin management
- `app/main.py` — Lifespan integration: startup plugin loading, shutdown cleanup, router registration
- `app/mcp/server.py` — 4 new MCP tools: list_plugins, get_plugin_config, enable_plugin, disable_plugin
- `app/services/manager_ai_watcher.py` — Watchdog reload for plugins.yaml changes
- `app/mcp/default_settings.json` — Tool descriptions

**Frontend (4 new files, 1 modified):**
- API client functions, React Query hooks, PluginsPanel component, route page
- Added "MCP Plugins" link to sidebar "More" dropdown
- Full CRUD UI: list plugins with status badges, add/edit form, enable/disable toggle

**Tests (22 passing):**
- PluginConfig validation, YAML load/save/invalid skip, PluginClient with dummy MCP subprocess, PluginManager lifecycle (start, stop, enable, disable), error cases (unreachable HTTP, disconnected call)

### Key design decisions

1. **Proxy pattern with `**kwargs`**: FastMCP type introspection (`issubclass`) fails on non-class annotations like `Any`. Dynamic proxy functions must use un-annotated `**kwargs`.
2. **`setdefault` for state init**: `_start_one` called from both `start_plugins_for_project` and `enable_plugin` — must handle missing project_id key.
3. **Per-project isolation**: `.manager_ai/plugins.yaml` per project, separate subprocess per project.
4. **access_level declarative only**: Injected into tool descriptions for LLM awareness. Real enforcement at credential/DB level.

### E2E validation

Dummy MCP Python script used in tests validates full round-trip: subprocess spawn → MCP initialize → tool discovery → tool invocation → disconnect. No real MCP server tested yet — first real plugin (e.g., mcp-server-mysql) will exercise the full path.