# src/reporting/email_generator.py
# Complete email generator with markdown library support
# Requirements: pip install markdown

import markdown
import smtplib
import html
import re
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger("market_aggregator.email")

class EmailGenerator:
    """
    Secure email generator with professional markdown-to-HTML conversion
    """

    def __init__(self):
        # Get email configuration from environment
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')

        # Validate email configuration
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            missing = []
            if not self.sender_email: missing.append('SENDER_EMAIL')
            if not self.sender_password: missing.append('SENDER_PASSWORD')
            if not self.recipient_email: missing.append('RECIPIENT_EMAIL')

            error_msg = f"Missing email configuration: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize markdown processor with extensions
        self.md = markdown.Markdown(extensions=[
            'extra',        # Tables, code blocks, definition lists
            'nl2br',        # Convert single newlines to <br>
            'toc',          # Table of contents support
            'abbr',         # Abbreviation support
            'tables'        # Enhanced table support
        ])

        logger.info("Email generator initialized with markdown support")

    def sanitize_html_content(self, text: str) -> str:
        """
        Sanitize text content to prevent XSS vulnerabilities
        
        Args:
            text: Raw text that might contain HTML
            
        Returns:
            HTML-escaped safe text
        """
        if not text:
            return ""
        
        # Escape HTML characters to prevent XSS
        return html.escape(text)

    def convert_markdown_to_html(self, text: str) -> str:
        """
        Convert markdown to HTML using professional markdown library
        
        Args:
            text: Text with markdown formatting
            
        Returns:
            Clean, safe HTML
        """
        if not text:
            return ""

        try:
            # Reset the markdown processor for clean conversion
            self.md.reset()
            
            # Convert markdown to HTML
            html_content = self.md.convert(text)
            
            # Add custom styling for market data (pipe-separated values)
            html_content = self._enhance_market_data_formatting(html_content)
            
            return html_content
            
        except Exception as e:
            logger.error(f"Markdown conversion error: {e}")
            # Fallback to basic HTML escaping
            return f"<pre>{html.escape(text)}</pre>"

    def _enhance_market_data_formatting(self, html_content: str) -> str:
        """
        Add custom styling to market data lines (contains $ and emoji indicators)
        """
        # Find lines that look like market data: contain $, 🟢, or 🔴
        market_pattern = r'<p>([^<]*(?:\$[0-9.,]+|🟢|🔴)[^<]*)</p>'
        
        def format_market_line(match):
            content = match.group(1)
            # Style as a formatted market data row
            return f'<div class="market-data">{content}</div>'
        
        return re.sub(market_pattern, format_market_line, html_content)

    def create_html_email(self, ai_analysis: str, ai_provider: str,
                         article_count: int, successful_feeds: int,
                         total_feeds: int) -> str:
        """
        Create a professional, mobile-responsive HTML email with the analysis
        
        Args:
            ai_analysis: The AI-generated analysis text
            ai_provider: Name of AI provider used
            article_count: Number of articles processed
            successful_feeds: Number of feeds that loaded successfully
            total_feeds: Total number of feeds attempted
            
        Returns:
            Complete HTML email content
        """
        # Convert the analysis to HTML using markdown library
        analysis_html = self.convert_markdown_to_html(ai_analysis)

        # Enhanced HTML template with better CSS
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>📊 Daily Market & News Intelligence</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                    -webkit-text-size-adjust: 100%;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    max-width: 800px;
                    margin: 20px auto;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #2c3e50;
                }}
                .header h1 {{
                    color: #2c3e50;
                    margin: 0;
                    font-size: 28px;
                }}
                .meta {{
                    color: #666;
                    font-size: 14px;
                    text-align: center;
                    margin-top: 10px;
                    background-color: #f8f9fa;
                    padding: 10px;
                    border-radius: 5px;
                }}
                
                /* Markdown-generated content styling */
                .content h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 15px;
                    margin-top: 40px;
                    margin-bottom: 25px;
                    font-size: 26px;
                }}
                .content h2 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                    padding-top: 20px;
                    margin-bottom: 20px;
                    margin-top: 30px;
                    font-size: 22px;
                }}
                .content h3 {{
                    color: #2c3e50;
                    font-size: 18px;
                    margin-bottom: 15px;
                    margin-top: 25px;
                    padding-left: 10px;
                    border-left: 4px solid #3498db;
                }}
                .content p {{
                    color: #444;
                    margin: 12px 0;
                    line-height: 1.7;
                }}
                .content ul, .content ol {{
                    margin: 15px 0;
                    padding-left: 30px;
                }}
                .content li {{
                    margin: 8px 0;
                    line-height: 1.6;
                }}
                .content strong {{
                    color: #2c3e50;
                    font-weight: 700;
                }}
                .content table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                .content th, .content td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                .content th {{
                    background-color: #f8f9fa;
                    font-weight: 600;
                }}
                .content code {{
                    background-color: #f8f9fa;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
                    font-size: 0.9em;
                }}
                .content pre {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    overflow-x: auto;
                    border-left: 4px solid #3498db;
                }}
                
                /* Custom market data styling */
                .market-data {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border-radius: 6px;
                    padding: 10px 15px;
                    margin: 8px 0;
                    font-family: 'SF Mono', Monaco, monospace;
                    font-size: 14px;
                    border-left: 4px solid #3498db;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 2px solid #eee;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
                .status-good {{ color: #27ae60; }}
                .status-warning {{ color: #f39c12; }}
                .status-error {{ color: #e74c3c; }}

                /* Mobile responsiveness */
                @media screen and (max-width: 600px) {{
                    .container {{
                        width: 100% !important;
                        margin: 0;
                        padding: 15px;
                        border-radius: 0;
                        box-shadow: none;
                    }}
                    .header h1 {{
                        font-size: 22px;
                    }}
                    .content h1 {{ font-size: 22px; }}
                    .content h2 {{ font-size: 20px; }}
                    .content h3 {{ font-size: 18px; }}
                    .content ul, .content ol {{
                        padding-left: 20px;
                    }}
                    .content table {{
                        font-size: 12px;
                    }}
                }}
            </style>
        </head>
        <body style="padding: 20px 0;">
            <div class="container">
                <div class="header">
                    <h1>📊 Daily Market & News Intelligence</h1>
                    <div class="meta">
                        <strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}<br>
                        <strong>Analysis by:</strong> {html.escape(ai_provider)}<br>
                        <strong>Data Sources:</strong> {article_count:,} articles from {successful_feeds}/{total_feeds} feeds
                        {self._get_feed_status_indicator(successful_feeds, total_feeds)}
                    </div>
                </div>

                <div class="content">
                    {analysis_html}
                </div>

                <div class="footer">
                    <p><strong>🤖 AI Market Intelligence System</strong></p>
                    <p>Tracking: QQQ | SPY | UUP | IWM | GLD | COINBASE:BTCUSD | MP</p>
                    <p>This report was automatically generated with security-hardened data processing</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_template

    def _get_feed_status_indicator(self, successful: int, total: int) -> str:
        """Get a visual indicator for feed success rate"""
        if total == 0:
            return ' <span class="status-error">❌</span>'
        if successful == total:
            return ' <span class="status-good">✅</span>'
        elif successful >= total * 0.8:  # 80% or better
            return ' <span class="status-warning">⚠️</span>'
        else:
            return ' <span class="status-error">❌</span>'

    def send_report(self, ai_analysis: str, ai_provider: str,
                   article_count: int, successful_feeds: int,
                   total_feeds: int) -> bool:
        """
        Send the analysis report via email
        
        Args:
            ai_analysis: The AI-generated analysis
            ai_provider: Name of AI provider used
            article_count: Number of articles processed
            successful_feeds: Number of successful feed fetches
            total_feeds: Total feeds attempted
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            logger.info("Generating HTML email content...")

            # Create the HTML email content
            html_content = self.create_html_email(
                ai_analysis, ai_provider, article_count,
                successful_feeds, total_feeds
            )

            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📊 Market Intelligence Brief - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email

            # Create text version as fallback (strip HTML tags)
            text_content = re.sub(r'<[^>]+>', '', ai_analysis)
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            # Send via Gmail SMTP
            logger.info("Connecting to Gmail SMTP server...")
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()

                # Don't log the actual password
                logger.info("Authenticating with Gmail...")
                server.login(self.sender_email, self.sender_password)

                logger.info(f"Sending email to {self.recipient_email}...")
                server.send_message(msg)

            logger.info("✅ Email sent successfully!")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Email authentication failed - check credentials")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected email error: {e}")
            return False
