"""
yfinance Fallback Market Data Connector
Priority 3 data source when Finnhub and Alpaca are unavailable

No API key required - free tier via Yahoo Finance
"""

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Lazy import yfinance to avoid import overhead if not used
_yfinance = None


def _get_yfinance():
    """Lazy import yfinance"""
    global _yfinance
    if _yfinance is None:
        try:
            import yfinance as yf
            _yfinance = yf
        except ImportError:
            logger.warning("yfinance not installed - sentiment unavailable")
            _yfinance = False  # Prevent repeated import attempts
    return _yfinance


def get_market_sentiment() -> Dict[str, Any]:
    """
    Derive market sentiment from yfinance price action
    
    Uses SPY (S&P 500 ETF) momentum and trend indicators
    
    Returns:
        {
            "score": 0.15,
            "source": "yfinance",
            "indicators": {...},
            "timestamp": "2024-11-23T10:30:00Z",
            "error": None
        }
    """
    yf = _get_yfinance()
    
    if not yf:
        return {
            "score": 0.0,
            "source": "yfinance",
            "error": "yfinance not installed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    try:
        # Fetch SPY data for last 10 days
        spy = yf.Ticker("SPY")
        hist = spy.history(period="10d")
        
        if hist.empty or len(hist) < 2:
            logger.warning("Insufficient yfinance data for sentiment calculation")
            return {
                "score": 0.0,
                "source": "yfinance",
                "error": "Insufficient data",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        
        # Calculate momentum: (latest_close - avg_close) / avg_close
        closes = hist['Close'].values
        avg_close = closes.mean()
        latest_close = closes[-1]
        
        momentum = (latest_close - avg_close) / avg_close if avg_close > 0 else 0.0
        
        # Normalize to [-1.0, +1.0] range (assume ±5% is max sentiment)
        score = max(-1.0, min(1.0, momentum * 20))  # Scale: 5% move = 1.0 score
        
        # Calculate trend: compare 5-day average vs 10-day average
        closes_5d = closes[-5:].mean()
        closes_10d = closes.mean()
        trend = (closes_5d - closes_10d) / closes_10d if closes_10d > 0 else 0.0
        
        # Weight momentum (70%) and trend (30%)
        weighted_score = (0.7 * score) + (0.3 * trend * 20)
        weighted_score = max(-1.0, min(1.0, weighted_score))
        
        logger.info(f"✅ yfinance sentiment: {weighted_score:.3f} (momentum: {momentum:.4f}, trend: {trend:.4f})")
        
        return {
            "score": weighted_score,
            "source": "yfinance",
            "indicators": {
                "momentum": momentum,
                "trend": trend,
                "latest_close": float(latest_close),
                "avg_close": float(avg_close)
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": None
        }
        
    except Exception as e:
        logger.exception("yfinance sentiment calculation error")
        return {
            "score": 0.0,
            "source": "yfinance",
            "error": f"Calculation error: {str(e)[:100]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


def health_check() -> Dict[str, Any]:
    """
    Check yfinance availability
    
    Returns:
        {
            "status": "healthy" | "unhealthy",
            "library_available": true,
            "last_check": "2024-11-23T10:30:00Z"
        }
    """
    yf = _get_yfinance()
    
    if not yf:
        return {
            "status": "unhealthy",
            "library_available": False,
            "message": "yfinance not installed",
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    # Try a simple quote fetch
    try:
        spy = yf.Ticker("SPY")
        info = spy.info
        
        if info and 'symbol' in info:
            return {
                "status": "healthy",
                "library_available": True,
                "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        else:
            return {
                "status": "degraded",
                "library_available": True,
                "message": "API response incomplete",
                "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
    except Exception as e:
        logger.warning(f"yfinance health check failed: {e}")
        return {
            "status": "degraded",
            "library_available": True,
            "error": str(e)[:100],
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
