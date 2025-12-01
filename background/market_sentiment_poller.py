"""
Market Sentiment Poller - Background Service
Polls market sentiment from Finnhub, Alpaca, and yfinance at configurable intervals

Environment Variables:
    CC_MARKET_SENTIMENT_INTERVAL: Poll interval in seconds (default: 60)
    CC_ENABLE_SENTIMENT_PUB: Enable sentiment publishing to external services (default: false)
    CC_SAFE_MODE: Enable safe mode (prevents external API calls in test env) (default: true)
    FINNHUB_API_KEY: Finnhub API key
    ALPACA_API_KEY: Alpaca API key
    ALPACA_SECRET: Alpaca API secret
    ALPACA_ENABLED: Enable Alpaca integration

Usage:
    # Start as background thread
    from background.market_sentiment_poller import start_poller, stop_poller
    start_poller()
    
    # Stop gracefully
    stop_poller()
"""

import os
import logging
import time
import json
import threading
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to sys.path at import time (before any project imports)
# Handle multiple possible locations of this file
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent  # background/ -> project root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

# Sentinel to track if imports succeeded
_finnhub_sentiment = None
_alpaca_sentiment = None  
_yfinance_sentiment = None

def _lazy_import_sentiment_modules():
    """Lazily import sentiment modules to ensure sys.path is set up"""
    global _finnhub_sentiment, _alpaca_sentiment, _yfinance_sentiment
    
    # Use importlib.util to import from absolute paths
    import importlib.util
    
    project_root = Path(__file__).resolve().parent.parent
    
    if _finnhub_sentiment is None:
        try:
            spec = importlib.util.spec_from_file_location(
                "ingest_finnhub", 
                project_root / "services" / "cc" / "ingest_finnhub.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _finnhub_sentiment = module.get_market_sentiment
            logger.info("✅ Finnhub sentiment module loaded successfully")
        except Exception as e:
            logger.warning(f"Could not import finnhub sentiment: {e}")
            _finnhub_sentiment = False
    
    if _alpaca_sentiment is None:
        try:
            spec = importlib.util.spec_from_file_location(
                "alpaca_market",
                project_root / "services" / "cc" / "alpaca_market.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _alpaca_sentiment = module.get_market_sentiment
            logger.info("✅ Alpaca sentiment module loaded successfully")
        except Exception as e:
            logger.warning(f"Could not import alpaca sentiment: {e}")
            _alpaca_sentiment = False
    
    if _yfinance_sentiment is None:
        try:
            spec = importlib.util.spec_from_file_location(
                "yfinance_fallback",
                project_root / "services" / "cc" / "yfinance_fallback.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _yfinance_sentiment = module.get_market_sentiment
            logger.info("✅ yfinance sentiment module loaded successfully")
        except Exception as e:
            logger.warning(f"Could not import yfinance sentiment: {e}")
            _yfinance_sentiment = False

# Configuration
POLL_INTERVAL = int(os.getenv("CC_MARKET_SENTIMENT_INTERVAL", "60"))
ENABLE_PUB = os.getenv("CC_ENABLE_SENTIMENT_PUB", "false").lower() == "true"
SAFE_MODE = os.getenv("CC_SAFE_MODE", "true").lower() == "true"
LOG_DIR = Path("reports/command_center/logs/market_sentiment")

# Poller state
_poller_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

def _poll_sentiment_sources() -> Dict[str, Any]:
    """
    Poll all sentiment sources in priority order
    
    Priority:
        1. Finnhub (news sentiment)
        2. Alpaca (price momentum)
        3. yfinance (fallback)
    
    Returns:
        {
            "market_sentiment_score": 0.35,
            "sources": ["finnhub", "alpaca"],
            "source_scores": {
                "finnhub": 0.45,
                "alpaca": 0.25,
                "yfinance": null
            },
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    # Ensure modules are loaded
    _lazy_import_sentiment_modules()
    
    source_scores = {}
    active_sources = []

    # Poll Finnhub (Priority 1)
    if _finnhub_sentiment and callable(_finnhub_sentiment):
        try:
            result = _finnhub_sentiment()
            if result.get("error") is None:
                source_scores["finnhub"] = result.get("score", 0.0)
                active_sources.append("finnhub")
                logger.debug(f"Finnhub sentiment: {source_scores['finnhub']:.3f}")
            else:
                logger.warning(f"Finnhub error: {result.get('error')}")
                source_scores["finnhub"] = None
        except Exception:
            logger.exception("Failed to fetch Finnhub sentiment")
            source_scores["finnhub"] = None
    else:
        logger.error("Finnhub sentiment module not available")
        source_scores["finnhub"] = None
    
    # Poll Alpaca (Priority 2)
    if _alpaca_sentiment and callable(_alpaca_sentiment):
        try:
            result = _alpaca_sentiment()
            if result.get("error") is None:
                source_scores["alpaca"] = result.get("score", 0.0)
                active_sources.append("alpaca")
                logger.debug(f"Alpaca sentiment: {source_scores['alpaca']:.3f}")
            else:
                logger.debug(f"Alpaca skipped: {result.get('error')}")
                source_scores["alpaca"] = None
        except Exception:
            logger.exception("Failed to fetch Alpaca sentiment")
            source_scores["alpaca"] = None
    else:
        logger.error("Alpaca sentiment module not available")
        source_scores["alpaca"] = None
    
    # Poll yfinance (Priority 3 - Fallback)
    if _yfinance_sentiment and callable(_yfinance_sentiment):
        try:
            result = _yfinance_sentiment()
            if result.get("error") is None:
                source_scores["yfinance"] = result.get("score", 0.0)
                active_sources.append("yfinance")
                logger.debug(f"yfinance sentiment: {source_scores['yfinance']:.3f}")
            else:
                logger.debug(f"yfinance skipped: {result.get('error')}")
                source_scores["yfinance"] = None
        except Exception:
            logger.exception("Failed to fetch yfinance sentiment")
            source_scores["yfinance"] = None
    else:
        logger.error("yfinance sentiment module not available")
        source_scores["yfinance"] = None
    
    # Calculate weighted composite score
    # Priority weighting: Finnhub (50%), Alpaca (30%), yfinance (20%)
    composite_score = 0.0
    total_weight = 0.0
    
    if source_scores.get("finnhub") is not None:
        composite_score += source_scores["finnhub"] * 0.5
        total_weight += 0.5
    
    if source_scores.get("alpaca") is not None:
        composite_score += source_scores["alpaca"] * 0.3
        total_weight += 0.3
    
    if source_scores.get("yfinance") is not None:
        composite_score += source_scores["yfinance"] * 0.2
        total_weight += 0.2
    
    # Normalize by total weight
    if total_weight > 0:
        composite_score = composite_score / total_weight
    else:
        # No sources available - default to neutral
        composite_score = 0.0
    
    # Clamp to valid range
    composite_score = max(-1.0, min(1.0, composite_score))
    
    return {
        "market_sentiment_score": composite_score,
        "sources": active_sources,
        "source_scores": source_scores,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


def _write_sentiment_log(sentiment_data: Dict[str, Any]):
    """
    Write sentiment data to JSON log file
    
    Log files: reports/command_center/logs/market_sentiment/sentiment_<timestamp>.json
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = int(time.time())
    log_file = LOG_DIR / f"sentiment_{timestamp}.json"
    
    try:
        with open(log_file, 'w') as f:
            json.dump(sentiment_data, f, indent=2)
        logger.debug(f"Wrote sentiment log: {log_file.name}")
    except Exception as e:
        logger.exception("Failed to write sentiment log")


def _poller_loop():
    """
    Main poller loop - runs in background thread
    """
    logger.info(f"🚀 Market sentiment poller started (interval: {POLL_INTERVAL}s, safe_mode: {SAFE_MODE})")
    
    while not _stop_event.is_set():
        try:
            # If safe mode is enabled we still run the poller but rely on
            # upstream services to respect safe-mode behaviour (they should
            # return mock or cached scores). Skipping the poll entirely
            # made the API return no data in test environments.
            if SAFE_MODE:
                logger.debug("Safe mode enabled - running poll with safe-mode fallbacks")

            # Poll sentiment sources
            sentiment_data = _poll_sentiment_sources()

            # Log results
            logger.info(
                f"📊 Market sentiment: {sentiment_data['market_sentiment_score']:.3f} "
                f"(sources: {', '.join(sentiment_data['sources'])})"
            )

            # Write to log file
            _write_sentiment_log(sentiment_data)
            
            # Publish to external services (if enabled)
            if ENABLE_PUB:
                # TODO: Implement sentiment publishing to external services
                logger.debug("Sentiment publishing not implemented yet")
            
        except Exception as e:
            logger.exception("Poller loop error")
        
        # Wait for next poll interval (or stop signal)
        _stop_event.wait(POLL_INTERVAL)
    
    logger.info("🛑 Market sentiment poller stopped")


def start_poller():
    """
    Start market sentiment poller in background thread
    
    Safe to call multiple times - will not start duplicate threads
    """
    global _poller_thread
    
    if _poller_thread is not None and _poller_thread.is_alive():
        logger.warning("Poller already running")
        return
    
    _stop_event.clear()
    _poller_thread = threading.Thread(target=_poller_loop, daemon=True, name="MarketSentimentPoller")
    _poller_thread.start()
    logger.info("✅ Market sentiment poller thread started")


def stop_poller(timeout: float = 5.0):
    """
    Stop market sentiment poller gracefully
    
    Args:
        timeout: Maximum wait time for thread to stop (seconds)
    """
    global _poller_thread
    
    if _poller_thread is None or not _poller_thread.is_alive():
        logger.warning("Poller not running")
        return
    
    logger.info("Stopping market sentiment poller...")
    _stop_event.set()
    _poller_thread.join(timeout=timeout)
    
    if _poller_thread.is_alive():
        logger.warning(f"Poller did not stop within {timeout}s timeout")
    else:
        logger.info("✅ Market sentiment poller stopped gracefully")
        _poller_thread = None


def get_poller_status() -> Dict[str, Any]:
    """
    Get current poller status
    
    Returns:
        {
            "running": true,
            "poll_interval": 60,
            "safe_mode": true,
            "enable_pub": false
        }
    """
    global _poller_thread
    
    return {
        "running": _poller_thread is not None and _poller_thread.is_alive(),
        "poll_interval": POLL_INTERVAL,
        "safe_mode": SAFE_MODE,
        "enable_pub": ENABLE_PUB
    }
