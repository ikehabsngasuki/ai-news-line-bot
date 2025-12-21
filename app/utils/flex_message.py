from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.social_scorer import ScoredArticle
    from app.models.article import Article
    from app.models.user_settings import UserSettings


def create_news_carousel(articles: List["ScoredArticle"]) -> dict:
    """ニュース配信用カルーセルFlex Message"""
    bubbles = []

    for i, article in enumerate(articles, 1):
        bubble = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"#{i}",
                                "size": "sm",
                                "weight": "bold",
                                "color": "#FFFFFF",
                            },
                            {
                                "type": "text",
                                "text": article.source[:15],
                                "size": "xs",
                                "color": "#FFFFFF",
                                "align": "end",
                            }
                        ]
                    }
                ],
                "backgroundColor": "#4A90D9",
                "paddingAll": "10px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": article.title[:60] + ("..." if len(article.title) > 60 else ""),
                        "weight": "bold",
                        "size": "sm",
                        "wrap": True,
                        "maxLines": 3,
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"Score: {article.popularity_score:,}",
                                "size": "xs",
                                "color": "#FF5551",
                                "weight": "bold",
                            },
                            {
                                "type": "text",
                                "text": f"HB:{article.hatena_count}",
                                "size": "xxs",
                                "color": "#888888",
                                "align": "end",
                            }
                        ],
                        "margin": "md",
                    }
                ],
                "spacing": "sm",
                "paddingAll": "12px",
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "読む",
                            "uri": article.url,
                        },
                        "style": "primary",
                        "height": "sm",
                        "flex": 2,
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "保存",
                            "data": f"action=favorite&article_id={_generate_article_id(article.url)}",
                        },
                        "style": "secondary",
                        "height": "sm",
                        "flex": 1,
                        "margin": "sm",
                    }
                ],
                "paddingAll": "10px",
            }
        }
        bubbles.append(bubble)

    return {
        "type": "carousel",
        "contents": bubbles,
    }


def create_favorites_list(articles: List["Article"]) -> dict:
    """お気に入り一覧Flex Message"""
    if not articles:
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "お気に入りはまだありません",
                        "align": "center",
                        "color": "#888888",
                    }
                ]
            }
        }

    bubbles = []
    for article in articles[:10]:  # 最大10件
        bubble = {
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": article.title[:50] + ("..." if len(article.title) > 50 else ""),
                        "weight": "bold",
                        "size": "sm",
                        "wrap": True,
                        "maxLines": 2,
                    },
                    {
                        "type": "text",
                        "text": article.source or "Unknown",
                        "size": "xs",
                        "color": "#888888",
                        "margin": "sm",
                    }
                ],
                "paddingAll": "12px",
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "読む",
                            "uri": article.url,
                        },
                        "style": "primary",
                        "height": "sm",
                        "flex": 2,
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "削除",
                            "data": f"action=unfavorite&article_id={article.id}",
                        },
                        "style": "secondary",
                        "height": "sm",
                        "flex": 1,
                        "margin": "sm",
                    }
                ],
                "paddingAll": "10px",
            }
        }
        bubbles.append(bubble)

    return {
        "type": "carousel",
        "contents": bubbles,
    }


def _generate_article_id(url: str) -> str:
    """URLからarticle_idを生成"""
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:16]


# ==================== 設定UI ====================

def create_settings_menu(settings: "UserSettings") -> dict:
    """設定メニューFlex Message"""
    from app.models.user_settings import CATEGORY_LABELS, LANGUAGE_LABELS

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "設定",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                }
            ],
            "backgroundColor": "#4A90D9",
            "paddingAll": "12px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                # 配信時間
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "配信時間",
                            "size": "sm",
                            "color": "#555555",
                            "flex": 3,
                        },
                        {
                            "type": "text",
                            "text": f"{settings.delivery_hour}:00",
                            "size": "sm",
                            "color": "#111111",
                            "weight": "bold",
                            "flex": 2,
                            "align": "end",
                        }
                    ],
                    "margin": "md",
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "時間を変更",
                        "data": "action=show_time_selector",
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "sm",
                },
                {
                    "type": "separator",
                    "margin": "lg",
                },
                # カテゴリ
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "カテゴリ",
                            "size": "sm",
                            "color": "#555555",
                            "flex": 3,
                        },
                        {
                            "type": "text",
                            "text": settings.get_categories_label(),
                            "size": "sm",
                            "color": "#111111",
                            "weight": "bold",
                            "flex": 2,
                            "align": "end",
                        }
                    ],
                    "margin": "lg",
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "カテゴリを変更",
                        "data": "action=show_category_selector",
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "sm",
                },
                {
                    "type": "separator",
                    "margin": "lg",
                },
                # 言語
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "言語",
                            "size": "sm",
                            "color": "#555555",
                            "flex": 3,
                        },
                        {
                            "type": "text",
                            "text": settings.get_language_label(),
                            "size": "sm",
                            "color": "#111111",
                            "weight": "bold",
                            "flex": 2,
                            "align": "end",
                        }
                    ],
                    "margin": "lg",
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "言語を変更",
                        "data": "action=show_language_selector",
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "sm",
                },
            ],
            "paddingAll": "12px",
        },
    }


