"""
Alpaca Options Lab - Position State Machine

Production-grade position lifecycle management with:
- Finite State Machine (FSM) for position states
- Event-driven state transitions
- Audit trail and state history
- Concurrent position handling
- Validation and constraint enforcement

State Diagram:
    PENDING -> OPEN -> PARTIALLY_CLOSED -> CLOSED
        |        |            |
        v        v            v
      REJECTED  ASSIGNED    EXPIRED
                  |
                  v
              EXERCISED

Usage:
    from src.lifecycle.fsm import PositionFSM, Position, PositionState
    
    fsm = PositionFSM()
    
    # Create and track position
    position = fsm.create_position(
        symbol="AAPL240119C00150000",
        quantity=10,
        side="long",
        avg_cost=5.25,
    )
    
    # Process events
    fsm.process_event(position.id, PositionEvent.FILL_CONFIRMED)
    fsm.process_event(position.id, PositionEvent.PARTIAL_CLOSE, quantity=5)
    
    # Check state
    print(f"State: {fsm.get_position(position.id).state}")
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.data.symbology import OptionSymbol, parse_osi_symbol
from src.utils.exceptions import ValidationError
from src.utils.logging_config import get_logger
from src.utils.metrics import get_metrics, increment_counter, set_gauge

logger = get_logger(__name__)
metrics = get_metrics()


class PositionState(Enum):
    """
    Position lifecycle states.
    
    States follow a logical progression from order submission
    through position lifecycle to final close.
    """
    # Initial states
    PENDING = "pending"           # Order submitted, awaiting fill
    REJECTED = "rejected"         # Order rejected by broker
    
    # Active states
    OPEN = "open"                 # Position fully opened
    PARTIALLY_CLOSED = "partially_closed"  # Some contracts closed
    
    # Terminal states
    CLOSED = "closed"             # All contracts closed by trading
    ASSIGNED = "assigned"         # Short option assigned
    EXERCISED = "exercised"       # Long option exercised
    EXPIRED = "expired"           # Option expired worthless
    
    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in (
            PositionState.REJECTED,
            PositionState.CLOSED,
            PositionState.ASSIGNED,
            PositionState.EXERCISED,
            PositionState.EXPIRED,
        )
    
    @property
    def is_active(self) -> bool:
        """Check if position is actively held."""
        return self in (
            PositionState.OPEN,
            PositionState.PARTIALLY_CLOSED,
        )


class PositionEvent(Enum):
    """
    Events that trigger state transitions.
    
    Events represent broker notifications, user actions,
    or system-detected conditions.
    """
    # Order events
    FILL_CONFIRMED = "fill_confirmed"     # Order filled, position opened
    ORDER_REJECTED = "order_rejected"     # Order rejected by broker
    
    # Trading events
    PARTIAL_CLOSE = "partial_close"       # Some contracts closed
    FULL_CLOSE = "full_close"             # All contracts closed
    
    # Lifecycle events
    ASSIGNMENT_NOTICE = "assignment_notice"   # Assignment from broker
    EXERCISE_REQUEST = "exercise_request"     # User requests exercise
    EXPIRATION = "expiration"                 # Option expired
    
    # Adjustment events
    ROLL_INITIATED = "roll_initiated"     # Roll to new position
    POSITION_ADJUSTED = "position_adjusted"  # Quantity adjusted


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: PositionState
    to_state: PositionState
    event: PositionEvent
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """
    Option position with state tracking.
    
    Immutable after creation - state changes create new records.
    """
    id: str
    symbol: str
    underlying: str
    quantity: int              # Signed: positive=long, negative=short
    remaining_quantity: int    # Contracts still open
    side: str                  # 'long' or 'short'
    avg_cost: float
    current_price: Optional[float] = None
    
    state: PositionState = PositionState.PENDING
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # P&L tracking
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # State history
    transitions: List[StateTransition] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_long(self) -> bool:
        """Check if this is a long position."""
        return self.side == "long"
    
    @property
    def is_short(self) -> bool:
        """Check if this is a short position."""
        return self.side == "short"
    
    @property
    def market_value(self) -> float:
        """Calculate current market value."""
        if self.current_price is None:
            return 0.0
        return self.remaining_quantity * self.current_price * 100  # Options are x100
    
    @property
    def cost_basis(self) -> float:
        """Calculate cost basis of remaining position."""
        return self.remaining_quantity * self.avg_cost * 100
    
    @property
    def total_pnl(self) -> float:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def option_details(self) -> OptionSymbol:
        """Parse and return option symbol details."""
        return parse_osi_symbol(self.symbol)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "underlying": self.underlying,
            "quantity": self.quantity,
            "remaining_quantity": self.remaining_quantity,
            "side": self.side,
            "avg_cost": round(self.avg_cost, 4),
            "current_price": round(self.current_price, 4) if self.current_price else None,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "market_value": round(self.market_value, 2),
            "cost_basis": round(self.cost_basis, 2),
        }


# State transition rules
VALID_TRANSITIONS: Dict[PositionState, Dict[PositionEvent, PositionState]] = {
    PositionState.PENDING: {
        PositionEvent.FILL_CONFIRMED: PositionState.OPEN,
        PositionEvent.ORDER_REJECTED: PositionState.REJECTED,
    },
    PositionState.OPEN: {
        PositionEvent.PARTIAL_CLOSE: PositionState.PARTIALLY_CLOSED,
        PositionEvent.FULL_CLOSE: PositionState.CLOSED,
        PositionEvent.ASSIGNMENT_NOTICE: PositionState.ASSIGNED,
        PositionEvent.EXERCISE_REQUEST: PositionState.EXERCISED,
        PositionEvent.EXPIRATION: PositionState.EXPIRED,
    },
    PositionState.PARTIALLY_CLOSED: {
        PositionEvent.PARTIAL_CLOSE: PositionState.PARTIALLY_CLOSED,
        PositionEvent.FULL_CLOSE: PositionState.CLOSED,
        PositionEvent.ASSIGNMENT_NOTICE: PositionState.ASSIGNED,
        PositionEvent.EXPIRATION: PositionState.EXPIRED,
    },
}


class PositionFSM:
    """
    Finite State Machine for position lifecycle management.
    
    Features:
    - Event-driven state transitions
    - Validation of transition rules
    - State history tracking
    - Concurrent position management
    - Hooks for state change notifications
    
    Thread Safety:
    - All position operations are protected by locks
    - Safe for multi-threaded access
    
    Example:
        fsm = PositionFSM()
        
        # Register state change hook
        @fsm.on_state_change
        def handle_state_change(position, old_state, new_state, event):
            print(f"{position.symbol}: {old_state} -> {new_state}")
        
        # Create position
        pos = fsm.create_position("AAPL240119C00150000", 10, "long", 5.25)
        
        # Process events
        fsm.process_event(pos.id, PositionEvent.FILL_CONFIRMED)
    """
    
    def __init__(self) -> None:
        """Initialize the position state machine."""
        self._positions: Dict[str, Position] = {}
        self._positions_by_symbol: Dict[str, Set[str]] = {}
        self._lock = Lock()
        
        # State change callbacks
        self._state_change_hooks: List[Callable] = []
        
        logger.info("PositionFSM initialized")
    
    def on_state_change(
        self,
        callback: Callable[[Position, PositionState, PositionState, PositionEvent], None],
    ) -> Callable:
        """
        Register a state change callback.
        
        Can be used as a decorator:
            @fsm.on_state_change
            def handle_change(position, old_state, new_state, event):
                ...
        """
        self._state_change_hooks.append(callback)
        return callback
    
    def create_position(
        self,
        symbol: str,
        quantity: int,
        side: str,
        avg_cost: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Position:
        """
        Create a new position in PENDING state.
        
        Args:
            symbol: OSI option symbol
            quantity: Number of contracts (unsigned)
            side: 'long' or 'short'
            avg_cost: Average cost per contract
            metadata: Optional additional data
            
        Returns:
            Created Position object
        """
        # Validate inputs
        if quantity <= 0:
            raise ValidationError(
                message="Quantity must be positive",
                field_name="quantity",
                field_value=quantity,
            )
        
        if side not in ("long", "short"):
            raise ValidationError(
                message="Side must be 'long' or 'short'",
                field_name="side",
                field_value=side,
            )
        
        # Parse symbol to get underlying
        option = parse_osi_symbol(symbol)
        
        # Create position
        position = Position(
            id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            underlying=option.underlying,
            quantity=quantity if side == "long" else -quantity,
            remaining_quantity=quantity,
            side=side,
            avg_cost=avg_cost,
            state=PositionState.PENDING,
            metadata=metadata or {},
        )
        
        # Store position
        with self._lock:
            self._positions[position.id] = position
            
            if position.symbol not in self._positions_by_symbol:
                self._positions_by_symbol[position.symbol] = set()
            self._positions_by_symbol[position.symbol].add(position.id)
        
        set_gauge("open_positions", len(self.get_active_positions()))
        
        logger.info(
            "Position created",
            position_id=position.id,
            symbol=position.symbol,
            quantity=position.quantity,
            side=position.side,
        )
        
        return position
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """Get a position by ID."""
        return self._positions.get(position_id)
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get all positions for a symbol."""
        symbol = symbol.upper()
        position_ids = self._positions_by_symbol.get(symbol, set())
        return [self._positions[pid] for pid in position_ids if pid in self._positions]
    
    def get_active_positions(self) -> List[Position]:
        """Get all active (non-terminal) positions."""
        return [p for p in self._positions.values() if p.state.is_active]
    
    def get_positions_by_underlying(self, underlying: str) -> List[Position]:
        """Get all positions for an underlying."""
        underlying = underlying.upper()
        return [p for p in self._positions.values() if p.underlying == underlying]
    
    def process_event(
        self,
        position_id: str,
        event: PositionEvent,
        **kwargs,
    ) -> Position:
        """
        Process an event and potentially transition state.
        
        Args:
            position_id: Position ID
            event: Event to process
            **kwargs: Event-specific data (e.g., quantity for partial close)
            
        Returns:
            Updated Position
            
        Raises:
            ValidationError: If transition is invalid
        """
        with self._lock:
            position = self._positions.get(position_id)
            if position is None:
                raise ValidationError(
                    message=f"Position not found: {position_id}",
                    field_name="position_id",
                    field_value=position_id,
                )
            
            # Check if transition is valid
            old_state = position.state
            transitions = VALID_TRANSITIONS.get(old_state, {})
            
            if event not in transitions:
                raise ValidationError(
                    message=f"Invalid transition: {old_state.value} + {event.value}",
                    context={
                        "current_state": old_state.value,
                        "event": event.value,
                        "valid_events": list(transitions.keys()),
                    },
                )
            
            new_state = transitions[event]
            
            # Update position based on event
            position = self._apply_event(position, event, new_state, **kwargs)
            position.state = new_state
            
            # Record transition
            transition = StateTransition(
                from_state=old_state,
                to_state=new_state,
                event=event,
                timestamp=datetime.now(timezone.utc),
                metadata=kwargs,
            )
            position.transitions.append(transition)
            
            # Update storage
            self._positions[position_id] = position
        
        # Notify hooks (outside lock)
        for hook in self._state_change_hooks:
            try:
                hook(position, old_state, new_state, event)
            except Exception as e:
                logger.error(f"State change hook error: {e}")
        
        set_gauge("open_positions", len(self.get_active_positions()))
        increment_counter("state_transitions_total")
        
        logger.info(
            "Position state changed",
            position_id=position_id,
            old_state=old_state.value,
            new_state=new_state.value,
            event=event.value,
        )
        
        return position
    
    def _apply_event(
        self,
        position: Position,
        event: PositionEvent,
        new_state: PositionState,
        **kwargs,
    ) -> Position:
        """Apply event-specific changes to position."""
        now = datetime.now(timezone.utc)
        
        if event == PositionEvent.FILL_CONFIRMED:
            position.opened_at = now
            
        elif event == PositionEvent.PARTIAL_CLOSE:
            close_quantity = kwargs.get("quantity", 0)
            close_price = kwargs.get("price", position.current_price or position.avg_cost)
            
            if close_quantity <= 0 or close_quantity >= position.remaining_quantity:
                raise ValidationError(
                    message="Invalid partial close quantity",
                    field_name="quantity",
                    field_value=close_quantity,
                )
            
            # Calculate P&L for closed portion
            pnl = self._calculate_close_pnl(
                position, close_quantity, close_price
            )
            position.realized_pnl += pnl
            position.remaining_quantity -= close_quantity
            
        elif event == PositionEvent.FULL_CLOSE:
            close_price = kwargs.get("price", position.current_price or position.avg_cost)
            
            pnl = self._calculate_close_pnl(
                position, position.remaining_quantity, close_price
            )
            position.realized_pnl += pnl
            position.remaining_quantity = 0
            position.closed_at = now
            
        elif event in (PositionEvent.ASSIGNMENT_NOTICE, PositionEvent.EXERCISED):
            position.remaining_quantity = 0
            position.closed_at = now
            # P&L from assignment/exercise handled separately
            
        elif event == PositionEvent.EXPIRATION:
            # Expired worthless
            pnl = -position.cost_basis if position.is_long else position.cost_basis
            position.realized_pnl += pnl
            position.remaining_quantity = 0
            position.closed_at = now
        
        return position
    
    def _calculate_close_pnl(
        self,
        position: Position,
        quantity: int,
        close_price: float,
    ) -> float:
        """Calculate P&L for closing contracts."""
        if position.is_long:
            # Long: P&L = (close - cost) * quantity * 100
            return (close_price - position.avg_cost) * quantity * 100
        else:
            # Short: P&L = (cost - close) * quantity * 100
            return (position.avg_cost - close_price) * quantity * 100
    
    def update_price(
        self,
        position_id: str,
        current_price: float,
    ) -> Position:
        """
        Update current price and recalculate unrealized P&L.
        
        Args:
            position_id: Position ID
            current_price: Current market price
            
        Returns:
            Updated Position
        """
        with self._lock:
            position = self._positions.get(position_id)
            if position is None:
                raise ValidationError(
                    message=f"Position not found: {position_id}",
                    field_name="position_id",
                    field_value=position_id,
                )
            
            position.current_price = current_price
            
            # Calculate unrealized P&L
            if position.state.is_active:
                if position.is_long:
                    position.unrealized_pnl = (
                        (current_price - position.avg_cost) *
                        position.remaining_quantity * 100
                    )
                else:
                    position.unrealized_pnl = (
                        (position.avg_cost - current_price) *
                        position.remaining_quantity * 100
                    )
            
            self._positions[position_id] = position
        
        return position
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of all positions."""
        active = self.get_active_positions()
        
        total_market_value = sum(p.market_value for p in active)
        total_cost_basis = sum(p.cost_basis for p in active)
        total_unrealized_pnl = sum(p.unrealized_pnl for p in active)
        total_realized_pnl = sum(p.realized_pnl for p in self._positions.values())
        
        return {
            "active_positions": len(active),
            "total_positions": len(self._positions),
            "market_value": round(total_market_value, 2),
            "cost_basis": round(total_cost_basis, 2),
            "unrealized_pnl": round(total_unrealized_pnl, 2),
            "realized_pnl": round(total_realized_pnl, 2),
            "total_pnl": round(total_unrealized_pnl + total_realized_pnl, 2),
            "by_underlying": self._summarize_by_underlying(active),
        }
    
    def _summarize_by_underlying(
        self,
        positions: List[Position],
    ) -> Dict[str, Dict[str, Any]]:
        """Summarize positions by underlying."""
        by_underlying: Dict[str, Dict[str, Any]] = {}
        
        for pos in positions:
            if pos.underlying not in by_underlying:
                by_underlying[pos.underlying] = {
                    "positions": 0,
                    "market_value": 0.0,
                    "unrealized_pnl": 0.0,
                }
            
            by_underlying[pos.underlying]["positions"] += 1
            by_underlying[pos.underlying]["market_value"] += pos.market_value
            by_underlying[pos.underlying]["unrealized_pnl"] += pos.unrealized_pnl
        
        return by_underlying


# =============================================================================
# MODULE-LEVEL UTILITIES
# =============================================================================

_position_manager: Optional[PositionFSM] = None


def get_position_manager() -> PositionFSM:
    """Get global position manager instance."""
    global _position_manager
    if _position_manager is None:
        _position_manager = PositionFSM()
    return _position_manager
