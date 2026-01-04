"""
Alpaca Options Lab - Advanced Analytics Module (Phase 2 Modules 11-13)

Comprehensive analytics and backtesting:
- Performance analytics
- Portfolio risk analysis
- Strategy backtesting engine
- ML-based predictions
"""

from src.analytics.performance import (
    PerformanceAnalyzer,
    PerformanceMetrics,
    TradeAnalysis,
    DrawdownAnalysis,
)
from src.analytics.risk import (
    RiskAnalyzer,
    PortfolioRisk,
    VaRCalculator,
    StressTest,
    CorrelationMatrix,
)
from src.analytics.backtest import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    TradeLog,
)
from src.analytics.ml_predictor import (
    VolatilityPredictor,
    DirectionPredictor,
    FeatureEngine,
)

__all__ = [
    # Performance
    "PerformanceAnalyzer",
    "PerformanceMetrics",
    "TradeAnalysis",
    "DrawdownAnalysis",
    # Risk
    "RiskAnalyzer",
    "PortfolioRisk",
    "VaRCalculator",
    "StressTest",
    "CorrelationMatrix",
    # Backtest
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "TradeLog",
    # ML
    "VolatilityPredictor",
    "DirectionPredictor",
    "FeatureEngine",
]
