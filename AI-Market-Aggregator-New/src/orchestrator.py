# src/orchestrator.py
"""
Main orchestrator that coordinates all components
This replaces the monolithic AIMarketAggregator class
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# Import our new modular components
from src.utils.logging_config import setup_logging, validate_environment
from src.data_sources.rss_ingest import RSSIngest
from src.data_sources.market_data import MarketDataClient
from src.analysis.llm_client import AIClient
from src.reporting.email_generator import EmailGenerator

class MarketIntelligenceOrchestrator:
    """
    Main orchestrator that coordinates all market intelligence components
    
    This replaces the original monolithic class with a clean, modular design
    """
    
    def __init__(self):
        # Set up secure logging first
        self.logger = setup_logging()
        
        # Validate environment before proceeding
        missing_vars = validate_environment()
        if missing_vars:
            error_msg = "Missing required environment variables:\n"
            for category, vars_list in missing_vars.items():
                error_msg += f"  {category}: {vars_list}\n"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize all components
        self.logger.info("Initializing Market Intelligence System...")
        
        try:
            self.rss_client = RSSIngest()
            self.logger.info("✅ RSS ingestion client initialized")
            
            self.market_client = MarketDataClient()
            self.logger.info("✅ Market data client initialized")
            
            self.ai_client = AIClient()
            self.logger.info("✅ AI analysis client initialized")
            
            self.email_generator = EmailGenerator()
            self.logger.info("✅ Email generator initialized")
            
            self.logger.info("🚀 All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise

    def create_enhanced_prompt(self, market_data_text: str, articles: List[Dict]) -> str:
        """
        Create an enhanced AI prompt that leverages reasoning capabilities
        
        Args:
            market_data_text: Formatted market data string
            articles: List of article dictionaries from RSS feeds
            
        Returns:
            Enhanced prompt string for AI analysis
        """
        # Group articles by source for better analysis
        articles_by_source = {}
        for article in articles:
            source = article['source']
            if source not in articles_by_source:
                articles_by_source[source] = []
            articles_by_source[source].append(article)
        
        # Format articles with source grouping
        articles_text = []
        for source, source_articles in articles_by_source.items():
            articles_text.append(f"\n=== {source} ({len(source_articles)} articles) ===")
            for i, article in enumerate(source_articles[:5], 1):
                articles_text.append(f"Article {i}:")
                articles_text.append(f"Title: {article['title']}")
                if article['description']:
                    articles_text.append(f"Summary: {article['description']}")
                articles_text.append(f"Date: {article['date']}")
                articles_text.append("")
        
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime('%A, %B %d')
        
        # Enhanced prompt for AI analysis
        prompt = f"""Analyze the following market data and news articles to create a comprehensive daily briefing. Use your reasoning capabilities to identify patterns, assess market sentiment, and determine the most significant developments.

## TODAY'S MARKET DATA:
{market_data_text}

## NEWS ARTICLES FROM {len(articles_by_source)} SOURCES:
Total articles: {len(articles)}
{chr(10).join(articles_text)}

## ANALYSIS INSTRUCTIONS:

When creating the briefing, use your analytical capabilities to:
1. Identify recurring themes across multiple news sources (stories covered by 3+ sources are especially important)
2. Assess the overall market sentiment based on both price movements and news tone
3. Calculate potential market impact of major news events
4. Detect any divergences between market performance and news sentiment

Create a daily briefing with THREE DISTINCT SECTIONS:

**SECTION 1 - MARKET PERFORMANCE:**
Present the market data with analysis of notable movements and patterns. For each ticker, show:
- The symbol
- Current/closing price
- Change in dollars
- Change in percentage
- Use 🟢 for positive changes and 🔴 for negative changes
- NOTE - Do not provide a summary of each market symbol. Only do the overarching market summary using the analyzed price movement as a source.

**SECTION 2 - TOP MARKET & ECONOMY STORIES (5 stories):**
Use pattern recognition to identify the 5 most significant market/economy stories based on:
- Cross-source validation (stories appearing in multiple sources)
- Temporal relevance (newest stories weighted higher)
- Market impact potential
- Federal Reserve, economic data, or major financial institution news

**SECTION 3 - GENERAL NEWS STORIES (10 stories):**
Identify the 10 most important non-financial stories using similar cross-source analysis.

