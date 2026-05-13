# MCP Plugin System: Feasibility Analysis & Design

## Overview

Expand Manager AI with per-project MCP plugins. Any MCP-compatible external server (database, API, file system) can be attached as a plugin. Tools from all plugins are exposed through the single Manager AI MCP endpoint at `/mcp` with prefixed names (e.g., `mysql__query`).

## Plugin Configuration

Per-project file `.manager_ai/plugins.yaml`:

```yaml
plugins:
  mysql:
    enabled: true
    name: "MySQL (produzione)"
    transport: stdio
    command: "uvx"
    args: ["mcp-server-mysql"]
    env:
      MYSQL_HOST: "${MYSQL_HOST}"
      MYSQL_PORT: "3306"
    access_level: read_only
  slack:
    enabled: false
    transport: http
    url: "https://mcp-slack.internal/sse"
    access_level: read_write
```

- `access_level`: declarative — `read_only`, `read_write`, `admin`. Injected into tool descriptions so the LLM understands the constraint. Actual enforcement is at the credential level (limited DB user).
- Real credentials (passwords, tokens) stay in the encrypted Fernet vault (`set_credential`/`get_credential`). The YAML references env vars that get resolved at plugin startup.
- Managed via frontend UI that writes the YAML file, OR edited directly. YAML is source of truth.

## Architecture: Aggregator Proxy

Single MCP endpoint at `/mcp`. Main server connects to each plugin at startup, discovers its tools, and registers proxy tools with `{plugin}__` prefix.

### Startup Flow

1. Lifespan startup → `PluginManager` reads `.manager_ai/plugins.yaml`
2. For each enabled plugin:
   - **Stdio transport**: spawn subprocess (e.g., `uvx mcp-server-mysql`)
   - **HTTP transport**: open SSE connection
   - Perform MCP `initialize` handshake
   - Call `tools/list` to discover tools
3. For each discovered tool, create async proxy function named `{plugin}__{tool}`
4. Register proxy in the main FastMCP instance
5. If a plugin fails startup → log warning, emit notification, plugin stays disabled. Other plugins unaffected.

### Runtime Architecture

```
FastAPI app
  /mcp (single endpoint)
    FastMCP (Manager AI)
      Built-in tools (issue, memory, files, credentials, ...)
      PluginProxy (mysql):
        mysql__list_tables → forward via MCP client
        mysql__query        → forward via MCP client
      PluginManager (lifespan):
        Read plugins.yaml
        Spawn/connect plugins
        Discover tools, register proxies
        Health check / restart on crash
```

### Tool Proxy Pattern

Each plugin tool gets an auto-generated async proxy:

```python
async def mysql__query(sql: str) -> dict:
    return await plugin_client.call_tool("query", {"sql": sql})
```

The proxy:
- Prefixes plugin name to avoid collisions
- Injects `[mysql plugin — read_only]` into tool description
- Validates parameters via MCP tool schema
- Forwards call to plugin via MCP client session
- Returns raw result

## Per-Project Isolation

Each project has its own `.manager_ai/plugins.yaml`. Projects A and B can use the same plugin type (mysql) with different connection parameters. Plugin processes are spawned per-project, fully isolated.

## Frontend UI

New section in project settings: **MCP Plugins**
- List plugins with: name, transport type, enabled/disabled toggle, `access_level` badge, health status
- "Add Plugin" form:
  - Name, transport (stdio/HTTP), command or URL, env vars
  - Credential picker from existing vault (no plaintext secrets in YAML)
- Writes `.manager_ai/plugins.yaml`. Backend picks up changes via existing `manager_ai_watcher` watchdog.

## Security

| Layer | Mechanism |
|-------|-----------|
| `access_level` in tool description | LLM sees constraint (e.g., "MySQL plugin — read_only") |
| Credentials | Fernet-encrypted vault, never in YAML |
| DB-level read-only | DBA creates user with SELECT-only grants; password in vault |
| Process isolation | Plugin runs in separate subprocess; crash doesn't affect Manager AI |

## Error Handling

- **Plugin startup fail**: logged, notification emitted, plugin stays disabled. Other plugins continue.
- **Plugin crash at runtime**: proxy returns `{"error": "Plugin mysql unreachable"}`. PluginManager retries startup (max 3 in 60s, then cooldown).
- **Plugin slow/timed out**: configurable per-call timeout (default 30s). Does not block other tools.
- **Tool name collision**: `{plugin}__` prefix prevents collisions. Plugin names must be unique within a project.

## Testing Strategy

- **Unit**: PluginManager YAML parsing, config validation, env var resolution from vault
- **Integration**: Dummy MCP subprocess exposing 2-3 tools; verify discovery, proxying, timeout, crash recovery
- **E2E**: Test project with mysql read-only plugin pointing to test DB; verify Claude Code sees and can call proxied tools

## Technical Feasibility

| Element | Status |
|---------|--------|
| MCP Python SDK client | `mcp` package 1.9.2+ has `ClientSession` for connecting to servers |
| Dynamic tool registration | FastMCP supports programmatic function registration at runtime |
| Subprocess management | `asyncio.create_subprocess_exec` — already used for PTY terminals |
| Per-project YAML files | Established pattern — issues.yaml, memories.yaml exist |
| Watchdog reload | Already active — `manager_ai_watcher` monitors `.manager_ai/` |
| Credential vault | Already exists — Fernet-encrypted with `set_credential`/`get_credential` |

**Verdict: Feasible.** Main complexity is MCP client handshake and dynamic tool proxying. Rest builds on established codebase patterns. Estimated effort: ~500-700 lines backend (PluginManager + proxy), ~300-400 lines frontend (plugin settings page).