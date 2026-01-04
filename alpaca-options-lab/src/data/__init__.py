"""
Alpaca Options Lab - Data Module

Production-grade data layer providing:
- TimescaleDB integration with connection pooling
- Symbol management with OSI parser
- Real-time market data feed handling

Components:
- DatabaseManager: Connection pooling and query execution
- SymbolMapper: OSI symbol parsing and management
- FeedHandler: WebSocket market data streaming
"""
from src.data.database import DatabaseManager, get_db
from src.data.symbology import SymbolMapper, OptionSymbol, parse_osi_symbol
from src.data.feed_handler import FeedHandler, MarketDataEvent

__all__ = [
    "DatabaseManager",
    "get_db",
    "SymbolMapper",
    "OptionSymbol",
    "parse_osi_symbol",
    "FeedHandler",
    "MarketDataEvent",
]
