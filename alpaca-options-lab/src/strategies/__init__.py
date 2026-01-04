"""
Alpaca Options Lab - Strategy Engine (Phase 2 Module 7)

Production-grade strategy framework with:
- Abstract Strategy base class with lifecycle hooks
- Strategy Registry for dynamic loading
- Strategy Context for system access
- Concurrent execution with error isolation
- YAML-based configuration

Components:
- base.py: Strategy base class and config
- context.py: Strategy execution context
- registry.py: Dynamic strategy registration
- executor.py: Concurrent strategy execution
- library/: Pre-built strategies (Iron Condor, Wheel, etc.)
"""

from src.strategies.base import (
    Strategy,
    StrategyConfig,
    Signal,
    OrderLeg,
)
from src.strategies.context import StrategyContext
from src.strategies.registry import StrategyRegistry
from src.strategies.executor import StrategyExecutor

__all__ = [
    "Strategy",
    "StrategyConfig",
    "Signal",
    "OrderLeg",
    "StrategyContext",
    "StrategyRegistry",
    "StrategyExecutor",
]
