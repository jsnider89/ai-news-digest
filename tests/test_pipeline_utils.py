from datetime import datetime, timedelta, timezone

from app.tasks.pipeline import _coerce_recipient_list, build_article_context, rank_articles


def test_coerce_recipient_list_parses_json_string():
    result = _coerce_recipient_list('["user@example.com"]', fallback=None)
    assert result == ["user@example.com"]


def test_coerce_recipient_list_splits_delimiters_and_deduplicates():
    raw = "alice@example.com, bob@example.com\nalice@example.com"
    result = _coerce_recipient_list(raw, fallback=None)
    assert result == ["alice@example.com", "bob@example.com"]


def test_coerce_recipient_list_uses_fallback_when_empty():
    fallback = ["fallback@example.com"]
    result = _coerce_recipient_list([], fallback=fallback)
    assert result == fallback


def test_coerce_recipient_list_returns_none_when_no_value_and_no_fallback():
    assert _coerce_recipient_list(None, fallback=None) is None


def test_rank_articles_prefers_recent_articles():
    now = datetime.now(timezone.utc)
    articles = [
        {
            "title": "Old Story",
            "link": "https://example.com/old",
            "published_at": (now - timedelta(hours=30)).isoformat(),
            "source": "Feed A",
            "description": "Old content",
        },
        {
            "title": "Fresh Story",
            "link": "https://example.com/fresh",
            "published_at": (now - timedelta(hours=2)).isoformat(),
            "source": "Feed B",
            "description": "Fresh content",
        },
    ]

    ranked = rank_articles(articles, recent_hours=24)

    assert ranked[0]["title"] == "Fresh Story"


def test_rank_articles_rewards_cross_feed_mentions():
    now = datetime.now(timezone.utc)
    articles = [
        {
            "title": "Shared Story",
            "link": "https://example.com/shared",
            "published_at": (now - timedelta(hours=3)).isoformat(),
            "source": "Feed A",
        },
        {
            "title": "Shared Story",
            "link": "https://example.com/shared",
            "published_at": (now - timedelta(hours=3)).isoformat(),
            "source": "Feed B",
        },
        {
            "title": "Single Story",
            "link": "https://example.com/single",
            "published_at": (now - timedelta(hours=1)).isoformat(),
            "source": "Feed C",
        },
    ]

    ranked = rank_articles(articles, recent_hours=24)

    assert ranked[0]["title"] == "Shared Story"
    assert ranked[0]["mention_count"] == 2


def test_build_article_context_includes_top_section():
    now = datetime.now(timezone.utc)
    articles = [
        {
            "title": "Story One",
            "link": "https://example.com/one",
            "published_at": (now - timedelta(hours=1)).isoformat(),
            "source": "Feed A",
            "description": "First description",
        },
        {
            "title": "Story One",
            "link": "https://example.com/one",
            "published_at": (now - timedelta(hours=1)).isoformat(),
            "source": "Feed B",
            "description": "Second description",
        },
    ]

    ranked = rank_articles(articles, recent_hours=24)
    context = build_article_context(articles, ranked_articles=ranked, top_limit=5)

    assert "Top stories" in context
    assert "Story One" in context
    assert "Feed A" in context
