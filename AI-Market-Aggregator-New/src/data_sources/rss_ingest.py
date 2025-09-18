# src/data_sources/rss_ingest.py
import feedparser
import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger("market_aggregator.rss")

class RSSIngest:
    """
    Handles RSS feed ingestion using proper feedparser library
    Now reads feed configuration from feeds_config.json
    """
    
    def __init__(self, config_file: str = "feeds_config.json"):
        self.config_file = config_file
        self.load_config()
        
        self.session = requests.Session()
        # Use a more realistic browser User-Agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def load_config(self):
        """Load RSS feeds configuration from JSON file"""
        try:
            # Try multiple locations for the config file
            possible_paths = [
                Path(self.config_file),  # Current directory
                Path(__file__).parent.parent.parent / self.config_file,  # Repository root from src/data_sources/
                Path.cwd() / self.config_file,  # Current working directory
                Path("./feeds_config.json"),  # Explicit relative path
            ]
            
            config_path = None
            for path in possible_paths:
                logger.info(f"🔍 Checking for config at: {path.absolute()}")
                if path.exists():
                    config_path = path
                    logger.info(f"✅ Found config file at: {path.absolute()}")
                    break
                else:
                    logger.info(f"❌ Not found at: {path.absolute()}")
            
            if not config_path:
                logger.warning(f"Config file {self.config_file} not found in any location, using fallback feeds")
                self._use_fallback_config()
                return
            
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Extract enabled feeds only
            self.feeds = []
            enabled_count = 0
            disabled_count = 0
            
            for feed in config_data.get('rss_feeds', []):
                if feed.get('enabled', True):  # Default to enabled if not specified
                    self.feeds.append((feed['name'], feed['url']))
                    enabled_count += 1
                else:
                    disabled_count += 1
            
            # Load configuration settings
            self.config = config_data.get('config', {})
            self.max_articles = self.config.get('max_articles_per_feed', 5)
            self.default_timeout = self.config.get('default_timeout', 15)
            self.newsmax_timeout = self.config.get('newsmax_timeout', 10)
            self.rate_limit_delay = self.config.get('rate_limit_delay', 2)
            
            logger.info(f"✅ Config loaded: {enabled_count} enabled feeds, {disabled_count} disabled feeds")
            logger.info(f"✅ Settings: {self.max_articles} articles/feed, {self.default_timeout}s timeout")
            
            # List all enabled feeds for debugging
            logger.info("📝 Enabled feeds:")
            for i, (name, url) in enumerate(self.feeds, 1):
                logger.info(f"   {i}. {name}")
            
        except Exception as e:
            logger.error(f"Error loading config file {self.config_file}: {e}")
            logger.info("Using fallback configuration")
            self._use_fallback_config()

    def _use_fallback_config(self):
        """Fallback configuration if config file is not available"""
        self.feeds = [
            ('Federal Reserve - Press Monetary', 'https://www.federalreserve.gov/feeds/press_monetary.xml'),
            ('Fox News Latest', 'https://feeds.feedburner.com/foxnews/latest'),
            ('The Hill Home News', 'https://thehill.com/homenews/feed/'),
            ('MarketWatch Top Stories', 'https://feeds.content.dowjones.io/public/rss/mw_topstories'),
            ('CNBC Markets', 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664')
        ]
        
        # Default config values
        self.max_articles = 5
        self.default_timeout = 15
        self.newsmax_timeout = 10
        self.rate_limit_delay = 2
        
        logger.info(f"Using fallback configuration with {len(self.feeds)} feeds")

    def parse_single_feed(self, source_name: str, feed_url: str, max_articles: int = None) -> Tuple[str, List[Dict]]:
        """
        Parse a single RSS feed using feedparser (much more reliable than regex)
        
        Returns:
            Tuple of (status_message, list_of_articles)
        """
        if max_articles is None:
            max_articles = self.max_articles
            
        try:
            logger.info(f"Fetching feed: {source_name}")
            
            # Add small delay for rate limiting (especially for same-domain requests)
            import time
            import urllib.parse
            
            # Extract domain for rate limiting
            domain = urllib.parse.urlparse(feed_url).netloc
            if 'newsmax.com' in domain:
                # Extra delay for Newsmax since they seem to be rate limiting
                time.sleep(self.rate_limit_delay)
                # Shorter timeout for known problematic feeds
                timeout = self.newsmax_timeout
            else:
                timeout = self.default_timeout
            
            # Fetch the feed with appropriate timeout
            response = self.session.get(feed_url, timeout=timeout)
            
            # Check for rate limiting responses
            if response.status_code == 429:
                logger.warning(f"{source_name}: Rate limited (429), retrying after delay...")
                time.sleep(5)
                response = self.session.get(feed_url, timeout=timeout)
            
            response.raise_for_status()
            
            # Parse with feedparser - handles all the XML complexity for us
            feed = feedparser.parse(response.content)
            
            # Check if feed was parsed successfully
            if hasattr(feed, 'bozo') and feed.bozo:
                logger.warning(f"Feed {source_name} has parsing issues: {feed.bozo_exception}")
            
            articles = []
            
            # Process entries (feedparser handles both RSS and Atom feeds)
            for entry in feed.entries[:max_articles]:
                # Extract title
                title = getattr(entry, 'title', 'No title').strip()
                
                # Extract description/summary (feedparser handles CDATA automatically)
                description = ""
                if hasattr(entry, 'description'):
                    description = entry.description
                elif hasattr(entry, 'summary'):
                    description = entry.summary
                
                # Clean HTML tags from description
                if description:
                    import re
                    description = re.sub(r'<[^>]+>', '', description)
                    description = description.strip()
                    if len(description) > 300:
                        description = description[:300] + "..."
                
                # Extract date (feedparser normalizes date formats)
                pub_date = "No date"
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6]).isoformat()
                
                # Only add if we have a meaningful title
                if title and title != 'No title' and len(title) > 3:
                    articles.append({
                        'title': title,
                        'description': description,
                        'date': pub_date,
                        'source': source_name,
                        'link': getattr(entry, 'link', '')
                    })
            
            status = f"✅ {source_name} ({len(articles)} articles)"
            logger.info(f"Successfully parsed {len(articles)} articles from {source_name}")
            return status, articles
            
        except requests.exceptions.Timeout:
            error_msg = f"❌ {source_name}: Timeout after {timeout} seconds"
            logger.error(error_msg)
            return error_msg, []
            
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ {source_name}: Network error - {str(e)}"
            logger.error(error_msg)
            return error_msg, []
            
        except Exception as e:
            error_msg = f"❌ {source_name}: Parse error - {str(e)}"
            logger.error(error_msg)
            return error_msg, []

    def fetch_all_feeds(self) -> Tuple[List[Dict], List[str]]:
        """
        Fetch all RSS feeds sequentially (will make async in next phase)
        
        Returns:
            Tuple of (all_articles, feed_statuses)
        """
        all_articles = []
        feed_statuses = []
        
        logger.info(f"Starting to fetch {len(self.feeds)} RSS feeds...")
        
        for source_name, feed_url in self.feeds:
            status, articles = self.parse_single_feed(source_name, feed_url)
            feed_statuses.append(status)
            all_articles.extend(articles)
        
        logger.info(f"Completed RSS ingestion: {len(all_articles)} total articles")
        return all_articles, feed_statuses
    
    def __del__(self):
        """Clean up session when object is destroyed"""
        if hasattr(self, 'session'):
            self.session.close()
