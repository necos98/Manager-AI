from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve project root (two levels up from this file: config.py -> app -> backend -> project_root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    lancedb_path: str = str(_PROJECT_ROOT / "data" / "lancedb")
    claude_library_path: str = str(_PROJECT_ROOT / "claude_library")
    backend_port: int = 8000
    embedding_driver: str = "sentence_transformer"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50

    model_config = {"env_file": ".env"}


settings = Settings()
