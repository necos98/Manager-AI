from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'manager_ai.db'}"
    lancedb_path: str = str(_PROJECT_ROOT / "data" / "lancedb")
    recordings_path: str = str(_PROJECT_ROOT / "data" / "recordings")
    claude_library_path: str = str(_PROJECT_ROOT / "claude_library")
    backend_port: int = 8000
    embedding_driver: str = "sentence_transformer"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50
    hook_timeout_seconds: int = 300
    terminal_max_buffer_bytes: int = 100_000

    model_config = {"env_file": ".env"}

    @field_validator("backend_port")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"backend_port must be 1-65535, got {v}")
        return v

    @field_validator("chunk_max_tokens", "chunk_overlap_tokens")
    @classmethod
    def tokens_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("token counts must be >= 1")
        return v

    @field_validator("embedding_driver")
    @classmethod
    def driver_must_be_known(cls, v: str) -> str:
        allowed = {"sentence_transformer"}
        if v not in allowed:
            raise ValueError(f"embedding_driver must be one of {allowed}, got {v!r}")
        return v

    @model_validator(mode="after")
    def overlap_must_be_less_than_max(self) -> "Settings":
        if self.chunk_overlap_tokens >= self.chunk_max_tokens:
            raise ValueError(
                f"chunk_overlap_tokens ({self.chunk_overlap_tokens}) must be "
                f"less than chunk_max_tokens ({self.chunk_max_tokens})"
            )
        return self


settings = Settings()
