from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


# DB URLをログ出力（パスワードは隠す）
db_url_display = settings.database_url
if "@" in db_url_display:
    # postgresql+asyncpg://user:password@host/db -> postgresql+asyncpg://***@host/db
    parts = db_url_display.split("@")
    prefix = parts[0].split("://")[0] + "://***"
    db_url_display = f"{prefix}@{parts[1]}"
print(f"[Database] Using: {db_url_display}")

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # コネクション切断検知
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """データベース初期化（テーブル作成）"""
    print("[Database] Initializing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[Database] Tables initialized successfully")


async def get_session() -> AsyncSession:
    """DBセッション取得（Dependency Injection用）"""
    async with async_session() as session:
        yield session
