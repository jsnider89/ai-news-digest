from app.data import models, repositories


def test_to_pipeline_config_ignores_disabled_feeds():
    newsletter = models.Newsletter(
        id=1,
        slug="test-newsletter",
        name="Test Newsletter",
        timezone="UTC",
        custom_prompt="",
        include_watchlist=False,
    )
    newsletter.feeds = [
        models.NewsletterFeed(
            id=1,
            newsletter_id=1,
            url="https://enabled.example/rss",
            title="Enabled Feed",
            category=None,
            order_index=0,
            enabled=True,
        ),
        models.NewsletterFeed(
            id=2,
            newsletter_id=1,
            url="https://disabled.example/rss",
            title="Disabled Feed",
            category=None,
            order_index=1,
            enabled=False,
        ),
    ]

    config = repositories.to_pipeline_config(newsletter)

    assert len(config.feeds) == 1
    assert config.feeds[0].url == "https://enabled.example/rss"
