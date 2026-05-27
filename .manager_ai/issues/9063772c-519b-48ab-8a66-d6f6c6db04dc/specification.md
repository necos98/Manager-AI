# Taskbar Icon Not Showing — Specification

## Problem

Manager AI window shows default Python icon instead of custom logo in:
- Windows taskbar
- Alt+Tab switcher  
- Window title bar

## Root Cause

Two bugs in icon-setting code:

1. **Premature flag**: `poll_worker` sets `icon_set = True` **before** `set_app_window_icon()` call. If `FindWindowW` returns 0 on first iteration (window not yet materialized), flag stays True forever — icon never retried. One-shot failure becomes permanent.

2. **Silent error swallowing**: Bare `except Exception: pass` in poll_worker + no logging in `desktop_icon.py`. Any failure is invisible — no way to detect or diagnose.

3. **Missing AppUserModelID**: Windows taskbar groups by process executable. Without `SetCurrentProcessExplicitAppUserModelID`, the app inherits `python.exe`'s identity and icon.

## Fix

### `backend/app/desktop_icon.py`

- **New**: `set_app_user_model_id()` — calls `SetCurrentProcessExplicitAppUserModelID("ManagerAI.ManagerAI")` via ctypes. Must be called before `webview.create_window()`.
- **Modified**: `set_app_window_icon()` — add retry loop (5 attempts, 300ms delay). Print warnings to stderr on each `FindWindowW` / `LoadImageW` failure. Return bool unchanged.

### `start.py`

- Call `set_app_user_model_id()` in `main()` before `webview.create_window()`.
- Move `icon_set = True` inside try block, only after `set_app_window_icon()` returns True.
- Keep defensive `except Exception: pass` — but `set_app_window_icon` now logs its own failures.

## Testing

- Manual: Run `python start.py`, verify custom icon appears in taskbar, Alt+Tab, and title bar within 1.5 seconds of window appearing.
- Verify stderr shows retry count if window creation is slow.
- Edge: Delete `logo.ico` — app starts normally, clear error message printed.