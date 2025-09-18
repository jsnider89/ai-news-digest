from datetime import datetime

from app.email.mailer import DigestMetadata, DigestRenderer


def test_digest_renderer_sanitises_html():
    renderer = DigestRenderer()
    metadata = DigestMetadata(
        newsletter_name="Test",
        ai_provider="openai",
        article_count=1,
        feed_successes=1,
        feed_total=1,
        run_started_at=datetime.utcnow(),
    )
    malicious = "# Heading\n\n<script>alert('xss')</script>\n\nLegit text."
    html = renderer.render(malicious, metadata)
    assert "<script" not in html
    assert "Legit text" in html
