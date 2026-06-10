"""Manager AI — local development launcher.

Usage: python start.py

Starts both the FastAPI backend and the Vite frontend dev server.
Press Ctrl+C to stop both.
"""

import os
import platform
import shutil
import signal
import socket
import subprocess
import ctypes
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_DIR = ROOT / "venv"
DATA_DIR = ROOT / "data"

IS_WINDOWS = platform.system() == "Windows"
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
VENV_PIP = VENV_DIR / ("Scripts/pip.exe" if IS_WINDOWS else "bin/pip")
VENV_ALEMBIC = VENV_DIR / ("Scripts/alembic.exe" if IS_WINDOWS else "bin/alembic")

if IS_WINDOWS:
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


def _in_project_venv():
    """True when current interpreter runs from this project's venv.

    Uses sys.prefix (not executable path) — on Linux venv/bin/python is a
    symlink to system python, so resolving paths gives false negatives.
    """
    try:
        return Path(sys.prefix).resolve() == VENV_DIR.resolve()
    except OSError:
        return False


def _install_backend_deps():
    """Install/update backend deps in the project venv. Idempotent — pip skips up-to-date."""
    print("[...] Checking backend dependencies...")
    subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt"), "-q"],
        check=True,
    )
    print("[ok] Backend dependencies up to date")


def _ensure_pth_patch():
    """Create a .pth file in the venv's site-packages so Python runs our
    event-loop patch at startup — before uvicorn has a chance to set
    WindowsSelectorEventLoopPolicy (which breaks subprocess support).

    .pth files are processed by Python's site module at interpreter startup,
    including for multiprocessing worker processes.  This is the only hook
    that runs early enough to beat uvicorn's setup_event_loop().
    """
    site_packages = None
    for p in sys.path:
        if p.endswith("site-packages") and VENV_DIR.resolve() in Path(p).resolve().parents:
            site_packages = Path(p)
            break
    if site_packages is None:
        # Fallback: guess the standard venv layout
        candidate = VENV_DIR / ("Lib" if IS_WINDOWS else "lib") / "site-packages"
        if candidate.exists():
            site_packages = candidate

    if site_packages is None:
        print("[!] Could not locate venv site-packages; .pth patch not installed")
        return

    pth_path = site_packages / "_manager_ai_proactor.pth"
    backend_path = str(BACKEND_DIR.resolve())

    # Path line adds backend to sys.path; import line runs the patcher.
    content = f"{backend_path}\nimport app._ensure_proactor\n"

    if pth_path.exists() and pth_path.read_text() == content:
        return

    pth_path.write_text(content)
    print("[ok] .pth patch installed for ProactorEventLoop")


def _run_windows_reexec(cmd):
    """Re-exec cmd under a Job Object. Kills child when this process dies.

    Uses Win32 Job Object API via ctypes (no pywin32 dep).
    Falls back silently if Job API fails (unusual security policy, old Windows).
    """
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
        ret = kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(info), ctypes.sizeof(info))
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


