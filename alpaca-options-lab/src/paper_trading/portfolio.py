"""
Alpaca Options Lab - Simulated Portfolio

Position and P&L tracking for paper trading:
- Position management
- Order tracking
- P&L calculation
- Buying power management
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class SimulatedOrder:
    """Simulated order."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    
    # Prices
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Fill info
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: str = "day"
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Fees
    commission: float = 0.0
    
    # Options specific
    is_option: bool = False
    option_symbol: Optional[str] = None
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = str(uuid.uuid4())[:12]
    
    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
    
    @property
    def is_pending(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED)
    
    @property
    def fill_pct(self) -> float:
        if self.quantity == 0:
            return 0.0
        return self.filled_quantity / self.quantity * 100
    
    @property
    def total_cost(self) -> float:
        """Total cost including commission."""
        if self.side == OrderSide.BUY:
            return self.filled_quantity * self.filled_price + self.commission
        else:
            return -(self.filled_quantity * self.filled_price - self.commission)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "commission": self.commission,
        }


@dataclass
class SimulatedPosition:
    """Simulated position."""
    symbol: str
    quantity: float
    avg_entry_price: float
    
    # Current
    current_price: float = 0.0
    
    # P&L
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Cost basis
    cost_basis: float = 0.0
    
    # Options specific
    is_option: bool = False
    option_symbol: Optional[str] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    option_type: Optional[str] = None  # "call" or "put"
    multiplier: int = 100  # Contract multiplier
    
    # Timestamps
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def market_value(self) -> float:
        """Current market value."""
        if self.is_option:
            return self.quantity * self.current_price * self.multiplier
        return self.quantity * self.current_price
    
    @property
    def pnl_pct(self) -> float:
        """P&L percentage."""
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / abs(self.cost_basis) * 100
    
    @property
    def is_long(self) -> bool:
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        return self.quantity < 0
    
    def update_pnl(self) -> None:
        """Update unrealized P&L."""
        self.unrealized_pnl = self.market_value - self.cost_basis
        self.last_update = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_entry_price": self.avg_entry_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "pnl_pct": self.pnl_pct,
            "is_option": self.is_option,
            "opened_at": self.opened_at.isoformat(),
        }


