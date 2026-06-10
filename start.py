"""Manager AI — development launcher.

Usage:
    python start.py                       Headless production (default)
    python start.py --dev                 Backend + Vite HMR (no build)
    python start.py --desktop             + pywebview desktop window
    python start.py --desktop --dev       Dev mode with desktop window
    python start.py --backend-only        Backend REST API only
    python start.py --port 8001           Custom backend port
"""

import os
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── Venv bootstrap (module-level, before any venv-dependent imports) ────────
from bootstrap.venv import ensure_venv
ensure_venv(ROOT)

# ── Now in venv with deps installed ────────────────────────────────────────
import argparse

from bootstrap.config import load_config
from bootstrap.desktop import convert_icon, kill_process_on_port, run_desktop, wait_and_cleanup, wait_for_ready
from bootstrap.frontend import (
    build_frontend,
    check_node,
    install_frontend_deps,
    start_dev_server,
    start_preview_server,
)
from bootstrap.database import run_migrations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manager AI — local development launcher")
    parser.add_argument(
        "--desktop", action="store_true",
        help="Open pywebview desktop window",
    )
    parser.add_argument(
        "--dev", action="store_true",
        help="Development mode: Vite HMR, no production build",
    )
    parser.add_argument(
        "--backend-only", action="store_true",
        help="Start backend REST API only (no frontend)",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Backend port (default: from .env or 8000)",
    )
    parser.add_argument(
        "--frontend-port", type=int, default=None,
        help="Frontend port (default: from .env or 4173)",
    )
    return parser.parse_args()


def start_backend(config) -> subprocess.Popen:
    """Start uvicorn backend subprocess."""
    env = os.environ.copy()
    if config.is_testing:
        env["DATABASE_URL"] = (
            f"sqlite+aiosqlite:///{config.root / 'data' / 'manager_ai_testing.db'}"
        )
    return subprocess.Popen(
        [
            str(config.venv_python), "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(config.backend_port),
        ],
        cwd=str(config.backend_dir),
        env=env,
    )


def main() -> None:
    args = parse_args()
    config = load_config(ROOT)
    if args.port is not None:
        config.backend_port = args.port
    if args.frontend_port is not None:
        config.frontend_port = args.frontend_port
    config.desktop_mode = args.desktop
    config.dev_mode = args.dev
    config.backend_only = args.backend_only

    kill_process_on_port(config.backend_port)

    frontend_proc = None
    if not config.backend_only:
        check_node()
        install_frontend_deps(config)
        if config.dev_mode:
            frontend_proc = start_dev_server(config)
        else:
            build_frontend(config)
            frontend_proc = start_preview_server(config)

    run_migrations(config)
    backend_proc = start_backend(config)
    wait_for_ready("Backend", backend_proc, config.backend_port)

    if config.is_testing:
        timer = threading.Timer(config.auto_kill_seconds, backend_proc.terminate)
        timer.daemon = True
        timer.start()
        print(f"[...] Auto-kill in {config.auto_kill_seconds}s")

    processes = [backend_proc]
    if not config.backend_only and frontend_proc is not None:
        wait_for_ready("Frontend", frontend_proc, config.frontend_port)
        processes.append(frontend_proc)

    print()
    print("=" * 50)
    print("  Manager AI")
    local_fe = f"http://localhost:{config.frontend_port}"
    local_be = f"http://localhost:{config.backend_port}"
    print(f"  Frontend: {local_fe}  (also accessible on LAN)")
    print(f"  Backend:  {local_be}  (also accessible on LAN)")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    print()

    if config.desktop_mode:
        if not config.backend_only:
            convert_icon(config.root)
        run_desktop(config, processes)
    else:
        wait_and_cleanup(processes)


if __name__ == "__main__":
    main()
