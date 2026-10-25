from pydantic_settings import BaseSettings, SettingsConfigDict


class DbSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://chat:chat@localhost:5432/chat"


def get_db_settings() -> DbSettings:
    return DbSettings()
