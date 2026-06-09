# Implementation Plan: Backend Error Logging System

## Architecture: Hybrid Approach

Custom `logging.Handler` for auto-capture of ALL `logger.error()/logger.exception()` calls (35+ modules, zero modifications) + explicit service for rich-context errors (HTTP request context, pipeline metadata). No external deps beyond stdlib.

## Files to Create

### 1. `backend/app/logging_config.py` — Core logging module

- **`ErrorFileHandler(logging.Handler)`**: Subclass `logging.Handler`. On `emit(record)`:
  - Read `MANAGER_AI_LOG_DIR` env var (fallback: `backend/logs/`)
  - Ensure dir exists via `mkdir(parents=True, exist_ok=True)`
  - Generate filename: `error_YYYYMMDD_HHMMSS[_6CHAR_RANDOM].log` — random suffix when same-second collision detected (check `os.path.exists`)
  - Format: sync/async thread-safe. Use `try/except OSError` around file write. On failure, call `logging.lastResort` (stderr) — never let log write crash app
  - Include in record: timestamp, error type, message, source location (`pathname:lineno`), full traceback (if `record.exc_info`), metadata (PID, process name, logger name)
  - **Request context attachment**: Define a thread-local / contextvar `_request_context` that the explicit service sets. Handler checks it when formatting and includes it if present.
  - **ClientDisconnect filtering**: Add filter to skip records whose exc_info is `ClientDisconnect`, preventing error files for normal client disconnections.

- **`ErrorLoggerService`**: Explicit service class for rich-context logging:
  - `log_exception(exc: Exception, request_context: dict | None = None, metadata: dict | None = None)` — formats and writes using `ErrorFileHandler`'s formatting, but can be called from any catch block
  - `set_request_context(ctx: dict)` / `clear_request_context()` — use `contextvars` for async-safe request context propagation
  - `capture_logger_error()` — decorator/context manager for wrapping background tasks

- **`configure_error_logging()`** — one-shot init function:
  - Creates `ErrorFileHandler`, sets formatter with the spec's format template
  - Attaches to root logger at ERROR level
  - Installs `sys.excepthook` (calls `ErrorLoggerService.log_exception()`)
  - Wraps (does NOT replace) existing asyncio exception handler — chains into the existing `_suppress_windows_accept_noise` handler so both Windows noise suppression and error file logging work
  - Returns the handler instance

### 2. `backend/app/error_format.py` — Log file format template

- Plain-text format builder matching spec requirement:
  ```
  ========================================
  ERROR — {timestamp}
  ========================================
  Type:       {exc_type_name}
  Message:    {message}
  Source:     {pathname}:{lineno}

  --- Request Context ---
  {key}: {value}  (only when present)

  --- Traceback ---
  {full_traceback}

  --- Metadata ---
  PID: {process}
  Logger: {name}
  Process: {processName}
  ```

## Files to Modify

### 3. `backend/app/config.py` — Add log dir setting

- Add `manager_ai_log_dir: str = "backend/logs/"` to `Settings`
- Field validator: resolve relative to project root

### 4. `backend/app/main.py` — Initialize and integrate

- After logging is configured, call `configure_error_logging()` early in lifespan (before `_startup_resolve_secret_key`)
- The existing `_SuppressClientDisconnectFilter` (line 47-58, attached to `mcp.server.streamable_http` logger) stays unchanged. The new `ErrorFileHandler` also gets a ClientDisconnect filter to prevent error log files for normal client disconnections. See logging_config.py.
- Wire exception handlers for sources that are NOT auto-captured by root logger:
  - **`@app.exception_handler(RequestValidationError)`** — FastAPI does NOT log RequestValidationError to root logger. The handler must call `ErrorLoggerService.log_exception()` with request context, then return 422 JSON response as before.
  - **`@app.exception_handler(AppError)`** (existing, line 365-367) — add `ErrorLoggerService.log_exception()` call with request context before returning JSON response. AppError subclasses (NotFoundError 404, InvalidTransitionError 409, ValidationError 422) will be covered here since they inherit AppError.
- ErrorLoggerMiddleware approach:
  - Keep middleware structure but redirect writes to `ErrorLoggerService` instead of raw JSON files. Middleware provides request context that the root logger handler alone cannot capture.
  - Old JSON format (`YYYY-MM-DD.log`) stops; plain-text per-error files replace it.

### 5. `backend/app/middleware/error_logger.py` — Refactor

- Remove `_write_error()` / `_log_file_path()` — no more direct file writes
- Remove JSON-specific imports (`json`, `traceback`, `date_str`, `iso_now`)
- Update `ErrorLoggerMiddleware.dispatch()`:
  - On exception, call `ErrorLoggerService.log_exception()` with request context (method, path, query, client)
  - Still re-raises for FastAPI exception handler chain

### 6. `backend/app/services/terminal_operations.py` — Error source coverage

- Around PTY creation (`create_terminal`), wrap in try/except that calls `ErrorLoggerService().log_exception()`
- Around WebSocket handlers, catch and log before close

