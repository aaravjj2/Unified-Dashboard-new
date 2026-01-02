"""
Real Data Connectors - Unified API Integration
Uses all keys from keys.env for live market data
"""

import os
import sys
import json
import logging
import asyncio
import aiohttp
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment - try multiple locations
possible_paths = [
    Path(__file__).parent.parent.parent / "keys.env",  # /home/aarav/Unified-Dashboard/keys.env
    Path(__file__).parent.parent / "keys.env",
    Path(__file__).parent / "keys.env",
    Path("/home/aarav/Unified-Dashboard/keys.env"),
    Path("/home/aarav/Unified-Dashboard/financial_dashboard/keys.env"),
]

env_loaded = False
for env_path in possible_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        env_loaded = True
        logger.info(f"Loaded environment from: {env_path}")
        break

if not env_loaded:
    logger.warning("No keys.env file found!")

# ===== API KEY CONFIGURATION =====
class APIKeys:
    """Centralized API key management"""
    
    # Market Data
    TIINGO = os.getenv("TIINGO_API_KEY", "")
    FINNHUB = os.getenv("FINNHUB_API_KEY", "")
    FINNHUB2 = os.getenv("FINNHUB2_API_KEY", "")
    POLYGON = os.getenv("POLYGON_API_KEY", "")
    TWELVEDATA = os.getenv("TWELVEDATA_API_KEY", "")
    FINAGE = os.getenv("FINAGE_API_KEY", "")
    
    # Trading
    ALPACA_KEY = os.getenv("APCA_API_KEY_ID", "")
    ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY", "")
    ALPACA_ENDPOINT = os.getenv("APCA_ENDPOINT", "https://paper-api.alpaca.markets")
    
    ALPACA2_KEY = os.getenv("ALPACA2_KEY", "")
    ALPACA2_SECRET = os.getenv("ALPACA2_SECRET", "")
    
    ALPACA3_KEY = os.getenv("ALPACA3_KEY", "")
    ALPACA3_SECRET = os.getenv("ALPACA3_SECRET", "")
    
    # News & Sentiment
    NEWS_API = os.getenv("NEWS_API_KEY", "")
    REDDIT_CLIENT = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_SECRET = os.getenv("REDDIT_SECRET", "")
    X_BEARER = os.getenv("X_API_BEARER", "")
    
    # Economic Data
    FRED = os.getenv("FRED_API_KEY", "")
    QUANDL = os.getenv("QUANDL_API_KEY", "")
    SEC = os.getenv("SEC_API_KEY", "")
    
    # AI/LLM
    GROQ = os.getenv("GROQ_API_KEY", "")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
    
    @classmethod
    def status(cls) -> Dict[str, bool]:
        """Check which APIs are configured"""
        return {
            "tiingo": bool(cls.TIINGO),
            "finnhub": bool(cls.FINNHUB),
            "polygon": bool(cls.POLYGON),
            "twelvedata": bool(cls.TWELVEDATA),
            "alpaca": bool(cls.ALPACA_KEY and cls.ALPACA_SECRET),
            "news_api": bool(cls.NEWS_API),
            "reddit": bool(cls.REDDIT_CLIENT and cls.REDDIT_SECRET),
            "fred": bool(cls.FRED),
            "quandl": bool(cls.QUANDL),
            "sec": bool(cls.SEC),
            "groq": bool(cls.GROQ),
            "ollama": bool(cls.OLLAMA_HOST),
        }


class UsageTracker:
    """Track API usage counts"""
    _counts = {}
    
    @classmethod
    def increment(cls, api_name: str):
        cls._counts[api_name] = cls._counts.get(api_name, 0) + 1
        
    @classmethod
    def get_counts(cls) -> Dict[str, int]:
        return cls._counts.copy()


