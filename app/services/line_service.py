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
from app.models import User, Article, Favorite, UserSettings, async_session


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


async def ensure_user_registered(line_user_id: str) -> User:
    """ユーザーが未登録の場合は登録する（サイレント登録）"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=str(uuid.uuid4()),
                line_user_id=line_user_id,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            print(f"[ensure_user_registered] New user registered: {line_user_id}")

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


async def add_favorite(line_user_id: str, article_id: str) -> tuple[bool, str]:
    """お気に入り追加

    Returns:
        tuple[bool, str]: (成功/失敗, エラーメッセージ)
    """
    async with async_session() as session:
        # ユーザー取得
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            print(f"[add_favorite] User not found: {line_user_id}")
            return False, "user_not_found"

        # 記事存在確認
        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()
        if not article:
            print(f"[add_favorite] Article not found: {article_id}")
            return False, "article_not_found"

        # 重複チェック
        result = await session.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.article_id == article_id
            )
        )
        if result.scalar_one_or_none():
            print(f"[add_favorite] Already favorited: user={user.id}, article={article_id}")
            return False, "already_favorited"

        favorite = Favorite(
            id=str(uuid.uuid4()),
            user_id=user.id,
            article_id=article_id,
        )
        session.add(favorite)
        await session.commit()
        print(f"[add_favorite] Success: user={user.id}, article={article_id}")
        return True, "success"


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


# ==================== ユーザー設定関連 ====================

async def get_user_settings(line_user_id: str) -> Optional[UserSettings]:
    """ユーザー設定を取得（なければデフォルト値で作成）"""
    async with async_session() as session:
        # ユーザー取得
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        # 設定取得
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        settings_obj = result.scalar_one_or_none()

        # なければ作成
        if not settings_obj:
            settings_obj = UserSettings(
                id=str(uuid.uuid4()),
                user_id=user.id,
            )
            session.add(settings_obj)
            await session.commit()
            await session.refresh(settings_obj)

        return settings_obj


async def update_user_delivery_hour(line_user_id: str, hour: int) -> bool:
    """配信時間を更新"""
    if not 0 <= hour <= 23:
        return False

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        settings_obj = result.scalar_one_or_none()

        if not settings_obj:
            settings_obj = UserSettings(
                id=str(uuid.uuid4()),
                user_id=user.id,
                delivery_hour=hour,
            )
            session.add(settings_obj)
        else:
            settings_obj.delivery_hour = hour

        await session.commit()
        return True


async def toggle_user_category(line_user_id: str, category: str) -> Optional[bool]:
    """カテゴリのON/OFFを切り替え。戻り値は切り替え後の状態（Noneはエラー）"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        settings_obj = result.scalar_one_or_none()

        if not settings_obj:
            settings_obj = UserSettings(
                id=str(uuid.uuid4()),
                user_id=user.id,
            )
            session.add(settings_obj)
            await session.flush()

        new_state = settings_obj.toggle_category(category)
        await session.commit()
        return new_state


async def update_user_language(line_user_id: str, language: str) -> bool:
    """言語設定を更新"""
    if language not in ("ja", "en", "both"):
        return False

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        settings_obj = result.scalar_one_or_none()

        if not settings_obj:
            settings_obj = UserSettings(
                id=str(uuid.uuid4()),
                user_id=user.id,
                language=language,
            )
            session.add(settings_obj)
        else:
            settings_obj.language = language

        await session.commit()
        return True


async def get_users_by_delivery_hour(hour: int) -> List[tuple]:
    """指定時間に配信設定しているアクティブユーザーを取得

    Returns:
        List[tuple]: [(line_user_id, categories, language), ...]
    """
    async with async_session() as session:
        # 設定があるユーザー
        result = await session.execute(
            select(User.line_user_id, UserSettings.categories, UserSettings.language)
            .join(UserSettings, UserSettings.user_id == User.id)
            .where(User.is_active == True)
            .where(UserSettings.delivery_hour == hour)
        )
        users_with_settings = list(result.all())

        # 設定がないユーザー（デフォルト8時）
        if hour == 8:
            result = await session.execute(
                select(User.line_user_id)
                .outerjoin(UserSettings, UserSettings.user_id == User.id)
                .where(User.is_active == True)
                .where(UserSettings.id == None)
            )
            users_without_settings = [(row[0], None, "both") for row in result.all()]
            users_with_settings.extend(users_without_settings)

        return users_with_settings
