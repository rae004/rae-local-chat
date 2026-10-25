from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://workhorse:11434"
    ollama_model: str = "qwen2.5-coder:latest"
    # Seconds between bytes before we give up; None = wait forever for a slow model.
    ollama_read_timeout: float | None = 120.0
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
