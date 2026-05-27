# Spec: Suppress ClientDisconnect ERROR logs in MCP streamable HTTP handler

## Problem

Console shows ERROR-level traceback when MCP client disconnects mid-POST request:

```
ERROR    Error handling POST request    streamable_http.py:526
```

Root cause: `mcp.server.streamable_http._handle_post_request` calls `request.body()` (line 337). When client disconnects before sending full body, Starlette raises `ClientDisconnect`. The method's catch-all `except Exception` (line 525) catches it and logs at ERROR level with full traceback via `logger.exception`. Client disconnect is normal behavior — not an error.

## Fix: Three-layer defense

### Layer 1 — Logging filter (primary)

Add `SuppressClientDisconnectFilter` to the `mcp.server.streamable_http` logger. The filter inspects `record.exc_info` and returns `False` (suppress) when the exception is `ClientDisconnect`. This stops the noisy ERROR at its source without changing MCP library behavior.

File: `backend/app/main.py` (startup section)

### Layer 2 — Exception handler on _streamable_app

After `_streamable_app` creation, add an exception handler for `ClientDisconnect`. Catches any `ClientDisconnect` that escapes the MCP handler (e.g., from failed error-response send after disconnect). Logs at DEBUG, returns empty 499 response.

File: `backend/app/main.py`

### Layer 3 — ErrorLoggerMiddleware

Catch `ClientDisconnect` before the generic `except Exception`, log at DEBUG level, return 499. Prevents writing spurious entries to the daily error log file.

File: `backend/app/middleware/error_logger.py`

## Files to change

- `backend/app/main.py` — Layer 1 (logging filter) + Layer 2 (exception handler)
- `backend/app/middleware/error_logger.py` — Layer 3 (early catch in middleware)

## Testing

1. Start Manager AI, send truncated POST to `/mcp` endpoint (simulate disconnect)
2. Verify no ERROR-level log from `streamable_http.py`
3. Verify `ClientDisconnect` appears at DEBUG level only
4. Verify daily error log file does NOT contain `ClientDisconnect` entries