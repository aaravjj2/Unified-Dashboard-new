"""
External API Clients for Market Data and Brokerage Operations.

This package provides robust, rate-limited clients for interacting with
external services required for the options trading system.

Available Clients:
    - FinnhubClient: Real-time quotes and historical market data
    - AlpacaTrader: Portfolio management and order execution

Example:
    >>> from financial_dashboard.utils.external_clients import FinnhubClient, AlpacaTrader
    >>> 
    >>> # Market data client
    >>> with FinnhubClient() as finnhub:
    ...     quote = finnhub.get_quote("AAPL")
    ...     print(f"Current price: ${quote['c']}")
    >>> 
    >>> # Trading client (paper mode)
    >>> with AlpacaTrader(paper_mode=True) as trader:
    ...     positions = trader.get_positions()
    ...     print(f"Portfolio has {len(positions)} positions")
"""

from .finnhub_client import FinnhubClient
from .alpaca_trader import AlpacaTrader

__all__ = [
    "FinnhubClient",
    "AlpacaTrader",
]

__version__ = "1.0.0"
