from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve project root (two levels up from this file: config.py -> app -> backend -> project_root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    lancedb_path: str = str(_PROJECT_ROOT / "data" / "lancedb")
    backend_port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
