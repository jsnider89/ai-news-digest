"""Newsletter pipeline execution."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Sequence

from app.ai.client import AIClient
from app.ai.prompts import build_prompt, load_system_prompt
from app.config.settings import get_settings
from app.data import repositories
from app.email.mailer import DigestMetadata, DigestRenderer, ResendMailer
from app.ingest.market_data import MarketDataClient
from app.ingest.rss import FeedDefinition, RSSFetcher

logger = logging.getLogger("market_aggregator.pipeline")


@dataclass
class NewsletterConfig:
    name: str
    feeds: Sequence[FeedDefinition]
    custom_prompt: str = ""
    newsletter_type: str = "general_business"
    verbosity_level: str = "medium"
    watchlist: Sequence[str] = field(default_factory=list)
    recipients: Sequence[str] | None = None


@dataclass
class RunResult:
    newsletter: NewsletterConfig
    success: bool
    ai_provider: str
    article_count: int
    feed_statuses: Sequence[str]
    started_at: datetime
    finished_at: datetime
    error: str | None = None
    token_usage: dict | None = None
    subject: str | None = None
    html_content: str | None = None


class NewsletterPipeline:
    """Coordinates ingestion, AI analysis, and emailing for a newsletter."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.renderer = DigestRenderer()
        self.mailer: ResendMailer | None = None
        # Mailer will be initialized with current settings when needed

    async def _get_current_mailer(self) -> ResendMailer | None:
        """Get mailer with current effective settings (env + database overrides)."""
        if not self.settings.resend_api_key:
            return None

        # Load current effective settings from database
        from app.data.database import SessionLocal

        async with SessionLocal() as session:
            overrides = await repositories.get_global_settings(session)

            recipients = overrides.get("default_recipients", self.settings.default_recipients)
            recipients = _coerce_recipient_list(recipients, fallback=self.settings.default_recipients)

            return ResendMailer(
                api_key=self.settings.resend_api_key,
                from_email=self.settings.resend_from_email,
                from_name=self.settings.resend_from_name,
                default_recipients=recipients,
            )

    async def run(self, config: NewsletterConfig) -> RunResult:
        started_at = datetime.utcnow()
        logger.info("Starting newsletter run for %s", config.name)

        ai_client = AIClient()
        rss_fetcher = RSSFetcher()
        market_client = MarketDataClient(api_key=os.getenv("FINNHUB_API_KEY"))

        try:
            articles, statuses = await rss_fetcher.fetch_many(list(config.feeds))
            ranked_articles = rank_articles(articles)
            watchlist = [ticker.upper() for ticker in config.watchlist if ticker]
            quotes = []
            if watchlist:
                quotes = await market_client.fetch_quotes(watchlist)
            market_text = format_market_data(quotes) if quotes else None
            articles_text = build_article_context(articles, ranked_articles=ranked_articles)

            prompt = build_prompt(
                articles_text=articles_text,
                market_text=market_text,
                watchlist=watchlist,
                newsletter_type=config.newsletter_type,
                custom_prompt=config.custom_prompt,
            )
            analysis, provider, usage = ai_client.generate(prompt, system_prompt=load_system_prompt(), verbosity=config.verbosity_level)
            if usage:
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
                total_tokens = usage.get("total_tokens")
                logger.info(
                    "AI usage (%s): prompt=%s, completion=%s, total=%s",
                    provider,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                )

            metadata = DigestMetadata(
                newsletter_name=config.name,
                ai_provider=provider,
                article_count=len(articles),
                feed_successes=sum(1 for status in statuses if status.startswith("✅")),
                feed_total=len(statuses),
                run_started_at=started_at,
            )
            html_content = self.renderer.render(analysis, metadata)

            # Get current mailer with effective settings
            current_mailer = await self._get_current_mailer()
            recipients = _coerce_recipient_list(config.recipients, fallback=None)
            subject = f"{config.name} Digest - {started_at.strftime('%Y-%m-%d')}"
            error_message = None
            success = False

            if not current_mailer:
                error_message = "Resend API key missing"
                logger.warning(error_message)
            else:
                success = current_mailer.send(
                    subject=subject,
                    html_content=html_content,
                    recipients=recipients,  # Use None to fall back to mailer's default recipients
                )
                if not success:
                    error_message = "Email send failed"

            finished_at = datetime.utcnow()
            return RunResult(
                newsletter=config,
                success=success,
                ai_provider=provider,
                article_count=len(articles),
                feed_statuses=statuses,
                started_at=started_at,
                finished_at=finished_at,
                error=error_message,
                token_usage=usage,
                subject=subject,
                html_content=html_content,
            )
        except Exception as exc:
            logger.exception("Newsletter run failed for %s", config.name)
            finished_at = datetime.utcnow()
            return RunResult(
                newsletter=config,
                success=False,
                ai_provider="",
                article_count=0,
                feed_statuses=[],
                started_at=started_at,
                finished_at=finished_at,
                error=str(exc),
                token_usage=None,
                subject=None,
                html_content=None,
            )
        finally:
            await rss_fetcher.close()
            await market_client.close()
            ai_client.close()


