"""
Execution Router - Phase 4 TradeOps

Implements OrderRouter that handles Paper vs Live order routing.
All orders pass through RiskManager.check() before execution.

Paper orders are simulated locally.
Live orders require CONFIRM + FORCE_PLACE_LIVE=true environment variable.
"""

import os
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from engines.risk.guard import (
    RiskManager, 
    RiskCheckResult, 
    RiskViolation,
    OrderRequest,
    get_risk_manager
)

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order lifecycle status."""
    PENDING = "pending"
    RISK_CHECKING = "risk_checking"
    RISK_REJECTED = "risk_rejected"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class ExecutionResult:
    """Result of an order execution attempt."""
    success: bool
    order_id: str
    status: OrderStatus
    message: str
    risk_result: Optional[RiskCheckResult] = None
    fill_price: Optional[float] = None
    filled_qty: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "order_id": self.order_id,
            "status": self.status.value,
            "message": self.message,
            "risk_result": self.risk_result.to_dict() if self.risk_result else None,
            "fill_price": self.fill_price,
            "filled_qty": self.filled_qty,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class Order:
    """Internal order representation."""
    order_id: str
    request: OrderRequest
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    risk_result: Optional[RiskCheckResult] = None
    fill_price: Optional[float] = None
    filled_qty: int = 0
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "order_id": self.order_id,
            "ticker": self.request.ticker,
            "side": self.request.side,
            "quantity": self.request.quantity,
            "order_type": self.request.order_type,
            "price": self.request.price,
            "status": self.status.value,
            "is_paper": self.request.is_paper,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "fill_price": self.fill_price,
            "filled_qty": self.filled_qty
        }


class OrderRouter:
    """
    Order Execution Router for TradeOps.
    
    Routes orders through:
    1. Risk Manager validation
    2. Paper or Live execution path
    3. Order tracking and status updates
    
    Paper mode (default): Simulates fills locally
    Live mode: Requires FORCE_PLACE_LIVE=true + explicit confirm
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for order router."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize order router."""
        if self._initialized:
            return
        
        # Risk manager reference
        self.risk_manager = get_risk_manager()
        
        # Mode configuration
        self.paper_mode = True  # Default to paper
        self.force_live_enabled = os.getenv("FORCE_PLACE_LIVE", "false").lower() == "true"
        self.deterministic = os.getenv("TRADEOPS_DETERMINISTIC", "0") == "1"
        
        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.active_orders: List[str] = []
        self.order_history: List[str] = []
        
        # Callbacks for UI updates
        self.on_order_update: Optional[Callable[[Order], None]] = None
        self.on_risk_reject: Optional[Callable[[RiskCheckResult], None]] = None
        
        # Simulated market prices for paper trading
        self._paper_prices: Dict[str, float] = {
            "SPY": 450.00,
            "QQQ": 380.00,
            "AAPL": 175.00,
            "MSFT": 375.00,
            "NVDA": 480.00,
            "TSLA": 250.00,
            "AMD": 145.00,
            "META": 350.00,
            "GOOGL": 140.00,
            "AMZN": 155.00,
        }
        
        self._initialized = True
        logger.info(f"OrderRouter initialized: paper_mode={self.paper_mode}, "
                   f"force_live_enabled={self.force_live_enabled}")
    
    def submit_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
        is_paper: bool = True,
        confirm_live: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Submit an order for execution.
        
        Args:
            ticker: Symbol to trade
            side: "buy" or "sell"
            quantity: Number of shares
            order_type: "market", "limit", "stop", "stop_limit"
            price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: "day", "gtc", "ioc", "fok"
            is_paper: Use paper trading (default True)
            confirm_live: Explicit confirmation for live orders
            metadata: Additional order metadata
            
        Returns:
            ExecutionResult with order status
        """
        # Generate order ID
        order_id = self._generate_order_id()
        
        # Build order request
        request = OrderRequest(
            ticker=ticker.upper(),
            side=side.lower(),
            quantity=quantity,
            order_type=order_type.lower(),
            price=price or self._get_market_price(ticker),
            stop_price=stop_price,
            time_in_force=time_in_force,
            is_paper=is_paper,
            metadata=metadata or {}
        )
        
        # Create order record
        now = datetime.now()
        order = Order(
            order_id=order_id,
            request=request,
            status=OrderStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        self.orders[order_id] = order
        
        logger.info(f"Order {order_id} created: {ticker} {side} {quantity} @ {order_type}")
        
        # Step 1: Risk check
        order.status = OrderStatus.RISK_CHECKING
        order.updated_at = datetime.now()
        
        risk_result = self.risk_manager.check(request)
        order.risk_result = risk_result
        
        if not risk_result.approved:
            # Risk rejected
            order.status = OrderStatus.RISK_REJECTED
            order.updated_at = datetime.now()
            order.error_message = risk_result.message
            
            logger.warning(f"Order {order_id} risk rejected: {risk_result.message}")
            
            # Trigger callback for UI notification
            if self.on_risk_reject:
                self.on_risk_reject(risk_result)
            
            return ExecutionResult(
                success=False,
                order_id=order_id,
                status=OrderStatus.RISK_REJECTED,
                message=f"Risk Rejected: {risk_result.message}",
                risk_result=risk_result,
                details={"violation": risk_result.violation.value}
            )
        
        # Step 2: Route to execution path
        if is_paper or self.paper_mode:
            return self._execute_paper(order)
        else:
            return self._execute_live(order, confirm_live)
    
    def _execute_paper(self, order: Order) -> ExecutionResult:
        """Execute order in paper trading mode."""
        order_id = order.order_id
        request = order.request
        
        # Simulate immediate fill for market orders
        fill_price = request.price or self._get_market_price(request.ticker)
        
        # Add small slippage for realism (deterministic if set)
        if not self.deterministic:
            import random
            slippage = random.uniform(-0.01, 0.01) * fill_price
            fill_price += slippage
        
        fill_price = round(fill_price, 2)
        
        # Update order
        order.status = OrderStatus.FILLED
        order.fill_price = fill_price
        order.filled_qty = request.quantity
        order.updated_at = datetime.now()
        
        self.order_history.append(order_id)
        
        # Update risk manager portfolio state
        if request.side == "buy":
            notional = fill_price * request.quantity
            self.risk_manager.update_portfolio_state(
                buying_power=self.risk_manager.buying_power - notional,
                open_positions=self.risk_manager.open_positions_count + 1
            )
        
        logger.info(f"Paper order {order_id} filled: {request.quantity} @ ${fill_price:.2f}")
        
        # Trigger update callback
        if self.on_order_update:
            self.on_order_update(order)
        
        return ExecutionResult(
            success=True,
            order_id=order_id,
            status=OrderStatus.FILLED,
            message=f"Paper order filled: {request.quantity} shares @ ${fill_price:.2f}",
            risk_result=order.risk_result,
            fill_price=fill_price,
            filled_qty=request.quantity,
            details={"execution_type": "paper"}
        )
    
    def _execute_live(self, order: Order, confirm: bool) -> ExecutionResult:
        """Execute order in live trading mode."""
        order_id = order.order_id
        
        # Safety check: require explicit confirmation AND force flag
        if not confirm:
            order.status = OrderStatus.REJECTED
            order.error_message = "Live order requires explicit confirmation"
            order.updated_at = datetime.now()
            
            return ExecutionResult(
                success=False,
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message="Live order requires confirm_live=True parameter",
                risk_result=order.risk_result
            )
        
        if not self.force_live_enabled:
            order.status = OrderStatus.REJECTED
            order.error_message = "FORCE_PLACE_LIVE not enabled"
            order.updated_at = datetime.now()
            
            return ExecutionResult(
                success=False,
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message="Live trading disabled. Set FORCE_PLACE_LIVE=true to enable.",
                risk_result=order.risk_result
            )
        
        # In a real implementation, this would call the broker API
        # For now, we simulate the live order as a paper order with a warning
        logger.warning(f"LIVE ORDER SIMULATION: {order_id} (broker integration not implemented)")
        
        order.status = OrderStatus.SUBMITTED
        order.updated_at = datetime.now()
        self.active_orders.append(order_id)
        
        return ExecutionResult(
            success=True,
            order_id=order_id,
            status=OrderStatus.SUBMITTED,
            message="Live order submitted (simulated - broker integration pending)",
            risk_result=order.risk_result,
            details={"execution_type": "live_simulated"}
        )
    
    def cancel_order(self, order_id: str) -> ExecutionResult:
        """Cancel an active order."""
        if order_id not in self.orders:
            return ExecutionResult(
                success=False,
                order_id=order_id,
                status=OrderStatus.ERROR,
                message=f"Order {order_id} not found"
            )
        
        order = self.orders[order_id]
        
        # Check if order can be cancelled
        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED):
            return ExecutionResult(
                success=False,
                order_id=order_id,
                status=order.status,
                message=f"Cannot cancel order in {order.status.value} status"
            )
        
        # Cancel the order
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        if order_id in self.active_orders:
            self.active_orders.remove(order_id)
        self.order_history.append(order_id)
        
        logger.info(f"Order {order_id} cancelled")
        
        if self.on_order_update:
            self.on_order_update(order)
        
        return ExecutionResult(
            success=True,
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            message=f"Order {order_id} cancelled successfully"
        )
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get all active (non-terminal) orders."""
        terminal_statuses = {
            OrderStatus.FILLED, 
            OrderStatus.CANCELLED, 
            OrderStatus.REJECTED,
            OrderStatus.RISK_REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.ERROR
        }
        
        active = []
        for order_id, order in self.orders.items():
            if order.status not in terminal_statuses:
                active.append(order.to_dict())
        
        return active
    
    def get_order_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent order history."""
        history = []
        for order_id in reversed(self.order_history[-limit:]):
            if order_id in self.orders:
                history.append(self.orders[order_id].to_dict())
        return history
    
    def set_paper_mode(self, enabled: bool):
        """Toggle paper trading mode."""
        self.paper_mode = enabled
        logger.info(f"Paper mode set to: {enabled}")
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        if self.deterministic:
            # Deterministic ID for testing
            count = len(self.orders) + 1
            return f"ORD-{count:06d}"
        return f"ORD-{uuid.uuid4().hex[:12].upper()}"
    
    def _get_market_price(self, ticker: str) -> float:
        """Get simulated market price for paper trading."""
        ticker = ticker.upper()
        if ticker in self._paper_prices:
            return self._paper_prices[ticker]
        # Default price for unknown tickers
        return 100.0
    
    def set_paper_price(self, ticker: str, price: float):
        """Set simulated price for paper trading."""
        self._paper_prices[ticker.upper()] = price


def get_order_router() -> OrderRouter:
    """Get the singleton OrderRouter instance."""
    return OrderRouter()
