# src/data_sources/market_data.py
import requests
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("market_aggregator.market")

class MarketDataClient:
    """
    Handles market data fetching from Finnhub API
    """
    
    def __init__(self):
        self.api_key = os.getenv('FINNHUB_API_KEY')
        self.base_url = "https://finnhub.io/api/v1"
        self.symbols = ['QQQ', 'SPY', 'UUP', 'IWM', 'GLD', 'MP']
        
        # Create a session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MarketAggregator/1.0'
        })
        
        if not self.api_key:
            logger.error("FINNHUB_API_KEY not found in environment variables")
            raise ValueError("FINNHUB_API_KEY is required")

    def fetch_quote(self, symbol: str) -> Optional[Dict]:
        """
        Fetch a single stock quote
        
        Returns:
            Dict with quote data or None if error
        """
        try:
            params = {
                'symbol': symbol,
                'token': self.api_key
            }
            
            response = self.session.get(
                f"{self.base_url}/quote", 
                params=params, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Validate that we got actual data
            if 'c' in data and data['c'] is not None:
                return {
                    'symbol': symbol,
                    'current': float(data['c']),
                    'change': float(data.get('d', 0) or 0),
                    'change_percent': float(data.get('dp', 0) or 0),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning(f"No price data available for {symbol}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching {symbol}: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Data parsing error for {symbol}: {e}")
            return None

    def fetch_all_quotes(self) -> List[Dict]:
        """
        Fetch quotes for all configured symbols
        
        Returns:
            List of quote dictionaries
        """
        quotes = []
        
        logger.info(f"Fetching market data for {len(self.symbols)} symbols...")
        
        for symbol in self.symbols:
            quote = self.fetch_quote(symbol)
            if quote:
                quotes.append(quote)
                logger.debug(f"✅ {symbol}: ${quote['current']:.2f} ({quote['change_percent']:+.2f}%)")
            else:
                logger.warning(f"❌ Failed to fetch data for {symbol}")
                # Add placeholder for failed quotes
                quotes.append({
                    'symbol': symbol,
                    'current': 0.0,
                    'change': 0.0,
                    'change_percent': 0.0,
                    'error': 'Data unavailable',
                    'timestamp': datetime.now().isoformat()
                })
        
        logger.info(f"Market data fetch complete: {len(quotes)} quotes")
        return quotes

    def format_market_data_text(self, quotes: List[Dict]) -> str:
        """
        Format market data for display/email
        
        Returns:
            Formatted string with market data
        """
        lines = []
        lines.append("📊 CURRENT MARKET DATA")
        lines.append("=" * 50)
        
        for quote in quotes:
            symbol = quote['symbol']
            
            if 'error' in quote:
                lines.append(f"{symbol:8} | {quote['error']}")
                continue
            
            current = quote['current']
            change = quote['change']
            change_pct = quote['change_percent']
            
            # Choose emoji based on change
            direction = "🟢" if change >= 0 else "🔴"
            
            lines.append(
                f"{symbol:8} | ${current:10.2f} | {direction} {change:+8.2f} ({change_pct:+6.2f}%)"
            )
        
        lines.append("=" * 50)
        lines.append(f"Data retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        return "\n".join(lines)

    def __del__(self):
        """Clean up session when object is destroyed"""
        if hasattr(self, 'session'):
            self.session.close()
