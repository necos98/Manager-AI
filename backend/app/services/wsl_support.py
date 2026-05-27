from __future__ import annotations

import os
import platform
import shutil
import subprocess
from functools import lru_cache


def is_wsl_shell(shell: str | None) -> bool:
    """True iff the shell path points at wsl.exe (any install location)."""
    if not shell:
        return False
    return os.path.basename(shell).lower() == "wsl.exe"


def win_to_wsl_path(path: str) -> str:
    """Translate a Windows path to its WSL equivalent.

    - ``C:\\foo\\bar``                       -> ``/mnt/c/foo/bar``
    - ``\\\\wsl.localhost\\Ubuntu\\home\\u`` -> ``/home/u``
    - ``\\\\wsl$\\Ubuntu\\home\\u``          -> ``/home/u``
    - POSIX or empty paths pass through unchanged.
    """
    if not path:
        return path
    if path.startswith("\\\\wsl.localhost\\") or path.startswith("\\\\wsl$\\"):
        parts = path.split("\\")
        tail = [p for p in parts[4:] if p]
        return "/" + "/".join(tail)
    if len(path) >= 2 and path[1] == ":":
        drive = path[0].lower()
        rest = path[2:].replace("\\", "/").lstrip("/")
        return f"/mnt/{drive}/{rest}" if rest else f"/mnt/{drive}/"
    return path


@lru_cache(maxsize=1)
def wsl_available() -> bool:
    """True iff we're on Windows and wsl.exe is on PATH."""
    if platform.system() != "Windows":
        return False
    return shutil.which("wsl.exe") is not None


def list_wsl_distros() -> list[str]:
    """Return user-usable WSL distro names. Empty list if WSL unavailable or errors.

    ``wsl.exe -l -q`` outputs UTF-16 LE with BOM on Windows; decode explicitly.
    Filters out docker-desktop* distros which are not end-user runnable.
    """
    if not wsl_available():
        return []
    try:
        result = subprocess.run(
            ["wsl.exe", "-l", "-q"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if result.returncode != 0:
        return []
    try:
        text = result.stdout.decode("utf-16-le").lstrip("\ufeff")
    except UnicodeDecodeError:
        text = result.stdout.decode("utf-8", errors="replace")
    distros = [line.strip() for line in text.splitlines() if line.strip()]
    return [d for d in distros if not d.startswith("docker-desktop")]


def get_default_distro() -> str | None:
    """Return the default WSL distro name or None."""
    distros = list_wsl_distros()
    return distros[0] if distros else None


def get_host_ip_for_wsl() -> str | None:
    """Return the Windows host IP on the WSL2 virtual switch.

    Queries the ``vEthernet (WSL)`` interface from Windows via PowerShell.
    This runs on the Windows host, completely outside WSL2, so it is immune
    to Docker Desktop or VPN route interference inside the Linux VM.
    Returns None when the interface cannot be found.
    """
    if platform.system() != "Windows":
        return None
    try:
        ps_cmd = (
            "Get-NetIPAddress -InterfaceAlias 'vEthernet (WSL)*'"
            " -AddressFamily IPv4 | Select-Object -First 1 -ExpandProperty IPAddress"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            ip = result.stdout.strip()
            if ip:
                return ip
    except (subprocess.SubprocessError, OSError):
        pass
    return None