class SimulatedPortfolio:
    """
    Simulated portfolio for paper trading.
    
    Tracks:
    - Cash balance
    - Positions
    - Orders
    - P&L
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        # Capital
        self._initial_capital = initial_capital
        self._cash = initial_capital
        
        # Positions and orders
        self._positions: Dict[str, SimulatedPosition] = {}
        self._orders: Dict[str, SimulatedOrder] = {}
        
        # P&L
        self._realized_pnl = 0.0
        self._daily_pnl_start = initial_capital
        
        # Transaction history
        self._transactions: List[Dict[str, Any]] = []
        
        logger.info(f"SimulatedPortfolio initialized with ${initial_capital:,.2f}")
    
    # -------------------- Properties --------------------
    
    @property
    def cash(self) -> float:
        """Available cash."""
        return self._cash
    
    @property
    def buying_power(self) -> float:
        """Available buying power."""
        # For now, same as cash (no margin)
        return max(0, self._cash)
    
    @property
    def total_value(self) -> float:
        """Total portfolio value."""
        positions_value = sum(p.market_value for p in self._positions.values())
        return self._cash + positions_value
    
    @property
    def unrealized_pnl(self) -> float:
        """Total unrealized P&L."""
        return sum(p.unrealized_pnl for p in self._positions.values())
    
    @property
    def realized_pnl(self) -> float:
        """Total realized P&L."""
        return self._realized_pnl
    
    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def daily_pnl(self) -> float:
        """P&L since start of day."""
        return self.total_value - self._daily_pnl_start
    
    @property
    def return_pct(self) -> float:
        """Total return percentage."""
        return (self.total_value - self._initial_capital) / self._initial_capital * 100
    
    # -------------------- Position Management --------------------
    
    def get_position(self, symbol: str) -> Optional[SimulatedPosition]:
        """Get position by symbol."""
        return self._positions.get(symbol)
    
    def get_positions(self) -> List[SimulatedPosition]:
        """Get all positions."""
        return list(self._positions.values())
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists."""
        return symbol in self._positions
    
    def _open_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
        is_option: bool = False,
        **kwargs,
    ) -> SimulatedPosition:
        """Open a new position."""
        multiplier = 100 if is_option else 1
        cost_basis = quantity * price * multiplier
        
        position = SimulatedPosition(
            symbol=symbol,
            quantity=quantity,
            avg_entry_price=price,
            current_price=price,
            cost_basis=cost_basis,
            is_option=is_option,
            **kwargs,
        )
        
        self._positions[symbol] = position
        self._cash -= cost_basis
        
        self._transactions.append({
            "type": "open",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.info(f"Position opened: {quantity} {symbol} @ ${price:.2f}")
        return position
    
    def _adjust_position(
        self,
        position: SimulatedPosition,
        quantity_delta: float,
        price: float,
    ) -> None:
        """Adjust existing position."""
        multiplier = position.multiplier if position.is_option else 1
        trade_value = quantity_delta * price * multiplier
        
        if quantity_delta > 0:
            # Adding to position
            total_cost = position.cost_basis + trade_value
            total_qty = position.quantity + quantity_delta
            position.avg_entry_price = total_cost / (total_qty * multiplier)
            position.quantity = total_qty
            position.cost_basis = total_cost
            self._cash -= trade_value
            
        else:
            # Reducing position
            realized = abs(quantity_delta) * (price - position.avg_entry_price) * multiplier
            self._realized_pnl += realized
            
            position.quantity += quantity_delta
            position.cost_basis = position.quantity * position.avg_entry_price * multiplier
            position.realized_pnl += realized
            self._cash += abs(trade_value)
        
        # Remove if closed
        if position.quantity == 0:
            del self._positions[position.symbol]
            logger.info(f"Position closed: {position.symbol}")
        
        self._transactions.append({
            "type": "adjust",
            "symbol": position.symbol,
            "quantity_delta": quantity_delta,
            "price": price,
            "realized_pnl": realized if quantity_delta < 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    def close_position(
        self,
        symbol: str,
        price: Optional[float] = None,
    ) -> Optional[float]:
        """Close entire position."""
        position = self._positions.get(symbol)
        if not position:
            return None
        
        close_price = price or position.current_price
        
        # Calculate P&L
        multiplier = position.multiplier if position.is_option else 1
        proceeds = position.quantity * close_price * multiplier
        realized = proceeds - position.cost_basis
        
        self._realized_pnl += realized
        self._cash += proceeds
        
        del self._positions[symbol]
        
        self._transactions.append({
            "type": "close",
            "symbol": symbol,
            "quantity": position.quantity,
            "price": close_price,
            "realized_pnl": realized,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.info(f"Position closed: {symbol} P&L: ${realized:.2f}")
        return realized
    
    # -------------------- Order Management --------------------
    
    def add_order(self, order: SimulatedOrder) -> None:
        """Add order to tracking."""
        self._orders[order.order_id] = order
    
    def get_order(self, order_id: str) -> Optional[SimulatedOrder]:
        """Get order by ID."""
        return self._orders.get(order_id)
    
    def get_pending_orders(self) -> List[SimulatedOrder]:
        """Get all pending orders."""
        return [o for o in self._orders.values() if o.is_pending]
    
    def get_all_orders(self) -> List[SimulatedOrder]:
        """Get all orders."""
        return list(self._orders.values())
    
    def process_fill(self, order: SimulatedOrder) -> None:
        """Process an order fill."""
        if order.side == OrderSide.BUY:
            self._process_buy_fill(order)
        else:
            self._process_sell_fill(order)
    
    def _process_buy_fill(self, order: SimulatedOrder) -> None:
        """Process buy order fill."""
        position = self._positions.get(order.symbol)
        
        if position:
            # Add to existing position
            self._adjust_position(
                position,
                order.filled_quantity,
                order.filled_price,
            )
        else:
            # Open new position
            self._open_position(
                symbol=order.symbol,
                quantity=order.filled_quantity,
                price=order.filled_price,
                is_option=order.is_option,
            )
    
    def _process_sell_fill(self, order: SimulatedOrder) -> None:
        """Process sell order fill."""
        position = self._positions.get(order.symbol)
        
        if position:
            # Reduce or close position
            self._adjust_position(
                position,
                -order.filled_quantity,
                order.filled_price,
            )
        else:
            # Short sale (open short position)
            self._open_position(
                symbol=order.symbol,
                quantity=-order.filled_quantity,
                price=order.filled_price,
                is_option=order.is_option,
            )
    
    # -------------------- Utilities --------------------
    
    def reset_daily_pnl(self) -> None:
        """Reset daily P&L tracking."""
        self._daily_pnl_start = self.total_value
    
    def get_summary(self) -> Dict[str, Any]:
        """Get portfolio summary."""
        return {
            "cash": self._cash,
            "buying_power": self.buying_power,
            "total_value": self.total_value,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "return_pct": self.return_pct,
            "position_count": len(self._positions),
            "pending_orders": len(self.get_pending_orders()),
            "total_orders": len(self._orders),
            "positions": [p.to_dict() for p in self._positions.values()],
        }
    
    def get_transaction_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction history."""
        return self._transactions[-limit:]
