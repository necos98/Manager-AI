# Implementation Plan

**Goal:** Suppress noisy ERROR-level `ClientDisconnect` logs from MCP streamable HTTP handler.

**Approach:** Three-layer defense: logging filter on MCP logger (primary fix), exception handler on `_streamable_app`, early catch in `ErrorLoggerMiddleware`.

## Architecture

All changes are additive — no existing behavior modified. Layer 1 (logging filter) stops the ERROR at source by filtering log records where `exc_info` contains `ClientDisconnect`. Layer 2 (Starlette exception handler) catches any `ClientDisconnect` escaping the MCP handler. Layer 3 (`ErrorLoggerMiddleware`) prevents writing `ClientDisconnect` to daily error log files.

## Files
- `backend/app/main.py` — logging filter setup + exception handler
- `backend/app/middleware/error_logger.py` — early return on `ClientDisconnect`
