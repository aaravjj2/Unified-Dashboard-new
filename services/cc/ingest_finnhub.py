"""
Finnhub Market Sentiment Connector
Priority 1 data source for market sentiment analysis

Environment Variables:
    FINNHUB_API_KEY: Finnhub API key (required)
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

# Load keys.env if environment variables not already set
def _load_keys_env():
    """Load keys.env file from project root"""
    try:
        from dotenv import load_dotenv
        # Find project root (look for keys.env)
        current = Path(__file__).resolve()
        for parent in current.parents:
            keys_file = parent / "keys.env"
            if keys_file.exists():
                load_dotenv(keys_file, override=False)
                logger.debug(f"Loaded keys from {keys_file}")
                return True
    except ImportError:
        pass  # dotenv not installed, try manual load
    except Exception as e:
        logger.warning(f"Failed to load keys.env: {e}")
    return False

# Load keys if FINNHUB_API_KEY not set
if not os.getenv("FINNHUB_API_KEY"):
    _load_keys_env()

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
        # Use general market news (free tier) instead of news-sentiment (premium)
        response = requests.get(
            f"{FINNHUB_BASE_URL}/news",
            params={
                "category": "general",
                "token": FINNHUB_API_KEY
            },
            timeout=10.0
        )
        response.raise_for_status()
        articles = response.json()
        
        if not articles or len(articles) == 0:
            logger.warning("No Finnhub news articles available")
            return {
                "score": 0.0,
                "source": "finnhub",
                "error": "No articles available",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        
        # Simple keyword-based sentiment analysis
        # Count positive vs negative keywords in headlines
        positive_keywords = ['gain', 'rise', 'surge', 'rally', 'jump', 'soar', 'boost', 
                            'bull', 'up', 'high', 'record', 'growth', 'profit', 'win']
        negative_keywords = ['drop', 'fall', 'crash', 'decline', 'plunge', 'sink', 'down',
                            'bear', 'low', 'loss', 'fear', 'risk', 'worry', 'concern']
        
        positive_count = 0
        negative_count = 0
        articles_analyzed = 0
        
        for article in articles[:50]:  # Limit to 50 articles
            headline = article.get("headline", "").lower()
            summary = article.get("summary", "").lower()
            text = headline + " " + summary
            
            for keyword in positive_keywords:
                if keyword in text:
                    positive_count += 1
            for keyword in negative_keywords:
                if keyword in text:
                    negative_count += 1
            articles_analyzed += 1
        
        # Calculate sentiment score from keyword counts
        total_keywords = positive_count + negative_count
        if total_keywords > 0:
            raw_score = (positive_count - negative_count) / total_keywords
        else:
            raw_score = 0.0
        
        # Clamp to valid range
        score = max(-1.0, min(1.0, raw_score))
        
        logger.info(f"✅ Finnhub sentiment: {score:.3f} (articles: {articles_analyzed}, pos: {positive_count}, neg: {negative_count})")
        
        return {
            "score": score,
            "source": "finnhub",
            "articles_count": articles_analyzed,
            "raw_data": {
                "positive_keywords": positive_count,
                "negative_keywords": negative_count
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
