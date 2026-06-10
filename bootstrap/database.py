"""Database migration runner.

Estratto da start.py: esegue alembic upgrade head.
"""

import os
import subprocess

from bootstrap.config import Config


def run_migrations(config: Config) -> None:
    """Run Alembic migrations."""
    config.data_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if config.is_testing:
        env["DATABASE_URL"] = (
            f"sqlite+aiosqlite:///{config.root / 'data' / 'manager_ai_testing.db'}"
        )
    print("[...] Running database migrations...")
    subprocess.run(
        [str(config.venv_python), "-m", "alembic", "upgrade", "head"],
        cwd=str(config.backend_dir),
        env=env,
        check=True,
    )
    print("[ok] Database migrations complete")
