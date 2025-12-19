import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List

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

    # 毎時0分に実行（ユーザーごとの配信時間に対応）
    scheduler.add_job(
        hourly_news_delivery,
        CronTrigger(
            minute=0,
            timezone=jst,
        ),
        id="hourly_news_delivery",
        replace_existing=True,
    )

    scheduler.start()
    print("Scheduler started: Hourly news delivery enabled")


def shutdown_scheduler():
    """スケジューラーの停止"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("Scheduler shutdown complete")


async def hourly_news_delivery():
    """毎時のニュース配信ジョブ（ユーザー設定に基づく）"""
    from app.services.social_scorer import get_top_articles
    from app.services.line_service import send_flex_message, get_users_by_delivery_hour

    jst = pytz.timezone(settings.timezone)
    current_hour = datetime.now(jst).hour

    print(f"Hourly news delivery started for {current_hour}:00 JST...")

    try:
        # この時間に配信するユーザーを取得
        users = await get_users_by_delivery_hour(current_hour)
        print(f"Users to deliver: {len(users)}")

        if not users:
            print(f"No users scheduled for {current_hour}:00")
            return

        # 各ユーザーに配信
        for user_data in users:
            line_user_id = user_data[0]
            categories_json = user_data[1]
            language = user_data[2] or "both"

            # カテゴリをパース
            categories = None
            if categories_json:
                try:
                    categories = json.loads(categories_json) if isinstance(categories_json, str) else categories_json
                except json.JSONDecodeError:
                    categories = None

            try:
                # ユーザー設定に基づいて記事取得
                top_articles = await get_top_articles(
                    count=settings.max_articles_per_delivery,
                    categories=categories,
                    language=language,
                )

                if not top_articles:
                    print(f"No articles for user {line_user_id[:8]}...")
                    continue

                # DBに記事を保存
                await _save_articles_to_db(top_articles)

                # Flex Message送信
                flex_content = create_news_carousel(top_articles)
                await send_flex_message(
                    line_user_id,
                    f"本日のAIニュース TOP{len(top_articles)}",
                    flex_content,
                )

                print(f"Delivered to {line_user_id[:8]}...: {len(top_articles)} articles")

            except Exception as e:
                print(f"Delivery error for {line_user_id[:8]}...: {e}")
                continue

        print(f"Hourly delivery complete for {current_hour}:00")

    except Exception as e:
        print(f"Hourly delivery error: {e}")
        raise


async def send_daily_news_to_user(user_id: str):
    """特定ユーザーにニュースを送信（ユーザー設定に基づく）"""
    from app.services.social_scorer import get_top_articles
    from app.services.line_service import send_flex_message, get_user_settings

    try:
        # ユーザー設定を取得
        user_settings = await get_user_settings(user_id)
        categories = None
        language = "both"

        if user_settings:
            categories = user_settings.get_categories()
            language = user_settings.language

        # ユーザー設定に基づいて記事取得
        top_articles = await get_top_articles(
            count=settings.max_articles_per_delivery,
            categories=categories,
            language=language,
        )

        if not top_articles:
            from app.services.line_service import send_text_message
            await send_text_message(user_id, "現在配信できるニュースがありません。\n設定を変更すると、より多くの記事が表示される場合があります。")
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

    print(f"[_save_articles_to_db] Saving {len(articles)} articles to DB...")

    try:
        async with async_session() as session:
            saved_count = 0
            updated_count = 0

            for article in articles:
                article_id = _generate_article_id(article.url)
                print(f"[_save_articles_to_db] Processing: {article_id} - {article.title[:30]}...")

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
                    updated_count += 1
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
                    saved_count += 1

            await session.commit()
            print(f"[_save_articles_to_db] Complete: {saved_count} new, {updated_count} updated")

    except Exception as e:
        print(f"[_save_articles_to_db] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