def build_article_context(
    articles: Sequence[dict],
    *,
    ranked_articles: Sequence[dict] | None = None,
    top_limit: int = 10,
    per_source_limit: int = 5,
) -> str:
    if not articles:
        return "No articles were retrieved from the configured feeds."

    ranked_articles = list(ranked_articles or [])
    lines: list[str] = []

    if ranked_articles:
        lines.append("## Top stories (prioritized by recency & cross-feed mentions)")
        for entry in ranked_articles[:top_limit]:
            title = entry.get("title", "").strip()
            if not title:
                continue
            sources = ", ".join(sorted(entry.get("sources", []) or [])) or "Unknown source"
            mention_count = entry.get("mention_count", 1)
            published_at = entry.get("latest")
            published_text = published_at.strftime("%Y-%m-%d %H:%M UTC") if isinstance(published_at, datetime) else "Unknown time"
            lines.append(
                f"- **{title}** — mentioned in {mention_count} feed{'s' if mention_count != 1 else ''}"
                f" ({sources}; published {published_text})"
            )
            description = entry.get("summary")
            if description:
                lines.append(f"  {description}")
            link = entry.get("link")
            if link:
                lines.append(f"  Source: {link}")
        lines.append("")

    grouped: dict[str, list[dict]] = {}
    for article in articles:
        source = article.get("source", "Unknown") or "Unknown"
        grouped.setdefault(source, []).append(article)

    for source, items in grouped.items():
        sorted_items = sorted(
            items,
            key=lambda item: (_parse_article_datetime(item.get("published_at")) or datetime.min, item.get("title", "")),
            reverse=True,
        )
        lines.append(f"### {source} ({len(items)} articles)")
        for entry in sorted_items[:per_source_limit]:
            title = (entry.get("title") or "").strip()
            if title:
                lines.append(f"- **{title}**")
            description = entry.get("description", "").strip()
            if description:
                lines.append(f"  {description}")
            link = entry.get("link")
            if link:
                lines.append(f"  Source: {link}")
        lines.append("")

    return "\n".join(lines).strip()


def format_market_data(quotes: Sequence[dict]) -> str:
    if not quotes:
        return ""
    headers = "| Symbol | Price | Change | % |\n| --- | ---: | ---: | ---: |"
    rows = []
    for quote in quotes:
        if quote.get("error"):
            rows.append(f"| {quote['symbol']} | N/A | {quote['error']} | |")
            continue
        rows.append(
            "| {symbol} | ${current:.2f} | {sign}{change:.2f} | {sign}{pct:.2f}% |".format(
                symbol=quote["symbol"],
                current=quote["current"],
                change=abs(quote["change"]),
                pct=abs(quote["change_percent"]),
                sign="+" if quote["change"] >= 0 else "-",
            )
        )
    return "\n".join([headers, *rows])