def _bootstrap_venv_and_reexec():
    """Create venv, install deps, then re-exec this script under venv python.

    Must run BEFORE importing webview/dotenv — those live in the venv.
    """
    if not VENV_PYTHON.exists():
        print("[...] Creating Python virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("[ok] Virtual environment created")

    _install_backend_deps()
    _ensure_pth_patch()

    # execv on Windows doesn't replace process cleanly in some shells; spawn+exit is safer.
    if IS_WINDOWS:
        _run_windows_reexec([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
    else:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])


if not _in_project_venv():
    _bootstrap_venv_and_reexec()
else:
    # Already in venv (re-exec or direct invoke): still verify deps every run
    # so newly-added requirements get installed without needing to nuke venv.
    _install_backend_deps()
    _ensure_pth_patch()

try:
    from dotenv import load_dotenv
    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

import webview  # pywebview: desktop window wrapper

if _HAS_DOTENV:
    load_dotenv(ROOT / ".env")
else:
    # Fallback: parse .env manually for BACKEND_PORT
    _env_file = ROOT / ".env"
    if _env_file.exists():
        for line in _env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", 4173))


def check_prerequisites():
    """Verify Node.js and npm are available."""
    if shutil.which("node") is None:
        print("ERROR: Node.js is not installed or not in PATH.")
        sys.exit(1)
    if shutil.which("npm") is None:
        print("ERROR: npm is not installed or not in PATH.")
        sys.exit(1)
    print("[ok] Node.js and npm found")


def setup_frontend():
    """Install frontend dependencies and build for production."""
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    node_modules = FRONTEND_DIR / "node_modules"
    package_json = FRONTEND_DIR / "package.json"
    needs_install = (
        not node_modules.exists()
        or package_json.stat().st_mtime > node_modules.stat().st_mtime
    )
    if needs_install:
        print("[...] Installing frontend dependencies...")
        subprocess.run(
            [npm_cmd, "install", "--legacy-peer-deps"],
            cwd=str(FRONTEND_DIR),
            check=True,
        )
        print("[ok] Frontend dependencies installed")
    print("[...] Building frontend...")
    subprocess.run(
        [npm_cmd, "run", "build"],
        cwd=str(FRONTEND_DIR),
        check=True,
    )
    print("[ok] Frontend build complete")


def run_migrations():
    """Run Alembic migrations."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("[...] Running database migrations...")
    subprocess.run(
        [str(VENV_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        check=True,
    )
    print("[ok] Database migrations complete")


def _ensure_app_icon():
    """Convert logo.png to logo.ico if missing or outdated."""
    logo_png = ROOT / "logo.png"
    logo_ico = ROOT / "logo.ico"

    if not logo_png.exists():
        return

    if logo_ico.exists() and logo_ico.stat().st_mtime >= logo_png.stat().st_mtime:
        return

    try:
        from PIL import Image

        img = Image.open(logo_png)
        img.save(logo_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
        print("[ok] App icon created: logo.ico")
    except Exception as e:
        print(f"[!] Could not create logo.ico: {e}")


def _get_pids_on_port(port: int) -> list[int]:
    """Return list of PIDs listening on *port* (Windows netstat).

    Uses ``netstat -ano`` to find TCP connections in LISTENING state
    on the given port.  Returns an empty list when nothing is found.
    """
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print(f"[!] netstat not found — skipping port-{port} check")
        return []

    pids: list[int] = []
    needle = f":{port}"
    for line in result.stdout.splitlines():
        # Typical output:  TCP    0.0.0.0:8001    0.0.0.0:LISTENING    12345
        line = line.strip()
        if needle not in line:
            continue
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[-1])
            pids.append(pid)
        except (ValueError, IndexError):
            continue
    return pids


def _kill_existing_backend(port: int) -> None:
    """Kill any existing backend process listening on *port*.

    Prints status messages along the way.  Never raises — errors are
    logged as warnings and swallowed so the launcher can proceed.
    """
    pids = _get_pids_on_port(port)

    if not pids:
        print(f"[ok] Nessun backend precedente trovato sulla porta {port}")
        return

    for pid in pids:
        print(f"[...] Trovato backend già in esecuzione su PID {pid}, terminazione...")
        try:
            kill_result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True,
                check=False,
            )
            if kill_result.returncode == 0:
                print(f"[ok] Processo PID {pid} terminato con successo")
            else:
                print(
                    f"[!] Impossibile terminare il processo PID {pid}: "
                    f"{kill_result.stderr.strip() or kill_result.stdout.strip()}"
                )
        except FileNotFoundError:
            print(f"[!] taskkill non trovato — impossibile terminare PID {pid}")
        except Exception as exc:
            print(f"[!] Errore durante la terminazione del PID {pid}: {exc}")


def main():
    backend_port = int(os.environ.get("BACKEND_PORT", 8000))

    _kill_existing_backend(backend_port)

    check_prerequisites()
    setup_frontend()
    run_migrations()

    print()
    print("=" * 50)
    print("  Manager AI")
    print(f"  Frontend: http://localhost:{FRONTEND_PORT}  (also accessible on LAN)")
    print(f"  Backend:  http://localhost:{backend_port}  (also accessible on LAN)")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    print()

    # Start backend
    backend_proc = subprocess.Popen(
        [
            str(VENV_PYTHON), "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(backend_port),
        ],
        cwd=str(BACKEND_DIR),
    )

    # Wait for backend to be ready before starting frontend
    print("[...] Waiting for backend to be ready...")
    for i in range(30):
        # Check if backend process crashed
        if backend_proc.poll() is not None:
            print(f"[!] Backend exited with code {backend_proc.returncode}")
            sys.exit(1)
        try:
            with socket.create_connection(("127.0.0.1", backend_port), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    else:
        print("[!] Backend did not start within 15 seconds")
        backend_proc.terminate()
        sys.exit(1)
    print("[ok] Backend is ready")

    # Start frontend — pass backend URL so Vite proxy points to the right port
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    frontend_env = {**os.environ, "BACKEND_URL": f"http://localhost:{backend_port}"}
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "preview"],
        cwd=str(FRONTEND_DIR),
        env=frontend_env,
    )

    print("[...] Waiting for frontend to be ready...")
    for i in range(30):
        if frontend_proc.poll() is not None:
            print(f"[!] Frontend exited with code {frontend_proc.returncode}")
            backend_proc.terminate()
            sys.exit(1)
        try:
            with socket.create_connection(("127.0.0.1", FRONTEND_PORT), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    else:
        print("[!] Frontend did not start within 15 seconds")
        frontend_proc.terminate()
        backend_proc.terminate()
        sys.exit(1)
    print("[ok] Frontend is ready")

    processes = [backend_proc, frontend_proc]
    shutdown_called = {"done": False}

    def shutdown(sig=None, frame=None):
        if shutdown_called["done"]:
            return
        shutdown_called["done"] = True
        print("\n[...] Shutting down...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[ok] All processes stopped")

    stop_event = threading.Event()

    _ensure_app_icon()

    sys.path.insert(0, str(BACKEND_DIR))
    from app.desktop_icon import set_app_user_model_id
    set_app_user_model_id()

    window = webview.create_window(
        "Manager AI",
        f"http://localhost:{FRONTEND_PORT}",
        width=1400,
        height=900,
    )
    window.events.closed += lambda: stop_event.set()

    def poll_worker():
        """Watch subprocess health on the webview worker thread.

        Destroying the window unblocks webview.start() on the main thread,
        which then runs shutdown() in its finally clause.
        """
        icon_set = False
        while not stop_event.is_set():
            if not icon_set:
                try:
                    sys.path.insert(0, str(BACKEND_DIR))
                    from app.desktop_icon import set_app_window_icon
                    if set_app_window_icon("Manager AI", str(ROOT / "logo.ico")):
                        icon_set = True
                except Exception:
                    pass
            for proc in processes:
                ret = proc.poll()
                if ret is not None:
                    proc_name = "Backend" if proc is backend_proc else "Frontend"
                    print(f"\n[!] {proc_name} exited with code {ret}")
                    stop_event.set()
                    try:
                        window.destroy()
                    except Exception:
                        pass
                    return
            time.sleep(0.5)

    def handle_sigint(sig, frame):
        stop_event.set()
        try:
            window.destroy()
        except Exception:
            pass

    signal.signal(signal.SIGINT, handle_sigint)

    webview_storage = DATA_DIR / "webview"
    webview_storage.mkdir(parents=True, exist_ok=True)

    try:
        webview.start(
            func=poll_worker,
            debug=bool(os.environ.get("MANAGER_AI_DEV")),
            private_mode=False,
            storage_path=str(webview_storage),
        )
    finally:
        shutdown()


if __name__ == "__main__":
    main()
