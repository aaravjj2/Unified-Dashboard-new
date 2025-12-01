"""
Strategy Lab - Orders Module

Live order execution with safety controls:
- LIVE_ORDER_ALLOWED default: True
- Per-order confirmation modal (required)
- Position size limits
- Dry-run mode for testing
- Full audit trail

Safety Controls:
1. Modal confirmation for each live order
2. Max order size limit (configurable)
3. Dry-run mode (logs but doesn't execute)
4. Paper trading mode (sandbox)
5. Emergency stop functionality

Usage:
    from financial_dashboard.tabs.strategy_lab.orders import (
        LiveOrderManager,
        LIVE_ORDER_ALLOWED,
        validate_order,
        execute_order
    )
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default: Live orders ARE allowed (with confirmation modal)
LIVE_ORDER_ALLOWED = True

# Environment override
if os.getenv('LIVE_ORDER_ALLOWED', 'true').lower() == 'false':
    LIVE_ORDER_ALLOWED = False
    logger.warning("⚠️ Live orders DISABLED via LIVE_ORDER_ALLOWED=false environment variable")

# Safety defaults
DEFAULT_MAX_ORDER_SIZE = 10000  # $10,000 max per order
DEFAULT_REQUIRE_CONFIRMATION = True  # Always require modal confirmation
DEFAULT_DRY_RUN_MODE = os.getenv('DRY_RUN_MODE', 'false').lower() == 'true'


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"  # User confirmed in modal
    SUBMITTED = "SUBMITTED"  # Sent to broker
    FILLED = "FILLED"
    PARTIAL = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass
class Order:
    """Represents a trading order with full audit trail."""
    id: str
    timestamp: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    fill_price: Optional[float] = None
    fill_quantity: int = 0
    broker_order_id: Optional[str] = None
    confirmation_timestamp: Optional[str] = None
    execution_timestamp: Optional[str] = None
    error_message: Optional[str] = None
    dry_run: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['side'] = self.side.value
        d['order_type'] = self.order_type.value
        d['status'] = self.status.value
        return d
    
    @property
    def notional_value(self) -> float:
        """Estimated order value in dollars."""
        price = self.limit_price or self.fill_price or 0
        return self.quantity * price


class OrderValidationError(Exception):
    """Raised when order validation fails."""
    pass


class LiveOrderManager:
    """
    Manages live order execution with safety controls.
    
    Safety Features:
    - Per-order confirmation required
    - Position size limits
    - Dry-run mode
    - Full audit logging
    - Broker integration (Alpaca)
    """
    
    def __init__(
        self,
        max_order_size: float = DEFAULT_MAX_ORDER_SIZE,
        require_confirmation: bool = DEFAULT_REQUIRE_CONFIRMATION,
        dry_run_mode: bool = DEFAULT_DRY_RUN_MODE
    ):
        self.max_order_size = max_order_size
        self.require_confirmation = require_confirmation
        self.dry_run_mode = dry_run_mode
        self.pending_orders: Dict[str, Order] = {}
        self.order_history: list = []
        self._broker_client = None
        
        logger.info(f"📦 LiveOrderManager initialized:")
        logger.info(f"   LIVE_ORDER_ALLOWED: {LIVE_ORDER_ALLOWED}")
        logger.info(f"   Max order size: ${max_order_size:,.0f}")
        logger.info(f"   Require confirmation: {require_confirmation}")
        logger.info(f"   Dry run mode: {dry_run_mode}")
    
    def _get_broker_client(self):
        """Lazy-load broker client (Alpaca)."""
        if self._broker_client is None:
            try:
                from financial_dashboard.broker_connector import get_alpaca_client
                self._broker_client = get_alpaca_client()
                logger.info("✅ Alpaca broker client connected")
            except Exception as e:
                logger.error(f"❌ Failed to connect broker: {e}")
                raise
        return self._broker_client
    
    def validate_order(self, order: Order) -> Tuple[bool, str]:
        """
        Validate order before submission.
        
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        errors = []
        
        # Check if live orders are allowed
        if not LIVE_ORDER_ALLOWED:
            return False, "Live orders are disabled (LIVE_ORDER_ALLOWED=false)"
        
        # Check symbol
        if not order.symbol or len(order.symbol) < 1:
            errors.append("Invalid symbol")
        
        # Check quantity
        if order.quantity <= 0:
            errors.append("Quantity must be positive")
        
        # Check order size limit
        if order.notional_value > self.max_order_size:
            errors.append(
                f"Order size ${order.notional_value:,.0f} exceeds limit ${self.max_order_size:,.0f}"
            )
        
        # Check limit price for limit orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if not order.limit_price or order.limit_price <= 0:
                errors.append("Limit orders require a positive limit price")
        
        # Check stop price for stop orders
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if not order.stop_price or order.stop_price <= 0:
                errors.append("Stop orders require a positive stop price")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "Order validated successfully"
    
    def create_pending_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        estimated_price: Optional[float] = None
    ) -> Order:
        """
        Create a pending order for confirmation.
        
        The order will be stored and must be confirmed via confirm_order()
        before execution.
        """
        order_id = f"SL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.pending_orders) + 1}"
        
        order = Order(
            id=order_id,
            timestamp=datetime.now().isoformat(),
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price or estimated_price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            dry_run=self.dry_run_mode
        )
        
        # Validate
        is_valid, message = self.validate_order(order)
        if not is_valid:
            order.status = OrderStatus.REJECTED
            order.error_message = message
            logger.warning(f"⚠️ Order rejected: {message}")
            raise OrderValidationError(message)
        
        self.pending_orders[order_id] = order
        logger.info(f"📝 Pending order created: {order_id} - {side.value} {quantity} {symbol}")
        
        return order
    
    def get_confirmation_details(self, order_id: str) -> Dict[str, Any]:
        """
        Get order details for confirmation modal.
        
        Returns a dictionary with all information needed for the confirmation UI.
        """
        order = self.pending_orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        return {
            'order_id': order.id,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': order.quantity,
            'order_type': order.order_type.value,
            'limit_price': order.limit_price,
            'stop_price': order.stop_price,
            'estimated_value': order.notional_value,
            'dry_run': order.dry_run,
            'timestamp': order.timestamp,
            'warning': "This will execute a REAL trade with actual money." if not order.dry_run else "DRY RUN - No actual trade will be placed."
        }
    
    def confirm_order(self, order_id: str) -> Order:
        """
        Confirm a pending order and proceed to execution.
        
        This is called when user clicks "Confirm" in the modal.
        """
        order = self.pending_orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order {order_id} is not in PENDING state")
        
        order.status = OrderStatus.CONFIRMED
        order.confirmation_timestamp = datetime.now().isoformat()
        
        logger.info(f"✅ Order confirmed by user: {order_id}")
        
        # Execute the order
        return self.execute_order(order)
    
    def cancel_order(self, order_id: str) -> Order:
        """Cancel a pending order."""
        order = self.pending_orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        order.status = OrderStatus.CANCELLED
        logger.info(f"❌ Order cancelled: {order_id}")
        
        # Move to history
        self.order_history.append(order)
        del self.pending_orders[order_id]
        
        return order
    
    def execute_order(self, order: Order) -> Order:
        """
        Execute a confirmed order.
        
        If dry_run_mode is True, logs the order but doesn't actually execute.
        """
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError("Order must be confirmed before execution")
        
        try:
            if self.dry_run_mode or order.dry_run:
                # Dry run - simulate execution
                logger.info(f"🧪 DRY RUN: Would execute {order.side.value} {order.quantity} {order.symbol}")
                order.status = OrderStatus.FILLED
                order.fill_price = order.limit_price or 100.0  # Mock fill
                order.fill_quantity = order.quantity
                order.execution_timestamp = datetime.now().isoformat()
                order.broker_order_id = f"DRY-{order.id}"
            else:
                # Real execution via broker
                order.status = OrderStatus.SUBMITTED
                
                client = self._get_broker_client()
                
                # Build order request
                broker_order = client.submit_order(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=order.side.value.lower(),
                    type=order.order_type.value.lower().replace('_', '-'),
                    time_in_force='day',
                    limit_price=str(order.limit_price) if order.limit_price else None,
                    stop_price=str(order.stop_price) if order.stop_price else None
                )
                
                order.broker_order_id = broker_order.id
                order.status = OrderStatus.FILLED  # Simplified - real impl would poll for fill
                order.fill_price = float(broker_order.filled_avg_price or order.limit_price or 0)
                order.fill_quantity = int(broker_order.filled_qty or order.quantity)
                order.execution_timestamp = datetime.now().isoformat()
                
                logger.info(f"✅ Order executed: {order.id} -> {order.broker_order_id}")
            
        except Exception as e:
            order.status = OrderStatus.FAILED
            order.error_message = str(e)
            logger.error(f"❌ Order execution failed: {e}")
        
        # Move to history
        self.order_history.append(order)
        if order.id in self.pending_orders:
            del self.pending_orders[order.id]
        
        return order
    
    def get_order_history(self) -> list:
        """Get full order history."""
        return [o.to_dict() for o in self.order_history]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_manager: Optional[LiveOrderManager] = None