**CRITICAL INSTRUCTIONS FOR ALL STORIES:**
- You MUST provide COMPLETE details for ALL 15 stories (5 market + 10 general)
- DO NOT abbreviate or say "additional stories available upon request"
- DO NOT use placeholders like "5-10: See full briefing"
- EVERY story needs:
  * A clear, descriptive headline
  * A FULL paragraph (4-6 sentences) explaining what happened, why it's significant, context, and implications
  * Source attribution showing which outlets reported it
- Number the stories clearly: 1-5 for market stories, 1-10 for general news

**LOOKING AHEAD - {tomorrow_str}:**
Based on patterns in today's news, identify specific events scheduled for tomorrow and key themes to monitor. Be specific with times if mentioned. If no specific events are mentioned for tomorrow, note key themes to watch.

IMPORTANT: This is an automated daily briefing. Provide ALL 15 stories with COMPLETE details. Do not truncate or abbreviate any section. The full analysis is required for each story."""

        return prompt

    def run_analysis(self) -> Dict:
        """
        Main execution method that orchestrates the entire analysis process
        
        Returns:
            Dictionary with execution results and metrics
        """
        start_time = datetime.now()
        self.logger.info("🚀 Starting Market Intelligence Analysis")
        self.logger.info(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        results = {
            'start_time': start_time.isoformat(),
            'success': False,
            'errors': [],
            'metrics': {}
        }
        
        try:
            # Step 1: Fetch market data
            self.logger.info("📊 Step 1: Fetching market data...")
            market_quotes = self.market_client.fetch_all_quotes()
            market_data_text = self.market_client.format_market_data_text(market_quotes)
            results['metrics']['market_symbols'] = len(market_quotes)
            self.logger.info(f"✅ Market data collected for {len(market_quotes)} symbols")
            
            # Step 2: Fetch RSS feeds
            self.logger.info("📰 Step 2: Collecting news articles...")
            articles, feed_statuses = self.rss_client.fetch_all_feeds()
            results['metrics']['articles_collected'] = len(articles)
            results['metrics']['feeds_processed'] = len(feed_statuses)
            
            # Log feed statuses for monitoring
            successful_feeds = len([s for s in feed_statuses if '✅' in s])
            failed_feeds = len([s for s in feed_statuses if '❌' in s])
            self.logger.info(f"✅ RSS collection complete: {len(articles)} articles from {successful_feeds} successful feeds, {failed_feeds} failed feeds")
            
            # Step 3: Generate AI analysis
            self.logger.info(f"🤖 Step 3: Generating AI analysis...")
            prompt = self.create_enhanced_prompt(market_data_text, articles)
            results['metrics']['prompt_length'] = len(prompt)
            
            ai_analysis, ai_provider = self.ai_client.generate_analysis(prompt)
            results['metrics']['ai_provider'] = ai_provider
            self.logger.info(f"✅ AI analysis completed using {ai_provider}")
            
            # Step 4: Generate and send email
            self.logger.info("📧 Step 4: Generating and sending email report...")
            email_sent = self.email_generator.send_report(
                ai_analysis, 
                ai_provider,
                len(articles),
                successful_feeds,
                failed_feeds
            )
            
            results['success'] = email_sent
            results['metrics']['email_sent'] = email_sent
            
            # Calculate execution time
            end_time = datetime.now()
            execution_time = end_time - start_time
            results['end_time'] = end_time.isoformat()
            results['execution_time_seconds'] = execution_time.total_seconds()
            
            # Log final summary
            self.logger.info("=" * 60)
            self.logger.info("📊 EXECUTION SUMMARY")
            self.logger.info("=" * 60)
            self.logger.info(f"Articles processed: {len(articles)}")
            self.logger.info(f"Successful feeds: {successful_feeds}/{len(feed_statuses)}")
            self.logger.info(f"AI provider: {ai_provider}")
            self.logger.info(f"Email sent: {'Yes' if email_sent else 'No'}")
            self.logger.info(f"Execution time: {execution_time.total_seconds():.1f} seconds")
            self.logger.info("✅ Analysis complete!")
            
            return results
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            results['success'] = False
            
            # Still calculate execution time for failed runs
            end_time = datetime.now()
            results['end_time'] = end_time.isoformat()
            results['execution_time_seconds'] = (end_time - start_time).total_seconds()
            
            return results
