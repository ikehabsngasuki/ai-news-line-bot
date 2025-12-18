from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # LINE Messaging API
    line_channel_access_token: str = ""
    line_channel_secret: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    @field_validator("database_url", mode="after")
    @classmethod
    def convert_database_url(cls, v: str) -> str:
        """RailwayのPostgreSQL URLを非同期用に変換"""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Application
    app_env: str = "development"
    debug: bool = True

    # Scheduler
    daily_delivery_hour: int = 8
    daily_delivery_minute: int = 0
    timezone: str = "Asia/Tokyo"

    # Article Settings
    max_articles_per_delivery: int = 5
    article_fetch_hours: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