# ===== TIINGO DATA CONNECTOR =====
class TiingoConnector:
    """Tiingo API for stock prices and news"""
    
    BASE_URL = "https://api.tiingo.com"
    
    def __init__(self):
        self.api_key = APIKeys.TIINGO
        self.session = None
        
    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}"
        }
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """Get current price for symbol"""
        UsageTracker.increment("tiingo")
        if not self.api_key:
            return None
        try:
            url = f"{self.BASE_URL}/iex/{symbol}"
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0] if isinstance(data, list) else data
        except Exception as e:
            logger.error(f"Tiingo price error: {e}")
        return None
    
    def get_history(self, symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Get historical daily prices"""
        if not self.api_key:
            return None
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            url = f"{self.BASE_URL}/tiingo/daily/{symbol}/prices"
            params = {
                "startDate": start.strftime("%Y-%m-%d"),
                "endDate": end.strftime("%Y-%m-%d")
            }
            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    return df
        except Exception as e:
            logger.error(f"Tiingo history error: {e}")
        return None
    
    def get_news(self, symbols: List[str], limit: int = 50) -> List[Dict]:
        """Get news for symbols"""
        if not self.api_key:
            return []
        try:
            url = f"{self.BASE_URL}/tiingo/news"
            params = {
                "tickers": ",".join(symbols),
                "limit": limit
            }
            resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Tiingo news error: {e}")
        return []


# ===== FINNHUB CONNECTOR =====
class FinnhubConnector:
    """Finnhub API for real-time quotes and news"""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self):
        self.api_key = APIKeys.FINNHUB
        
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote"""
        UsageTracker.increment("finnhub")
        if not self.api_key:
            return None
        try:
            url = f"{self.BASE_URL}/quote"
            params = {"symbol": symbol, "token": self.api_key}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Finnhub quote error: {e}")
        return None
    
    def get_company_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """Get company news"""
        if not self.api_key:
            return []
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            url = f"{self.BASE_URL}/company-news"
            params = {
                "symbol": symbol,
                "from": start.strftime("%Y-%m-%d"),
                "to": end.strftime("%Y-%m-%d"),
                "token": self.api_key
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Finnhub news error: {e}")
        return []
    
    def get_sentiment(self, symbol: str) -> Optional[Dict]:
        """Get social sentiment"""
        if not self.api_key:
            return None
        try:
            url = f"{self.BASE_URL}/stock/social-sentiment"
            params = {"symbol": symbol, "token": self.api_key}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Finnhub sentiment error: {e}")
        return None
    
    def get_earnings(self, symbol: str) -> List[Dict]:
        """Get earnings calendar"""
        if not self.api_key:
            return []
        try:
            url = f"{self.BASE_URL}/stock/earnings"
            params = {"symbol": symbol, "token": self.api_key}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Finnhub earnings error: {e}")
        return []


# ===== POLYGON CONNECTOR =====
class PolygonConnector:
    """Polygon.io for tick data and options"""
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self):
        self.api_key = APIKeys.POLYGON
        
    def get_aggregates(self, symbol: str, multiplier: int = 1, 
                       timespan: str = "day", days: int = 365) -> Optional[pd.DataFrame]:
        """Get aggregate bars"""
        UsageTracker.increment("polygon")
        if not self.api_key:
            return None
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            url = f"{self.BASE_URL}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
            params = {"apiKey": self.api_key, "limit": 50000}
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    df = pd.DataFrame(data["results"])
                    df['date'] = pd.to_datetime(df['t'], unit='ms')
                    df.set_index('date', inplace=True)
                    df.rename(columns={
                        'o': 'open', 'h': 'high', 'l': 'low', 
                        'c': 'close', 'v': 'volume'
                    }, inplace=True)
                    return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Polygon aggregates error: {e}")
        return None
    
    def get_options_chain(self, symbol: str) -> List[Dict]:
        """Get options chain"""
        if not self.api_key:
            return []
        try:
            url = f"{self.BASE_URL}/v3/reference/options/contracts"
            params = {
                "underlying_ticker": symbol,
                "apiKey": self.api_key,
                "limit": 1000
            }
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])
        except Exception as e:
            logger.error(f"Polygon options error: {e}")
        return []


