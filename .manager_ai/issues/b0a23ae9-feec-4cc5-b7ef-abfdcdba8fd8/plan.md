# Implementation Plan: Plugin Gateway Tool Descriptions

## Files

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/mcp/plugin_proxy.py` | Modify | Add `build_gateway_description()`, `_update_tool_description()`; modify `register_plugin_gateway()` |
| `backend/app/mcp/plugin_manager.py` | Modify | Call description update after pre-connect and reconnect |
| `backend/tests/test_plugin_descriptions.py` | Create | Unit tests for `build_gateway_description` |

---

### Task 1: Add `build_gateway_description()` to plugin_proxy.py

**File:** `backend/app/mcp/plugin_proxy.py`

Add a function that builds a rich description string from a plugin's discovered Tool objects:

```python
def build_gateway_description(
    plugin_key: str,
    access_level: AccessLevel,
    plugin_description: str,
    tools: list,
) -> str:
    """Build gateway tool description with available tools and their parameters."""
    access_tag = f"[{plugin_key} plugin — {access_level.value}]"
    base = f"{access_tag} {plugin_description}".strip()
    
    if not tools:
        return base
    
    lines = [base, "", "Available tools:"]
    for tool in tools:
        name = tool.name if hasattr(tool, "name") else tool.get("name", "?")
        desc = (tool.description if hasattr(tool, "description") else tool.get("description", "")) or ""
        
        schema = (tool.inputSchema if hasattr(tool, "inputSchema") else tool.get("inputSchema", {})) or {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        
        if properties:
            param_parts = []
            for pname, pinfo in properties.items():
                ptype = pinfo.get("type", "any") if isinstance(pinfo, dict) else "any"
                req = "required" if pname in required else "optional"
                pdesc = (pinfo.get("description", "") if isinstance(pinfo, dict) else "")
                param_str = f"{pname} ({ptype}, {req})"
                if pdesc:
                    param_str += f" - {pdesc}"
                param_parts.append(param_str)
            params = "; ".join(param_parts)
        else:
            params = "(none)"
        
        tool_line = f"- {name}"
        if desc:
            tool_line += f": {desc}"
        tool_line += f". Parameters: {params}"
        lines.append(tool_line)
    
    return "\n".join(lines)
```

Also add a helper to update a tool's description on FastMCP:

```python
def _update_tool_description(mcp: FastMCP, tool_name: str, new_description: str) -> None:
    """Update the description of an already-registered tool on FastMCP."""
    tool_mgr = mcp._tool_manager
    if tool_name in tool_mgr._tools:
        tool_mgr._tools[tool_name].description = new_description
```

- [ ] Add `build_gateway_description()` function
- [ ] Add `_update_tool_description()` helper

---

### Task 2: Update gateway description from inside proxy function

**File:** `backend/app/mcp/plugin_proxy.py` — `register_plugin_gateway()`

Modify the `_gateway` proxy to update its own description after first connect. After `ensure_connected()`, `client._tools` is populated. Build the enriched description and apply it.

Change:
```python
async def _gateway(tool_name: str, arguments: Optional[dict] = None) -> dict:
    try:
        await client.ensure_connected()
    except BaseException as exc:
        ...
```

To:
```python
async def _gateway(tool_name: str, arguments: Optional[dict] = None) -> dict:
    try:
        await client.ensure_connected()
    except BaseException as exc:
        ...
    # Update description with discovered tools on first connect
    try:
        if client._tools:
            new_desc = build_gateway_description(
                plugin_key, access_level, plugin_description, client._tools
            )
            _update_tool_description(mcp, proxy_name, new_desc)
    except Exception:
        pass  # best-effort, not critical
```

- [ ] Modify `_gateway` to call `build_gateway_description` + `_update_tool_description` after `ensure_connected()`

---

### Task 3: Update gateway description after background pre-connect

**File:** `backend/app/mcp/plugin_manager.py` — `_start_one()`

After `client.connect()` succeeds in the background pre-connect task, update the gateway description on `mcp_instance`.

Change the `_pre_connect` inner function from:
```python
async def _pre_connect():
    try:
        await client.connect()
    except BaseException:
        logger.debug(...)
```

To:
```python
async def _pre_connect():
    try:
        await client.connect()
        if client._tools:
            from app.mcp.plugin_proxy import build_gateway_description, _update_tool_description
            proxy_name = f"{key}__call"
            new_desc = build_gateway_description(
                key, cfg.access_level, (cfg.name or key), client._tools
            )
            _update_tool_description(mcp_instance, proxy_name, new_desc)
    except BaseException:
        logger.debug(...)
```

- [ ] Modify `_start_one()` pre-connect to update description after connect
- [ ] Same for `restart_plugin()` pre-connect

---

### Task 4: Tests

**File:** `backend/tests/test_plugin_descriptions.py`

```python
import pytest
from app.mcp.plugin_proxy import build_gateway_description
from app.mcp.plugin_config import AccessLevel


class FakeTool:
    def __init__(self, name, description="", input_schema=None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema or {}


def test_build_description_no_tools():
    desc = build_gateway_description("test", AccessLevel.READ_ONLY, "Test plugin", [])
    assert "Available tools:" not in desc
    assert "[test plugin — read_only] Test plugin" == desc


def test_build_description_with_tools():
    tools = [
        FakeTool(
            "execute_query",
            "Execute SQL query",
            {
                "properties": {
                    "query": {"type": "string", "description": "The SQL query"}
                },
                "required": ["query"],
            },
        ),
        FakeTool("list_tables", "List all tables", {}),
    ]
    desc = build_gateway_description("mysql", AccessLevel.READ_ONLY, "MySQL Database", tools)
    
    assert "Available tools:" in desc
    assert "execute_query" in desc
    assert "query (string, required) - The SQL query" in desc
    assert "list_tables" in desc
    assert "Parameters: (none)" in desc


def test_build_description_optional_params():
    tools = [
        FakeTool(
            "search",
            "Search records",
            {
                "properties": {
                    "term": {"type": "string", "description": "Search term"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["term"],
            },
        ),
    ]
    desc = build_gateway_description("db", AccessLevel.READ_ONLY, "DB", tools)
    
    assert "term (string, required) - Search term" in desc
    assert "limit (integer, optional) - Max results" in desc
```

- [ ] Write unit tests for `build_gateway_description`
- [ ] Run tests: `cd backend && python -m pytest tests/test_plugin_descriptions.py -v`
- [ ] Verify all pass
