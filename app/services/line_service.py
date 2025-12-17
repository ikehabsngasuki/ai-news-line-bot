from typing import List, Optional
import uuid

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    TextMessage,
    FlexMessage,
    FlexContainer,
    PushMessageRequest,
    BroadcastRequest,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Article, Favorite, async_session


configuration = Configuration(access_token=settings.line_channel_access_token)
handler = WebhookHandler(settings.line_channel_secret)


async def get_messaging_api() -> AsyncMessagingApi:
    """LINE Messaging API クライアント取得"""
    api_client = AsyncApiClient(configuration)
    return AsyncMessagingApi(api_client)


async def send_text_message(user_id: str, text: str) -> None:
    """テキストメッセージ送信"""
    api = await get_messaging_api()
    await api.push_message(
        PushMessageRequest(
            to=user_id,
            messages=[TextMessage(text=text)]
        )
    )


async def send_flex_message(user_id: str, alt_text: str, flex_content: dict) -> None:
    """Flex Message送信"""
    api = await get_messaging_api()
    await api.push_message(
        PushMessageRequest(
            to=user_id,
            messages=[
                FlexMessage(
                    alt_text=alt_text,
                    contents=FlexContainer.from_dict(flex_content)
                )
            ]
        )
    )


async def broadcast_flex_message(alt_text: str, flex_content: dict) -> None:
    """全ユーザーにFlex Messageをブロードキャスト"""
    api = await get_messaging_api()
    await api.broadcast(
        BroadcastRequest(
            messages=[
                FlexMessage(
                    alt_text=alt_text,
                    contents=FlexContainer.from_dict(flex_content)
                )
            ]
        )
    )


async def register_user(line_user_id: str, display_name: Optional[str] = None) -> User:
    """ユーザー登録（follow時）"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.is_active = True
            if display_name:
                user.display_name = display_name
        else:
            user = User(
                id=str(uuid.uuid4()),
                line_user_id=line_user_id,
                display_name=display_name,
                is_active=True,
            )
            session.add(user)

        await session.commit()
        return user


async def deactivate_user(line_user_id: str) -> None:
    """ユーザー無効化（unfollow時）"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            await session.commit()


async def add_favorite(line_user_id: str, article_id: str) -> bool:
    """お気に入り追加"""
    async with async_session() as session:
        # ユーザー取得
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        # 記事存在確認
        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()
        if not article:
            return False

        # 重複チェック
        result = await session.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.article_id == article_id
            )
        )
        if result.scalar_one_or_none():
            return False  # 既に登録済み

        favorite = Favorite(
            id=str(uuid.uuid4()),
            user_id=user.id,
            article_id=article_id,
        )
        session.add(favorite)
        await session.commit()
        return True


async def remove_favorite(line_user_id: str, article_id: str) -> bool:
    """お気に入り削除"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        result = await session.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.article_id == article_id
            )
        )
        favorite = result.scalar_one_or_none()
        if not favorite:
            return False

        await session.delete(favorite)
        await session.commit()
        return True


async def get_user_favorites(line_user_id: str) -> List[Article]:
    """ユーザーのお気に入り記事一覧取得"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return []

        result = await session.execute(
            select(Article)
            .join(Favorite, Favorite.article_id == Article.id)
            .where(Favorite.user_id == user.id)
            .order_by(Favorite.created_at.desc())
        )
        return list(result.scalars().all())