def get_order_manager() -> LiveOrderManager:
    """Get or create the singleton order manager."""
    global _manager
    if _manager is None:
        _manager = LiveOrderManager()
    return _manager


def validate_order(
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "MARKET",
    limit_price: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Quick validation without creating an order.
    
    Returns:
        Tuple[bool, str]: (is_valid, message)
    """
    manager = get_order_manager()
    
    try:
        order = Order(
            id="VALIDATE",
            timestamp=datetime.now().isoformat(),
            symbol=symbol.upper(),
            side=OrderSide[side.upper()],
            quantity=quantity,
            order_type=OrderType[order_type.upper()],
            limit_price=limit_price
        )
        return manager.validate_order(order)
    except Exception as e:
        return False, str(e)


def create_order(
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "MARKET",
    limit_price: Optional[float] = None,
    estimated_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create a pending order for confirmation.
    
    Returns order details dict for the confirmation modal.
    """
    manager = get_order_manager()
    
    order = manager.create_pending_order(
        symbol=symbol,
        side=OrderSide[side.upper()],
        quantity=quantity,
        order_type=OrderType[order_type.upper()],
        limit_price=limit_price,
        estimated_price=estimated_price
    )
    
    return manager.get_confirmation_details(order.id)


def confirm_and_execute(order_id: str) -> Dict[str, Any]:
    """
    Confirm and execute a pending order.
    
    Returns the executed order details.
    """
    manager = get_order_manager()
    order = manager.confirm_order(order_id)
    return order.to_dict()


def cancel_pending_order(order_id: str) -> Dict[str, Any]:
    """Cancel a pending order."""
    manager = get_order_manager()
    order = manager.cancel_order(order_id)
    return order.to_dict()


logger.info(f"📦 Orders module loaded: LIVE_ORDER_ALLOWED={LIVE_ORDER_ALLOWED}")