# ===== ALPACA CONNECTOR =====
class AlpacaConnector:
    """Alpaca for trading and market data"""
    
    def __init__(self, account: str = "primary"):
        if account == "primary":
            self.api_key = APIKeys.ALPACA_KEY
            self.api_secret = APIKeys.ALPACA_SECRET
        elif account == "account2":
            self.api_key = APIKeys.ALPACA2_KEY
            self.api_secret = APIKeys.ALPACA2_SECRET
        else:  # account3
            self.api_key = APIKeys.ALPACA3_KEY
            self.api_secret = APIKeys.ALPACA3_SECRET
            
        self.base_url = APIKeys.ALPACA_ENDPOINT.rstrip('/')
        self.data_url = "https://data.alpaca.markets"
        
    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret
        }
    
    def get_account(self) -> Optional[Dict]:
        """Get account info"""
        if not self.api_key or not self.api_secret:
            return None
        try:
            url = f"{self.base_url}/v2/account"
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Alpaca account error: {e}")
        return None
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.api_key or not self.api_secret:
            return []
        try:
            url = f"{self.base_url}/v2/positions"
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Alpaca positions error: {e}")
        return []
    
    def get_bars(self, symbol: str, timeframe: str = "1Day", 
                 limit: int = 1000) -> Optional[pd.DataFrame]:
        """Get historical bars"""
        UsageTracker.increment("alpaca")
        if not self.api_key or not self.api_secret:
            return None
        try:
            url = f"{self.data_url}/v2/stocks/{symbol}/bars"
            params = {"timeframe": timeframe, "limit": limit}
            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("bars"):
                    df = pd.DataFrame(data["bars"])
                    df['date'] = pd.to_datetime(df['t'])
                    df.set_index('date', inplace=True)
                    df.rename(columns={
                        'o': 'open', 'h': 'high', 'l': 'low',
                        'c': 'close', 'v': 'volume'
                    }, inplace=True)
                    return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Alpaca bars error: {e}")
        return None
    
    def submit_order(self, symbol: str, qty: int, side: str, 
                     order_type: str = "market", time_in_force: str = "day") -> Optional[Dict]:
        """Submit trading order"""
        if not self.api_key or not self.api_secret:
            return None
        try:
            url = f"{self.base_url}/v2/orders"
            data = {
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": order_type,
                "time_in_force": time_in_force
            }
            resp = requests.post(url, headers=self._headers(), json=data, timeout=10)
            if resp.status_code in [200, 201]:
                return resp.json()
            else:
                logger.error(f"Alpaca order error: {resp.text}")
        except Exception as e:
            logger.error(f"Alpaca submit order error: {e}")
        return None


# ===== NEWS API CONNECTOR =====
class NewsAPIConnector:
    """News API for headlines"""
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self):
        self.api_key = APIKeys.NEWS_API
        
    def get_headlines(self, query: str = None, category: str = "business", 
                      country: str = "us", limit: int = 50) -> List[Dict]:
        """Get top headlines"""
        UsageTracker.increment("news_api")
        if not self.api_key:
            return []
        try:
            url = f"{self.BASE_URL}/top-headlines"
            params = {
                "apiKey": self.api_key,
                "category": category,
                "country": country,
                "pageSize": limit
            }
            if query:
                params["q"] = query
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("articles", [])
        except Exception as e:
            logger.error(f"News API error: {e}")
        return []
    
    def search_news(self, query: str, days: int = 7, limit: int = 100) -> List[Dict]:
        """Search everything"""
        if not self.api_key:
            return []
        try:
            url = f"{self.BASE_URL}/everything"
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            params = {
                "apiKey": self.api_key,
                "q": query,
                "from": from_date,
                "sortBy": "relevancy",
                "pageSize": limit
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("articles", [])
        except Exception as e:
            logger.error(f"News API search error: {e}")
        return []


# ===== REDDIT CONNECTOR =====
class RedditConnector:
    """Reddit API for social sentiment"""
    
    def __init__(self):
        self.client_id = APIKeys.REDDIT_CLIENT
        self.client_secret = APIKeys.REDDIT_SECRET
        self.access_token = None
        
    def _authenticate(self) -> bool:
        """Get OAuth token"""
        if not self.client_id or not self.client_secret:
            return False
        try:
            auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
            data = {"grant_type": "client_credentials"}
            headers = {"User-Agent": "QuantDashboard/1.0"}
            resp = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth, data=data, headers=headers, timeout=10
            )
            if resp.status_code == 200:
                self.access_token = resp.json().get("access_token")
                return True
        except Exception as e:
            logger.error(f"Reddit auth error: {e}")
        return False
    
    def get_subreddit_posts(self, subreddit: str = "wallstreetbets", 
                            limit: int = 50, sort: str = "hot") -> List[Dict]:
        """Get posts from subreddit"""
        if not self.access_token:
            if not self._authenticate():
                return []
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": "QuantDashboard/1.0"
            }
            url = f"https://oauth.reddit.com/r/{subreddit}/{sort}"
            params = {"limit": limit}
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                posts = []
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    posts.append({
                        "title": post.get("title"),
                        "score": post.get("score"),
                        "num_comments": post.get("num_comments"),
                        "created_utc": post.get("created_utc"),
                        "author": post.get("author"),
                        "url": post.get("url"),
                        "selftext": post.get("selftext", "")[:500]
                    })
                return posts
        except Exception as e:
            logger.error(f"Reddit posts error: {e}")
        return []


