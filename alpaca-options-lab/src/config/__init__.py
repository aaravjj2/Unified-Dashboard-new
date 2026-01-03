"""
Configuration module for Financial Dashboard.

Phase 1: Added Hybrid Sentiment Engine configuration.
"""

from .focus_assets import (
    PRIMARY_WATCHLIST,
    PRECIOUS_METALS,
    MAJOR_TECH,
    MARKET_ETFS,
    OPTIONS_WATCHLIST,
    STRATEGY_LAB_TICKERS,
    MARKET_TRENDS_TICKERS,
    VOLATILITY_LAB_TICKERS,
    ASSET_METADATA,
    VOLATILITY_PROFILES,
    OPTIONS_CHARACTERISTICS,
    CORRELATION_PAIRS,
    get_primary_watchlist,
    get_volatility_profile,
    get_options_characteristics,
    get_asset_info,
    is_precious_metal,
    is_major_tech,
)

# Phase 1: Sentiment Engine Configuration
from .sentiment import (
    SentimentConfig,
    ScannerConfig,
    get_sentiment_config,
    get_scanner_config,
    get_cfg,
    get_alpaca_keys,
    is_alpaca_configured,
)

# Alias for consistency
get_asset_metadata = get_asset_info

__all__ = [
    # Focus assets
    'PRIMARY_WATCHLIST',
    'PRECIOUS_METALS',
    'MAJOR_TECH',
    'MARKET_ETFS',
    'OPTIONS_WATCHLIST',
    'STRATEGY_LAB_TICKERS',
    'MARKET_TRENDS_TICKERS',
    'VOLATILITY_LAB_TICKERS',
    'ASSET_METADATA',
    'VOLATILITY_PROFILES',
    'OPTIONS_CHARACTERISTICS',
    'CORRELATION_PAIRS',
    'get_primary_watchlist',
    'get_volatility_profile',
    'get_options_characteristics',
    'get_asset_info',
    'get_asset_metadata',
    'is_precious_metal',
    'is_major_tech',
    # Phase 1: Sentiment config
    'SentimentConfig',
    'ScannerConfig',
    'get_sentiment_config',
    'get_scanner_config',
    'get_cfg',
    'get_alpaca_keys',
    'is_alpaca_configured',
]
