---
id: c5b72862-9cff-4d52-ad4c-37fcfce6a9cb
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: 'Error Logger: no double logging for AppError'
parent_id: null
created_at: '2026-06-09T14:58:29.027386+00:00'
updated_at: '2026-06-09T14:58:29.027386+00:00'
links: []
---
The Developer documented intentional "double logging for AppError" as defense-in-depth. This assumption is WRONG. In FastAPI/Starlette, `@app.exception_handler()` handles AppError INSIDE the middleware's `call_next`, so the middleware never sees AppError as an exception — it sees the Response. Only the exception handler's explicit ErrorLoggerService.log_exception() fires. Result: 1 log file per error, not 2. This applies to all registered exception handlers (AppError, RequestValidationError). The code is correct; the documented reasoning was inaccurate. No fix needed.