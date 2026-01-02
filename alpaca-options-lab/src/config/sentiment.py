"""
Sentiment Engine Configuration - Phase 1: Hybrid Sentiment Engine
==================================================================
Configuration for news and sentiment data sources.
"""

import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_env(k: str, default: Any = None) -> Any:
    """Get environment variable with optional default."""
    return os.getenv(k, default)


def get_cfg(k: str, default=None):
    """Get configuration value from environment."""
    return get_env(k, default)


# =============================================================================
# ALPACA CONFIGURATION
# =============================================================================
def get_alpaca_keys() -> tuple[Optional[str], Optional[str]]:
    """Get Alpaca API credentials (tries multiple env var names)."""
    api_key = get_cfg('APCA_API_KEY_ID') or get_cfg('ALPACA_API_KEY')
    secret_key = get_cfg('APCA_API_SECRET_KEY') or get_cfg('ALPACA_SECRET_KEY')
    return api_key, secret_key


def is_alpaca_configured() -> bool:
    """Check if Alpaca credentials are available."""
    key, secret = get_alpaca_keys()
    return bool(key and secret)


# =============================================================================
# SENTIMENT ENGINE CONFIGURATION
# =============================================================================
class SentimentConfig:
    """Configuration for the Hybrid Sentiment Engine."""
    
    # Finnhub (Primary sentiment source)
    FINNHUB_API_KEY: Optional[str] = None
    FINNHUB_BASE_URL: str = "https://finnhub.io/api/v1"
    
    # NewsAPI (Macro context)
    NEWSAPI_KEY: Optional[str] = None
    NEWSAPI_BASE_URL: str = "https://newsapi.org/v2"
    
    # StockTwits (Retail sentiment)
    STOCKTWITS_API_KEY: Optional[str] = None
    STOCKTWITS_BASE_URL: str = "https://api.stocktwits.com/api/2"
    
    # Tiingo (Backup news source)
    TIINGO_API_KEY: Optional[str] = None
    TIINGO_BASE_URL: str = "https://api.tiingo.com"
    
    # Cache settings
    CACHE_TTL_SECONDS: int = 300  # 5 minutes default
    NEWS_CACHE_TTL_SECONDS: int = 120  # 2 minutes for news
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = 60
    
    # Feature flags
    ENABLE_SENTIMENT_ENGINE: bool = True
    ENABLE_PATTERN_DETECTION: bool = True
    
    @classmethod
    def load(cls) -> 'SentimentConfig':
        """Load configuration from environment variables."""
        config = cls()
        config.FINNHUB_API_KEY = get_cfg('FINNHUB_API_KEY')
        config.NEWSAPI_KEY = get_cfg('NEWSAPI_KEY')
        config.STOCKTWITS_API_KEY = get_cfg('STOCKTWITS_API_KEY')
        config.TIINGO_API_KEY = get_cfg('TIINGO_API_KEY')
        config.ENABLE_SENTIMENT_ENGINE = get_cfg('ENABLE_SENTIMENT_ENGINE', '1') == '1'
        config.ENABLE_PATTERN_DETECTION = get_cfg('ENABLE_PATTERN_DETECTION', '1') == '1'
        return config
    
    def is_finnhub_configured(self) -> bool:
        """Check if Finnhub API is configured."""
        return bool(self.FINNHUB_API_KEY)
    
    def is_newsapi_configured(self) -> bool:
        """Check if NewsAPI is configured."""
        return bool(self.NEWSAPI_KEY)
    
    def is_tiingo_configured(self) -> bool:
        """Check if Tiingo API is configured."""
        return bool(self.TIINGO_API_KEY)
    
    def get_available_sources(self) -> list[str]:
        """Get list of configured news/sentiment sources."""
        sources = []
        if self.is_finnhub_configured():
            sources.append('finnhub')
        if self.is_newsapi_configured():
            sources.append('newsapi')
        if self.is_tiingo_configured():
            sources.append('tiingo')
        # StockTwits public API always available
        sources.append('stocktwits')
        # FinViz scraping always available (no API key needed)
        sources.append('finviz')
        return sources
    
    def log_status(self) -> None:
        """Log the configuration status."""
        sources = self.get_available_sources()
        logger.info(f"📡 Sentiment Engine Sources: {', '.join(sources)}")
        if not self.is_finnhub_configured():
            logger.warning("⚠️ FINNHUB_API_KEY not set - using mock sentiment data")
        if not self.is_newsapi_configured():
            logger.warning("⚠️ NEWSAPI_KEY not set - macro news limited")


# Singleton instance
_sentiment_config: Optional[SentimentConfig] = None


def get_sentiment_config() -> SentimentConfig:
    """Get the singleton sentiment configuration."""
    global _sentiment_config
    if _sentiment_config is None:
        _sentiment_config = SentimentConfig.load()
    return _sentiment_config


# =============================================================================
# SCANNER WORKSPACE CONFIGURATION
# =============================================================================
class ScannerConfig:
    """Configuration for the Scanner Workspace UI."""
    
    # Default watchlist symbols
    DEFAULT_SYMBOLS: list[str] = ['NVDA', 'TSLA', 'SPY', 'GLD']
    
    # Refresh intervals (milliseconds)
    HYPE_GAUGE_REFRESH_MS: int = 30000  # 30 seconds
    NEWS_FEED_REFRESH_MS: int = 60000   # 1 minute
    CHART_REFRESH_MS: int = 15000       # 15 seconds
    
    # UI settings
    MAX_NEWS_ITEMS: int = 20
    PATTERN_CONFIDENCE_THRESHOLD: float = 0.7
    
    @classmethod
    def load(cls) -> 'ScannerConfig':
        """Load scanner configuration."""
        config = cls()
        # Could extend to load from env/file in future
        return config


def get_scanner_config() -> ScannerConfig:
    """Get scanner configuration."""
    return ScannerConfig.load()

