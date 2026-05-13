# MCP Plugin System: Implementation Plan

> **Goal:** Enable per-project MCP plugins that aggregate external MCP tools into the single Manager AI `/mcp` endpoint.

> **Architecture:** PluginManager reads `.manager_ai/plugins.yaml` per project, spawns/connects to MCP servers, discovers tools, and registers auto-generated proxy functions on the main FastMCP instance with `{plugin}__` name prefix. Tool access_level is declared in YAML and injected into descriptions.

> **Tech Stack:** Python (FastMCP 1.9.2 client/server), asyncio subprocess, existing watchdog, React frontend with existing settings patterns.

**Total files:** ~5 new, ~4 modified. **Estimated lines:** ~600 backend, ~350 frontend.

---

## Task 1: Plugin Config Schema & YAML Store

**Files:** Create `backend/app/mcp/plugin_config.py`, modify `backend/app/mcp/__init__.py`

Define Pydantic models for plugin configuration and a loader for `.manager_ai/plugins.yaml`. Validate transport type, required fields per transport, unique plugin names.

- PluginConfig: name, enabled, transport (stdio|http), command, args, url, env dict, access_level (read_only|read_write|admin), timeout (default 30)
- PluginsFile: dict of plugin_name → PluginConfig
- load_plugins(project_path) → PluginsFile: reads and validates the YAML
- save_plugins(project_path, plugins) → writes YAML atomically (temp + rename pattern from existing stores)

## Task 2: MCP Client Session Manager

**Files:** Create `backend/app/mcp/plugin_client.py`

Thin wrapper around `mcp.client.session.ClientSession` that handles handshake + tool discovery + tool invocation. One instance per plugin.

- `connect_stdio(command, args, env)`: spawn subprocess, create session, send initialize, return session + list of Tool objects
- `connect_http(url)`: open SSE transport, same handshake flow
- `call_tool(session, tool_name, arguments)`: invoke tool, return result dict
- `disconnect(session)`: terminate transport, reap subprocess
- Context manager API for lifecycle

## Task 3: Dynamic Tool Proxy Registration

**Files:** Modify `backend/app/mcp/server.py`

Function that takes a FastMCP instance + plugin tool list and registers auto-generated proxy functions with `{plugin}__` prefix. Must handle:

- Generate wrapper function per tool that calls `plugin_client.call_tool`
- Inject `access_level` into tool description
- Map MCP JSON Schema params to Python function signature
- Register with `mcp.tool(name=..., description=...)(wrapper)`

## Task 4: PluginManager (Lifecycle Orchestrator)

**Files:** Create `backend/app/mcp/plugin_manager.py`

Main orchestrator called from lifespan. Per project: load config → connect plugins → register proxies. Handles restart logic and cleanup.

- `start_plugins_for_project(project_id, project_path, mcp_instance)`: full startup flow
- `stop_plugins_for_project(project_id)`: disconnect all, cleanup
- `restart_plugin(project_id, plugin_name)`: stop + start single plugin
- Health check: periodic ping or watch for subprocess exit
- Max retry counter (3 in 60s, then cooldown for 5 min) stored in memory dict
- Emit realtime events (plugin_started, plugin_failed, plugin_stopped) via event_service

## Task 5: Lifespan Integration

**Files:** Modify `backend/app/main.py`

Wire PluginManager into the FastAPI lifespan. After `manager_ai_watcher` startup, iterate all projects and call `start_plugins_for_project`. On shutdown, call `stop_plugins_for_project` for all.

The PluginManager holds a dict `project_id → {plugin_name → PluginClient}` in memory on the main process (not in SQLite — plugins are runtime-only state).

## Task 6: Watchdog Reload for plugins.yaml

**Files:** Modify `backend/app/services/manager_ai_watcher.py`

Add `.manager_ai/plugins.yaml` to the existing watchdog observer. On change: validate YAML, call `PluginManager.restart_plugins_for_project()` to stop removed plugins, start new ones, restart changed ones. Emit event so frontend refreshes plugin list.

Must handle: file not found (no plugins configured), invalid YAML (log error, keep current running config), partial failures (start what you can).

## Task 7: MCP Tools for Plugin Management

**Files:** Modify `backend/app/mcp/server.py`, `backend/app/mcp/default_settings.json`

New MCP tools exposed to Claude Code:

- `list_plugins(project_id)`: return plugin name, status (running/stopped/error), access_level, transport, health
- `get_plugin_config(project_id, plugin_name)`: return full config (no secrets)
- `enable_plugin(project_id, plugin_name)`: set enabled=true in YAML, trigger startup
- `disable_plugin(project_id, plugin_name)`: set enabled=false, trigger stop

## Task 8: Plugin Settings Frontend

**Files:** Create `frontend/src/pages/ProjectPlugins.jsx` (or component), modify `frontend/src/App.jsx` (router), modify `frontend/src/api/` (API client functions)

New page under project settings: `/projects/:id/plugins`

- List: table with plugin name, transport icon, status indicator (green/red dot), access_level badge, toggle
- Add/Edit form: modal/drawer with fields matching PluginConfig schema
- API functions: `fetchPlugins`, `updatePlugin`, `togglePlugin`
- Follow existing project settings patterns (ProjectSettings, ProjectVariables pages)

## Task 9: Integration Tests

**Files:** Create `backend/tests/test_plugin_manager.py`

- Test YAML parsing/validation (valid config, invalid transport, missing fields)
- Test dummy MCP server: a small Python script started as subprocess that responds to initialize + tools/list with 2 hardcoded tools
- Test end-to-end: PluginManager.start → tools registered on FastMCP → tool call proxied → PluginManager.stop
- Test error cases: unreachable HTTP URL, subprocess crash, timeout
- Test collision: two plugins with same name → error

## Task 10: End-to-End Validation

Manual validation checklist:
- Configure a real MCP server plugin (e.g., mcp-server-mysql, or filesystem MCP)
- Verify tools appear in Claude Code's tool list
- Call a proxied tool and verify correct forwarding
- Toggle plugin off, verify tools disappear
- Crash plugin process, verify error message and auto-restart logic