# ===== FRED CONNECTOR =====
class FREDConnector:
    """FRED API for economic data"""
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    def __init__(self):
        self.api_key = APIKeys.FRED
        
    def get_series(self, series_id: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Get economic series data"""
        if not self.api_key:
            return None
        try:
            url = f"{self.BASE_URL}/series/observations"
            params = {
                "api_key": self.api_key,
                "series_id": series_id,
                "file_type": "json",
                "limit": limit,
                "sort_order": "desc"
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                observations = data.get("observations", [])
                if observations:
                    df = pd.DataFrame(observations)
                    df['date'] = pd.to_datetime(df['date'])
                    df['value'] = pd.to_numeric(df['value'], errors='coerce')
                    df.set_index('date', inplace=True)
                    return df[['value']].dropna()
        except Exception as e:
            logger.error(f"FRED error: {e}")
        return None
    
    # Common series IDs
    SERIES = {
        "GDP": "GDP",
        "UNEMPLOYMENT": "UNRATE",
        "INFLATION": "CPIAUCSL",
        "FED_RATE": "FEDFUNDS",
        "YIELD_10Y": "DGS10",
        "YIELD_2Y": "DGS2",
        "VIX": "VIXCLS",
        "SP500": "SP500",
        "M2": "M2SL",
        "HOUSING_STARTS": "HOUST"
    }


# ===== OLLAMA LLM CONNECTOR =====
class OllamaConnector:
    """Ollama for local LLM inference"""
    
    def __init__(self):
        self.host = APIKeys.OLLAMA_HOST
        self.model = APIKeys.OLLAMA_MODEL
        
    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Generate text completion"""
        if not self.is_available():
            return None
        try:
            url = f"{self.host}/api/generate"
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens}
            }
            resp = requests.post(url, json=data, timeout=60)
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
        return None
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        prompt = f"""Analyze the sentiment of the following text and provide:
1. Overall sentiment: positive, negative, or neutral
2. Confidence score: 0.0 to 1.0
3. Key themes mentioned

Text: {text}

Respond in JSON format:
{{"sentiment": "positive/negative/neutral", "confidence": 0.8, "themes": ["theme1", "theme2"]}}"""
        
        response = self.generate(prompt)
        if response:
            try:
                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        return {"sentiment": "neutral", "confidence": 0.5, "themes": []}


