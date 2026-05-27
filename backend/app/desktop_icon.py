"""Set the Windows window icon and AppUserModelID via Win32 API (ctypes). No extra dependencies."""

import ctypes
import sys
import time
from pathlib import Path


def set_app_user_model_id(app_id: str = "ManagerAI.ManagerAI") -> bool:
    """Set the AppUserModelID so Windows taskbar treats this as a standalone app.

    Must be called BEFORE creating any windows for full effect.
    On non-Windows platforms this is a no-op returning False.
    """
    if sys.platform != "win32":
        return False
    try:
        shell32 = ctypes.windll.shell32
        result = shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return result == 0  # S_OK
    except Exception:
        return False


def set_app_window_icon(window_title: str, ico_path: str) -> bool:

    if sys.platform != "win32":
        return False

    if not Path(ico_path).exists():
        print(f"[!] set_app_window_icon: icon file not found: {ico_path}", file=sys.stderr)
        return False

    user32 = ctypes.windll.user32

    WM_SETICON = 0x0080
    ICON_BIG = 1
    ICON_SMALL = 0
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010

    hwnd = None
    for attempt in range(5):
        hwnd = user32.FindWindowW(None, window_title)
        if hwnd:
            break
        if attempt < 4:
            print(f"[!] set_app_window_icon: window '{window_title}' not found, retry {attempt + 1}/5...", file=sys.stderr)
            time.sleep(0.3)

    if not hwnd:
        print(f"[!] set_app_window_icon: window '{window_title}' not found after 5 attempts", file=sys.stderr)
        return False

    hicon_big = user32.LoadImageW(0, ico_path, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
    hicon_small = user32.LoadImageW(0, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

    if not hicon_big:
        print("[!] set_app_window_icon: LoadImageW failed for ICON_BIG (48x48)", file=sys.stderr)
    else:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)

    if not hicon_small:
        print("[!] set_app_window_icon: LoadImageW failed for ICON_SMALL (16x16)", file=sys.stderr)
    else:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)

    success = bool(hicon_big or hicon_small)
    if not success:
        print("[!] set_app_window_icon: both ICON_BIG and ICON_SMALL failed to load", file=sys.stderr)
    return success
