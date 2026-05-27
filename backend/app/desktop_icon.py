"""Set the Windows window icon via Win32 API (ctypes). No extra dependencies."""

import ctypes
import sys
from pathlib import Path


def set_app_window_icon(window_title: str, ico_path: str) -> bool:

    if sys.platform != "win32":
        return False

    if not Path(ico_path).exists():
        return False

    try:
        user32 = ctypes.windll.user32

        WM_SETICON = 0x0080
        ICON_BIG = 1
        ICON_SMALL = 0
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010

        hwnd = user32.FindWindowW(None, window_title)
        if not hwnd:
            return False

        hicon_big = user32.LoadImageW(0, ico_path, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
        hicon_small = user32.LoadImageW(0, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

        if hicon_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
        if hicon_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)

        return bool(hicon_big or hicon_small)
    except Exception:
        return False
