"""Virtual environment bootstrap.

Estratto da start.py: creazione venv, pip install, .pth patch, re-exec.
Usa solo stdlib — importato PRIMA che il venv sia attivo.
"""

import ctypes
import os
import platform
import subprocess
import sys
from pathlib import Path


def _script_dir(is_windows: bool) -> str:
    return "Scripts" if is_windows else "bin"


def _venv_python(venv_dir: Path, is_windows: bool) -> Path:
    exe = "python.exe" if is_windows else "python"
    return venv_dir / _script_dir(is_windows) / exe


def _venv_pip(venv_dir: Path, is_windows: bool) -> Path:
    exe = "pip.exe" if is_windows else "pip"
    return venv_dir / _script_dir(is_windows) / exe


# ── Windows Job Object helpers ──────────────────────────────────────────────

if platform.system() == "Windows":
    CREATE_BREAKAWAY_FROM_JOB = 0x02000000
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("_pad1", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_uint64),
            ("MaximumWorkingSetSize", ctypes.c_uint64),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("_pad2", ctypes.c_uint32),
            ("Affinity", ctypes.c_uint64),
            ("ChildProcessNotify", ctypes.c_uint32),
            ("_pad3", ctypes.c_uint32),
            ("MaximumSchedulingClass", ctypes.c_uint32),
            ("_pad4", ctypes.c_uint32),
            ("IoInfo", ctypes.c_uint64 * 6),
            ("ProcessMemoryLimit", ctypes.c_uint64),
            ("JobMemoryLimit", ctypes.c_uint64),
            ("PeakProcessMemoryUsed", ctypes.c_uint64),
            ("PeakJobMemoryUsed", ctypes.c_uint64),
        ]


def _run_windows_reexec(cmd: list[str]) -> None:
    """Re-exec cmd under a Job Object. Kills child when this process dies."""
    proc = None
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            raise ctypes.WinError()

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

        kernel32.SetInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
        ]
        ret = kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
        if not ret:
            raise ctypes.WinError()

        proc = subprocess.Popen(cmd, creationflags=CREATE_BREAKAWAY_FROM_JOB)
        kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        ret = kernel32.AssignProcessToJobObject(job, proc._handle)
        if not ret:
            raise ctypes.WinError()
    except Exception:
        pass

    if proc is None:
        proc = subprocess.Popen(cmd)

    sys.exit(proc.wait())


# ── Core bootstrap functions ────────────────────────────────────────────────

def in_project_venv(venv_dir: Path) -> bool:
    """True when current interpreter runs from this project's venv."""
    try:
        return Path(sys.prefix).resolve() == venv_dir.resolve()
    except OSError:
        return False


def install_backend_deps(python: Path, requirements: Path) -> None:
    """Install/update backend deps in the project venv."""
    print("[...] Checking backend dependencies...")
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(requirements), "-q"],
        check=True,
    )
    print("[ok] Backend dependencies up to date")


def ensure_pth_patch(backend_dir: Path, venv_dir: Path, is_windows: bool) -> None:
    """Create .pth file in venv site-packages for ProactorEventLoop patch.

    Runs before uvicorn sets WindowsSelectorEventLoopPolicy (which breaks
    subprocess support). .pth files are processed by Python's site module
    at interpreter startup, including for multiprocessing workers.
    """
    site_packages: Path | None = None
    for p in sys.path:
        if p.endswith("site-packages") and venv_dir.resolve() in Path(p).resolve().parents:
            site_packages = Path(p)
            break
    if site_packages is None:
        candidate = venv_dir / ("Lib" if is_windows else "lib") / "site-packages"
        if candidate.exists():
            site_packages = candidate

    if site_packages is None:
        print("[!] Could not locate venv site-packages; .pth patch not installed")
        return

    pth_path = site_packages / "_manager_ai_proactor.pth"
    content = f"{backend_dir.resolve()}\nimport app._ensure_proactor\n"

    if pth_path.exists() and pth_path.read_text() == content:
        return

    pth_path.write_text(content)
    print("[ok] .pth patch installed for ProactorEventLoop")


def bootstrap_and_reexec(root: Path) -> None:
    """Create venv, install deps, patch .pth, then re-exec under venv python.

    Called ONLY when not already in the project venv. Never returns in the
    original process — either sys.exit() after spawning re-exec or os.execv().
    """
    is_windows = platform.system() == "Windows"
    venv_dir = root / "venv"
    python = _venv_python(venv_dir, is_windows)
    backend_dir = root / "backend"

    if not python.exists():
        print("[...] Creating Python virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("[ok] Virtual environment created")

    install_backend_deps(python, backend_dir / "requirements.txt")
    ensure_pth_patch(backend_dir, venv_dir, is_windows)

    cmd = [str(python), str(root / "start.py"), *sys.argv[1:]]
    if is_windows:
        _run_windows_reexec(cmd)
    else:
        os.execv(str(python), cmd)


def ensure_venv(root: Path) -> None:
    """Bootstrap venv and re-exec if needed.

    Call at module level in start.py BEFORE any venv-dependent imports.
    After this returns, the process is guaranteed to be running inside the
    project venv with deps installed and .pth patched.
    """
    is_windows = platform.system() == "Windows"
    venv_dir = root / "venv"
    python = _venv_python(venv_dir, is_windows)
    backend_dir = root / "backend"

    if in_project_venv(venv_dir):
        # Already inside venv: ensure deps + .pth every run
        install_backend_deps(python, backend_dir / "requirements.txt")
        ensure_pth_patch(backend_dir, venv_dir, is_windows)
        return

    bootstrap_and_reexec(root)
    # Never reached — re-exec happens above
