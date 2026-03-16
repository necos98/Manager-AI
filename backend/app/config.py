from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://manager:changeme@localhost:5432/manager_ai"

    model_config = {"env_file": ".env"}


settings = Settings()
