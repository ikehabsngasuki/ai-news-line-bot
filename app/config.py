from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LINE Messaging API
    line_channel_access_token: str = ""
    line_channel_secret: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./dev.db"

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
