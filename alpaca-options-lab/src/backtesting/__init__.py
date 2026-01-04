"""
Alpaca Options Lab - Backtesting Module

Production-grade backtesting engine with:
- Event-driven architecture
- Options-specific logic (assignment, expiration, exercise)
- Realistic execution simulation (slippage, fills)
- Comprehensive performance metrics

Components:
- BacktestEngine: Core event-driven engine
- ExecutionSimulator: Order fill simulation
- OptionsBacktest: Options-specific logic
- PerformanceAnalyzer: Metrics and reporting
"""
from src.backtesting.engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    Event,
    EventType,
)
from src.backtesting.execution import (
    ExecutionSimulator,
    Fill,
    SlippageModel,
)
from src.backtesting.options_logic import (
    OptionsBacktest,
    ExpirationHandler,
    AssignmentHandler,
)
from src.backtesting.metrics import (
    PerformanceAnalyzer,
    PerformanceMetrics,
    TradeAnalysis,
)

__all__ = [
    # Engine
    "EventType",
    "Event",
    "BacktestConfig",
    "BacktestResult",
    "BacktestEngine",
    # Execution
    "SlippageModel",
    "Fill",
    "ExecutionSimulator",
    # Options
    "ExpirationHandler",
    "AssignmentHandler",
    "OptionsBacktest",
    # Metrics
    "PerformanceMetrics",
    "TradeAnalysis",
    "PerformanceAnalyzer",
]
