"""Bootstrap modules for Manager AI launcher.

Split from the original monolithic start.py into focused modules:
  config   — Env loading, path resolution, Config dataclass
  venv     — Virtual environment creation, pip, .pth patch, re-exec
  frontend — Node check, npm install, build, dev/preview server
  database — Alembic migration runner
  desktop  — pywebview window, icon, health poll, shutdown
"""

from bootstrap.config import Config, load_config
from bootstrap.venv import ensure_venv
from bootstrap.frontend import (
    check_node,
    install_frontend_deps,
    build_frontend,
    start_dev_server,
    start_preview_server,
)
from bootstrap.database import run_migrations
from bootstrap.desktop import kill_process_on_port, run_desktop, wait_and_cleanup, convert_icon

__all__ = [
    "Config",
    "load_config",
    "ensure_venv",
    "check_node",
    "install_frontend_deps",
    "build_frontend",
    "start_dev_server",
    "start_preview_server",
    "run_migrations",
    "kill_process_on_port",
    "run_desktop",
    "wait_and_cleanup",
    "convert_icon",
]
