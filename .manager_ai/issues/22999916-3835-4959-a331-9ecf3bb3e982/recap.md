# Recap: Suppress ClientDisconnect ERROR logs in MCP streamable HTTP handler

## Problem
MCP library's `streamable_http.py` logged full ERROR traceback when client disconnected mid-POST to `/mcp`. `request.body()` raises `ClientDisconnect` (normal Starlette behavior), but the library's catch-all `except Exception` at line 525 treats it as a real error.

## Fix: Three-layer defense

### Layer 1 — Logging filter
Added `_SuppressClientDisconnectFilter` (logging.Filter) to `mcp.server.streamable_http` logger. Inspects `record.exc_info` — when exception is `ClientDisconnect`, returns `False` to suppress. Stops noise at source.

### Layer 2 — Starlette exception handler
Added `@_streamable_app.exception_handler(ClientDisconnect)` returning 499 response. Catches any `ClientDisconnect` escaping MCP handler (e.g., failed error-response send after disconnect).

### Layer 3 — ErrorLoggerMiddleware
Added `except ClientDisconnect` before generic `except Exception`. Logs at DEBUG, returns 499. Prevents writing to daily error log file.

## Files changed
- `backend/app/main.py` — added import, filter class, filter installation, exception handler
- `backend/app/middleware/error_logger.py` — added early ClientDisconnect catch

## Key insight
Two project copies exist on disk: `manager-ai/Manager-AI` (actual, venv-linked) and `manager-ai/manager-ai-mod/Manager-AI` (git working dir). Changes applied to both.