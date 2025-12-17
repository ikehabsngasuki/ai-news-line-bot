import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass

import feedparser
import httpx

from app.config import settings


@dataclass
class CollectedArticle:
    url: str
    title: str
    summary: str
    source: str
    thumbnail_url: Optional[str]
    published_at: Optional[datetime]


# AI関連RSSフィード一覧
RSS_FEEDS = [
    {
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "name": "TechCrunch AI"
    },
    {
        "url": "https://venturebeat.com/category/ai/feed/",
        "name": "VentureBeat AI"
    },
    {
        "url": "https://www.artificialintelligence-news.com/feed/",
        "name": "AI News"
    },
    {
        "url": "https://blog.google/technology/ai/rss/",
        "name": "Google AI Blog"
    },
]

# Hacker News API
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


class NewsCollector:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def collect_all(self, hours: int = 24) -> List[CollectedArticle]:
        """全ソースから記事を収集"""
        articles = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # RSS収集
        rss_articles = await self._collect_from_rss(cutoff_time)
        articles.extend(rss_articles)

        # Hacker News収集
        hn_articles = await self._collect_from_hackernews(cutoff_time)
        articles.extend(hn_articles)

        # 重複排除（URLベース）
        seen_urls = set()
        unique_articles = []
        for article in articles:
            normalized_url = self._normalize_url(article.url)
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_articles.append(article)

        return unique_articles

    async def _collect_from_rss(self, cutoff_time: datetime) -> List[CollectedArticle]:
        """RSSフィードから記事収集"""
        articles = []

        for feed_info in RSS_FEEDS:
            try:
                response = await self.client.get(feed_info["url"])
                feed = feedparser.parse(response.text)

                for entry in feed.entries:
                    published = self._parse_feed_date(entry)
                    if published and published < cutoff_time:
                        continue

                    article = CollectedArticle(
                        url=entry.get("link", ""),
                        title=entry.get("title", "")[:500],
                        summary=self._clean_summary(entry.get("summary", ""))[:500],
                        source=feed_info["name"],
                        thumbnail_url=self._extract_thumbnail(entry),
                        published_at=published,
                    )
                    if article.url and article.title:
                        articles.append(article)

            except Exception as e:
                print(f"RSS収集エラー ({feed_info['name']}): {e}")
                continue

        return articles

    async def _collect_from_hackernews(self, cutoff_time: datetime) -> List[CollectedArticle]:
        """Hacker Newsから記事収集（AI関連のみ）"""
        articles = []
        ai_keywords = ["ai", "artificial intelligence", "machine learning", "ml",
                       "gpt", "llm", "openai", "anthropic", "claude", "chatgpt",
                       "deep learning", "neural", "transformer"]

        try:
            # Top Stories取得
            response = await self.client.get(f"{HN_API_BASE}/topstories.json")
            story_ids = response.json()[:100]  # 上位100件

            # 並列で記事詳細取得
            tasks = [self._fetch_hn_story(story_id) for story_id in story_ids[:50]]
            stories = await asyncio.gather(*tasks, return_exceptions=True)

            for story in stories:
                if isinstance(story, Exception) or not story:
                    continue

                title_lower = story.get("title", "").lower()
                if not any(kw in title_lower for kw in ai_keywords):
                    continue

                published = datetime.fromtimestamp(story.get("time", 0))
                if published < cutoff_time:
                    continue

                url = story.get("url", "")
                if not url:
                    url = f"https://news.ycombinator.com/item?id={story.get('id')}"

                article = CollectedArticle(
                    url=url,
                    title=story.get("title", "")[:500],
                    summary="",
                    source="Hacker News",
                    thumbnail_url=None,
                    published_at=published,
                )
                articles.append(article)

        except Exception as e:
            print(f"Hacker News収集エラー: {e}")

        return articles

    async def _fetch_hn_story(self, story_id: int) -> Optional[dict]:
        """Hacker News記事詳細取得"""
        try:
            response = await self.client.get(f"{HN_API_BASE}/item/{story_id}.json")
            return response.json()
        except Exception:
            return None

    def _parse_feed_date(self, entry) -> Optional[datetime]:
        """RSSフィードの日付をパース"""
        date_fields = ["published_parsed", "updated_parsed", "created_parsed"]
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    time_tuple = getattr(entry, field)
                    return datetime(*time_tuple[:6])
                except Exception:
                    continue
        return None

    def _clean_summary(self, summary: str) -> str:
        """サマリーからHTMLタグを除去"""
        import re
        clean = re.sub(r"<[^>]+>", "", summary)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _extract_thumbnail(self, entry) -> Optional[str]:
        """記事からサムネイルURLを抽出"""
        # media:thumbnail
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            return entry.media_thumbnail[0].get("url")

        # enclosure
        if hasattr(entry, "enclosures") and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("image"):
                    return enc.get("href")

        return None

    def _normalize_url(self, url: str) -> str:
        """URLを正規化して重複判定用に使用"""
        url = url.lower().strip()
        url = url.rstrip("/")
        # クエリパラメータを除去
        if "?" in url:
            url = url.split("?")[0]
        return url
