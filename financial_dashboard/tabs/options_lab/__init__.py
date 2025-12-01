"""
Options Lab Module - Enhanced with Full Feature Suite

14 canonical subtabs:
1. Chain Viewer
2. Greeks Calculator
3. IV Surface & Forecast
4. Flow Scanner - Options flow & GEX analysis
5. IV Analysis - Term structure, skew, IV percentile
6. Strategy Builder - Visual multi-leg constructor
7. Manual Trade / Paper Orders
8. Portfolio Greeks - Aggregate Greeks dashboard
9. Screener - Find options by criteria
10. AI Recommendations - Smart trade suggestions
11. Earnings Calendar - Track earnings & expected moves
12. Trade Journal - Track & analyze trades
13. Backtester / Strategy
14. Settings

All controls follow STABLE ID RULE (ol-* prefix).
Safe layout factory pattern with error boundaries.

Author: Phase 31+ Enhanced Options Lab
Status: Canonical with Full Feature Suite
"""

from .layout import create_layout
from .callbacks import register_callbacks

# Import new modules for external access
try:
    from .flow_scanner import OptionsFlowScanner, get_flow_scanner
    from .iv_analysis import IVAnalyzer, get_iv_analyzer
    from .portfolio_greeks import PortfolioGreeks, get_portfolio_greeks
    from .strategy_builder import StrategyBuilder, get_strategy_builder
    from .options_screener import OptionsScreener, get_options_screener
    from .trade_journal import TradeJournal, get_trade_journal
    from .ai_recommendations import AIRecommendationEngine, get_recommendation_engine
    from .earnings_calendar import EarningsCalendar, get_earnings_calendar
except ImportError as e:
    # Graceful degradation if modules not yet available
    import logging
    logging.getLogger(__name__).warning(f"Optional module import failed: {e}")

# Backward compatibility alias for index.py
layout = create_layout

__all__ = [
    'create_layout', 
    'layout', 
    'register_callbacks',
    'OptionsFlowScanner',
    'IVAnalyzer',
    'PortfolioGreeks',
    'StrategyBuilder',
    'OptionsScreener',
    'TradeJournal',
    'AIRecommendationEngine',
    'EarningsCalendar'
]
