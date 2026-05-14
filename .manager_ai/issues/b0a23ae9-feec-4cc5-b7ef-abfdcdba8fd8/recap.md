## Recap

Added tool discovery information to plugin gateway descriptions so LLM agents can see available plugin tools and their parameters without brute-force guessing.

### Changes
1. **`plugin_proxy.py`** — Added `build_gateway_description()` that formats a rich description from plugin Tool objects (name, description, inputSchema properties with types and required/optional). Added `_update_tool_description()` helper to update tool descriptions on FastMCP at runtime. Modified `register_plugin_gateway()` to update its own description after first `ensure_connected()` call.

2. **`plugin_manager.py`** — Modified `_start_one()` and `restart_plugin()` background pre-connect tasks to update the gateway tool description after successful plugin connection.

3. **`tests/test_plugin_descriptions.py`** — 5 unit tests covering: no tools, tools with params, optional params, tool without description, mixed access levels. All pass.

### Result
Gateway tool description changes from:
`[mysql plugin — read_only] MySQL Database`

To:
```
[mysql plugin — read_only] MySQL Database

Available tools:
- execute_query: Execute SQL query. Parameters: query (string, required) - The SQL query
- list_tables: List all tables. Parameters: (none)
```

LLM agents now see exactly what tools are available and what parameters each expects, eliminating brute-force guesswork.