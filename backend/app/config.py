from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    recordings_path: str = str(_PROJECT_ROOT / "data" / "recordings")
    claude_library_path: str = str(_PROJECT_ROOT / "claude_library")
    backend_port: int = 8000
    hook_timeout_seconds: int = 300
    terminal_max_buffer_bytes: int = 100_000

    model_config = {"env_file": ".env"}

    @field_validator("backend_port")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"backend_port must be 1-65535, got {v}")
        return v


settings = Settings()
