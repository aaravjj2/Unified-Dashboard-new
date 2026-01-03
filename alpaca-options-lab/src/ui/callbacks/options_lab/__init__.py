"""
Options Lab Module - Enhanced with Full Feature Suite

v2 Layout: Consolidated 5 tabs (NOW DEFAULT):
1. Chain Viewer - Options chain browser
2. Analysis Hub - Greeks, IV Surface, Flow Scanner, IV Analysis
3. Strategy Lab - Strategy builder, screener, backtester
4. AI Recommendations - Enhanced smart trade suggestions
5. Portfolio & Journal - Portfolio Greeks, earnings calendar, trade journal

v1 Layout (legacy): Available via create_layout_v1 for backward compatibility

All controls follow STABLE ID RULE (ol-* prefix).
Safe layout factory pattern with error boundaries.

Author: Phase 31+ Enhanced Options Lab
Status: Canonical with Full Feature Suite (v2 DEFAULT)
"""

from .callbacks import register_callbacks

# Import v2 consolidated layout AS DEFAULT
try:
    from .layout_v2 import create_layout as create_layout
    V2_AVAILABLE = True
except ImportError:
    # Fallback to v1 if v2 not available
    from .layout import create_layout
    V2_AVAILABLE = False

# Keep v1 available for backward compatibility
from .layout import create_layout as create_layout_v1

# Import enhanced AI recommendations v2
try:
    from .ai_recommendations_v2 import EnhancedAIRecommendationEngine, get_enhanced_recommendation_engine
except ImportError:
    pass

# Import Alpaca-style UI components
try:
    from .alpaca_ui import create_alpaca_layout
    from .alpaca_ui_enhanced import create_enhanced_options_layout
    from .alpaca_callbacks import *  # Register callbacks
    from .alpaca_options import get_alpaca_client, get_cached_option_chain, get_alpaca_metrics
    from .options_cache import get_options_cache, OptionsChainCache
    from .circuit_breaker import CircuitBreaker, get_all_breaker_stats, with_circuit_breaker
    from .export_utils import export_chain_to_csv, export_chain_to_json
    from .health_endpoints import health_bp as options_health_blueprint
    from .types import OptionContract, ChainData, CacheStats, CircuitBreakerStats, AlpacaMetrics
    # Import new enhanced modules
    from .analytics import (
        calculate_portfolio_greeks, create_greeks_dashboard, create_iv_surface,
        create_iv_skew_chart, simulate_pnl, create_payoff_diagram,
        create_volume_oi_heatmap, calculate_max_pain, calculate_put_call_ratio
    )
    from .strategies import (
        StrategyType, StrategyLeg, StrategyTemplate,
        build_bull_call_spread, build_bear_put_spread, build_iron_condor,
        build_iron_butterfly, build_long_straddle, build_long_strangle,
        suggest_strategies, calculate_strategy_greeks
    )
    from .trading_client import AlpacaTradingClient, OrderRequest, Order, Position, RiskLimits
    from .ml_integration import OptionsMLEngine, PricePrediction, IVForecast, StrikeRecommendation, TradeRecommendation
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Alpaca module import failed: {e}")

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

# Backward compatibility alias for index.py - USE V2 as default
layout = create_layout

__all__ = [
    'create_layout',      # NOW USES V2 (5 tabs)
    'create_layout_v1',   # Legacy 12-subtab version
    'V2_AVAILABLE',
    'layout', 
    'register_callbacks',
    # Feature modules
    'OptionsFlowScanner',
    'IVAnalyzer',
    'PortfolioGreeks',
    'StrategyBuilder',
    'OptionsScreener',
    'TradeJournal',
    'AIRecommendationEngine',
    'EarningsCalendar',
    # Alpaca integration
    'create_alpaca_layout',
    'get_alpaca_client',
    'get_cached_option_chain',
    'get_alpaca_metrics',
    # Cache & resilience
    'get_options_cache',
    'OptionsChainCache',
    'CircuitBreaker',
    'get_all_breaker_stats',
    'with_circuit_breaker',
    # Export utilities  
    'export_chain_to_csv',
    'export_chain_to_json',
    # Health endpoints
    'options_health_blueprint',
    # Type definitions
    'OptionContract',
    'ChainData',
    'CacheStats',
    'CircuitBreakerStats',
    'AlpacaMetrics',
]
