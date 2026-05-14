# Plugin Gateway Tool Description — Specification

## Problem

When an LLM agent uses an MCP plugin via the gateway tool (`{plugin}__call`), it cannot discover:

1. **Which tools** the plugin exposes (e.g., `execute_query`, `list_tables`)
2. **What parameters** each tool accepts (e.g., `query` not `sql`)

The gateway description currently shows only: `[mysql plugin — read_only] MySQL Database`

The LLM must brute-force guess both `tool_name` and `arguments` keys, costing many failed calls.

**Root cause**: `register_plugin_gateway()` builds the description BEFORE the plugin connects. At registration time, the tool list and schemas are unknown. After background pre-connect, the discovered tools are stored on `PluginClient._tools` but never injected into the gateway tool description on FastMCP.

## Design

Update the gateway tool description **after** plugin connection, injecting the full list of available tools with their parameter names, types, and required status.

### Description Format

```
[mysql plugin — read_only] MySQL Database

Available tools:
- execute_query: Execute a SQL query. Parameters: query (string, required) - The SQL query to execute; params (array, optional) - Query parameters
- list_tables: List all tables. Parameters: (none)
- describe_table: Describe a table structure. Parameters: table (string, required) - Table name
```

### How descriptions are built from inputSchema

For each plugin tool, extract from `inputSchema`:
- Tool `name` and `description`
- `properties` → parameter name + type, marked required or optional
- Format: `{name} ({type}, {required|optional}) - {description}`

If a tool has no parameters, show: `Parameters: (none)`

If a tool has no description, omit the `- {description}` suffix.

### Update Timing

1. **On background pre-connect** (`_start_one`): After `client.connect()` succeeds, build the enriched description and update the tool on `mcp_instance._tool_manager._tools`
2. **On lazy connect** (`ensure_connected` inside gateway `_proxy`): After first connect, update the description similarly
3. **On reconnect** (`restart_plugin`): Same as #1

### Fallback

If pre-connect fails, description stays as the current base format. The first actual gateway call triggers `ensure_connected()`, which connects and then updates the description. Subsequent calls see the enriched version.

## Implementation Plan

### File changes

1. **`backend/app/mcp/plugin_proxy.py`**
   - Add `build_gateway_description(plugin_key, access_level, plugin_description, tools)` — formats the rich description string from a tool list
   - Add `update_gateway_tool_description(mcp, proxy_name, description)` — updates the description of an already-registered tool on FastMCP
   - Modify `register_plugin_gateway()` to accept optional `tools` param for initial enriched description, or keep base and rely on update

2. **`backend/app/mcp/plugin_manager.py`**
   - In `_start_one()`: After background pre-connect succeeds, call `build_gateway_description` + `update_gateway_tool_description`
   - In `restart_plugin()`: Same after reconnect
   - In `_gateway()` proxy function (inside `register_plugin_gateway`): After `ensure_connected()`, update description on first connect from inside the proxy

3. **`backend/app/mcp/plugin_client.py`**
   - No changes needed. `self._tools` already populated with full `Tool` objects (name, description, inputSchema) after `connect()`.

### Edge cases
- Plugin with 0 tools (unlikely but handle gracefully)
- Tool names that are not valid Python identifiers (already handled in `_make_proxy_function`)
- Very long descriptions (keep reasonable, truncate parameter descriptions to ~200 chars)
- Plugin connection never succeeds → description stays base format, not worse than current state