# ===== UNIFIED DATA SERVICE =====
class UnifiedDataService:
    """Unified interface for all data sources"""
    
    def __init__(self):
        self.tiingo = TiingoConnector()
        self.finnhub = FinnhubConnector()
        self.polygon = PolygonConnector()
        self.alpaca = AlpacaConnector()
        self.news = NewsAPIConnector()
        self.reddit = RedditConnector()
        self.fred = FREDConnector()
        self.ollama = OllamaConnector()
        
    def get_status(self) -> Dict[str, Any]:
        """Get status of all connectors"""
        status = APIKeys.status()
        status["ollama_available"] = self.ollama.is_available()
        return status
    
    def get_stock_data(self, symbol: str, days: int = 365) -> Dict[str, Any]:
        """Get comprehensive stock data from all sources"""
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "price": None,
            "history": None,
            "quote": None,
            "news": [],
            "sentiment": None
        }
        
        # Try Tiingo first for price
        result["price"] = self.tiingo.get_price(symbol)
        
        # Get historical data (try multiple sources)
        result["history"] = self.tiingo.get_history(symbol, days)
        if result["history"] is None:
            result["history"] = self.polygon.get_aggregates(symbol, days=days)
        if result["history"] is None:
            result["history"] = self.alpaca.get_bars(symbol)
        
        # Get real-time quote from Finnhub
        result["quote"] = self.finnhub.get_quote(symbol)
        
        # Get news
        result["news"] = self.finnhub.get_company_news(symbol)
        if not result["news"]:
            result["news"] = self.tiingo.get_news([symbol])
        
        # Get sentiment
        result["sentiment"] = self.finnhub.get_sentiment(symbol)
        
        return result
    
    def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview data"""
        overview = {
            "indices": {},
            "economic": {},
            "sentiment": {},
            "news": []
        }
        
        # Major indices
        for symbol in ["SPY", "QQQ", "IWM", "DIA"]:
            quote = self.finnhub.get_quote(symbol)
            if quote:
                overview["indices"][symbol] = quote
        
        # Economic data
        for name, series_id in list(FREDConnector.SERIES.items())[:5]:
            data = self.fred.get_series(series_id, limit=10)
            if data is not None and len(data) > 0:
                overview["economic"][name] = float(data.iloc[0]['value'])
        
        # Top business news
        overview["news"] = self.news.get_headlines(category="business", limit=20)
        
        # Reddit sentiment
        overview["sentiment"]["reddit"] = self.reddit.get_subreddit_posts("wallstreetbets", limit=20)
        
        return overview
    
    def analyze_with_ai(self, text: str) -> Dict[str, Any]:
        """Analyze text with local LLM"""
        return self.ollama.analyze_sentiment(text)
    
    def get_trading_account(self, account: str = "primary") -> Dict[str, Any]:
        """Get trading account info"""
        connector = AlpacaConnector(account)
        return {
            "account": connector.get_account(),
            "positions": connector.get_positions()
        }


# Export main service
data_service = UnifiedDataService()

if __name__ == "__main__":
    # Test all connectors
    print("=" * 60)
    print("UNIFIED DATA SERVICE - API STATUS")
    print("=" * 60)
    
    status = data_service.get_status()
    for api, available in status.items():
        icon = "✅" if available else "❌"
        print(f"{icon} {api}: {'Available' if available else 'Not configured'}")
    
    print("\n" + "=" * 60)
    print("TESTING CONNECTIONS")
    print("=" * 60)
    
    # Test Tiingo
    if status.get("tiingo"):
        price = data_service.tiingo.get_price("AAPL")
        print(f"Tiingo AAPL: {price.get('last') if price else 'Error'}")
    
    # Test Finnhub
    if status.get("finnhub"):
        quote = data_service.finnhub.get_quote("AAPL")
        print(f"Finnhub AAPL: c={quote.get('c') if quote else 'Error'}")
    
    # Test Alpaca
    if status.get("alpaca"):
        account = data_service.alpaca.get_account()
        print(f"Alpaca account: {account.get('status') if account else 'Error'}")
    
    # Test FRED
    if status.get("fred"):
        gdp = data_service.fred.get_series("GDP", limit=1)
        print(f"FRED GDP: {gdp.iloc[0]['value'] if gdp is not None else 'Error'}")
    
    # Test Ollama
    if status.get("ollama_available"):
        print(f"Ollama: Available ({APIKeys.OLLAMA_MODEL})")
    
    print("=" * 60)
