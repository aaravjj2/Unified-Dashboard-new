"""
Alpaca Options Lab - Advanced Order Router (Phase 2 Module 8)

Smart order routing with:
- Multi-leg order atomicity
- Contingent orders (if-then logic)
- Bracket orders (entry + profit + stop)
- Retry logic with exponential backoff
- Order modification and cancellation
- Partial fill handling and rollback
"""

from src.orders.router import (
    SmartOrderRouter,
    RoutingStrategy,
    RoutingConfig,
    ExecutionMetrics,
)
from src.orders.types import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    TimeInForce,
    OrderLeg,
    MultiLegOrder,
    BracketOrder,
    OCOOrder,
    OTOOrder,
    ExecutionResult,
)
from src.orders.execution import (
    ExecutionSimulator,
    SimulatorConfig,
    FillMode,
    SimulatedQuote,
    SimulatedBrokerAPI,
)

__all__ = [
    # Router
    "SmartOrderRouter",
    "RoutingStrategy",
    "RoutingConfig",
    "ExecutionMetrics",
    # Order Types
    "Order",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "TimeInForce",
    "OrderLeg",
    "MultiLegOrder",
    "BracketOrder",
    "OCOOrder",
    "OTOOrder",
    "ExecutionResult",
    # Simulator
    "ExecutionSimulator",
    "SimulatorConfig",
    "FillMode",
    "SimulatedQuote",
    "SimulatedBrokerAPI",
]
