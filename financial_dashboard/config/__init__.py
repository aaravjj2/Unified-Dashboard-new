"""
Configuration module for Financial Dashboard.
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

# Alias for consistency
get_asset_metadata = get_asset_info

__all__ = [
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
]
