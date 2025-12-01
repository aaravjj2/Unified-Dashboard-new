"""
Alpaca Market Data Connector (Read-Only)
Priority 2 data source for market sentiment via price action analysis

Environment Variables:
    ALPACA_API_KEY: Alpaca API key
    ALPACA_SECRET: Alpaca API secret
    ALPACA_ENABLED: Enable Alpaca integration (default: false)

SAFETY: This connector is READ-ONLY. No trade execution capabilities.
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
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

# Load keys if ALPACA credentials not set
if not os.getenv("ALPACA_API_KEY") and not os.getenv("APCA_API_KEY_ID"):
    _load_keys_env()

# Support multiple env var naming conventions (APCA_* used in keys.env)
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID") or os.getenv("APCA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET") or os.getenv("APCA_API_SECRET_KEY") or os.getenv("APCA_API_SECRET")
# If ALPACA_ENABLED is explicitly set honor it; otherwise enable if credentials are present
ALPACA_ENABLED = os.getenv("ALPACA_ENABLED", "").lower() == "true" or bool(ALPACA_API_KEY and ALPACA_SECRET)
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL") or os.getenv("APCA_ENDPOINT") or "https://paper-api.alpaca.markets"
# Normalize base URL: ensure we don't end up with duplicate '/v2' segments
if ALPACA_BASE_URL:
    ALPACA_BASE_URL = ALPACA_BASE_URL.rstrip('/')
    if ALPACA_BASE_URL.endswith('/v2'):
        ALPACA_BASE_URL = ALPACA_BASE_URL[: -3]

# Data API is separate from trading API
ALPACA_DATA_URL = "https://data.alpaca.markets"


def get_market_sentiment() -> Dict[str, Any]:
    """
    Derive market sentiment from Alpaca market data
    
    Uses price momentum and volatility indicators from major indices
    
    Returns:
        {
            "score": 0.25,
            "source": "alpaca",
            "indicators": {...},
            "timestamp": "2024-11-23T10:30:00Z",
            "error": None
        }
    """
    if not ALPACA_ENABLED or not ALPACA_API_KEY or not ALPACA_SECRET:
        logger.debug("Alpaca not enabled or credentials not configured")
        return {
            "score": 0.0,
            "source": "alpaca",
            "error": "Not enabled or credentials missing",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    try:
        from datetime import datetime, timedelta
        
        # Calculate date range (last 10 days to ensure we get 5 trading days)
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        # Fetch SPY (S&P 500 ETF) bars for last 5 days
        # Use data.alpaca.markets for market data (not paper-api)
        headers = {
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET
        }
        
        response = requests.get(
            f"{ALPACA_DATA_URL}/v2/stocks/SPY/bars",
            headers=headers,
            params={
                "timeframe": "1Day",
                "limit": 5,
                "adjustment": "split",
                "start": start_date
            },
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        
        bars = data.get("bars") or []
        
        if len(bars) < 2:
            logger.warning("Insufficient Alpaca bar data for sentiment calculation")
            return {
                "score": 0.0,
                "source": "alpaca",
                "error": "Insufficient data",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        
        # Calculate simple momentum: (latest_close - avg_close) / avg_close
        closes = [float(bar.get("c", 0)) for bar in bars]
        avg_close = sum(closes) / len(closes)
        latest_close = closes[-1]
        
        momentum = (latest_close - avg_close) / avg_close if avg_close > 0 else 0.0
        
        # Normalize to [-1.0, +1.0] range (assume ±5% is max sentiment)
        score = max(-1.0, min(1.0, momentum * 20))  # Scale: 5% move = 1.0 score
        
        logger.info(f"✅ Alpaca sentiment: {score:.3f} (momentum: {momentum:.4f})")
        
        return {
            "score": score,
            "source": "alpaca",
            "indicators": {
                "momentum": momentum,
                "latest_close": latest_close,
                "avg_close": avg_close
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": None
        }
        
    except requests.RequestException as e:
        logger.exception("Alpaca API request failed")
        return {
            "score": 0.0,
            "source": "alpaca",
            "error": f"API request failed: {str(e)[:100]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception as e:
        logger.exception("Alpaca sentiment calculation error")
        return {
            "score": 0.0,
            "source": "alpaca",
            "error": f"Calculation error: {str(e)[:100]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


def get_alpaca_positions() -> List[Dict[str, Any]]:
    """
    Fetch current Alpaca positions (READ-ONLY)
    
    Used by Command Center portfolio snapshot widget
    
    Returns:
        [
            {
                "symbol": "AAPL",
                "qty": 10,
                "current_price": 175.50,
                "market_value": 1755.00,
                "unrealized_pl": 50.00
            }
        ]
    """
    if not ALPACA_ENABLED or not ALPACA_API_KEY or not ALPACA_SECRET:
        logger.debug("Alpaca not enabled for positions fetch")
        return []
    
    try:
        headers = {
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET
        }
        
        response = requests.get(
            f"{ALPACA_BASE_URL}/v2/positions",
            headers=headers,
            timeout=10.0
        )
        response.raise_for_status()
        positions = response.json()
        
        # Transform to simplified format
        result = []
        for pos in positions:
            result.append({
                "symbol": pos.get("symbol"),
                "qty": float(pos.get("qty", 0)),
                "current_price": float(pos.get("current_price", 0)),
                "market_value": float(pos.get("market_value", 0)),
                "unrealized_pl": float(pos.get("unrealized_pl", 0))
            })
        
        logger.info(f"✅ Fetched {len(result)} Alpaca positions")
        return result
        
    except Exception as e:
        logger.exception("Alpaca positions fetch error")
        return []


def health_check() -> Dict[str, Any]:
    """
    Check Alpaca API health
    
    Returns:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "enabled": true,
            "credentials_configured": true,
            "last_check": "2024-11-23T10:30:00Z"
        }
    """
    credentials_configured = bool(ALPACA_API_KEY and ALPACA_SECRET)
    
    if not ALPACA_ENABLED:
        return {
            "status": "disabled",
            "enabled": False,
            "credentials_configured": credentials_configured,
            "message": "ALPACA_ENABLED=false",
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    if not credentials_configured:
        return {
            "status": "unhealthy",
            "enabled": True,
            "credentials_configured": False,
            "message": "API credentials not set",
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    # Try account info fetch
    try:
        headers = {
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET
        }
        
        response = requests.get(
            f"{ALPACA_BASE_URL}/v2/account",
            headers=headers,
            timeout=5.0
        )
        response.raise_for_status()
        
        return {
            "status": "healthy",
            "enabled": True,
            "credentials_configured": True,
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception as e:
        logger.warning(f"Alpaca health check failed: {e}")
        return {
            "status": "degraded",
            "enabled": True,
            "credentials_configured": True,
            "error": str(e)[:100],
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
