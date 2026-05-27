## Root Cause

Two bugs prevented the custom window icon from appearing:

1. **Premature `icon_set` flag**: In `start.py` poll_worker, `icon_set = True` was set BEFORE calling `set_app_window_icon()`. If `FindWindowW` returned 0 on the first iteration (window not yet materialized), the flag stayed True forever — icon never retried. One-shot timing failure became permanent.

2. **Missing AppUserModelID**: Without `SetCurrentProcessExplicitAppUserModelID`, Windows taskbar grouped the app with `python.exe` and used the Python icon instead of the custom logo.

## Changes

### `backend/app/desktop_icon.py`
- Added `set_app_user_model_id()` — calls `SetCurrentProcessExplicitAppUserModelID("ManagerAI.ManagerAI")` via ctypes/shell32. Must be called before window creation.
- Rewrote `set_app_window_icon()`:
  - Retry loop: 5 attempts with 300ms delay for FindWindowW
  - Stderr logging on each failure (missing .ico, window not found, LoadImageW failures)
  - Removed bare try/except — errors now surfaced explicitly

### `start.py`
- Call `set_app_user_model_id()` in `main()` before `webview.create_window()`
- Fixed `icon_set` flag: now set to True only after `set_app_window_icon()` returns True
- Kept defensive `except Exception: pass` since `desktop_icon.py` handles its own logging

## Verification

- Syntax check: both files pass `py_compile`
- Import check: both functions importable from `app.desktop_icon`
- Manual test needed: run `python start.py`, verify icon appears in taskbar, Alt+Tab, and title bar within 1.5s of window appearing