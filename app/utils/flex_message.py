from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.social_scorer import ScoredArticle
    from app.models.article import Article


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
