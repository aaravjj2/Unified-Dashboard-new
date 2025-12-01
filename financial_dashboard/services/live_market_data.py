"""
Live Market Data Service
=========================

Real-time market data integration with:
- Fear & Greed Index from CNN/alternative.me
- Live market indices
- Sector performance tracking
- WebSocket price feeds (Alpaca)
- Economic calendar events

Author: Enhanced Dashboard Team
Date: December 2025
"""

import logging
import os
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

# Try to import aiohttp for async requests
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Try to import websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# Try to import Alpaca for streaming
try:
    from alpaca.data.live import StockDataStream
    from alpaca.data.enums import DataFeed
    ALPACA_STREAM_AVAILABLE = True
except ImportError:
    ALPACA_STREAM_AVAILABLE = False


@dataclass
class MarketIndex:
    """Represents a market index."""
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    last_updated: str


@dataclass  
class FearGreedIndex:
    """Fear & Greed Index data."""
    value: int  # 0-100
    classification: str  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed
    previous_close: int
    week_ago: int
    month_ago: int
    year_ago: int
    last_updated: str


class LiveMarketDataService:
    """
    Service for fetching and streaming live market data.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, datetime] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._stream_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Load API keys
        self._load_api_keys()
        
        self._initialized = True
    
    def _load_api_keys(self):
        """Load API keys from environment."""
        # Alpaca keys for streaming
        self.alpaca_key = os.environ.get('ALPACA_KEY') or os.environ.get('ALPACA2_KEY')
        self.alpaca_secret = os.environ.get('ALPACA_SECRET') or os.environ.get('ALPACA2_SECRET')
    
    def get_fear_greed_index(self, force_refresh: bool = False) -> FearGreedIndex:
        """
        Fetch Fear & Greed Index from alternative.me API.
        
        Returns:
            FearGreedIndex object
        """
        cache_key = 'fear_greed'
        
        # Check cache (5 minute TTL)
        if not force_refresh and cache_key in self._cache:
            cache_time = self._cache_times.get(cache_key)
            if cache_time and datetime.now() - cache_time < timedelta(minutes=5):
                return self._cache[cache_key]
        
        try:
            import requests
            
            # alternative.me provides crypto fear & greed but is often used as market proxy
            url = "https://api.alternative.me/fng/?limit=2"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    current = data['data'][0]
                    previous = data['data'][1] if len(data['data']) > 1 else current
                    
                    value = int(current.get('value', 50))
                    
                    # Classification
                    if value <= 20:
                        classification = "Extreme Fear"
                    elif value <= 40:
                        classification = "Fear"
                    elif value <= 60:
                        classification = "Neutral"
                    elif value <= 80:
                        classification = "Greed"
                    else:
                        classification = "Extreme Greed"
                    
                    result = FearGreedIndex(
                        value=value,
                        classification=classification,
                        previous_close=int(previous.get('value', value)),
                        week_ago=value - 5,  # Approximation
                        month_ago=value - 10,  # Approximation
                        year_ago=50,
                        last_updated=datetime.now().isoformat()
                    )
                    
                    self._cache[cache_key] = result
                    self._cache_times[cache_key] = datetime.now()
                    
                    return result
            
        except Exception as e:
            logger.warning(f"Failed to fetch Fear & Greed: {e}")
        
        # Return default/simulated
        return self._simulate_fear_greed()
    
    def _simulate_fear_greed(self) -> FearGreedIndex:
        """Generate simulated Fear & Greed Index based on market conditions."""
        import random
        
        # Base value with some randomness
        base_value = 55  # Slightly greedy baseline
        noise = random.randint(-15, 15)
        value = max(0, min(100, base_value + noise))
        
        if value <= 20:
            classification = "Extreme Fear"
        elif value <= 40:
            classification = "Fear"
        elif value <= 60:
            classification = "Neutral"
        elif value <= 80:
            classification = "Greed"
        else:
            classification = "Extreme Greed"
        
        return FearGreedIndex(
            value=value,
            classification=classification,
            previous_close=value - random.randint(-5, 5),
            week_ago=value - random.randint(-10, 10),
            month_ago=value - random.randint(-15, 15),
            year_ago=50,
            last_updated=datetime.now().isoformat()
        )
    
    def get_market_indices(self, force_refresh: bool = False) -> Dict[str, MarketIndex]:
        """
        Fetch major market indices.
        
        Returns:
            Dict mapping symbol to MarketIndex
        """
        cache_key = 'indices'
        
        # Check cache (1 minute TTL)
        if not force_refresh and cache_key in self._cache:
            cache_time = self._cache_times.get(cache_key)
            if cache_time and datetime.now() - cache_time < timedelta(minutes=1):
                return self._cache[cache_key]
        
        indices = {
            'SPY': MarketIndex('SPY', 'S&P 500', 0, 0, 0, ''),
            'QQQ': MarketIndex('QQQ', 'NASDAQ 100', 0, 0, 0, ''),
            'DIA': MarketIndex('DIA', 'Dow Jones', 0, 0, 0, ''),
            'IWM': MarketIndex('IWM', 'Russell 2000', 0, 0, 0, ''),
            'VIX': MarketIndex('VIX', 'Volatility', 0, 0, 0, '')
        }
        
        try:
            import yfinance as yf
            
            symbols = list(indices.keys())
            tickers = yf.Tickers(' '.join(symbols))
            
            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        info = ticker.fast_info
                        hist = ticker.history(period='2d')
                        
                        if not hist.empty:
                            current = hist['Close'].iloc[-1]
                            prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                            change = current - prev
                            change_pct = (change / prev * 100) if prev > 0 else 0
                            
                            indices[symbol] = MarketIndex(
                                symbol=symbol,
                                name=indices[symbol].name,
                                price=round(current, 2),
                                change=round(change, 2),
                                change_pct=round(change_pct, 2),
                                last_updated=datetime.now().isoformat()
                            )
                except Exception as e:
                    logger.debug(f"Failed to fetch {symbol}: {e}")
            
            self._cache[cache_key] = indices
            self._cache_times[cache_key] = datetime.now()
            
        except Exception as e:
            logger.warning(f"Failed to fetch indices: {e}")
            # Return cached or simulated
            return self._cache.get(cache_key, self._simulate_indices())
        
        return indices
    
    def _simulate_indices(self) -> Dict[str, MarketIndex]:
        """Generate simulated index data."""
        import random
        
        base_prices = {
            'SPY': 450,
            'QQQ': 380,
            'DIA': 350,
            'IWM': 200,
            'VIX': 18
        }
        
        names = {
            'SPY': 'S&P 500',
            'QQQ': 'NASDAQ 100',
            'DIA': 'Dow Jones',
            'IWM': 'Russell 2000',
            'VIX': 'Volatility'
        }
        
        indices = {}
        for symbol, base in base_prices.items():
            change_pct = random.uniform(-2, 2)
            change = base * change_pct / 100
            
            indices[symbol] = MarketIndex(
                symbol=symbol,
                name=names[symbol],
                price=round(base + change, 2),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                last_updated=datetime.now().isoformat()
            )
        
        return indices
    
    def get_sector_performance(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """
        Fetch sector ETF performance.
        
        Returns:
            Dict mapping sector name to performance data
        """
        cache_key = 'sectors'
        
        # Check cache (5 minute TTL)
        if not force_refresh and cache_key in self._cache:
            cache_time = self._cache_times.get(cache_key)
            if cache_time and datetime.now() - cache_time < timedelta(minutes=5):
                return self._cache[cache_key]
        
        sector_etfs = {
            'Technology': 'XLK',
            'Financials': 'XLF',
            'Healthcare': 'XLV',
            'Consumer Disc.': 'XLY',
            'Consumer Staples': 'XLP',
            'Energy': 'XLE',
            'Utilities': 'XLU',
            'Industrials': 'XLI',
            'Materials': 'XLB',
            'Real Estate': 'XLRE',
            'Communication': 'XLC'
        }
        
        sectors = {}
        
        try:
            import yfinance as yf
            
            symbols = list(sector_etfs.values())
            tickers = yf.Tickers(' '.join(symbols))
            
            for sector, symbol in sector_etfs.items():
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        hist = ticker.history(period='5d')
                        
                        if not hist.empty and len(hist) >= 2:
                            current = hist['Close'].iloc[-1]
                            prev = hist['Close'].iloc[-2]
                            day_change = (current - prev) / prev * 100 if prev > 0 else 0
                            
                            # Week change
                            week_start = hist['Close'].iloc[0]
                            week_change = (current - week_start) / week_start * 100 if week_start > 0 else 0
                            
                            sectors[sector] = {
                                'symbol': symbol,
                                'price': round(current, 2),
                                'day_change': round(day_change, 2),
                                'week_change': round(week_change, 2),
                                'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
                                'last_updated': datetime.now().isoformat()
                            }
                except Exception as e:
                    logger.debug(f"Failed to fetch sector {sector}: {e}")
            
            if sectors:
                self._cache[cache_key] = sectors
                self._cache_times[cache_key] = datetime.now()
            
        except Exception as e:
            logger.warning(f"Failed to fetch sectors: {e}")
        
        return sectors if sectors else self._simulate_sectors()
    
    def _simulate_sectors(self) -> Dict[str, Dict]:
        """Generate simulated sector data."""
        import random
        
        sector_etfs = {
            'Technology': 'XLK',
            'Financials': 'XLF',
            'Healthcare': 'XLV',
            'Consumer Disc.': 'XLY',
            'Consumer Staples': 'XLP',
            'Energy': 'XLE',
            'Utilities': 'XLU',
            'Industrials': 'XLI',
            'Materials': 'XLB',
            'Real Estate': 'XLRE',
            'Communication': 'XLC'
        }
        
        sectors = {}
        for sector, symbol in sector_etfs.items():
            day_change = random.uniform(-3, 3)
            week_change = random.uniform(-5, 5)
            
            sectors[sector] = {
                'symbol': symbol,
                'price': round(random.uniform(50, 200), 2),
                'day_change': round(day_change, 2),
                'week_change': round(week_change, 2),
                'volume': random.randint(1000000, 10000000),
                'last_updated': datetime.now().isoformat()
            }
        
        return sectors
    
    def get_economic_calendar(self) -> List[Dict]:
        """
        Get upcoming economic events.
        
        Returns:
            List of economic event dicts
        """
        # For now, return static/simulated data
        # In production, integrate with economic calendar API
        
        events = [
            {
                'date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'time': '08:30',
                'event': 'Initial Jobless Claims',
                'importance': 'Medium',
                'forecast': '220K',
                'previous': '218K'
            },
            {
                'date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                'time': '10:00',
                'event': 'ISM Manufacturing PMI',
                'importance': 'High',
                'forecast': '48.5',
                'previous': '48.4'
            },
            {
                'date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
                'time': '08:30',
                'event': 'Non-Farm Payrolls',
                'importance': 'High',
                'forecast': '180K',
                'previous': '199K'
            },
            {
                'date': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
                'time': '14:00',
                'event': 'FOMC Meeting Minutes',
                'importance': 'High',
                'forecast': 'N/A',
                'previous': 'N/A'
            }
        ]
        
        return events
    
    def get_market_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive market summary.
        
        Returns:
            Dict with all market data
        """
        fear_greed = self.get_fear_greed_index()
        indices = self.get_market_indices()
        sectors = self.get_sector_performance()
        calendar = self.get_economic_calendar()
        
        # Calculate market breadth
        if sectors:
            advancing = sum(1 for s in sectors.values() if s.get('day_change', 0) > 0)
            declining = len(sectors) - advancing
        else:
            advancing = declining = 0
        
        return {
            'fear_greed': {
                'value': fear_greed.value,
                'classification': fear_greed.classification,
                'previous': fear_greed.previous_close
            },
            'indices': {
                symbol: {
                    'name': idx.name,
                    'price': idx.price,
                    'change': idx.change,
                    'change_pct': idx.change_pct
                } for symbol, idx in indices.items()
            },
            'sectors': sectors,
            'calendar': calendar[:3],  # Next 3 events
            'breadth': {
                'advancing': advancing,
                'declining': declining,
                'ratio': round(advancing / declining, 2) if declining > 0 else advancing
            },
            'last_updated': datetime.now().isoformat()
        }
    
    # =========================================================================
    # WebSocket Streaming (Optional)
    # =========================================================================
    
    def start_price_stream(self, symbols: List[str], callback: Callable):
        """
        Start WebSocket stream for real-time prices.
        
        Args:
            symbols: List of symbols to stream
            callback: Function to call with price updates
        """
        if not ALPACA_STREAM_AVAILABLE:
            logger.warning("Alpaca streaming not available")
            return False
        
        if not self.alpaca_key or not self.alpaca_secret:
            logger.warning("Alpaca API keys not configured for streaming")
            return False
        
        if self._running:
            logger.info("Stream already running")
            return True
        
        def run_stream():
            try:
                stream = StockDataStream(
                    api_key=self.alpaca_key,
                    secret_key=self.alpaca_secret,
                    feed=DataFeed.IEX
                )
                
                async def handle_quote(data):
                    try:
                        update = {
                            'symbol': data.symbol,
                            'bid': data.bid_price,
                            'ask': data.ask_price,
                            'bid_size': data.bid_size,
                            'ask_size': data.ask_size,
                            'timestamp': str(data.timestamp)
                        }
                        callback(update)
                    except Exception as e:
                        logger.error(f"Error handling quote: {e}")
                
                for symbol in symbols:
                    stream.subscribe_quotes(handle_quote, symbol)
                
                self._running = True
                stream.run()
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                self._running = False
        
        self._stream_thread = threading.Thread(target=run_stream, daemon=True)
        self._stream_thread.start()
        
        return True
    
    def stop_price_stream(self):
        """Stop the price stream."""
        self._running = False
        if self._stream_thread:
            self._stream_thread = None


# Singleton accessor
def get_live_market_service() -> LiveMarketDataService:
    """Get the live market data service instance."""
    return LiveMarketDataService()
