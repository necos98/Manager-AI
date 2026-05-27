# Taskbar Icon Fix — Implementation Plan

**Goal:** Fix custom window icon not appearing in taskbar/Alt+Tab/title bar by fixing retry logic, adding AppUserModelID, and surfacing errors.

**Architecture:** Two-file change. `desktop_icon.py` gains retry loop + logging + AppUserModelID function. `start.py` calls AppUserModelID before window creation and fixes the `icon_set` flag timing bug.

**Tech Stack:** Python 3.12, ctypes (Win32 API), pywebview 5.0

---

## Summary

Three concrete changes:
1. Add `set_app_user_model_id()` to `desktop_icon.py` — sets Windows AppUserModelID so taskbar treats app as standalone, not `python.exe`
2. Add retry loop + stderr logging to `set_app_window_icon()` — retries FindWindowW up to 5 times with 300ms delay
3. Fix `start.py`: call AppUserModelID before window creation, fix `icon_set` flag position
