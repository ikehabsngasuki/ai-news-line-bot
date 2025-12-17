from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import settings
from app.api.routes import health, webhook
from app.models.database import init_db
from app.services.scheduler import setup_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # Startup
    await init_db()
    setup_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


app = FastAPI(
    title="AI News LINE Bot",
    description="AI技術ニュースを毎朝配信するLINE Bot",
    version="1.0.0",
    lifespan=lifespan,
)

# ルーター登録
app.include_router(health.router, tags=["Health"])
app.include_router(webhook.router, tags=["LINE Webhook"])


@app.get("/")
async def root():
    return {
        "message": "AI News LINE Bot is running",
        "env": settings.app_env,
    }
