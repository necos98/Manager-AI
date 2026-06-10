"""Database migration runner.

Estratto da start.py: esegue alembic upgrade head.
"""

import subprocess

from bootstrap.config import Config


def run_migrations(config: Config) -> None:
    """Run Alembic migrations."""
    config.data_dir.mkdir(parents=True, exist_ok=True)
    print("[...] Running database migrations...")
    subprocess.run(
        [str(config.venv_python), "-m", "alembic", "upgrade", "head"],
        cwd=str(config.backend_dir),
        check=True,
    )
    print("[ok] Database migrations complete")
