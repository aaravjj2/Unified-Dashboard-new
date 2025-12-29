"""
Broker Interface - Paper & Live Trading Execution
=================================================

Provides abstract broker interface and implementations for paper/live trading.
The PaperBroker tracks fake trades and P&L for strategy testing.

Architecture:
------------
BrokerInterface (Abstract)
├── PaperBroker - Simulated trading with virtual capital
└── LiveBroker - Connects to real brokers (Alpaca, Tradier, etc.)

Position Lifecycle:
-----------------
1. PENDING: Order submitted, awaiting fill
2. OPEN: Position is active
3. PARTIALLY_CLOSED: Some contracts closed
4. CLOSED: Position fully exited
5. EXPIRED: Options expired worthless/ITM

Frontend Integration:
-------------------
```javascript
// React position display
const [positions, setPositions] = useState([]);

useEffect(() => {
    fetch('/api/positions')
        .then(r => r.json())
        .then(setPositions);
}, []);

// Position table with real-time P&L updates
<PositionTable 
    positions={positions}
    onClose={(id) => closePosition(id)}
/>
```
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class OrderSide(str, Enum):
    """Order direction."""
    BUY = "buy"
    SELL = "sell"
    BUY_TO_OPEN = "buy_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_OPEN = "sell_to_open"
    SELL_TO_CLOSE = "sell_to_close"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionStatus(str, Enum):
    """Position status."""
    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"
    EXPIRED = "expired"


class AssetType(str, Enum):
    """Asset type."""
    EQUITY = "equity"
    OPTION = "option"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class OptionLegOrder:
    """Single leg of a multi-leg options order."""
    option_type: str  # "call" or "put"
    side: OrderSide
    strike: float
    expiration: str
    quantity: int
    symbol: Optional[str] = None  # Full option symbol (auto-generated)
    
    def generate_symbol(self, underlying: str) -> str:
        """Generate OCC option symbol."""
        # Format: AAPL230120C00150000 (AAPL Jan 20 2023 $150 Call)
        exp_date = datetime.strptime(self.expiration, "%Y-%m-%d")
        opt_type = "C" if self.option_type.lower() == "call" else "P"
        strike_str = f"{int(self.strike * 1000):08d}"
        self.symbol = f"{underlying}{exp_date.strftime('%y%m%d')}{opt_type}{strike_str}"
        return self.symbol


@dataclass
class Order:
    """
    Order representation.
    
    Can be a simple equity order or multi-leg options order.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    bot_id: Optional[str] = None
    recipe_id: Optional[str] = None
    
    # Order details
    symbol: str = ""
    asset_type: AssetType = AssetType.EQUITY
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 1
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Options legs (for multi-leg orders)
    legs: List[OptionLegOrder] = field(default_factory=list)
    strategy: Optional[str] = None  # e.g., "short_put_spread"
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    commission: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Metadata
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "recipe_id": self.recipe_id,
            "symbol": self.symbol,
            "asset_type": self.asset_type.value,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "limit_price": self.limit_price,
            "legs": [
                {
                    "symbol": leg.symbol,
                    "option_type": leg.option_type,
                    "side": leg.side.value,
                    "strike": leg.strike,
                    "expiration": leg.expiration,
                    "quantity": leg.quantity,
                }
                for leg in self.legs
            ],
            "strategy": self.strategy,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "commission": self.commission,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
        }


@dataclass
class PositionLeg:
    """Single leg of an options position."""
    symbol: str  # Full option symbol
    option_type: str
    side: str  # "long" or "short"
    strike: float
    expiration: str
    quantity: int
    entry_price: float
    current_price: float = 0.0
    
    @property
    def pnl(self) -> float:
        """Calculate P&L for this leg."""
        multiplier = 100  # Options multiplier
        if self.side == "long":
            return (self.current_price - self.entry_price) * self.quantity * multiplier
        else:
            return (self.entry_price - self.current_price) * self.quantity * multiplier


