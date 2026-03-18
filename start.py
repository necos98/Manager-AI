"""Manager AI — local development launcher.

Usage: python start.py

Starts both the FastAPI backend and the Vite frontend dev server.
Press Ctrl+C to stop both.
"""

import platform
import shutil
import signal
import subprocess
import sys
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
        [str(VENV_PIP), "install", "-r", str(BACKEND_DIR / "requirements.txt"), "-q"],
        check=True,
    )
    print("[ok] Backend dependencies installed")


def setup_frontend():
    """Install frontend dependencies if needed."""
    if not (FRONTEND_DIR / "node_modules").exists():
        print("[...] Installing frontend dependencies...")
        npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
        subprocess.run(
            [npm_cmd, "install", "--legacy-peer-deps"],
            cwd=str(FRONTEND_DIR),
            check=True,
        )
        print("[ok] Frontend dependencies installed")


def run_migrations():
    """Run Alembic migrations."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("[...] Running database migrations...")
    subprocess.run(
        [str(VENV_ALEMBIC), "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        check=True,
    )
    print("[ok] Database migrations complete")


def main():
    check_prerequisites()
    setup_venv()
    setup_frontend()
    run_migrations()

    print()
    print("=" * 50)
    print("  Manager AI")
    print("  Frontend: http://localhost:5173")
    print("  Backend:  http://localhost:8000")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    print()

    # Start backend
    backend_proc = subprocess.Popen(
        [
            str(VENV_PYTHON), "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--host", "127.0.0.1",
            "--port", "8000",
        ],
        cwd=str(BACKEND_DIR),
    )

    # Start frontend
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    processes = [backend_proc, frontend_proc]

    def shutdown(sig=None, frame=None):
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
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    # Wait — poll processes and exit if one crashes
    try:
        while True:
            for proc in processes:
                ret = proc.poll()
                if ret is not None:
                    proc_name = "Backend" if proc == backend_proc else "Frontend"
                    print(f"\n[!] {proc_name} exited with code {ret}")
                    shutdown()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
