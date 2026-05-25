# Suppress Plugin Connection Error Stack Traces

## Problem
When an MCP plugin (e.g., MySQL) fails to connect, the console shows full Python stack traces. Users want only: `Plugin mysql connect failed`.

## Root Cause
`plugin_client.py` uses `logger.exception()` (≡ `logger.error(exc_info=True)`) in 4 locations, which always includes the traceback. `plugin_manager.py` uses `traceback.format_exc()` in one location.

## Solution
Replace `logger.exception()` with `logger.error()` for user-facing messages. Add separate `logger.debug(exc_info=True)` so full tracebacks remain accessible when `LOG_LEVEL=DEBUG`.

## Files Changed
- **`backend/app/mcp/plugin_client.py`**: lines 177, 197, 250, 258 — `logger.exception()` → `logger.error()` + `logger.debug(exc_info=True)`
- **`backend/app/mcp/plugin_manager.py`**: line 118 — remove `traceback.format_exc()`, log clean error only

## Constraints
- Console output must be: `Plugin <name> connect failed` (no traceback)
- Full traceback available at DEBUG log level
- No behavior change to error handling or retry logic
- All plugin types affected (stdio, HTTP/SSE)
