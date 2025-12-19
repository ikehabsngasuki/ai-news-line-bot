import hashlib
import hmac
import base64
from fastapi import APIRouter, Request, HTTPException, Header

from app.config import settings
from app.services.line_service import (
    handler,
    register_user,
    deactivate_user,
    send_text_message,
    send_flex_message,
    add_favorite,
    remove_favorite,
    get_user_favorites,
    ensure_user_registered,
    get_user_settings,
    update_user_delivery_hour,
    toggle_user_category,
    update_user_language,
)
from app.utils.flex_message import (
    create_favorites_list,
    create_settings_menu,
    create_time_selector,
    create_category_selector,
    create_language_selector,
)

router = APIRouter()


def verify_signature(body: bytes, signature: str) -> bool:
    """LINE署名検証"""
    hash_value = hmac.new(
        settings.line_channel_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash_value).decode("utf-8")
    return hmac.compare_digest(signature, expected_signature)


@router.post("/webhook")
async def webhook(
    request: Request,
    x_line_signature: str = Header(None, alias="X-Line-Signature")
):
    """LINE Webhookエンドポイント"""
    body = await request.body()

    # 署名検証
    if not x_line_signature or not verify_signature(body, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # イベント解析
    import json
    events = json.loads(body.decode("utf-8")).get("events", [])

    for event in events:
        await handle_event(event)

    return {"status": "ok"}


async def handle_event(event: dict) -> None:
    """イベントハンドリング"""
    event_type = event.get("type")
    user_id = event.get("source", {}).get("userId")

    if not user_id:
        return

    if event_type == "follow":
        await handle_follow(user_id)

    elif event_type == "unfollow":
        await handle_unfollow(user_id)

    elif event_type == "message":
        # メッセージ受信時にユーザーを自動登録（未登録の場合）
        await ensure_user_registered(user_id)
        await handle_message(event, user_id)

    elif event_type == "postback":
        # Postback時もユーザーを自動登録
        await ensure_user_registered(user_id)
        await handle_postback(event, user_id)


async def handle_follow(user_id: str) -> None:
    """フォローイベント処理"""
    await register_user(user_id)
    await send_text_message(
        user_id,
        "友だち追加ありがとうございます!\n\n"
        "毎朝8時にAI技術の最新ニュースTOP5をお届けします。\n\n"
        "メニューから以下の操作ができます:\n"
        "- お気に入り一覧: 保存した記事を確認\n"
        "- 今日のニュース: 最新ニュースを再表示\n"
        "- ヘルプ: 使い方を確認"
    )


async def handle_unfollow(user_id: str) -> None:
    """アンフォローイベント処理"""
    await deactivate_user(user_id)


async def handle_message(event: dict, user_id: str) -> None:
    """メッセージイベント処理"""
    message = event.get("message", {})
    message_type = message.get("type")

    if message_type != "text":
        return

    text = message.get("text", "").strip()

    if text == "お気に入り一覧" or text == "お気に入り":
        await show_favorites(user_id)

    elif text == "今日のニュース" or text == "ニュース":
        from app.services.scheduler import send_daily_news_to_user
        await send_daily_news_to_user(user_id)

    elif text == "設定":
        await show_settings(user_id)

    elif text == "ヘルプ" or text == "help":
        await send_help(user_id)

    else:
        await send_text_message(
            user_id,
            "以下のコマンドが使えます:\n"
            "- 「お気に入り」: 保存した記事を表示\n"
            "- 「ニュース」: 最新ニュースを表示\n"
            "- 「設定」: 配信設定を変更\n"
            "- 「ヘルプ」: 使い方を確認"
        )


async def handle_postback(event: dict, user_id: str) -> None:
    """Postbackイベント処理"""
    data = event.get("postback", {}).get("data", "")
    params = dict(param.split("=") for param in data.split("&") if "=" in param)

    action = params.get("action")
    article_id = params.get("article_id")

    if action == "favorite" and article_id:
        success, reason = await add_favorite(user_id, article_id)
        if success:
            await send_text_message(user_id, "お気に入りに追加しました!")
        else:
            if reason == "user_not_found":
                await send_text_message(user_id, "ユーザー情報が見つかりません。友だち追加し直してください。")
            elif reason == "article_not_found":
                await send_text_message(user_id, "記事が見つかりません。再度ニュースを取得してからお試しください。")
            elif reason == "already_favorited":
                await send_text_message(user_id, "この記事は既にお気に入りに追加済みです。")
            else:
                await send_text_message(user_id, "お気に入りの追加に失敗しました。")

    elif action == "unfavorite" and article_id:
        success = await remove_favorite(user_id, article_id)
        if success:
            await send_text_message(user_id, "お気に入りから削除しました。")
        else:
            await send_text_message(user_id, "削除に失敗しました。")

    elif action == "show_favorites":
        await show_favorites(user_id)

    elif action == "today_news":
        from app.services.scheduler import send_daily_news_to_user
        await send_daily_news_to_user(user_id)

    elif action == "help":
        await send_help(user_id)

    # ========== 設定関連 ==========
    elif action == "settings":
        await show_settings(user_id)

    elif action == "show_time_selector":
        flex_content = create_time_selector()
        await send_flex_message(user_id, "配信時間を選択", flex_content)

    elif action == "set_hour":
        hour = int(params.get("hour", 8))
        success = await update_user_delivery_hour(user_id, hour)
        if success:
            await send_text_message(user_id, f"配信時間を {hour}:00 に設定しました。")
            await show_settings(user_id)
        else:
            await send_text_message(user_id, "設定の更新に失敗しました。")

    elif action == "show_category_selector":
        user_settings = await get_user_settings(user_id)
        if user_settings:
            flex_content = create_category_selector(user_settings)
            await send_flex_message(user_id, "カテゴリを選択", flex_content)
        else:
            await send_text_message(user_id, "設定の取得に失敗しました。")

    elif action == "toggle_category":
        category = params.get("category", "")
        new_state = await toggle_user_category(user_id, category)
        if new_state is not None:
            from app.models.user_settings import CATEGORY_LABELS
            cat_label = CATEGORY_LABELS.get(category, category)
            state_text = "ON" if new_state else "OFF"
            await send_text_message(user_id, f"「{cat_label}」を {state_text} にしました。")
            # カテゴリ選択画面を再表示
            user_settings = await get_user_settings(user_id)
            if user_settings:
                flex_content = create_category_selector(user_settings)
                await send_flex_message(user_id, "カテゴリを選択", flex_content)
        else:
            await send_text_message(user_id, "設定の更新に失敗しました。")

    elif action == "show_language_selector":
        user_settings = await get_user_settings(user_id)
        if user_settings:
            flex_content = create_language_selector(user_settings)
            await send_flex_message(user_id, "言語を選択", flex_content)
        else:
            await send_text_message(user_id, "設定の取得に失敗しました。")

    elif action == "set_language":
        lang = params.get("lang", "both")
        success = await update_user_language(user_id, lang)
        if success:
            from app.models.user_settings import LANGUAGE_LABELS
            lang_label = LANGUAGE_LABELS.get(lang, lang)
            await send_text_message(user_id, f"言語設定を「{lang_label}」に変更しました。")
            await show_settings(user_id)
        else:
            await send_text_message(user_id, "設定の更新に失敗しました。")


async def show_favorites(user_id: str) -> None:
    """お気に入り一覧表示"""
    from app.services.line_service import send_flex_message
    articles = await get_user_favorites(user_id)

    if not articles:
        await send_text_message(user_id, "お気に入りはまだありません。\n記事の「保存」ボタンで追加できます。")
        return

    flex_content = create_favorites_list(articles)
    await send_flex_message(user_id, "お気に入り一覧", flex_content)


async def show_settings(user_id: str) -> None:
    """設定メニュー表示"""
    user_settings = await get_user_settings(user_id)
    if user_settings:
        flex_content = create_settings_menu(user_settings)
        await send_flex_message(user_id, "設定", flex_content)
    else:
        await send_text_message(user_id, "設定の取得に失敗しました。")


async def send_help(user_id: str) -> None:
    """ヘルプメッセージ送信"""
    await send_text_message(
        user_id,
        "AI News Botの使い方\n\n"
        "【自動配信】\n"
        "設定した時間にAI技術の最新ニュースをお届けします。\n\n"
        "【お気に入り機能】\n"
        "記事の「保存」ボタンを押すと、後で読み返せます。\n\n"
        "【コマンド】\n"
        "「ニュース」: 最新ニュースを表示\n"
        "「お気に入り」: 保存した記事を表示\n"
        "「設定」: 配信時間/カテゴリ/言語を変更\n"
        "「ヘルプ」: この説明を表示"
    )
