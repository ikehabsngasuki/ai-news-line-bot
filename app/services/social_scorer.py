import re
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx

from app.services.news_collector import CollectedArticle, CATEGORY_KEYWORDS


@dataclass
class ScoredArticle:
    url: str
    title: str
    summary: str
    source: str
    thumbnail_url: str
    published_at: any
    hatena_count: int
    hackernews_score: int
    reddit_score: int
    source_count: int
    popularity_score: int


# スコアリングの重み
WEIGHTS = {
    "hatena": 3.0,       # はてブ1件 = 3点
    "hackernews": 2.0,   # HNスコア1 = 2点
    "reddit": 1.0,       # Redditスコア1 = 1点
    "source_count": 10.0 # 複数ソース掲載ボーナス
}


class SocialScorer:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self.client.aclose()

    async def score_articles(self, articles: List[CollectedArticle]) -> List[ScoredArticle]:
        """記事リストにスコアを付与"""
        tasks = [self._score_single(article) for article in articles]
        scored = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for item in scored:
            if isinstance(item, ScoredArticle):
                results.append(item)

        # スコア順にソート
        results.sort(key=lambda x: x.popularity_score, reverse=True)
        return results

    async def _score_single(self, article: CollectedArticle) -> ScoredArticle:
        """単一記事のスコアリング"""
        hatena_count = await self._get_hatena_count(article.url)
        hn_score = await self._get_hackernews_score(article.url)
        reddit_score = 0  # Reddit APIは認証が複雑なため初期実装では省略

        # ソース数（同じURLが複数ソースで取り上げられている場合）
        source_count = 1

        # 総合スコア計算
        popularity_score = int(
            hatena_count * WEIGHTS["hatena"] +
            hn_score * WEIGHTS["hackernews"] +
            reddit_score * WEIGHTS["reddit"] +
            (source_count - 1) * WEIGHTS["source_count"]
        )

        return ScoredArticle(
            url=article.url,
            title=article.title,
            summary=article.summary,
            source=article.source,
            thumbnail_url=article.thumbnail_url or "",
            published_at=article.published_at,
            hatena_count=hatena_count,
            hackernews_score=hn_score,
            reddit_score=reddit_score,
            source_count=source_count,
            popularity_score=popularity_score,
        )

    async def _get_hatena_count(self, url: str) -> int:
        """はてなブックマーク数を取得"""
        try:
            api_url = f"https://bookmark.hatenaapis.com/count/entry?url={url}"
            response = await self.client.get(api_url)
            if response.status_code == 200:
                return int(response.text)
        except Exception as e:
            print(f"はてブAPI エラー: {e}")
        return 0

    async def _get_hackernews_score(self, url: str) -> int:
        """Hacker Newsでの該当記事スコアを取得"""
        try:
            # Algolia HN Search API
            api_url = f"https://hn.algolia.com/api/v1/search?query={url}&restrictSearchableAttributes=url"
            response = await self.client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", [])
                if hits:
                    # 最もスコアの高いものを返す
                    return max(hit.get("points", 0) for hit in hits)
        except Exception as e:
            print(f"HN Search API エラー: {e}")
        return 0


def detect_language(text: str) -> str:
    """テキストの言語を判定（日本語/英語）"""
    # 日本語文字（ひらがな/カタカナ/漢字）を含むか判定
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text):
        return "ja"
    return "en"


def match_category(text: str, categories: List[str]) -> bool:
    """テキストが指定カテゴリのキーワードにマッチするか判定"""
    if not categories:
        return False

    text_lower = text.lower()
    for category in categories:
        keywords = CATEGORY_KEYWORDS.get(category, [])
        for keyword in keywords:
            if keyword in text_lower:
                return True
    return False


def filter_articles(
    articles: List[ScoredArticle],
    categories: Optional[List[str]] = None,
    language: str = "both"
) -> List[ScoredArticle]:
    """記事をカテゴリと言語でフィルタリング"""
    filtered = []

    for article in articles:
        # カテゴリフィルター（設定があれば適用）
        if categories:
            search_text = f"{article.title} {article.summary}"
            if not match_category(search_text, categories):
                continue

        # 言語フィルター
        if language != "both":
            article_lang = detect_language(article.title)
            if article_lang != language:
                continue

        filtered.append(article)

    return filtered


async def get_top_articles(
    count: int = 5,
    categories: Optional[List[str]] = None,
    language: str = "both"
) -> List[ScoredArticle]:
    """人気記事Top Nを取得（フィルタリング対応）"""
    from app.services.news_collector import NewsCollector
    from app.config import settings

    collector = NewsCollector()
    scorer = SocialScorer()

    try:
        # 記事収集
        articles = await collector.collect_all(hours=settings.article_fetch_hours)
        print(f"収集記事数: {len(articles)}")

        # スコアリング
        scored_articles = await scorer.score_articles(articles)
        print(f"スコアリング完了: {len(scored_articles)}件")

        # フィルタリング（カテゴリ/言語）
        if categories or language != "both":
            scored_articles = filter_articles(scored_articles, categories, language)
            print(f"フィルタリング後: {len(scored_articles)}件 (categories={categories}, language={language})")

        # Top N返却
        return scored_articles[:count]

    finally:
        await collector.close()
        await scorer.close()
