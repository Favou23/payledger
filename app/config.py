from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PayLedger API"
    app_env: str = "development"
    database_url: str = Field(
        default="postgresql+asyncpg://payleger:payleger_pass@localhost:5432/payleger_db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
