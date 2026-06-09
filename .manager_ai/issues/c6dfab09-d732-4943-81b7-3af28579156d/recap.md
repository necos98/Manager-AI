## Recap — Backend Error Logging System

### What was built
Per-error plain-text logging system in `backend/logs/`. Each error → one `error_YYYYMMDD_HHMMSS[_SUFFIX].log` file with timestamp, type, source, traceback, request context, metadata.

### Files created
- `backend/app/error_format.py` — plain-text log format builder
- `backend/app/logging_config.py` — ErrorFileHandler (auto-capture), ErrorLoggerService (rich-context), configure_error_logging()

### Files modified
- `backend/app/config.py` — added `manager_ai_log_dir` setting
- `backend/app/middleware/error_logger.py` — refactored to use ErrorLoggerService
- `backend/app/main.py` — wired init, validation/AppError handlers
- `backend/app/services/terminal_operations.py` — error logging around PTY
- `backend/app/services/pipeline_run/_execution.py` — error logging around step execution

### Test results
660/720 passed, 1 regression found:
- `main.py:394` — `JSONResponse(content={"detail": exc.errors()})` fails when Pydantic errors contain non-serializable objects (~38 tests affected). Fix needed: sanitize before JSON serialization.

### Pre-existing failures (not from this issue)
- MCP `question_store` attribute error (11 tests)
- DB backup mock issue (2 tests)
- Settings count mismatch (2 tests)