### 7. `backend/app/services/pipeline_run/_execution.py` — Error source coverage

- Wrap pipeline step execution in try/except that logs via `ErrorLoggerService`

### 8. `backend/app/mcp/plugin_manager.py` / `backend/app/mcp/plugin_client.py` — Error source coverage

- Plugin connection failures and tool call errors already use `logger.error()` — auto-captured by `ErrorFileHandler`. No changes needed unless spec requires explicit request context.

### 9. `backend/app/services/file_reader.py` — Error source coverage

- File processing errors already use `logger.exception()` — auto-captured.

## Error Source Coverage Map

| Source | Capture Method | File Changes |
|--------|---------------|-------------|
| HTTP errors | `ErrorLoggerMiddleware` → `ErrorLoggerService.log_exception()` | `middleware/error_logger.py` |
| Validation errors (422) | `@app.exception_handler(RequestValidationError)` → `ErrorLoggerService.log_exception()` | `main.py` |
| Database errors | `ErrorFileHandler` auto-capture (SQLAlchemy already logs at ERROR) | None needed |
| MCP plugin errors | `ErrorFileHandler` auto-capture (existing `logger.error()` calls) | None needed |
| Terminal service errors | Explicit `ErrorLoggerService.log_exception()` wraps | `services/terminal_operations.py` |
| Background tasks | Explicit `ErrorLoggerService.log_exception()` wraps | `services/pipeline_run/_execution.py` |
| Uncaught (sync) | `sys.excepthook` | `main.py` (via logging_config) |
| Uncaught (async) | Chained asyncio exception handler | `main.py` (via logging_config) |
| AppError hierarchy (404, 409, 422) | Existing `@app.exception_handler(AppError)` → add `ErrorLoggerService.log_exception()` | `main.py` |

## AC Mapping

| AC | How satisfied |
|----|-------------|
| AC1 | `sys.excepthook` + chained asyncio exception handler + root logger `ErrorFileHandler` |
| AC2 | `ErrorLoggerMiddleware` → `ErrorLoggerService.log_exception()` with request context |
| AC3 | `@app.exception_handler(RequestValidationError)` → `ErrorLoggerService.log_exception()` |
| AC4 | `ErrorFileHandler` auto-captures SQLAlchemy `logger.error()` |
| AC5 | `ErrorFileHandler` auto-captures existing `logger.error()` in plugin_client/plugin_manager |
| AC6 | Explicit try/except in terminal_operations.py |
| AC7 | Explicit try/except in pipeline_run/_execution.py |
| AC8 | Random suffix via `os.path.exists` check in `ErrorFileHandler.emit()` |
| AC9 | `try/except OSError` guards in `ErrorFileHandler.emit()` |
| AC10 | No changes to console logging — handler only writes files, doesn't touch stderr |
| AC11 | ErrorLoggerMiddleware refactored to use ErrorLoggerService — HTTP error coverage maintained. Old JSON format stops but all HTTP error types are logged via ErrorLoggerService in the new plain-text format. |
| AC12 | `MANAGER_AI_LOG_DIR` env var in `ErrorFileHandler` with fallback to config default |

## Key Design Decisions

1. **`contextvars` for request context** (not thread-local): Async-safe via Python 3.7+ `contextvars`. Middleware sets it before request, clears after. `ErrorFileHandler` reads it when formatting.

2. **Random suffix strategy**: Use `os.urandom(3).hex()` (6 chars) appended after `_` when the base filename already exists. Low collision probability, no locking needed.

3. **Middleware transition**: The ErrorLoggerMiddleware stays in place as the HTTP error interceptor but its file writes go through ErrorLoggerService instead of raw JSON. Old `YYYY-MM-DD.log` JSON files stop; new `error_*.log` plain-text files replace them. No data loss — all error types still captured.

4. **`configure_error_logging()` called once**: In `main.py` lifespan, after `logging` is set up but before project loading. Ensures all startup errors are also captured.

5. **Asyncio exception handler chaining**: The lifespan already sets `set_exception_handler(_suppress_windows_accept_noise)`. The new handler wraps the existing one: on exception, it first calls `ErrorLoggerService.log_exception()`, then delegates to the existing `_suppress_windows_accept_noise` handler. No handler replacement — only wrapping.

6. **ClientDisconnect suppression**: The existing `_SuppressClientDisconnectFilter` on `mcp.server.streamable_http` logger stays. The new `ErrorFileHandler` gets its own ClientDisconnect filter to prevent writing error files for normal client disconnections.

## Implementation Order

1. `backend/app/config.py` — add `manager_ai_log_dir`
2. `backend/app/error_format.py` — log file format builder
3. `backend/app/logging_config.py` — `ErrorFileHandler`, `ErrorLoggerService`, `configure_error_logging()`
4. `backend/app/middleware/error_logger.py` — refactor to use new service
5. `backend/app/main.py` — wire everything: init, global hooks, exception handlers, middleware update
6. `backend/app/services/terminal_operations.py` — add explicit error logging
7. `backend/app/services/pipeline_run/_execution.py` — add explicit error logging