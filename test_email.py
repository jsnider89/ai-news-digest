#!/usr/bin/env python3
"""Quick test script to verify email sending functionality."""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from app.email.mailer import DigestRenderer, DigestMetadata, ResendMailer

load_dotenv()  # Load environment variables from .env file


async def test_email_send():
    """Test sending a simple email digest."""

    # Check if required environment variables are set
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "market-intel@yourdomain.com")
    from_name = os.getenv("RESEND_FROM_NAME", "Market Aggregator")
    recipients = os.getenv("DEFAULT_RECIPIENTS", "").split(",")
    recipients = [r.strip() for r in recipients if r.strip()]

    if not api_key:
        print("❌ RESEND_API_KEY not set in .env file")
        print("Please get your API key from https://resend.com/api-keys")
        return False

    if not recipients:
        print("❌ DEFAULT_RECIPIENTS not set in .env file")
        print("Please add at least one email address to DEFAULT_RECIPIENTS")
        return False

    print(f"📧 Testing email send to: {', '.join(recipients)}")
    print(f"📮 From: {from_name} <{from_email}>")

    # Create test digest content
    markdown_content = """
# Market Update - Test

## Key Highlights
- This is a test email from your AI Market Aggregator
- Email configuration is working properly
- Ready to process real market data

## Next Steps
1. Add your AI provider API keys to .env
2. Create newsletters via the web dashboard
3. Configure RSS feeds and schedules

**System Status**: ✅ Email delivery operational
"""

    # Create metadata
    metadata = DigestMetadata(
        newsletter_name="Test Newsletter",
        ai_provider="System Test",
        article_count=3,
        feed_successes=2,
        feed_total=2,
        run_started_at=datetime.now()
    )

    # Render the email
    renderer = DigestRenderer()
    html_content = renderer.render(markdown_content, metadata)

    # Send the email
    try:
        mailer = ResendMailer(
            api_key=api_key,
            from_email=from_email,
            from_name=from_name,
            default_recipients=recipients
        )

        success = mailer.send(
            subject="✅ AI Market Aggregator - Email Test Successful",
            html_content=html_content
        )

        if success:
            print("✅ Test email sent successfully!")
            print("Check your inbox for the test digest.")
            return True
        else:
            print("❌ Failed to send test email. Check the logs for details.")
            return False

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing AI Market Aggregator Email Functionality")
    print("=" * 50)

    success = asyncio.run(test_email_send())

    if success:
        print("\n🎉 Email system is ready!")
        print("You can now:")
        print("1. Start the web server with: uvicorn app.web.main:app --reload")
        print("2. Create newsletters via the dashboard at http://localhost:8000")
    else:
        print("\n⚠️  Please fix the configuration issues above before proceeding.")