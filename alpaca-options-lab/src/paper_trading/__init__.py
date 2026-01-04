"""
Alpaca Options Lab - Paper Trading Module

Complete paper trading orchestration system:
- PaperTradingEngine: Main orchestrator
- SimulatedPortfolio: Position and P&L tracking
- OrderSimulator: Realistic order fills
- MarketDataFeed: Price simulation
"""

from src.paper_trading.engine import (
    PaperTradingEngine,
    TradingMode,
    EngineState,
    EngineConfig,
)
from src.paper_trading.portfolio import (
    SimulatedPortfolio,
    SimulatedPosition,
    SimulatedOrder,
    OrderStatus,
    OrderType,
    OrderSide,
)
from src.paper_trading.market_data import (
    MarketDataFeed,
    Quote,
    Trade,
    Bar,
    MarketDataSource,
)
from src.paper_trading.simulator import (
    OrderSimulator,
    FillSimulation,
    SlippageModel,
)

__all__ = [
    # Engine
    "PaperTradingEngine",
    "TradingMode",
    "EngineState",
    "EngineConfig",
    # Portfolio
    "SimulatedPortfolio",
    "SimulatedPosition",
    "SimulatedOrder",
    "OrderStatus",
    "OrderType",
    "OrderSide",
    # Market Data
    "MarketDataFeed",
    "Quote",
    "Trade",
    "Bar",
    "MarketDataSource",
    # Simulator
    "OrderSimulator",
    "FillSimulation",
    "SlippageModel",
]
