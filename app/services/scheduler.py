import uuid
import asyncio
from typing import Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.models import Article, async_session
from app.utils.flex_message import create_news_carousel, _generate_article_id

scheduler: Optional[AsyncIOScheduler] = None


def setup_scheduler():
    """スケジューラーの初期化と開始"""
    global scheduler

    if not settings.line_channel_access_token:
        print("LINE credentials not set. Scheduler disabled.")
        return

    scheduler = AsyncIOScheduler()
    jst = pytz.timezone(settings.timezone)

    # 毎朝8時に実行
    scheduler.add_job(
        daily_news_broadcast,
        CronTrigger(
            hour=settings.daily_delivery_hour,
            minute=settings.daily_delivery_minute,
            timezone=jst,
        ),
        id="daily_news_broadcast",
        replace_existing=True,
    )

    scheduler.start()
    print(f"Scheduler started: Daily news at {settings.daily_delivery_hour}:{settings.daily_delivery_minute:02d} JST")


def shutdown_scheduler():
    """スケジューラーの停止"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("Scheduler shutdown complete")


async def daily_news_broadcast():
    """毎朝のニュース配信ジョブ"""
    from app.services.social_scorer import get_top_articles
    from app.services.line_service import broadcast_flex_message

    print("Daily news broadcast started...")

    try:
        # 人気記事取得
        top_articles = await get_top_articles(count=settings.max_articles_per_delivery)

        if not top_articles:
            print("No articles found for broadcast")
            return

        # DBに記事を保存（お気に入り機能用）
        await _save_articles_to_db(top_articles)

        # Flex Message生成
        flex_content = create_news_carousel(top_articles)

        # ブロードキャスト
        await broadcast_flex_message(
            alt_text=f"本日のAIニュース TOP{len(top_articles)}",
            flex_content=flex_content,
        )

        print(f"Broadcast complete: {len(top_articles)} articles")

    except Exception as e:
        print(f"Broadcast error: {e}")
        raise


async def send_daily_news_to_user(user_id: str):
    """特定ユーザーにニュースを送信"""
    from app.services.social_scorer import get_top_articles
    from app.services.line_service import send_flex_message

    try:
        top_articles = await get_top_articles(count=settings.max_articles_per_delivery)

        if not top_articles:
            from app.services.line_service import send_text_message
            await send_text_message(user_id, "現在配信できるニュースがありません。")
            return

        # DBに記事を保存
        await _save_articles_to_db(top_articles)

        # Flex Message送信
        flex_content = create_news_carousel(top_articles)
        await send_flex_message(
            user_id,
            f"AIニュース TOP{len(top_articles)}",
            flex_content,
        )

    except Exception as e:
        print(f"Send news error: {e}")
        from app.services.line_service import send_text_message
        await send_text_message(user_id, "ニュースの取得に失敗しました。しばらく後にお試しください。")


async def _save_articles_to_db(articles):
    """記事をDBに保存（お気に入り用）"""
    from sqlalchemy import select

    async with async_session() as session:
        for article in articles:
            article_id = _generate_article_id(article.url)

            # 既存チェック
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # スコア更新
                existing.popularity_score = article.popularity_score
                existing.hatena_count = article.hatena_count
                existing.hackernews_score = article.hackernews_score
            else:
                # 新規作成
                new_article = Article(
                    id=article_id,
                    url=article.url,
                    title=article.title,
                    summary=article.summary,
                    source=article.source,
                    thumbnail_url=article.thumbnail_url,
                    popularity_score=article.popularity_score,
                    hatena_count=article.hatena_count,
                    hackernews_score=article.hackernews_score,
                    reddit_score=article.reddit_score,
                    source_count=article.source_count,
                    published_at=article.published_at,
                )
                session.add(new_article)

        await session.commit()
