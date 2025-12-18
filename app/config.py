from pydantic_settings import BaseSettings
from functools import lru_cache
import os


def get_database_url() -> str:
    """データベースURLを取得（Railway対応）"""
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")

    # RailwayのPostgreSQL URLを非同期用に変換
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


class Settings(BaseSettings):
    # LINE Messaging API
    line_channel_access_token: str = ""
    line_channel_secret: str = ""

    # Database
    database_url: str = get_database_url()

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
