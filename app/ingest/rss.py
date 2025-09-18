"""RSS ingestion helpers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Iterable, List, Sequence

import feedparser
import httpx

logger = logging.getLogger("market_aggregator.ingest.rss")


@dataclass
class FeedDefinition:
    """Simple container representing an RSS feed."""

    name: str
    url: str
    category: str | None = None


class RSSFetcher:
    """Fetch and parse RSS feeds asynchronously."""

    def __init__(
        self,
        *,
        max_articles_per_feed: int = 10,
        request_timeout: float = 15.0,
        concurrent_requests: int = 5,
    ) -> None:
        self.max_articles_per_feed = max_articles_per_feed
        self.request_timeout = request_timeout
        self.semaphore = asyncio.Semaphore(concurrent_requests)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=5.0, pool=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; FeedReader/1.0; +https://github.com/aggregator)",
                "Accept": "application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _fetch(self, feed: FeedDefinition) -> tuple[str, list[dict]]:
        status = f"❌ {feed.name}: Unprocessed"
        articles: list[dict] = []

        # Retry logic for flaky feeds
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.semaphore:
                    response = await self._client.get(feed.url)
                    response.raise_for_status()
                parsed = feedparser.parse(response.content)
                break  # Success, exit retry loop
            except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == max_retries - 1:  # Last attempt
                    logger.error("Failed to fetch feed %s after %d attempts: %s", feed.name, max_retries, e)
                    return status, articles
                else:
                    logger.warning("Attempt %d failed for feed %s, retrying: %s", attempt + 1, feed.name, e)
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except Exception as e:
                logger.error("Failed to fetch feed %s: %s", feed.name, e)
                return status, articles

        try:

            entries = parsed.entries[: self.max_articles_per_feed]
            for entry in entries:
                title = getattr(entry, "title", "").strip()
                if not title:
                    continue
                description = getattr(entry, "summary", getattr(entry, "description", "")) or ""
                if description:
                    description = _strip_html(description)
                pub_date = _coerce_datetime(entry)
                articles.append(
                    {
                        "title": title,
                        "description": description,
                        "link": getattr(entry, "link", ""),
                        "published_at": pub_date,
                        "source": feed.name,
                        "category": feed.category,
                    }
                )
            status = f"✅ {feed.name} ({len(articles)} articles)"
        except httpx.TimeoutException:
            status = f"❌ {feed.name}: Timeout after {self.request_timeout}s"
            logger.warning(status)
        except Exception as exc:  # pragma: no cover - best effort logging
            status = f"❌ {feed.name}: {exc}"[:180]
            logger.exception("Failed to fetch feed %s", feed.name)
        return status, articles

    async def fetch_many(self, feeds: Sequence[FeedDefinition]) -> tuple[list[dict], list[str]]:
        """Fetch and parse multiple feeds concurrently."""
        tasks = [self._fetch(feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        articles: list[dict] = []
        statuses: list[str] = []
        for status, items in results:
            statuses.append(status)
            articles.extend(items)
        return articles, statuses


def _strip_html(value: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", "", value)
    text = text.replace("&nbsp;", " ").strip()
    if len(text) > 400:
        text = f"{text[:397]}..."
    return text


def _coerce_datetime(entry: object) -> str:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        dt_tuple = getattr(entry, attr, None)
        if dt_tuple:
            try:
                return datetime(*dt_tuple[:6]).isoformat()
            except Exception:  # pragma: no cover - fallback to created
                continue
    return ""


async def fetch_feeds(feeds: Iterable[FeedDefinition], **kwargs) -> tuple[list[dict], list[str]]:
    """Convenience helper for one-off uses."""
    fetcher = RSSFetcher(**kwargs)
    try:
        return await fetcher.fetch_many(list(feeds))
    finally:
        await fetcher.close()

