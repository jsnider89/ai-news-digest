"""Email composition and delivery via Resend."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Iterable, Sequence

import bleach
import markdown
import resend

logger = logging.getLogger("market_aggregator.email")


@dataclass
class DigestMetadata:
    newsletter_name: str
    ai_provider: str
    article_count: int
    feed_successes: int
    feed_total: int
    run_started_at: datetime


class DigestRenderer:
    """Render markdown analysis into locked HTML layout."""

    def __init__(self) -> None:
        self._markdown = markdown.Markdown(
            extensions=["extra", "toc", "abbr", "tables", "nl2br"],
            output_format="xhtml",
        )
        self._allowed_tags = set(bleach.sanitizer.ALLOWED_TAGS).union(
            {"p", "h1", "h2", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td", "hr"}
        )
        self._allowed_attrs = {"a": ["href", "title", "rel"], "th": ["align"], "td": ["align"]}

    def render(self, markdown_body: str, metadata: DigestMetadata) -> str:
        self._markdown.reset()
        dirty_html = self._markdown.convert(markdown_body or "")
        cleaned_html = bleach.clean(
            dirty_html,
            tags=self._allowed_tags,
            attributes=self._allowed_attrs,
            strip=True,
        )
        return _wrap_template(cleaned_html, metadata)


class ResendMailer:
    """Send rendered digests using Resend's email API."""

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        from_name: str,
        default_recipients: Sequence[str] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Resend API key is required")
        self.from_email = from_email
        self.from_name = from_name
        self._default_recipients = list(default_recipients or [])
        resend.api_key = api_key

    def send(
        self,
        *,
        subject: str,
        html_content: str,
        recipients: Iterable[str] | None = None,
        cc: Iterable[str] | None = None,
    ) -> bool:
        to_list = list(recipients or self._default_recipients)
        if not to_list:
            raise ValueError("At least one recipient is required")
        payload = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": to_list,
            "subject": subject,
            "html": html_content,
        }
        if cc:
            payload["cc"] = list(cc)
        try:
            resend.Emails.send(payload)
            logger.info("Sent digest to %s", ", ".join(to_list))
            return True
        except Exception as exc:  # pragma: no cover - network failure
            logger.exception("Failed to send email via Resend: %s", exc)
            return False


def _wrap_template(html_body: str, metadata: DigestMetadata) -> str:
    """Insert analysis HTML into locked template."""
    run_time = metadata.run_started_at.strftime("%Y-%m-%d %H:%M %Z")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{metadata.newsletter_name} Digest</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f5f5;
      margin: 0;
      padding: 0;
      color: #1f2933;
    }}
    .container {{
      max-width: 800px;
      margin: 0 auto;
      padding: 24px;
    }}
    .card {{
      background: #fff;
      border-radius: 16px;
      padding: 32px 28px;
      box-shadow: 0 18px 30px rgba(15, 23, 42, 0.08);
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 13px;
      color: #475467;
    }}
    .meta span {{
      background: #eef2ff;
      border-radius: 999px;
      padding: 6px 12px;
    }}
    .content h1, .content h2, .content h3 {{
      color: #111827;
      margin-top: 28px;
    }}
    .content table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }}
    .content table th,
    .content table td {{
      border: 1px solid #e5e7eb;
      padding: 8px 12px;
      text-align: left;
    }}
    .content ul {{
      padding-left: 20px;
    }}
    @media (max-width: 640px) {{
      .card {{ padding: 24px 20px; }}
      .meta {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1 style="margin-top: 0;">{metadata.newsletter_name} Digest</h1>
      <div class="meta">
        <span>AI Provider: {metadata.ai_provider}</span>
        <span>Articles: {metadata.article_count}</span>
        <span>Feeds: {metadata.feed_successes}/{metadata.feed_total}</span>
        <span>Run started: {run_time}</span>
      </div>
      <div class="content">{html_body}</div>
    </div>
  </div>
</body>
</html>
"""