@dataclass
class Position:
    """
    Open or closed position.
    
    Tracks all legs, entry/exit prices, and P&L.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    bot_id: Optional[str] = None
    recipe_id: Optional[str] = None
    order_id: Optional[str] = None
    
    # Position details
    symbol: str = ""  # Underlying symbol
    asset_type: AssetType = AssetType.OPTION
    strategy: Optional[str] = None
    quantity: int = 1
    
    # For equity positions
    side: str = "long"  # "long" or "short"
    entry_price: float = 0.0
    current_price: float = 0.0
    
    # For options positions
    legs: List[PositionLeg] = field(default_factory=list)
    
    # Financial metrics
    entry_value: float = 0.0  # Total cost/credit at entry
    current_value: float = 0.0  # Current market value
    max_profit: Optional[float] = None  # For credit spreads
    max_loss: Optional[float] = None  # For defined risk
    
    # Status
    status: PositionStatus = PositionStatus.OPEN
    
    # Timestamps
    opened_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    expiration: Optional[str] = None
    
    # Exit details
    exit_price: Optional[float] = None
    exit_value: Optional[float] = None
    realized_pnl: float = 0.0
    
    # Metadata
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L."""
        if self.asset_type == AssetType.EQUITY:
            if self.side == "long":
                return (self.current_price - self.entry_price) * self.quantity
            else:
                return (self.entry_price - self.current_price) * self.quantity
        else:
            # Options: sum of all legs
            return sum(leg.pnl for leg in self.legs)
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Calculate unrealized P&L as percentage."""
        if abs(self.entry_value) < 0.01:
            return 0.0
        return (self.unrealized_pnl / abs(self.entry_value)) * 100
    
    @property
    def days_held(self) -> int:
        """Days since position opened."""
        end = self.closed_at or datetime.now()
        return (end - self.opened_at).days
    
    @property
    def dte(self) -> Optional[int]:
        """Days to expiration (for options)."""
        if not self.expiration:
            return None
        exp_date = datetime.strptime(self.expiration, "%Y-%m-%d")
        return max(0, (exp_date - datetime.now()).days)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "recipe_id": self.recipe_id,
            "symbol": self.symbol,
            "asset_type": self.asset_type.value,
            "strategy": self.strategy,
            "quantity": self.quantity,
            "side": self.side,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "legs": [
                {
                    "symbol": leg.symbol,
                    "option_type": leg.option_type,
                    "side": leg.side,
                    "strike": leg.strike,
                    "expiration": leg.expiration,
                    "quantity": leg.quantity,
                    "entry_price": leg.entry_price,
                    "current_price": leg.current_price,
                    "pnl": leg.pnl,
                }
                for leg in self.legs
            ],
            "entry_value": self.entry_value,
            "current_value": self.current_value,
            "max_profit": self.max_profit,
            "max_loss": self.max_loss,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "realized_pnl": self.realized_pnl,
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "expiration": self.expiration,
            "dte": self.dte,
            "days_held": self.days_held,
        }


# =============================================================================
# ABSTRACT BROKER INTERFACE
# =============================================================================

class BrokerInterface(ABC):
    """
    Abstract broker interface.
    
    All broker implementations must implement these methods.
    This allows swapping between paper and live trading seamlessly.
    """
    
    @abstractmethod
    def submit_order(self, order: Order) -> Order:
        """Submit an order for execution."""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        pass
    
    @abstractmethod
    def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        bot_id: Optional[str] = None
    ) -> List[Order]:
        """Get all orders, optionally filtered."""
        pass
    
    @abstractmethod
    def get_position(self, position_id: str) -> Optional[Position]:
        """Get position by ID."""
        pass
    
    @abstractmethod
    def get_positions(
        self,
        status: Optional[PositionStatus] = None,
        bot_id: Optional[str] = None
    ) -> List[Position]:
        """Get all positions, optionally filtered."""
        pass
    
    @abstractmethod
    def close_position(
        self,
        position_id: str,
        percent: float = 100.0,
        order_type: OrderType = OrderType.MARKET
    ) -> Order:
        """Close a position (fully or partially)."""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account balance and buying power."""
        pass
    
    @abstractmethod
    def update_positions(self, data_handler: Any) -> None:
        """Update position prices from market data."""
        pass


# =============================================================================
# PAPER BROKER IMPLEMENTATION
# =============================================================================

