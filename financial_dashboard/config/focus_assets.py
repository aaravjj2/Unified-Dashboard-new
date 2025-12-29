"""
Focus Assets Configuration - Port 8053
=====================================

Central configuration for primary focus assets:
- Precious Metals: GLD, SLV
- Market ETFs: SPY, QQQ, IWM
- Major Tech: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA

This module provides consistent ticker lists across all dashboard components.
"""

from typing import List, Dict, Tuple
import os

# ============================================================================
# PRIMARY FOCUS ASSETS (GLD, SLV, SPY + Major Tech)
# ============================================================================

# Precious Metals ETFs
PRECIOUS_METALS = ['GLD', 'SLV']
PRECIOUS_METALS_EXTENDED = ['GLD', 'SLV', 'IAU', 'SLV', 'PPLT', 'PALL']  # Gold, Silver, Platinum, Palladium

# Market ETFs  
MARKET_ETFS = ['SPY', 'QQQ', 'IWM', 'DIA']
SECTOR_ETFS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLB', 'XLP', 'XLU', 'XLRE']

# Major Tech (Magnificent 7 + Others)
MAJOR_TECH = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']
TECH_EXTENDED = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD', 'INTC', 'AVGO', 'CRM', 'ORCL', 'ADBE']

# Semiconductor Focus
SEMICONDUCTORS = ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM', 'MU', 'AMAT', 'LRCX', 'KLAC', 'TSM', 'ASML']

# ============================================================================
# COMBINED WATCHLISTS
# ============================================================================

# Primary watchlist - GLD, SLV, SPY + Top Tech (15 tickers)
PRIMARY_WATCHLIST = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD', 'AVGO', 'XLK', 'IWM']

# Extended watchlist (25 tickers)
EXTENDED_WATCHLIST = PRIMARY_WATCHLIST + ['INTC', 'CRM', 'ORCL', 'ADBE', 'DIA', 'XLF', 'XLE', 'IAU', 'VIX', 'TLT']

# Options-focused watchlist (high liquidity options)
OPTIONS_WATCHLIST = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'TSLA', 'AMD', 'AMZN', 'META', 'GOOGL', 'MSFT', 'GLD', 'SLV', 'IWM', 'XLK']

# Strategy Lab default tickers
STRATEGY_LAB_TICKERS = ['SPY', 'QQQ', 'GLD', 'SLV', 'AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD']

