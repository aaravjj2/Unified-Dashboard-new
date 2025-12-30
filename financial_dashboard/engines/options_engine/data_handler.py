"""
Data Handler - Market Data & Indicator Provider
===============================================

Provides a standardized interface for fetching market data and calculating
technical indicators. Includes both Mock and Live implementations.

Architecture:
------------
DataHandler (Abstract)
├── MockDataHandler - Returns deterministic/random data for testing
└── LiveDataHandler - Connects to real data sources (yfinance, Alpaca)

Frontend Integration:
-------------------
The DataHandler can be exposed via WebSocket for real-time updates:

```javascript
// React WebSocket connection
const ws = new WebSocket('ws://localhost:8051/ws/market-data');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Update charts, indicators, etc.
};
```
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import hashlib
import math
import random
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Quote:
    """Real-time quote data."""
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    timestamp: datetime
    prev_close: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "prev_close": self.prev_close,
            "change": self.change,
            "change_pct": self.change_pct,
        }


@dataclass
class OHLCV:
    """Single OHLCV bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class MarketData:
    """Complete market data snapshot for a symbol."""
    symbol: str
    quote: Quote
    bars: List[OHLCV] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quote": self.quote.to_dict(),
            "bars": [bar.to_dict() for bar in self.bars],
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class IndicatorData:
    """Technical indicator data."""
    symbol: str
    indicator: str
    period: int
    value: float
    timestamp: datetime
    history: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "indicator": self.indicator,
            "period": self.period,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "history": self.history,
            "metadata": self.metadata,
        }


@dataclass
class OptionChain:
    """Options chain data."""
    symbol: str
    expiration: str
    calls: List[Dict[str, Any]] = field(default_factory=list)
    puts: List[Dict[str, Any]] = field(default_factory=list)
    underlying_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class OptionContract:
    """Single option contract data."""
    symbol: str
    underlying: str
    option_type: str  # "call" or "put"
    strike: float
    expiration: str
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    iv: float  # Implied volatility
    delta: float
    gamma: float
    theta: float
    vega: float


# =============================================================================
# ABSTRACT DATA HANDLER
# =============================================================================

class DataHandler(ABC):
    """
    Abstract base class for market data providers.
    
    All data handlers must implement these methods to be compatible
    with the RecipeExecutor engine.
    """
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol."""
        pass
    
    @abstractmethod
    def get_bars(
        self, 
        symbol: str, 
        period: int = 100,
        interval: str = "1d"
    ) -> List[OHLCV]:
        """Get historical OHLCV bars."""
        pass
    
    @abstractmethod
    def get_indicator(
        self,
        symbol: str,
        indicator: str,
        period: int = 14,
        **kwargs
    ) -> IndicatorData:
        """Get technical indicator value."""
        pass
    
    @abstractmethod
    def get_option_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None
    ) -> OptionChain:
        """Get options chain for a symbol."""
        pass
    
    @abstractmethod
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status (open/closed, hours)."""
        pass
    
    def get_field(self, symbol: str, field: str) -> Any:
        """
        Generic field getter for the LogicParser.
        
        Supports fields like:
        - price, bid, ask, volume
        - RSI, MACD, SMA, EMA
        - VIX (special case)
        """
        # Special cases
        if symbol.upper() == "VIX" or field.upper() == "VIX":
            return self.get_indicator("VIX", "VIX", 1).value
        
        # Price fields
        if field.lower() in ["price", "bid", "ask", "volume", "prev_close"]:
            quote = self.get_quote(symbol)
            return getattr(quote, field.lower())
        
        # Indicator fields
        indicator_map = {
            "rsi": ("RSI", 14),
            "macd": ("MACD", 12),
            "macd_signal": ("MACD_SIGNAL", 26),
            "macd_histogram": ("MACD_HISTOGRAM", 9),
            "sma": ("SMA", 20),
            "ema": ("EMA", 20),
            "atr": ("ATR", 14),
            "vwap": ("VWAP", 1),
            "iv_rank": ("IV_RANK", 1),
            "iv_percentile": ("IV_PERCENTILE", 1),
        }
        
        field_lower = field.lower()
        if field_lower in indicator_map:
            ind_name, default_period = indicator_map[field_lower]
            return self.get_indicator(symbol, ind_name, default_period).value
        
        # Unknown field
        raise ValueError(f"Unknown field: {field}")