def create_time_selector() -> dict:
    """配信時間選択Flex Message（時間帯ごとに分割）"""
    time_groups = [
        ("深夜・早朝", list(range(0, 6))),
        ("朝", list(range(6, 12))),
        ("午後", list(range(12, 18))),
        ("夜", list(range(18, 24))),
    ]

    bubbles = []
    for group_name, hours in time_groups:
        buttons = []
        for hour in hours:
            buttons.append({
                "type": "button",
                "action": {
                    "type": "postback",
                    "label": f"{hour}:00",
                    "data": f"action=set_hour&hour={hour}",
                },
                "style": "secondary",
                "height": "sm",
                "margin": "sm",
            })

        bubble = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"配信時間 - {group_name}",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#FFFFFF",
                    }
                ],
                "backgroundColor": "#4A90D9",
                "paddingAll": "10px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": buttons,
                "paddingAll": "8px",
            },
        }
        bubbles.append(bubble)

    return {
        "type": "carousel",
        "contents": bubbles,
    }


def create_category_selector(settings: "UserSettings") -> dict:
    """カテゴリ選択Flex Message"""
    from app.models.user_settings import CATEGORY_LABELS

    current_categories = settings.get_categories()

    buttons = []
    for cat_key, cat_label in CATEGORY_LABELS.items():
        is_selected = cat_key in current_categories
        buttons.append({
            "type": "button",
            "action": {
                "type": "postback",
                "label": f"{'[ON] ' if is_selected else '[OFF] '}{cat_label}",
                "data": f"action=toggle_category&category={cat_key}",
            },
            "style": "primary" if is_selected else "secondary",
            "height": "sm",
            "margin": "sm",
        })

    # 戻るボタン
    buttons.append({
        "type": "button",
        "action": {
            "type": "postback",
            "label": "設定に戻る",
            "data": "action=settings",
        },
        "style": "link",
        "height": "sm",
        "margin": "lg",
    })

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "カテゴリ選択",
                    "weight": "bold",
                    "size": "md",
                    "color": "#FFFFFF",
                },
                {
                    "type": "text",
                    "text": "興味のあるカテゴリをON/OFFしてください",
                    "size": "xs",
                    "color": "#FFFFFF",
                    "margin": "sm",
                }
            ],
            "backgroundColor": "#4A90D9",
            "paddingAll": "12px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": buttons,
            "paddingAll": "12px",
        },
    }


def create_language_selector(settings: "UserSettings") -> dict:
    """言語選択Flex Message"""
    from app.models.user_settings import LANGUAGE_LABELS

    current_lang = settings.language

    buttons = []
    for lang_key, lang_label in LANGUAGE_LABELS.items():
        is_selected = lang_key == current_lang
        buttons.append({
            "type": "button",
            "action": {
                "type": "postback",
                "label": f"{'● ' if is_selected else ''}{lang_label}",
                "data": f"action=set_language&lang={lang_key}",
            },
            "style": "primary" if is_selected else "secondary",
            "height": "sm",
            "margin": "sm",
        })

    # 戻るボタン
    buttons.append({
        "type": "button",
        "action": {
            "type": "postback",
            "label": "設定に戻る",
            "data": "action=settings",
        },
        "style": "link",
        "height": "sm",
        "margin": "lg",
    })

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "言語設定",
                    "weight": "bold",
                    "size": "md",
                    "color": "#FFFFFF",
                },
                {
                    "type": "text",
                    "text": "表示する記事の言語を選択してください",
                    "size": "xs",
                    "color": "#FFFFFF",
                    "margin": "sm",
                }
            ],
            "backgroundColor": "#4A90D9",
            "paddingAll": "12px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": buttons,
            "paddingAll": "12px",
        },
    }


def create_main_menu() -> dict:
    """メインメニューFlex Message（ボタン操作用）"""
    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "AI News Bot",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                },
                {
                    "type": "text",
                    "text": "メニューから選択してください",
                    "size": "xs",
                    "color": "#FFFFFF",
                    "margin": "sm",
                }
            ],
            "backgroundColor": "#4A90D9",
            "paddingAll": "12px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "今日のニュース",
                        "data": "action=today_news",
                    },
                    "style": "primary",
                    "height": "sm",
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "お気に入り一覧",
                        "data": "action=show_favorites",
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "sm",
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "設定",
                        "data": "action=settings",
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "sm",
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "ヘルプ",
                        "data": "action=help",
                    },
                    "style": "link",
                    "height": "sm",
                    "margin": "md",
                },
            ],
            "paddingAll": "12px",
        },
    }
