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
import sys
import threading
import time
from pathlib import Path
try:
    from dotenv import load_dotenv
    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

import webview  # pywebview: desktop window wrapper

ROOT = Path(__file__).resolve().parent

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
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_DIR = ROOT / "venv"
DATA_DIR = ROOT / "data"

FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", 4173))

IS_WINDOWS = platform.system() == "Windows"
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
VENV_PIP = VENV_DIR / ("Scripts/pip.exe" if IS_WINDOWS else "bin/pip")
VENV_ALEMBIC = VENV_DIR / ("Scripts/alembic.exe" if IS_WINDOWS else "bin/alembic")


def check_prerequisites():
    """Verify Node.js and npm are available."""
    if shutil.which("node") is None:
        print("ERROR: Node.js is not installed or not in PATH.")
        sys.exit(1)
    if shutil.which("npm") is None:
        print("ERROR: npm is not installed or not in PATH.")
        sys.exit(1)
    print("[ok] Node.js and npm found")


def setup_venv():
    """Create venv and install backend dependencies if needed."""
    if not VENV_PYTHON.exists():
        print("[...] Creating Python virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("[ok] Virtual environment created")

    print("[...] Installing backend dependencies...")
    subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt"), "-q"],
        check=True,
    )
    print("[ok] Backend dependencies installed")


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


def main():
    backend_port = int(os.environ.get("BACKEND_PORT", 8000))

    check_prerequisites()
    setup_venv()
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
            "--reload",
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
        while not stop_event.is_set():
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

    try:
        webview.start(
            func=poll_worker,
            debug=bool(os.environ.get("MANAGER_AI_DEV")),
        )
    finally:
        shutdown()


if __name__ == "__main__":
    main()
