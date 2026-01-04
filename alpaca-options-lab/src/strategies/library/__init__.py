"""
Alpaca Options Lab - Strategy Library

Pre-built production-ready strategies:
1. Iron Condor (0DTE) - Short volatility income
2. Covered Call Wheel - Income on equity holdings
3. Volatility Arbitrage - Calendar spreads
4. Delta-Neutral Market Making - Gamma scalping
5. Earnings Straddle - Event-driven volatility
"""

from src.strategies.library.iron_condor import IronCondor0DTEStrategy
from src.strategies.library.wheel import CoveredCallWheelStrategy
from src.strategies.library.calendar_spread import CalendarSpreadStrategy
from src.strategies.library.delta_neutral import DeltaNeutralStrategy
from src.strategies.library.earnings_straddle import EarningsStraddleStrategy

__all__ = [
    "IronCondor0DTEStrategy",
    "CoveredCallWheelStrategy",
    "CalendarSpreadStrategy",
    "DeltaNeutralStrategy",
    "EarningsStraddleStrategy",
]
