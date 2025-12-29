"""
Bot Engine Package
==================

AlphaVantage + Alpaca integration for automated trading bots.

Components:
- alpha_vantage.py: Rate-limited AV client for RSI, MACD
- broker.py: Alpaca execution bridge
- strategy_bot.py: RSI-based trading bot logic
"""

from .alpha_vantage import (
    AlphaVantageClient,
    RateLimiter,
    get_av_client
)
from .broker import (
    AlpacaBroker,
    get_broker,
    Side,
    OrderType,
    OrderResult,
    Position
)
from .strategy_bot import (
    StrategyBot,
    BotStatus,
    SignalType,
    TradeLog,
    BotConfig,
    BotManager,
    get_bot_manager
)

__all__ = [
    # AlphaVantage
    'AlphaVantageClient',
    'RateLimiter',
    'get_av_client',
    # Broker
    'AlpacaBroker',
    'get_broker',
    'Side',
    'OrderType',
    'OrderResult',
    'Position',
    # Strategy Bot
    'StrategyBot',
    'BotStatus',
    'SignalType',
    'TradeLog',
    'BotConfig',
    'BotManager',
    'get_bot_manager'
]
