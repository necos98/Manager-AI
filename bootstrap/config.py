"""Config loading and path resolution.

Estratto da start.py: carica .env, risolve path, esporta Config dataclass.
"""

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Paths and settings for the Manager AI launcher."""

    root: Path
    backend_dir: Path
    frontend_dir: Path
    venv_dir: Path
    data_dir: Path
    is_windows: bool

    # Ports (from .env or defaults)
    backend_port: int = 8000
    frontend_port: int = 4173

    # Testing / Workbench mode
    is_testing: bool = False
    auto_kill_seconds: int = 60

    # CLI mode flags (set by start.py after parsing args)
    desktop_mode: bool = False
    dev_mode: bool = False
    backend_only: bool = False

    # Computed venv paths
    venv_python: Path = field(init=False)
    venv_pip: Path = field(init=False)
    venv_alembic: Path = field(init=False)

    def __post_init__(self):
        script = "Scripts" if self.is_windows else "bin"
        self.venv_python = self.venv_dir / script / "python.exe" if self.is_windows else self.venv_dir / script / "python"
        self.venv_pip = self.venv_dir / script / "pip.exe" if self.is_windows else self.venv_dir / script / "pip"
        self.venv_alembic = self.venv_dir / script / "alembic.exe" if self.is_windows else self.venv_dir / script / "alembic"


def _load_dotenv(env_file: Path) -> None:
    """Load .env file using python-dotenv if available, else manual fallback."""
    try:
        from dotenv import load_dotenv as _dotenv
        _dotenv(env_file)
    except ImportError:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())


def load_config(root: Path | None = None) -> Config:
    """Load env, resolve paths, return Config."""
    if root is None:
        root = Path(__file__).resolve().parent.parent

    _load_dotenv(root / ".env")

    is_testing = os.environ.get("IS_TESTING", "").lower() == "true"
    backend_port = int(os.environ.get("BACKEND_PORT", 8000))
    frontend_port = int(os.environ.get("FRONTEND_PORT", 4173))

    if is_testing:
        from bootstrap.desktop import find_free_port

        backend_port = find_free_port()

    return Config(
        root=root,
        backend_dir=root / "backend",
        frontend_dir=root / "frontend",
        venv_dir=root / "venv",
        data_dir=root / "data",
        is_windows=platform.system() == "Windows",
        backend_port=backend_port,
        frontend_port=frontend_port,
        is_testing=is_testing,
        auto_kill_seconds=int(os.environ.get("AUTO_KILL_SECONDS", 60)),
    )
