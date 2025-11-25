"""
Finnhub Market Sentiment Connector
Priority 1 data source for market sentiment analysis

Environment Variables:
    FINNHUB_API_KEY: Finnhub API key (required)
"""

import os
import logging
import time
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def get_market_sentiment() -> Dict[str, Any]:
    """
    Fetch market sentiment from Finnhub News Sentiment API
    
    Returns sentiment score in range [-1.0, +1.0]
    
    Returns:
        {
            "score": 0.45,
            "source": "finnhub",
            "articles_count": 50,
            "timestamp": "2024-11-23T10:30:00Z",
            "error": None
        }
    """
    if not FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set - skipping Finnhub sentiment")
        return {
            "score": 0.0,
            "source": "finnhub",
            "error": "API key not configured",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    try:
        # Fetch market news sentiment for major indices
        # SPY (S&P 500 ETF) is a good proxy for overall market sentiment
        response = requests.get(
            f"{FINNHUB_BASE_URL}/news-sentiment",
            params={
                "symbol": "SPY",
                "token": FINNHUB_API_KEY
            },
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract sentiment metrics
        # Finnhub provides: buzz (volume metrics) and sentiment (polarity metrics)
        sentiment_data = data.get("sentiment", {})
        
        # Calculate composite sentiment score
        # Use bullishPercent, bearishPercent, and articlesInLastWeek
        bullish_pct = sentiment_data.get("bullishPercent", 0.5)
        bearish_pct = sentiment_data.get("bearishPercent", 0.5)
        
        # Normalize to [-1.0, +1.0] range
        # Formula: (bullish - bearish) normalized
        raw_score = (bullish_pct - bearish_pct)
        
        # Clamp to valid range
        score = max(-1.0, min(1.0, raw_score))
        
        articles_count = data.get("buzz", {}).get("articlesInLastWeek", 0)
        
        logger.info(f"✅ Finnhub sentiment: {score:.3f} (articles: {articles_count})")
        
        return {
            "score": score,
            "source": "finnhub",
            "articles_count": articles_count,
            "raw_data": {
                "bullish_percent": bullish_pct,
                "bearish_percent": bearish_pct
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": None
        }
        
    except requests.RequestException as e:
        logger.exception("Finnhub API request failed")
        return {
            "score": 0.0,
            "source": "finnhub",
            "error": f"API request failed: {str(e)[:100]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception as e:
        logger.exception("Finnhub sentiment calculation error")
        return {
            "score": 0.0,
            "source": "finnhub",
            "error": f"Calculation error: {str(e)[:100]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


def health_check() -> Dict[str, Any]:
    """
    Check Finnhub API health
    
    Returns:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "api_key_configured": true,
            "last_check": "2024-11-23T10:30:00Z"
        }
    """
    api_key_configured = bool(FINNHUB_API_KEY)
    
    if not api_key_configured:
        return {
            "status": "unhealthy",
            "api_key_configured": False,
            "message": "FINNHUB_API_KEY not set",
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    # Try a simple API call to verify connectivity
    try:
        response = requests.get(
            f"{FINNHUB_BASE_URL}/quote",
            params={"symbol": "AAPL", "token": FINNHUB_API_KEY},
            timeout=5.0
        )
        response.raise_for_status()
        
        return {
            "status": "healthy",
            "api_key_configured": True,
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception as e:
        logger.warning(f"Finnhub health check failed: {e}")
        return {
            "status": "degraded",
            "api_key_configured": True,
            "error": str(e)[:100],
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
