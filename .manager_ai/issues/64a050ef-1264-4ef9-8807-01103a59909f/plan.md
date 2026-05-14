# Implementation Plan: Fix MySQL plugin kwargs → explicit parameters

## Files

- **Modify:** `backend/app/mcp/plugin_proxy.py`

## Implementation

### Step 1: Add `import inspect` at top of file

```python
import inspect
```

### Step 2: Update `_make_proxy_function` signature to accept `tool`

Change:
```python
def _make_proxy_function(
    proxy_name: str,
    tool_name: str,
    client: PluginClient,
) -> Any:
```

To:
```python
def _make_proxy_function(
    proxy_name: str,
    tool_name: str,
    client: PluginClient,
    tool: Tool,
) -> Any:
```

### Step 3: Build explicit signature from tool.inputSchema

Replace the body of `_make_proxy_function`:

```python
    # Build explicit parameter signature from the tool's inputSchema
    props = tool.inputSchema.get("properties", {})
    required = set(tool.inputSchema.get("required", []))

    params = []
    for name in props:
        default = inspect.Parameter.empty if name in required else None
        params.append(
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=default)
        )

    async def proxy(**kwargs):
        return await client.call_tool(tool_name, kwargs)

    proxy.__signature__ = inspect.Signature(params)
    proxy.__name__ = proxy_name
    return proxy
```

### Step 4: Update `register_plugin_tools` to pass `tool`

Change:
```python
fn = _make_proxy_function(proxy_name, tool.name, client)
```

To:
```python
fn = _make_proxy_function(proxy_name, tool.name, client, tool)
```

### Step 5: Restart and verify

```bash
python start.py
```

Enable MySQL plugin, call `mysql__list_tables` (no params needed) — should succeed without Pydantic validation error.