# Market Trends default tickers
MARKET_TRENDS_TICKERS = ['SPY', 'QQQ', 'GLD', 'SLV', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD', 'AVGO', 'XLK', 'IWM']

# Volatility Lab default tickers
VOLATILITY_LAB_TICKERS = ['SPY', 'QQQ', 'GLD', 'SLV', 'NVDA', 'AAPL', 'TSLA', 'AMD', 'META']

# Portfolio default tickers (for demo mode)
PORTFOLIO_DEFAULT_TICKERS = ['SPY', 'QQQ', 'GLD', 'SLV', 'AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META']

# ============================================================================
# ASSET CATEGORIES & METADATA
# ============================================================================

ASSET_CATEGORIES: Dict[str, List[str]] = {
    'precious_metals': PRECIOUS_METALS,
    'market_etfs': MARKET_ETFS,
    'sector_etfs': SECTOR_ETFS,
    'major_tech': MAJOR_TECH,
    'semiconductors': SEMICONDUCTORS,
}

ASSET_METADATA: Dict[str, Dict] = {
    'GLD': {'name': 'SPDR Gold Shares', 'category': 'precious_metals', 'sector': 'Commodities', 'asset_class': 'ETF'},
    'SLV': {'name': 'iShares Silver Trust', 'category': 'precious_metals', 'sector': 'Commodities', 'asset_class': 'ETF'},
    'SPY': {'name': 'SPDR S&P 500', 'category': 'market_etf', 'sector': 'Broad Market', 'asset_class': 'ETF'},
    'QQQ': {'name': 'Invesco QQQ', 'category': 'market_etf', 'sector': 'Technology', 'asset_class': 'ETF'},
    'IWM': {'name': 'iShares Russell 2000', 'category': 'market_etf', 'sector': 'Small Cap', 'asset_class': 'ETF'},
    'AAPL': {'name': 'Apple Inc', 'category': 'major_tech', 'sector': 'Technology', 'asset_class': 'Stock'},
    'MSFT': {'name': 'Microsoft Corp', 'category': 'major_tech', 'sector': 'Technology', 'asset_class': 'Stock'},
    'NVDA': {'name': 'NVIDIA Corp', 'category': 'major_tech', 'sector': 'Semiconductors', 'asset_class': 'Stock'},
    'GOOGL': {'name': 'Alphabet Inc', 'category': 'major_tech', 'sector': 'Technology', 'asset_class': 'Stock'},
    'AMZN': {'name': 'Amazon.com', 'category': 'major_tech', 'sector': 'Technology', 'asset_class': 'Stock'},
    'META': {'name': 'Meta Platforms', 'category': 'major_tech', 'sector': 'Technology', 'asset_class': 'Stock'},
    'TSLA': {'name': 'Tesla Inc', 'category': 'major_tech', 'sector': 'Consumer Discretionary', 'asset_class': 'Stock'},
    'AMD': {'name': 'AMD Inc', 'category': 'semiconductors', 'sector': 'Semiconductors', 'asset_class': 'Stock'},
    'AVGO': {'name': 'Broadcom Inc', 'category': 'semiconductors', 'sector': 'Semiconductors', 'asset_class': 'Stock'},
    'XLK': {'name': 'Technology Select Sector', 'category': 'sector_etf', 'sector': 'Technology', 'asset_class': 'ETF'},
}

# ============================================================================
# CORRELATION PAIRS (for pairs trading / hedging)
# ============================================================================

CORRELATION_PAIRS: List[Tuple[str, str]] = [
    ('GLD', 'SLV'),     # Precious metals correlation
    ('SPY', 'QQQ'),     # Market indices correlation
    ('NVDA', 'AMD'),    # Semiconductor competitors
    ('AAPL', 'MSFT'),   # Tech giants correlation
    ('GOOGL', 'META'),  # Ad-tech correlation
    ('GLD', 'SPY'),     # Gold vs equity correlation (often inverse)
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_primary_watchlist() -> List[str]:
    """Get primary watchlist with GLD, SLV, SPY + Major Tech."""
    return PRIMARY_WATCHLIST.copy()

def get_extended_watchlist() -> List[str]:
    """Get extended watchlist with 25 tickers."""
    return EXTENDED_WATCHLIST.copy()

def get_options_watchlist() -> List[str]:
    """Get options-focused watchlist (high liquidity)."""
    return OPTIONS_WATCHLIST.copy()

def get_precious_metals() -> List[str]:
    """Get precious metals tickers."""
    return PRECIOUS_METALS.copy()

def get_major_tech() -> List[str]:
    """Get major tech tickers."""
    return MAJOR_TECH.copy()

def get_tickers_by_category(category: str) -> List[str]:
    """Get tickers by asset category."""
    return ASSET_CATEGORIES.get(category, []).copy()

def get_asset_info(ticker: str) -> Dict:
    """Get metadata for a ticker."""
    return ASSET_METADATA.get(ticker, {'name': ticker, 'category': 'unknown', 'sector': 'Unknown', 'asset_class': 'Stock'})

def is_precious_metal(ticker: str) -> bool:
    """Check if ticker is a precious metal ETF."""
    return ticker in PRECIOUS_METALS_EXTENDED

def is_major_tech(ticker: str) -> bool:
    """Check if ticker is major tech."""
    return ticker in TECH_EXTENDED

def is_market_etf(ticker: str) -> bool:
    """Check if ticker is a market ETF."""
    return ticker in MARKET_ETFS

# ============================================================================
# ENV OVERRIDE (allows customization via environment variable)
# ============================================================================

def get_env_watchlist() -> List[str]:
    """Get watchlist from environment variable if set, else default."""
    env_tickers = os.getenv('FOCUS_TICKERS', '')
    if env_tickers:
        return [t.strip().upper() for t in env_tickers.split(',') if t.strip()]
    return PRIMARY_WATCHLIST.copy()

# ============================================================================
# VOLATILITY PROFILES (for risk management)
# ============================================================================

VOLATILITY_PROFILES: Dict[str, str] = {
    'GLD': 'low',       # Gold - lower volatility safe haven
    'SLV': 'medium',    # Silver - more volatile than gold
    'SPY': 'medium',    # S&P 500 - moderate volatility
    'QQQ': 'medium',    # Nasdaq - slightly higher than SPY
    'AAPL': 'medium',   # Apple - relatively stable large cap
    'MSFT': 'medium',   # Microsoft - stable large cap
    'NVDA': 'high',     # NVIDIA - high growth, high volatility
    'GOOGL': 'medium',  # Alphabet - moderate volatility
    'AMZN': 'medium',   # Amazon - moderate volatility
    'META': 'high',     # Meta - higher volatility
    'TSLA': 'very_high', # Tesla - extreme volatility
    'AMD': 'high',      # AMD - high volatility semi
}

def get_volatility_profile(ticker: str) -> str:
    """Get volatility profile for risk-adjusted position sizing."""
    return VOLATILITY_PROFILES.get(ticker, 'medium')

# ============================================================================
# OPTIONS CHARACTERISTICS
# ============================================================================

OPTIONS_CHARACTERISTICS: Dict[str, Dict] = {
    'SPY': {'avg_spread': 0.01, 'liquidity': 'excellent', 'weekly_options': True, 'recommended_dte': [7, 30, 45]},
    'QQQ': {'avg_spread': 0.02, 'liquidity': 'excellent', 'weekly_options': True, 'recommended_dte': [7, 30, 45]},
    'GLD': {'avg_spread': 0.05, 'liquidity': 'good', 'weekly_options': True, 'recommended_dte': [30, 45, 60]},
    'SLV': {'avg_spread': 0.03, 'liquidity': 'good', 'weekly_options': True, 'recommended_dte': [30, 45, 60]},
    'AAPL': {'avg_spread': 0.02, 'liquidity': 'excellent', 'weekly_options': True, 'recommended_dte': [7, 30, 45]},
    'NVDA': {'avg_spread': 0.05, 'liquidity': 'excellent', 'weekly_options': True, 'recommended_dte': [14, 30, 45]},
    'TSLA': {'avg_spread': 0.10, 'liquidity': 'excellent', 'weekly_options': True, 'recommended_dte': [7, 14, 30]},
    'AMD': {'avg_spread': 0.03, 'liquidity': 'good', 'weekly_options': True, 'recommended_dte': [14, 30, 45]},
    'META': {'avg_spread': 0.05, 'liquidity': 'good', 'weekly_options': True, 'recommended_dte': [14, 30, 45]},
    'AMZN': {'avg_spread': 0.10, 'liquidity': 'excellent', 'weekly_options': True, 'recommended_dte': [14, 30, 45]},
    'GOOGL': {'avg_spread': 0.05, 'liquidity': 'good', 'weekly_options': True, 'recommended_dte': [14, 30, 45]},
    'MSFT': {'avg_spread': 0.03, 'liquidity': 'excellent', 'weekly_options': True, 'recommended_dte': [14, 30, 45]},
}

def get_options_characteristics(ticker: str) -> Dict:
    """Get options trading characteristics for a ticker."""
    return OPTIONS_CHARACTERISTICS.get(ticker, {'avg_spread': 0.10, 'liquidity': 'fair', 'weekly_options': False, 'recommended_dte': [30, 45]})

# Make these available for import
__all__ = [
    'PRIMARY_WATCHLIST',
    'EXTENDED_WATCHLIST',
    'OPTIONS_WATCHLIST',
    'PRECIOUS_METALS',
    'MAJOR_TECH',
    'MARKET_ETFS',
    'STRATEGY_LAB_TICKERS',
    'MARKET_TRENDS_TICKERS',
    'VOLATILITY_LAB_TICKERS',
    'get_primary_watchlist',
    'get_extended_watchlist',
    'get_options_watchlist',
    'get_asset_info',
    'get_volatility_profile',
    'get_options_characteristics',
    'is_precious_metal',
    'is_major_tech',
    'is_market_etf',
    'CORRELATION_PAIRS',
    'ASSET_METADATA',
]
