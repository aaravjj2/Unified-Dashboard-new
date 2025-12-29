"""
Bot Engine Package
==================

AlphaVantage + Alpaca integration for automated trading bots.

Components:
- alpha_vantage.py: Rate-limited AV client for RSI, MACD
- broker.py: Alpaca execution bridge
- strategy_bot.py: RSI-based trading bot logic
"""

from .alpha_vantage import AlphaVantageClient, RateLimiter
from .broker import AlpacaBroker
from .strategy_bot import StrategyBot, BotStatus, TradeLog

__all__ = [
    'AlphaVantageClient',
    'RateLimiter',
    'AlpacaBroker',
    'StrategyBot',
    'BotStatus',
    'TradeLog',
]
