"""
AlphaSim Engine - Data ingestion and assembly for AlphaV-compatible responses.
"""
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import pandas as pd

# Use unified price fetcher (Alpaca -> yfinance fallback) for historical data
try:
    from financial_dashboard.utils.price_fetch import fetch_historical_data
    PRICE_FETCH_AVAILABLE = True
except Exception:
    PRICE_FETCH_AVAILABLE = False
    # Provide module-level `yf` symbol for tests that patch `engine.yf`
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        yf = None
else:
    # Also expose yf symbol when price_fetch is available but yfinance may still be patched in tests
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        yf = None

from .schema import (
    build_time_series_daily,
    build_sma_response,
    build_error_response,
)
from .indicators import sma, ema, rsi, macd
from .cache import get_cache, CacheTTL, cached


class AlphaSimEngine:
    """
    Core engine for AlphaSim data fetching and processing.
    Uses yfinance as the primary data source with caching.
    """
    
    def __init__(self):
        self.cache = get_cache()
    
    def _fetch_ohlcv(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for a symbol.
        
        Args:
            symbol: Ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            DataFrame with OHLCV data or None on error
        """
        # Prefer unified fetcher; return a daily OHLCV-like DataFrame when possible
        if PRICE_FETCH_AVAILABLE:
            try:
                # Map period to days (approx)
                period_map = {
                    '1d': 1,
                    '5d': 5,
                    '1mo': 30,
                    '3mo': 90,
                    '6mo': 180,
                    '1y': 365,
                    '2y': 730,
                    '5y': 1825,
                    '10y': 3650,
                    'max': 3650
                }
                days = period_map.get(period, 365)
                from datetime import datetime, timedelta
                end_date = datetime.utcnow().date()
                start_date = end_date - timedelta(days=days + 5)

                df = fetch_historical_data([symbol], start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'), use_alpaca=True)

                if df is None or df.empty or symbol not in df.columns:
                    return None

                # fetch_historical_data returns adjusted close series; build synthetic OHLCV
                close = df[symbol].dropna()
                if close.empty:
                    return None

                ohlcv = pd.DataFrame({
                    'Open': close,
                    'High': close * 1.001,
                    'Low': close * 0.999,
                    'Close': close,
                    'Volume': 0
                })
                # Ensure datetime index
                if not isinstance(ohlcv.index, pd.DatetimeIndex):
                    ohlcv.index = pd.to_datetime(ohlcv.index)

                return ohlcv
            except Exception as e:
                print(f"Error fetching data for {symbol} via price_fetch: {e}")
                return None

        # Fallback: no price fetcher available
        return None
    
    def time_series_daily(
        self,
        symbol: str,
        outputsize: str = "compact"
    ) -> Dict[str, Any]:
        """
        Get daily time series data (TIME_SERIES_DAILY function).
        
        Args:
            symbol: Ticker symbol
            outputsize: 'compact' (100 points) or 'full' (all data)
        
        Returns:
            AlphaV-compatible JSON response
        """
        # Check cache first
        cache_key = f"time_series_daily:{symbol}:{outputsize}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Fetch data
        period = "1y" if outputsize == "compact" else "5y"
        df = self._fetch_ohlcv(symbol, period=period, interval="1d")
        
        if df is None:
            return build_error_response(
                f"Unable to fetch data for symbol: {symbol}",
                note="Please check the symbol and try again."
            )
        
        # Build response
        result = build_time_series_daily(symbol, df, outputsize)
        
        # Cache result
        self.cache.set(cache_key, result, ttl=CacheTTL.DAILY)
        
        return result
    
    def time_series_intraday(
        self,
        symbol: str,
        interval: str = "5min",
        outputsize: str = "compact"
    ) -> Dict[str, Any]:
        """
        Get intraday time series data (TIME_SERIES_INTRADAY function).
        
        Note: yfinance has limitations on intraday data.
        Falls back to daily if intraday unavailable.
        """
        # Map AlphaV intervals to yfinance intervals
        interval_map = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "60min": "60m",
        }
        
        yf_interval = interval_map.get(interval, "5m")
        
        # Check cache
        cache_key = f"time_series_intraday:{symbol}:{interval}:{outputsize}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Fetch intraday data (limited period due to yfinance restrictions)
        df = self._fetch_ohlcv(symbol, period="5d", interval=yf_interval)
        
        if df is None or df.empty:
            # Fallback to daily
            result = self.time_series_daily(symbol, outputsize)
            result["Note"] = "Intraday data unavailable; returning daily data."
            return result
        
        # Build response similar to daily
        result = build_time_series_daily(symbol, df, outputsize)
        result["Meta Data"]["1. Information"] = f"Intraday ({interval}) (AlphaSim)"
        result["Meta Data"]["4. Interval"] = interval
        
        # Rename key
        if "Time Series (Daily)" in result:
            result[f"Time Series ({interval})"] = result.pop("Time Series (Daily)")
        
        # Cache with shorter TTL
        self.cache.set(cache_key, result, ttl=CacheTTL.INTRADAY)
        
        return result
    
    def calculate_sma(
        self,
        symbol: str,
        time_period: int = 10,
        series_type: str = "close",
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """
        Calculate Simple Moving Average (SMA function).
        
        Args:
            symbol: Ticker symbol
            time_period: Number of periods for SMA
            series_type: Price type to use (open, high, low, close)
            interval: Time interval (daily, weekly, monthly)
        
        Returns:
            AlphaV-compatible SMA response
        """
        # Check cache
        cache_key = f"sma:{symbol}:{time_period}:{series_type}:{interval}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Fetch underlying data
        df = self._fetch_ohlcv(symbol, period="2y", interval="1d")
        
        if df is None:
            return build_error_response(
                f"Unable to fetch data for symbol: {symbol}",
                note="SMA calculation requires historical data."
            )
        
        # Get the right price series
        series_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        }
        col_name = series_map.get(series_type.lower(), "Close")
        
        if col_name not in df.columns:
            # Try lowercase
            col_name = col_name.lower()
        
        if col_name not in df.columns:
            return build_error_response(
                f"Series type '{series_type}' not available",
                note="Available types: open, high, low, close"
            )
        
        price_series = df[col_name]
        
        # Calculate SMA
        sma_values = sma(price_series, period=time_period)
        
        # Handle case where SMA returns empty series (period > data length)
        if len(sma_values) == 0:
            return build_sma_response(symbol, pd.Series(dtype=float), time_period, series_type)
        
        # Build response
        result = build_sma_response(symbol, sma_values, time_period, series_type)
        
        # Cache result
        self.cache.set(cache_key, result, ttl=CacheTTL.INDICATORS)
        
        return result
    
    def calculate_ema(
        self,
        symbol: str,
        time_period: int = 10,
        series_type: str = "close"
    ) -> Dict[str, Any]:
        """Calculate Exponential Moving Average."""
        cache_key = f"ema:{symbol}:{time_period}:{series_type}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        df = self._fetch_ohlcv(symbol, period="2y", interval="1d")
        
        if df is None:
            return build_error_response(f"Unable to fetch data for symbol: {symbol}")
        
        col_name = series_type.capitalize()
        if col_name not in df.columns:
            col_name = series_type.lower()
        
        if col_name not in df.columns:
            return build_error_response(f"Series type '{series_type}' not available")
        
        ema_values = ema(df[col_name], period=time_period)
        ema_values.index = df.index
        
        # Build response similar to SMA
        result = build_sma_response(symbol, ema_values, time_period, series_type)
        result["Meta Data"]["1. Information"] = "EMA (AlphaSim)"
        result["Meta Data"]["5. Indicator"] = "EMA"
        
        if "Technical Analysis: SMA" in result:
            tech_data = result.pop("Technical Analysis: SMA")
            result["Technical Analysis: EMA"] = {
                k: {"EMA": v["SMA"]} for k, v in tech_data.items()
            }
        
        self.cache.set(cache_key, result, ttl=CacheTTL.INDICATORS)
        return result
    
    def calculate_rsi(
        self,
        symbol: str,
        time_period: int = 14,
        series_type: str = "close"
    ) -> Dict[str, Any]:
        """Calculate Relative Strength Index."""
        cache_key = f"rsi:{symbol}:{time_period}:{series_type}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        df = self._fetch_ohlcv(symbol, period="2y", interval="1d")
        
        if df is None:
            return build_error_response(f"Unable to fetch data for symbol: {symbol}")
        
        col_name = series_type.capitalize()
        if col_name not in df.columns:
            col_name = series_type.lower()
        
        if col_name not in df.columns:
            return build_error_response(f"Series type '{series_type}' not available")
        
        rsi_values = rsi(df[col_name], period=time_period)
        rsi_values.index = df.index
        
        tech_analysis = {}
        for idx, val in rsi_values.dropna().items():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)
            tech_analysis[date_str] = {"RSI": f"{val:.4f}"}
        
        from .schema import build_meta_data
        result = {
            "Meta Data": build_meta_data(
                "RSI (AlphaSim)",
                symbol,
                extra={"Indicator": "RSI", "Time Period": time_period, "Series Type": series_type}
            ),
            "Technical Analysis: RSI": tech_analysis
        }
        
        self.cache.set(cache_key, result, ttl=CacheTTL.INDICATORS)
        return result


# Global engine instance
_engine: Optional[AlphaSimEngine] = None


def get_engine() -> AlphaSimEngine:
    """Get or create the global engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaSimEngine()
    return _engine