def _coerce_recipient_list(
    value: Sequence[str] | str | None,
    *,
    fallback: Sequence[str] | None,
) -> Sequence[str] | None:
    """Normalise recipient inputs into a clean list, or fall back when empty."""

    if value is None:
        return list(fallback) if isinstance(fallback, Sequence) else fallback

    items: list[str] = []

    def _flatten(candidate) -> None:
        if candidate is None:
            return
        if isinstance(candidate, str):
            stripped = candidate.strip()
            if not stripped:
                return
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)
                except (json.JSONDecodeError, TypeError):
                    parsed = None
                if parsed is not None:
                    _flatten(parsed)
                    return
            import re

            for part in re.split(r"[,\n]", candidate):
                entry = part.strip()
                if entry:
                    items.append(entry)
            return
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            for entry in candidate:
                _flatten(entry)
            return

        items.append(str(candidate).strip())

    _flatten(value)

    normalized = [entry for entry in (item.strip() for item in items) if entry]

    if normalized:
        seen: set[str] = set()
        unique: list[str] = []
        for entry in normalized:
            if entry not in seen:
                seen.add(entry)
                unique.append(entry)
        return unique

    return list(fallback) if isinstance(fallback, Sequence) else fallback


def rank_articles(
    articles: Sequence[dict],
    *,
    recent_hours: int = 24,
    decay_window_hours: int = 72,
) -> list[dict]:
    """Aggregate and score articles by recency and mention frequency."""

    if not articles:
        return []

    now = datetime.now(timezone.utc)
    recent_window = max(recent_hours, 1)
    decay_window = max(decay_window_hours, recent_window)

    aggregates: dict[str, dict] = {}

    for article in articles:
        key = _article_key(article)
        if not key:
            continue

        published_at = _parse_article_datetime(article.get("published_at"))
        normalized_source = article.get("source") or "Unknown"
        entry = aggregates.setdefault(
            key,
            {
                "title": article.get("title", "").strip(),
                "link": article.get("link"),
                "latest": published_at,
                "summary": (article.get("description", "") or "").strip(),
                "sources": set(),
                "mention_count": 0,
            },
        )

        if published_at and (entry["latest"] is None or published_at > entry["latest"]):
            entry["latest"] = published_at
            if article.get("description"):
                entry["summary"] = (article.get("description", "") or "").strip()
            if article.get("link"):
                entry["link"] = article.get("link")
            if article.get("title"):
                entry["title"] = article.get("title", "").strip()

        entry["sources"].add(normalized_source)
        entry["mention_count"] += 1

    ranked: list[dict] = []
    for data in aggregates.values():
        latest = data.get("latest") or datetime.min.replace(tzinfo=timezone.utc)
        age_hours = max((now - latest).total_seconds() / 3600, 0.0) if latest != datetime.min.replace(tzinfo=timezone.utc) else decay_window * 2
        recency_bonus = max(0.0, 1.0 - (age_hours / decay_window))
        recent_boost = 1.0 if age_hours <= recent_window else max(0.0, 1.0 - ((age_hours - recent_window) / decay_window))

        spread_factor = min(len(data["sources"]), data["mention_count"])
        score = (spread_factor * 2.5) + (data["mention_count"] * 0.5) + (recency_bonus * 3.0) + (recent_boost * 2.0)

        ranked.append(
            {
                **data,
                "latest": latest.replace(tzinfo=None),
                "sources": set(data["sources"]),
                "score": score,
            }
        )

    ranked.sort(
        key=lambda item: (
            -item["score"],
            -_datetime_to_timestamp(item.get("latest")),
            -item.get("mention_count", 0),
        )
    )

    for item in ranked:
        item["sources"] = list(item["sources"])

    return ranked


def _article_key(article: dict) -> str:
    link = (article.get("link") or "").strip().lower()
    if link:
        return link.split("#", 1)[0]
    title = (article.get("title") or "").strip().lower()
    return title


def _parse_article_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _datetime_to_timestamp(value: datetime | None) -> float:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc).timestamp()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()
