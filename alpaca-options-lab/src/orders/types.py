"""
Alpaca Options Lab - Order Types

Comprehensive order type definitions for options trading:
- Basic orders (market, limit, stop)
- Multi-leg orders (spreads, condors)
- Bracket orders (entry + exit automation)
- OCO (One-Cancels-Other)
- OTO (One-Triggers-Other)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"
    BUY_TO_OPEN = "buy_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_OPEN = "sell_to_open"
    SELL_TO_CLOSE = "sell_to_close"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class TimeInForce(Enum):
    """Time in force for orders."""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill
    OPG = "opg"  # At Open
    CLS = "cls"  # At Close


@dataclass
class OrderLeg:
    """Single leg of an order."""
    contract_id: int
    symbol: str
    side: OrderSide
    quantity: int
    price: Optional[float] = None  # None for market orders
    
    def __post_init__(self):
        if isinstance(self.side, str):
            self.side = OrderSide(self.side)
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")


@dataclass
class Order:
    """
    Single-leg order.
    
    Represents a simple order for one option contract.
    """
    contract_id: int
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.LIMIT
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    strategy: str = ""
    correlation_id: str = ""
    
    # Status fields
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.side, str):
            self.side = OrderSide(self.side)
        if isinstance(self.order_type, str):
            self.order_type = OrderType(self.order_type)
        if isinstance(self.time_in_force, str):
            self.time_in_force = TimeInForce(self.time_in_force)
        if not self.order_id:
            self.order_id = str(uuid.uuid4())[:12]
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())[:8]
    
    def validate(self) -> bool:
        """Validate order parameters."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Limit price required for limit orders")
        
        if self.order_type == OrderType.STOP and self.stop_price is None:
            raise ValueError("Stop price required for stop orders")
        
        if self.order_type == OrderType.STOP_LIMIT:
            if self.stop_price is None or self.limit_price is None:
                raise ValueError("Both stop and limit prices required for stop-limit orders")
        
        return True
    
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_terminal(self) -> bool:
        """Check if order is in terminal state."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.FAILED,
        )
    
    @property
    def remaining_quantity(self) -> int:
        """Get remaining unfilled quantity."""
        return self.quantity - self.filled_quantity


@dataclass
class MultiLegOrder:
    """
    Multi-leg order for spreads, condors, butterflies.
    
    Critical: All legs must fill or none fill (atomicity).
    """
    legs: List[OrderLeg]
    net_price: float  # Net credit (positive) or debit (negative)
    order_type: OrderType = OrderType.LIMIT
    time_in_force: TimeInForce = TimeInForce.DAY
    strategy: str = ""
    correlation_id: str = ""
    
    # Status
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    leg_order_ids: Dict[int, str] = field(default_factory=dict)  # leg_idx -> order_id
    leg_statuses: Dict[int, OrderStatus] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = str(uuid.uuid4())[:12]
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())[:8]
    
    def validate(self) -> bool:
        """Validate multi-leg order."""
        if len(self.legs) < 2:
            raise ValueError("Multi-leg order must have at least 2 legs")
        
        # Validate each leg
        for leg in self.legs:
            if leg.quantity <= 0:
                raise ValueError(f"Invalid quantity for leg {leg.symbol}")
        
        return True
    
    @property
    def is_credit(self) -> bool:
        """Check if this is a net credit trade."""
        return self.net_price > 0
    
    @property
    def is_debit(self) -> bool:
        """Check if this is a net debit trade."""
        return self.net_price < 0
    
    @property
    def num_legs(self) -> int:
        """Number of legs."""
        return len(self.legs)
    
    @property
    def all_legs_filled(self) -> bool:
        """Check if all legs are filled."""
        if not self.leg_statuses:
            return False
        return all(
            s == OrderStatus.FILLED 
            for s in self.leg_statuses.values()
        )


@dataclass
class BracketOrder:
    """
    Bracket order: entry + profit target + stop loss.
    
    Automatically places profit target and stop loss orders
    when the entry order fills.
    """
    entry_order: Order
    profit_target: Order  # Placed when entry fills
    stop_loss: Order       # Placed when entry fills (OCO with profit)
    correlation_id: str = ""
    
    # Status
    bracket_id: str = ""
    status: str = "pending"  # pending, entry_filled, closed
    active_order: Optional[str] = None  # Which exit order is active
    
    def __post_init__(self):
        if not self.bracket_id:
            self.bracket_id = str(uuid.uuid4())[:12]
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())[:8]
    
    def validate(self) -> bool:
        """Validate bracket order."""
        self.entry_order.validate()
        self.profit_target.validate()
        self.stop_loss.validate()
        
        # Profit target and stop loss should be opposite side of entry
        if self.entry_order.side == OrderSide.BUY:
            if self.profit_target.side not in (OrderSide.SELL, OrderSide.SELL_TO_CLOSE):
                raise ValueError("Profit target must be sell for buy entry")
            if self.stop_loss.side not in (OrderSide.SELL, OrderSide.SELL_TO_CLOSE):
                raise ValueError("Stop loss must be sell for buy entry")
        
        return True


@dataclass
class OCOOrder:
    """
    One-Cancels-Other order.
    
    When one order fills or is cancelled, the other is automatically cancelled.
    """
    order_a: Order
    order_b: Order
    correlation_id: str = ""
    
    oco_id: str = ""
    status: str = "pending"
    triggered_order: Optional[str] = None
    
    def __post_init__(self):
        if not self.oco_id:
            self.oco_id = str(uuid.uuid4())[:12]
    
    def validate(self) -> bool:
        """Validate OCO order."""
        self.order_a.validate()
        self.order_b.validate()
        
        # Should be same contract
        if self.order_a.symbol != self.order_b.symbol:
            raise ValueError("OCO orders must be for same symbol")
        
        return True


@dataclass
class OTOOrder:
    """
    One-Triggers-Other order.
    
    When the primary order fills, the secondary order is submitted.
    """
    primary: Order
    secondary: Order  # Submitted when primary fills
    correlation_id: str = ""
    
    oto_id: str = ""
    status: str = "pending"
    
    def __post_init__(self):
        if not self.oto_id:
            self.oto_id = str(uuid.uuid4())[:12]
    
    def validate(self) -> bool:
        """Validate OTO order."""
        self.primary.validate()
        self.secondary.validate()
        return True


@dataclass
class ExecutionResult:
    """Result of order execution."""
    success: bool
    order_id: str = ""
    fill_price: Optional[float] = None
    filled_quantity: int = 0
    commission: float = 0.0
    message: str = ""
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Detailed results for multi-leg
    leg_results: Dict[int, Dict[str, Any]] = field(default_factory=dict)
