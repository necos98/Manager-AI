## Fix

Updated `_make_proxy_function` in `backend/app/mcp/plugin_proxy.py` to generate proxy functions with explicit parameter signatures instead of bare `**kwargs`.

**Before:** `**kwargs` proxy → FastMCP registers tool with single `kwargs: str` param → Pydantic rejects actual named args like `query="SELECT..."`.

**After:** `proxy.__signature__` set from `tool.inputSchema` properties → FastMCP sees real params → Pydantic validates correctly.

**Changes:**
- Added `import inspect`
- `_make_proxy_function` now accepts `tool: Tool` parameter
- Builds `inspect.Signature` from `inputSchema["properties"]`, required params → no default, optional → `None` default
- `register_plugin_tools` passes `tool` to `_make_proxy_function`

**Tests:** 137 passed, 1 pre-existing unrelated failure.