# =============================================================================
# MOCK DATA HANDLER (For Testing)
# =============================================================================

class MockDataHandler(DataHandler):
    """
    Mock data handler that returns deterministic or random data.
    
    Use for:
    - Unit testing
    - Strategy backtesting
    - Demo/development without API keys
    
    Configuration:
    - deterministic: Use hash-based values (same input = same output)
    - seed: Random seed for reproducibility
    """
    
    def __init__(
        self,
        deterministic: bool = True,
        seed: Optional[int] = 42,
        base_prices: Optional[Dict[str, float]] = None
    ):
        self.deterministic = deterministic
        self.seed = seed
        self._base_prices = base_prices or {
            "SPY": 590.0,
            "QQQ": 520.0,
            "AAPL": 250.0,
            "MSFT": 430.0,
            "NVDA": 140.0,
            "TSLA": 420.0,
            "VIX": 15.0,
        }
        self._indicator_cache: Dict[str, IndicatorData] = {}
        
        if seed is not None:
            random.seed(seed)
        
        logger.info(f"MockDataHandler initialized (deterministic={deterministic})")
    
    def _hash_value(self, *args) -> int:
        """Generate deterministic hash from args."""
        s = "|".join(str(a) for a in args)
        return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)
    
    def _get_base_price(self, symbol: str) -> float:
        """Get base price for symbol."""
        return self._base_prices.get(symbol.upper(), 100.0)
    
    def get_quote(self, symbol: str) -> Quote:
        """Get mock quote."""
        symbol = symbol.upper()
        base = self._get_base_price(symbol)
        
        if self.deterministic:
            h = self._hash_value(symbol, "quote")
            variation = ((h % 1000) - 500) / 10000  # -5% to +5%
        else:
            variation = random.uniform(-0.05, 0.05)
        
        price = base * (1 + variation)
        spread = price * 0.001  # 0.1% spread
        
        return Quote(
            symbol=symbol,
            price=round(price, 2),
            bid=round(price - spread / 2, 2),
            ask=round(price + spread / 2, 2),
            volume=random.randint(1000000, 10000000) if not self.deterministic 
                   else self._hash_value(symbol, "volume") % 10000000,
            timestamp=datetime.now(),
            prev_close=round(base, 2),
            change=round(price - base, 2),
            change_pct=round(variation * 100, 2),
        )
    
    def get_bars(
        self,
        symbol: str,
        period: int = 100,
        interval: str = "1d"
    ) -> List[OHLCV]:
        """Get mock OHLCV bars."""
        symbol = symbol.upper()
        base = self._get_base_price(symbol)
        bars = []
        
        for i in range(period):
            if self.deterministic:
                h = self._hash_value(symbol, i)
                daily_return = ((h % 200) - 100) / 2000  # -5% to +5%
            else:
                daily_return = random.gauss(0.0005, 0.015)  # μ=0.05%, σ=1.5%
            
            base = base * (1 + daily_return)
            high = base * (1 + abs(random.uniform(0, 0.02)))
            low = base * (1 - abs(random.uniform(0, 0.02)))
            open_price = base * (1 + random.uniform(-0.01, 0.01))
            
            bars.append(OHLCV(
                timestamp=datetime.now() - timedelta(days=period - i),
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(base, 2),
                volume=random.randint(100000, 10000000),
            ))
        
        return bars
    
    def get_indicator(
        self,
        symbol: str,
        indicator: str,
        period: int = 14,
        **kwargs
    ) -> IndicatorData:
        """
        Get mock indicator value.
        
        Supports: RSI, MACD, SMA, EMA, ATR, VIX, IV_RANK
        """
        symbol = symbol.upper()
        indicator = indicator.upper()
        cache_key = f"{symbol}_{indicator}_{period}"
        
        # Return cached value if recent (within 60 seconds)
        if cache_key in self._indicator_cache:
            cached = self._indicator_cache[cache_key]
            if (datetime.now() - cached.timestamp).seconds < 60:
                return cached
        
        # Generate indicator value
        if self.deterministic:
            h = self._hash_value(symbol, indicator, period)
        else:
            h = random.randint(0, 10000)
        
        if indicator == "RSI":
            # RSI: 0-100, typically 30-70
            value = 30 + (h % 40)
        elif indicator == "VIX":
            # VIX: typically 10-30
            value = 12 + (h % 20)
        elif indicator in ["MACD", "MACD_SIGNAL"]:
            # MACD: small values around 0
            value = ((h % 100) - 50) / 10
        elif indicator == "MACD_HISTOGRAM":
            value = ((h % 60) - 30) / 10
        elif indicator in ["SMA", "EMA"]:
            base = self._get_base_price(symbol)
            value = base * (1 + ((h % 100) - 50) / 1000)
        elif indicator == "ATR":
            base = self._get_base_price(symbol)
            value = base * 0.02 * (1 + (h % 50) / 100)
        elif indicator in ["IV_RANK", "IV_PERCENTILE"]:
            value = h % 100
        elif indicator == "VWAP":
            value = self._get_base_price(symbol)
        else:
            value = h % 100
        
        result = IndicatorData(
            symbol=symbol,
            indicator=indicator,
            period=period,
            value=round(value, 4),
            timestamp=datetime.now(),
            history=[value + random.uniform(-5, 5) for _ in range(10)],
        )
        
        self._indicator_cache[cache_key] = result
        return result
    
    def get_option_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None
    ) -> OptionChain:
        """Get mock options chain."""
        symbol = symbol.upper()
        price = self.get_quote(symbol).price
        
        # Generate strikes around current price
        strikes = [
            round(price * (1 + i * 0.02), 0)
            for i in range(-10, 11)
        ]
        
        calls = []
        puts = []
        
        for strike in strikes:
            moneyness = (strike - price) / price
            
            # Mock Black-Scholes-ish values
            call_iv = 0.20 + abs(moneyness) * 0.5
            put_iv = 0.20 + abs(moneyness) * 0.5
            
            # Delta approximation
            call_delta = max(0, min(1, 0.5 - moneyness * 2))
            put_delta = call_delta - 1
            
            call_price = max(0.01, price * call_iv * 0.1 * max(0.01, call_delta))
            put_price = max(0.01, price * put_iv * 0.1 * max(0.01, -put_delta))
            
            calls.append({
                "strike": strike,
                "bid": round(call_price * 0.95, 2),
                "ask": round(call_price * 1.05, 2),
                "last": round(call_price, 2),
                "volume": random.randint(100, 10000),
                "open_interest": random.randint(1000, 50000),
                "iv": round(call_iv, 4),
                "delta": round(call_delta, 4),
                "gamma": round(0.02 * (1 - abs(moneyness)), 4),
                "theta": round(-price * call_iv / 365 * 0.1, 4),
                "vega": round(price * 0.01 * math.sqrt(30/365), 4),
            })
            
            puts.append({
                "strike": strike,
                "bid": round(put_price * 0.95, 2),
                "ask": round(put_price * 1.05, 2),
                "last": round(put_price, 2),
                "volume": random.randint(100, 10000),
                "open_interest": random.randint(1000, 50000),
                "iv": round(put_iv, 4),
                "delta": round(put_delta, 4),
                "gamma": round(0.02 * (1 - abs(moneyness)), 4),
                "theta": round(-price * put_iv / 365 * 0.1, 4),
                "vega": round(price * 0.01 * math.sqrt(30/365), 4),
            })
        
        # Default expiration: 30 days from now
        if expiration is None:
            expiration = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        return OptionChain(
            symbol=symbol,
            expiration=expiration,
            calls=calls,
            puts=puts,
            underlying_price=price,
            timestamp=datetime.now(),
        )
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get mock market status."""
        # Return override if set
        if hasattr(self, '_market_status_override') and self._market_status_override is not None:
            return self._market_status_override
        
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()
        
        # Market hours: 9:30 AM - 4:00 PM ET, Mon-Fri
        is_weekday = weekday < 5
        is_market_hours = 9 <= hour < 16
        is_open = is_weekday and is_market_hours
        
        return {
            "is_open": is_open,
            "is_market_hours": is_market_hours,
            "current_time": now.isoformat(),
            "market_open": "09:30:00",
            "market_close": "16:00:00",
            "timezone": "America/New_York",
            "next_open": None,
            "next_close": None,
        }
    
    def set_market_status(self, is_open: bool = True) -> None:
        """Override market status for testing."""
        self._market_status_override = {
            "is_open": is_open,
            "is_market_hours": is_open,
            "current_time": datetime.now().isoformat(),
            "market_open": "09:30:00",
            "market_close": "16:00:00",
            "timezone": "America/New_York",
            "next_open": None,
            "next_close": None,
        }
    
    def set_indicator_value(
        self,
        symbol: str,
        indicator: str,
        value: float,
        period: int = 14
    ) -> None:
        """
        Manually set an indicator value (for testing).
        
        This allows tests to control exact market conditions.
        """
        cache_key = f"{symbol.upper()}_{indicator.upper()}_{period}"
        self._indicator_cache[cache_key] = IndicatorData(
            symbol=symbol.upper(),
            indicator=indicator.upper(),
            period=period,
            value=value,
            timestamp=datetime.now(),
        )
        logger.debug(f"Set {cache_key} = {value}")
    
    def set_price(self, symbol: str, price: float) -> None:
        """Manually set a symbol's base price (for testing)."""
        self._base_prices[symbol.upper()] = price


