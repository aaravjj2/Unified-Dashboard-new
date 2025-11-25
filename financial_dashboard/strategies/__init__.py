"""
Strategies Package - Trading Strategy Implementations

This package contains all trading strategy implementations for the
Unified Financial Dashboard Options Alpha module.

Available Strategies:
- IncomeGeneratorStrategy: Iron Condor bot for range-bound income
- TrendFollowerStrategy: Bull Call Spread bot for momentum trading
- VolatilityHedgeStrategy: Bear Put Spread bot for crash protection
"""

from strategies.base_strategy import BaseStrategy
from strategies.income_generator_strategy import IncomeGeneratorStrategy
from strategies.trend_follower_strategy import TrendFollowerStrategy
from strategies.volatility_hedge_strategy import VolatilityHedgeStrategy

__all__ = [
    'BaseStrategy',
    'IncomeGeneratorStrategy',
    'TrendFollowerStrategy',
    'VolatilityHedgeStrategy'
]