class PaperBroker(BrokerInterface):
    """
    Paper trading broker for strategy testing.
    
    Features:
    - Virtual capital management
    - Realistic fill simulation
    - P&L tracking
    - Position management
    - Commission simulation
    
    Usage:
        broker = PaperBroker(initial_capital=100000)
        order = Order(symbol="SPY", side=OrderSide.BUY, quantity=100)
        broker.submit_order(order)
        positions = broker.get_positions(status=PositionStatus.OPEN)
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_per_contract: float = 0.65,
        commission_per_share: float = 0.0,
        slippage_pct: float = 0.001,  # 0.1% slippage
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_per_contract = commission_per_contract
        self.commission_per_share = commission_per_share
        self.slippage_pct = slippage_pct
        
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0.0
        self.total_realized_pnl = 0.0
        
        logger.info(f"PaperBroker initialized with ${initial_capital:,.2f}")
    
    def submit_order(self, order: Order) -> Order:
        """
        Submit and immediately fill a paper order.
        
        For paper trading, we simulate immediate fills with slippage.
        """
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.now()
        
        # Calculate fill price with slippage
        if order.limit_price:
            fill_price = order.limit_price
        else:
            # Simulate slippage for market orders
            base_price = order.limit_price or 100.0  # Will be set by caller
            slippage = base_price * self.slippage_pct
            if order.side in [OrderSide.BUY, OrderSide.BUY_TO_OPEN]:
                fill_price = base_price + slippage
            else:
                fill_price = base_price - slippage
        
        # Calculate commission
        if order.asset_type == AssetType.OPTION:
            total_contracts = sum(leg.quantity for leg in order.legs) if order.legs else order.quantity
            commission = total_contracts * self.commission_per_contract
        else:
            commission = order.quantity * self.commission_per_share
        
        # Update order
        order.filled_price = round(fill_price, 2)
        order.filled_quantity = order.quantity
        order.commission = commission
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        
        # Store order
        self._orders[order.id] = order
        
        # Update cash
        self.cash -= commission
        self.total_commission += commission
        
        # Create position if opening trade
        if order.side in [OrderSide.BUY, OrderSide.BUY_TO_OPEN, OrderSide.SELL_TO_OPEN]:
            self._create_position_from_order(order)
        
        self.total_trades += 1
        logger.info(f"Order {order.id} filled: {order.symbol} {order.side.value} @ ${order.filled_price:.2f}")
        
        return order
    
    def _create_position_from_order(self, order: Order) -> Position:
        """Create a position from a filled order."""
        position = Position(
            bot_id=order.bot_id,
            recipe_id=order.recipe_id,
            order_id=order.id,
            symbol=order.symbol,
            asset_type=order.asset_type,
            strategy=order.strategy,
            quantity=order.quantity,
            opened_at=datetime.now(),
        )
        
        if order.asset_type == AssetType.EQUITY:
            position.side = "long" if order.side == OrderSide.BUY else "short"
            position.entry_price = order.filled_price
            position.current_price = order.filled_price
            position.entry_value = order.filled_price * order.quantity
            position.current_value = position.entry_value
            
            # Deduct from cash
            if position.side == "long":
                self.cash -= position.entry_value
            else:
                self.cash += position.entry_value  # Short sale proceeds
        
        else:
            # Options position
            entry_value = 0.0
            max_profit = 0.0
            max_loss = 0.0
            
            for leg_order in order.legs:
                leg = PositionLeg(
                    symbol=leg_order.symbol or leg_order.generate_symbol(order.symbol),
                    option_type=leg_order.option_type,
                    side="long" if leg_order.side in [OrderSide.BUY, OrderSide.BUY_TO_OPEN] else "short",
                    strike=leg_order.strike,
                    expiration=leg_order.expiration,
                    quantity=leg_order.quantity,
                    entry_price=order.filled_price / len(order.legs),  # Simplified
                    current_price=order.filled_price / len(order.legs),
                )
                position.legs.append(leg)
                
                # Calculate entry value
                multiplier = 100
                if leg.side == "long":
                    entry_value -= leg.entry_price * leg.quantity * multiplier
                else:
                    entry_value += leg.entry_price * leg.quantity * multiplier
            
            position.entry_value = entry_value
            position.current_value = entry_value
            position.expiration = order.legs[0].expiration if order.legs else None
            
            # For credit spreads: max profit = credit received, max loss = width - credit
            if "spread" in (order.strategy or "").lower():
                if entry_value > 0:  # Credit spread
                    position.max_profit = entry_value
                    # Calculate width (difference between strikes)
                    strikes = sorted(set(leg.strike for leg in position.legs))
                    if len(strikes) >= 2:
                        width = (strikes[-1] - strikes[0]) * 100 * position.quantity
                        position.max_loss = width - entry_value
                else:  # Debit spread
                    position.max_loss = abs(entry_value)
            
            # Deduct/add to cash
            self.cash += entry_value  # Positive for credits, negative for debits
        
        self._positions[position.id] = position
        logger.info(f"Position {position.id} opened: {position.symbol} {position.strategy or position.side}")
        
        return position
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            order.status = OrderStatus.CANCELLED
            return True
        return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self._orders.get(order_id)
    
    def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        bot_id: Optional[str] = None
    ) -> List[Order]:
        """Get all orders, optionally filtered."""
        orders = list(self._orders.values())
        
        if status:
            orders = [o for o in orders if o.status == status]
        if bot_id:
            orders = [o for o in orders if o.bot_id == bot_id]
        
        return sorted(orders, key=lambda o: o.created_at, reverse=True)
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """Get position by ID."""
        return self._positions.get(position_id)
    
    def get_positions(
        self,
        status: Optional[PositionStatus] = None,
        bot_id: Optional[str] = None
    ) -> List[Position]:
        """Get all positions, optionally filtered."""
        positions = list(self._positions.values())
        
        if status:
            positions = [p for p in positions if p.status == status]
        if bot_id:
            positions = [p for p in positions if p.bot_id == bot_id]
        
        return sorted(positions, key=lambda p: p.opened_at, reverse=True)
    
    def close_position(
        self,
        position_id: str,
        percent: float = 100.0,
        order_type: OrderType = OrderType.MARKET,
        exit_price: Optional[float] = None
    ) -> Order:
        """Close a position."""
        position = self._positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if position.status == PositionStatus.CLOSED:
            raise ValueError(f"Position {position_id} already closed")
        
        # Calculate exit value
        if exit_price:
            position.exit_price = exit_price
        else:
            position.exit_price = position.current_price
        
        # Calculate P&L
        if position.asset_type == AssetType.EQUITY:
            if position.side == "long":
                pnl = (position.exit_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - position.exit_price) * position.quantity
            position.exit_value = position.exit_price * position.quantity
        else:
            # Options: use unrealized P&L
            pnl = position.unrealized_pnl
            position.exit_value = position.current_value
        
        position.realized_pnl = pnl
        position.status = PositionStatus.CLOSED
        position.closed_at = datetime.now()
        
        # Update cash
        self.cash += position.exit_value
        self.total_realized_pnl += pnl
        
        # Track win/loss
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1
        
        logger.info(f"Position {position_id} closed: P&L ${pnl:,.2f}")
        
        # Create close order for record
        close_order = Order(
            bot_id=position.bot_id,
            recipe_id=position.recipe_id,
            symbol=position.symbol,
            asset_type=position.asset_type,
            side=OrderSide.SELL_TO_CLOSE if position.side == "long" else OrderSide.BUY_TO_CLOSE,
            order_type=order_type,
            quantity=position.quantity,
            status=OrderStatus.FILLED,
            filled_price=position.exit_price,
            filled_quantity=position.quantity,
            filled_at=datetime.now(),
        )
        self._orders[close_order.id] = close_order
        
        return close_order
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account balance and performance metrics."""
        open_positions = self.get_positions(status=PositionStatus.OPEN)
        
        # Calculate portfolio value
        positions_value = sum(p.current_value for p in open_positions)
        total_equity = self.cash + positions_value
        
        # Calculate unrealized P&L
        unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)
        
        # Win rate
        total_closed = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_closed * 100) if total_closed > 0 else 0.0
        
        return {
            "cash": self.cash,
            "positions_value": positions_value,
            "total_equity": total_equity,
            "initial_capital": self.initial_capital,
            "total_return": (total_equity - self.initial_capital) / self.initial_capital * 100,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": self.total_realized_pnl,
            "total_pnl": unrealized_pnl + self.total_realized_pnl,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "total_commission": self.total_commission,
            "open_positions_count": len(open_positions),
        }
    
    def update_positions(self, data_handler: Any) -> None:
        """Update all open position prices from market data."""
        for position in self.get_positions(status=PositionStatus.OPEN):
            try:
                if position.asset_type == AssetType.EQUITY:
                    quote = data_handler.get_quote(position.symbol)
                    position.current_price = quote.price
                    position.current_value = quote.price * position.quantity
                else:
                    # Options: update each leg
                    chain = data_handler.get_option_chain(
                        position.symbol,
                        position.expiration
                    )
                    
                    for leg in position.legs:
                        # Find matching contract in chain
                        contracts = chain.calls if leg.option_type == "call" else chain.puts
                        for contract in contracts:
                            if contract.get("strike") == leg.strike:
                                leg.current_price = (contract.get("bid", 0) + contract.get("ask", 0)) / 2
                                break
                    
                    # Update position value
                    position.current_value = sum(
                        leg.current_price * leg.quantity * 100 * (1 if leg.side == "long" else -1)
                        for leg in position.legs
                    )
                    
            except Exception as e:
                logger.warning(f"Failed to update position {position.id}: {e}")
    
    def reset(self) -> None:
        """Reset broker to initial state."""
        self.cash = self.initial_capital
        self._orders.clear()
        self._positions.clear()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0.0
        self.total_realized_pnl = 0.0
        logger.info("PaperBroker reset to initial state")
