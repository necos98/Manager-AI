"""Frontend management: Node check, npm install, build, dev/preview server.

Estratto da start.py. Tutte le funzioni che avviano server ritornano
subprocess.Popen per il lifecycle management.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from bootstrap.config import Config


def _npm_cmd(is_windows: bool) -> str:
    return "npm.cmd" if is_windows else "npm"


def check_node() -> None:
    """Verify Node.js and npm are available. Exit if not."""
    if shutil.which("node") is None:
        print("ERROR: Node.js is not installed or not in PATH.")
        sys.exit(1)
    if shutil.which("npm") is None:
        print("ERROR: npm is not installed or not in PATH.")
        sys.exit(1)
    print("[ok] Node.js and npm found")


def install_frontend_deps(config: Config) -> None:
    """Install frontend dependencies (npm install)."""
    npm = _npm_cmd(config.is_windows)
    node_modules = config.frontend_dir / "node_modules"
    package_json = config.frontend_dir / "package.json"
    needs_install = (
        not node_modules.exists()
        or package_json.stat().st_mtime > node_modules.stat().st_mtime
    )
    if not needs_install:
        return

    print("[...] Installing frontend dependencies...")
    subprocess.run(
        [npm, "install", "--legacy-peer-deps"],
        cwd=str(config.frontend_dir),
        check=True,
    )
    print("[ok] Frontend dependencies installed")


def build_frontend(config: Config) -> None:
    """Build frontend for production (npm run build)."""
    npm = _npm_cmd(config.is_windows)
    print("[...] Building frontend...")
    subprocess.run(
        [npm, "run", "build"],
        cwd=str(config.frontend_dir),
        check=True,
    )
    print("[ok] Frontend build complete")


def start_dev_server(config: Config) -> subprocess.Popen:
    """Start Vite dev server (HMR). Returns Popen."""
    npm = _npm_cmd(config.is_windows)
    print("[...] Starting frontend dev server (HMR)...")
    return subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(config.frontend_dir),
    )


def start_preview_server(config: Config) -> subprocess.Popen:
    """Start Vite preview server for production build. Returns Popen."""
    npm = _npm_cmd(config.is_windows)
    frontend_env = {**os.environ, "BACKEND_URL": f"http://localhost:{config.backend_port}"}
    print("[...] Starting frontend preview server...")
    return subprocess.Popen(
        [npm, "run", "preview"],
        cwd=str(config.frontend_dir),
        env=frontend_env,
    )