# =============================================================================
# LIVE DATA HANDLER (Production)
# =============================================================================

class LiveDataHandler(DataHandler):
    """
    Live data handler that connects to real data sources.
    
    Supported providers:
    - yfinance (free, delayed)
    - Alpaca (real-time with API key)
    - Polygon.io (real-time with API key)
    
    Configuration via environment variables or constructor args.
    """
    
    def __init__(
        self,
        provider: str = "yfinance",
        api_key: Optional[str] = None,
        cache_ttl: int = 60,  # seconds
    ):
        self.provider = provider
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, datetime] = {}
        
        # Import data library
        if provider == "yfinance":
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                raise ImportError("yfinance not installed. Run: pip install yfinance")
        
        logger.info(f"LiveDataHandler initialized (provider={provider})")
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache_times:
            return False
        age = (datetime.now() - self._cache_times[key]).seconds
        return age < self.cache_ttl
    
    def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote from provider."""
        cache_key = f"quote_{symbol}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        if self.provider == "yfinance":
            ticker = self._yf.Ticker(symbol)
            info = ticker.info
            
            quote = Quote(
                symbol=symbol,
                price=info.get("currentPrice", info.get("regularMarketPrice", 0)),
                bid=info.get("bid", 0),
                ask=info.get("ask", 0),
                volume=info.get("volume", info.get("regularMarketVolume", 0)),
                timestamp=datetime.now(),
                prev_close=info.get("previousClose", 0),
                change=info.get("regularMarketChange", 0),
                change_pct=info.get("regularMarketChangePercent", 0),
            )
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented")
        
        self._cache[cache_key] = quote
        self._cache_times[cache_key] = datetime.now()
        return quote
    
    def get_bars(
        self,
        symbol: str,
        period: int = 100,
        interval: str = "1d"
    ) -> List[OHLCV]:
        """Get historical bars from provider."""
        cache_key = f"bars_{symbol}_{period}_{interval}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        if self.provider == "yfinance":
            ticker = self._yf.Ticker(symbol)
            df = ticker.history(period=f"{period}d", interval=interval)
            
            bars = [
                OHLCV(
                    timestamp=idx.to_pydatetime(),
                    open=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=int(row["Volume"]),
                )
                for idx, row in df.iterrows()
            ]
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented")
        
        self._cache[cache_key] = bars
        self._cache_times[cache_key] = datetime.now()
        return bars
    
    def get_indicator(
        self,
        symbol: str,
        indicator: str,
        period: int = 14,
        **kwargs
    ) -> IndicatorData:
        """Calculate indicator from historical data."""
        import numpy as np
        import pandas as pd
        
        # Get historical bars
        bars = self.get_bars(symbol, period=period * 3)
        closes = pd.Series([b.close for b in bars])
        
        if indicator.upper() == "RSI":
            delta = closes.diff()
            gain = delta.where(delta > 0, 0).ewm(span=period).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(span=period).mean()
            rs = gain / loss.replace(0, 1e-10)
            rsi = 100 - (100 / (1 + rs))
            value = float(rsi.iloc[-1])
        
        elif indicator.upper() in ["SMA", "EMA"]:
            if indicator.upper() == "SMA":
                value = float(closes.rolling(period).mean().iloc[-1])
            else:
                value = float(closes.ewm(span=period).mean().iloc[-1])
        
        elif indicator.upper() == "MACD":
            ema12 = closes.ewm(span=12).mean()
            ema26 = closes.ewm(span=26).mean()
            value = float((ema12 - ema26).iloc[-1])
        
        elif indicator.upper() == "ATR":
            highs = pd.Series([b.high for b in bars])
            lows = pd.Series([b.low for b in bars])
            tr = pd.concat([
                highs - lows,
                (highs - closes.shift()).abs(),
                (lows - closes.shift()).abs()
            ], axis=1).max(axis=1)
            value = float(tr.rolling(period).mean().iloc[-1])
        
        elif indicator.upper() == "VIX":
            # VIX is a special symbol, fetch directly
            vix_quote = self.get_quote("^VIX")
            value = vix_quote.price
        
        else:
            raise ValueError(f"Indicator {indicator} not implemented")
        
        return IndicatorData(
            symbol=symbol,
            indicator=indicator.upper(),
            period=period,
            value=round(value, 4),
            timestamp=datetime.now(),
        )
    
    def get_option_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None
    ) -> OptionChain:
        """Get options chain from provider."""
        if self.provider == "yfinance":
            ticker = self._yf.Ticker(symbol)
            
            # Get available expirations
            expirations = ticker.options
            if not expirations:
                raise ValueError(f"No options available for {symbol}")
            
            # Use first expiration if not specified
            if expiration is None:
                expiration = expirations[0]
            
            chain = ticker.option_chain(expiration)
            
            calls = chain.calls.to_dict("records")
            puts = chain.puts.to_dict("records")
            
            return OptionChain(
                symbol=symbol,
                expiration=expiration,
                calls=calls,
                puts=puts,
                underlying_price=self.get_quote(symbol).price,
                timestamp=datetime.now(),
            )
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented")
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get real market status."""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()
        
        # NYSE hours: 9:30 AM - 4:00 PM ET
        is_weekday = weekday < 5
        market_open_time = 9 * 60 + 30  # 9:30 AM in minutes
        market_close_time = 16 * 60     # 4:00 PM in minutes
        current_minutes = hour * 60 + minute
        
        is_market_hours = market_open_time <= current_minutes < market_close_time
        is_open = is_weekday and is_market_hours
        
        return {
            "is_open": is_open,
            "is_market_hours": is_market_hours,
            "current_time": now.isoformat(),
            "market_open": "09:30:00",
            "market_close": "16:00:00",
            "timezone": "America/New_York",
        }
