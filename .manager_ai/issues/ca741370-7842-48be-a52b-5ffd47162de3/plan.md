# Suppress Plugin Connection Error Stack Traces — Implementation Plan

**Goal:** Replace `logger.exception()` with `logger.error()` + `logger.debug(exc_info=True)` in plugin connection error paths so console output is clean by default but full tracebacks remain available at DEBUG level.

**Architecture:** Two-file change. `plugin_client.py` handles low-level connect failures; `plugin_manager.py` handles gateway registration failures. Both currently emit full tracebacks to console — switch to clean `logger.error()` with optional `logger.debug(exc_info=True)`.

**Tech Stack:** Python logging (stdlib), no new dependencies.

---

## Task 1: Fix plugin_client.py — suppress stack traces in connect errors

**Files:**
- Modify: `backend/app/mcp/plugin_client.py:177,197,250,258`

Change 4 `logger.exception()` calls to `logger.error()` + `logger.debug(exc_info=True)`:
- Line 177: `connect()` — `logger.exception("Plugin %s connect failed", ...)` 
- Line 197: `_connect_stdio()` — `logger.exception("Plugin %s __aenter__ failed", ...)`
- Line 250: `_connect_http()` — `logger.exception("Plugin %s SSE __aenter__ failed", ...)`
- Line 258: `_connect_http()` — `logger.exception("Plugin %s SSE _init_session failed", ...)`

## Task 2: Fix plugin_manager.py — remove traceback.format_exc()

**Files:**
- Modify: `backend/app/mcp/plugin_manager.py:118`

Line 118 currently: `logger.error("Plugin %s (project %s) gateway registration failed: %s\n%s", key, project_id, error_msg, traceback.format_exc())`
Change to: `logger.error("Plugin %s (project %s) gateway registration failed: %s", key, project_id, error_msg)` + `logger.debug("Plugin %s gateway registration traceback", exc_info=True)`
Also remove unused `import traceback` (line 5).

## Task 3: Verify — no regressions, clean console output

Run backend tests, check that `logger.exception` and `traceback.format_exc` are gone from plugin files.
