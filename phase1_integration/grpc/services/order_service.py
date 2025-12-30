"""
gRPC Order Service Implementation
Handles order execution between trading and execution engines
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, AsyncIterator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import os

import grpc
from concurrent import futures

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------

@dataclass
class OrderLeg:
    """Option leg in a multi-leg order"""
    leg_id: str = ""
    symbol: str = ""
    underlying: str = ""
    strike: float = 0.0
    expiry: str = ""
    option_type: str = ""  # call, put
    side: str = ""         # buy, sell
    quantity: int = 0
    limit_price: float = 0.0
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    
    def __post_init__(self):
        if not self.leg_id:
            self.leg_id = f"leg_{uuid.uuid4().hex[:6]}"


@dataclass
class OrderMetadata:
    """Order metadata"""
    signal_id: str = ""
    strategy_id: str = ""
    target_credit: float = 0.0
    target_debit: float = 0.0
    max_slippage: float = 0.05  # 5% default
    paper_mode: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Order:
    """Order data class"""
    order_id: str = ""
    client_order_id: str = ""
    symbol: str = ""
    side: str = ""          # buy, sell
    order_type: str = "limit"
    time_in_force: str = "day"
    quantity: int = 0
    limit_price: float = 0.0
    stop_price: float = 0.0
    status: str = "pending"
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    strategy: str = ""
    legs: List[OrderLeg] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: OrderMetadata = field(default_factory=OrderMetadata)
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"ord_{uuid.uuid4().hex[:8]}"
        if not self.client_order_id:
            self.client_order_id = f"cli_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "quantity": self.quantity,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "status": self.status,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price": self.avg_fill_price,
            "strategy": self.strategy,
            "legs": [vars(leg) for leg in self.legs],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": vars(self.metadata) if self.metadata else {},
        }


@dataclass
class Fill:
    """Trade fill"""
    fill_id: str = ""
    order_id: str = ""
    leg_id: str = ""
    quantity: int = 0
    price: float = 0.0
    commission: float = 0.0
    timestamp: str = ""
    venue: str = "paper"
    
    def __post_init__(self):
        if not self.fill_id:
            self.fill_id = f"fill_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class OrderUpdate:
    """Order update event"""
    order_id: str
    event_type: str  # submitted, partial, filled, cancelled, rejected
    order: Order
    fill: Optional[Fill] = None
    timestamp: str = ""
    message: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


# -----------------------------------------------------------------------------
# Service Implementation
# -----------------------------------------------------------------------------

class OrderServiceImpl:
    """
    Order Service implementation.
    
    Handles:
    - Order submission and lifecycle
    - Fill tracking
    - Position management
    - Streaming updates
    """
    
    def __init__(self, paper_mode: bool = True):
        self.paper_mode = paper_mode
        
        # Order store
        self._orders: Dict[str, Order] = {}
        self._order_history: List[Order] = []
        
        # Fill store
        self._fills: Dict[str, List[Fill]] = defaultdict(list)
        
        # Update subscribers
        self._update_subscribers: List[asyncio.Queue] = []
        
        # Stats
        self._orders_today = 0
        self._last_reset = datetime.utcnow().date()
        self._latencies: List[float] = []
        
        # Redis streams (optional)
        self._redis_streams = None
        
        logger.info(f"OrderService initialized (paper_mode={paper_mode})")
    
    async def init_redis(self):
        """Initialize Redis streams integration"""
        try:
            from ..redis import get_streams
            self._redis_streams = get_streams()
            logger.info("Redis streams integration enabled")
        except ImportError:
            logger.warning("Redis streams not available")
    
    def _reset_daily_stats(self):
        """Reset daily stats if needed"""
        today = datetime.utcnow().date()
        if today != self._last_reset:
            self._orders_today = 0
            self._last_reset = today
    
    # -------------------------------------------------------------------------
    # Order Operations
    # -------------------------------------------------------------------------
    
    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        limit_price: float = 0.0,
        stop_price: float = 0.0,
        time_in_force: str = "day",
        strategy: str = "",
        legs: List[OrderLeg] = None,
        metadata: OrderMetadata = None,
    ) -> tuple:
        """
        Submit a new order.
        
        Returns:
            (success, order_id, client_order_id, order, error)
        """
        start_time = datetime.utcnow()
        self._reset_daily_stats()
        
        try:
            # Create order
            order = Order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                time_in_force=time_in_force,
                quantity=quantity,
                limit_price=limit_price,
                stop_price=stop_price,
                strategy=strategy,
                legs=legs or [],
                metadata=metadata or OrderMetadata(paper_mode=self.paper_mode),
            )
            
            # Validate order
            validation_error = self._validate_order(order)
            if validation_error:
                order.status = OrderStatus.REJECTED.value
                return (False, order.order_id, order.client_order_id, order, validation_error)
            
            # Store order
            self._orders[order.order_id] = order
            self._order_history.append(order)
            self._orders_today += 1
            
            # In paper mode, simulate immediate submission
            if self.paper_mode or order.metadata.paper_mode:
                order.status = OrderStatus.SUBMITTED.value
                order.updated_at = datetime.utcnow().isoformat()
                
                # Broadcast update
                await self._broadcast_update(OrderUpdate(
                    order_id=order.order_id,
                    event_type="submitted",
                    order=order,
                    message="Order submitted (paper mode)",
                ))
                
                # Simulate fill for market orders
                if order.order_type == OrderType.MARKET.value:
                    await self._simulate_fill(order)
            
            # Redis streams persistence
            if self._redis_streams:
                try:
                    from ..redis import OrderEvent as RedisOrderEvent
                    event = RedisOrderEvent(
                        order_id=order.order_id,
                        status=order.status,
                        symbol=order.symbol,
                        side=order.side,
                        quantity=order.quantity,
                        order_type=order.order_type,
                        price=order.limit_price,
                        strategy=order.strategy,
                    )
                    await self._redis_streams.add_order_event(event)
                except Exception as e:
                    logger.warning(f"Redis stream write failed: {e}")
            
            # Track latency
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._latencies.append(latency)
            if len(self._latencies) > 1000:
                self._latencies.pop(0)
            
            logger.info(f"Order submitted: {order.order_id} ({order.side} {order.quantity} {order.symbol})")
            return (True, order.order_id, order.client_order_id, order, None)
            
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            return (False, None, None, None, str(e))
    
    def _validate_order(self, order: Order) -> Optional[str]:
        """Validate order parameters"""
        if not order.symbol:
            return "Symbol is required"
        if not order.side or order.side not in ["buy", "sell"]:
            return "Invalid side"
        if order.quantity <= 0:
            return "Quantity must be positive"
        if order.order_type == OrderType.LIMIT.value and order.limit_price <= 0:
            return "Limit price required for limit orders"
        return None
    
    async def _simulate_fill(self, order: Order):
        """Simulate order fill in paper mode"""
        await asyncio.sleep(0.1)  # Simulate execution delay
        
        # Create fill
        fill = Fill(
            order_id=order.order_id,
            quantity=order.quantity,
            price=order.limit_price or 100.0,  # Mock price
            commission=0.65,  # Typical commission
        )
        
        # Update order
        order.status = OrderStatus.FILLED.value
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill.price
        order.updated_at = datetime.utcnow().isoformat()
        
        # Store fill
        self._fills[order.order_id].append(fill)
        
        # Broadcast update
        await self._broadcast_update(OrderUpdate(
            order_id=order.order_id,
            event_type="filled",
            order=order,
            fill=fill,
            message=f"Order filled at {fill.price}",
        ))
        
        logger.info(f"Order filled: {order.order_id} @ {fill.price}")
    
    async def cancel_order(self, order_id: str) -> tuple:
        """
        Cancel an order.
        
        Returns:
            (success, order_id, error)
        """
        try:
            order = self._orders.get(order_id)
            if not order:
                return (False, order_id, "Order not found")
            
            if order.status in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value]:
                return (False, order_id, f"Cannot cancel {order.status} order")
            
            order.status = OrderStatus.CANCELLED.value
            order.updated_at = datetime.utcnow().isoformat()
            
            await self._broadcast_update(OrderUpdate(
                order_id=order.order_id,
                event_type="cancelled",
                order=order,
                message="Order cancelled",
            ))
            
            logger.info(f"Order cancelled: {order_id}")
            return (True, order_id, None)
            
        except Exception as e:
            return (False, order_id, str(e))
    
    async def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        limit_price: float = None,
        stop_price: float = None,
    ) -> tuple:
        """Modify an existing order"""
        try:
            order = self._orders.get(order_id)
            if not order:
                return (False, order_id, None, "Order not found")
            
            if order.status not in [OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value]:
                return (False, order_id, None, "Cannot modify order in this state")
            
            if quantity is not None:
                order.quantity = quantity
            if limit_price is not None:
                order.limit_price = limit_price
            if stop_price is not None:
                order.stop_price = stop_price
            
            order.updated_at = datetime.utcnow().isoformat()
            
            logger.info(f"Order modified: {order_id}")
            return (True, order_id, order, None)
            
        except Exception as e:
            return (False, order_id, None, str(e))
    
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    async def get_open_orders(
        self,
        symbol: str = None,
        strategy: str = None,
    ) -> List[Order]:
        """Get all open orders"""
        open_statuses = [OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value, OrderStatus.PARTIAL.value]
        
        orders = []
        for order in self._orders.values():
            if order.status not in open_statuses:
                continue
            if symbol and order.symbol != symbol:
                continue
            if strategy and order.strategy != strategy:
                continue
            orders.append(order)
        
        return orders
    
    async def get_order_history(
        self,
        count: int = 100,
        symbol: str = None,
        strategy: str = None,
        since: str = None,
        until: str = None,
        statuses: List[str] = None,
    ) -> List[Order]:
        """Get order history with filters"""
        orders = []
        
        for order in reversed(self._order_history):
            if symbol and order.symbol != symbol:
                continue
            if strategy and order.strategy != strategy:
                continue
            if statuses and order.status not in statuses:
                continue
            
            # Time filters
            if since:
                order_dt = datetime.fromisoformat(order.created_at)
                since_dt = datetime.fromisoformat(since)
                if order_dt < since_dt:
                    continue
            if until:
                order_dt = datetime.fromisoformat(order.created_at)
                until_dt = datetime.fromisoformat(until)
                if order_dt > until_dt:
                    continue
            
            orders.append(order)
            if len(orders) >= count:
                break
        
        return orders
    
    async def bulk_cancel(
        self,
        order_ids: List[str] = None,
        symbol: str = None,
        cancel_all: bool = False,
    ) -> tuple:
        """Bulk cancel orders"""
        cancelled = []
        failed = []
        
        if cancel_all:
            targets = list(self._orders.values())
        elif symbol:
            targets = [o for o in self._orders.values() if o.symbol == symbol]
        elif order_ids:
            targets = [self._orders.get(oid) for oid in order_ids if oid in self._orders]
        else:
            return (0, [], [], "No orders specified")
        
        for order in targets:
            if not order:
                continue
            success, _, error = await self.cancel_order(order.order_id)
            if success:
                cancelled.append(order.order_id)
            else:
                failed.append(order.order_id)
        
        return (len(cancelled), cancelled, failed, None)
    
    # -------------------------------------------------------------------------
    # Streaming
    # -------------------------------------------------------------------------
    
    async def _broadcast_update(self, update: OrderUpdate):
        """Broadcast order update to all subscribers"""
        for queue in self._update_subscribers:
            await queue.put(update)
    
    async def stream_order_updates(
        self,
        order_ids: List[str] = None,
        symbols: List[str] = None,
        include_fills: bool = True,
    ) -> AsyncIterator[OrderUpdate]:
        """Stream order updates"""
        queue = asyncio.Queue()
        self._update_subscribers.append(queue)
        
        try:
            while True:
                update = await queue.get()
                
                # Apply filters
                if order_ids and update.order_id not in order_ids:
                    continue
                if symbols and update.order.symbol not in symbols:
                    continue
                if not include_fills and update.fill:
                    continue
                
                yield update
        finally:
            self._update_subscribers.remove(queue)
    
    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------
    
    async def health_check(self) -> dict:
        """Service health check"""
        self._reset_daily_stats()
        
        open_orders = len([o for o in self._orders.values() 
                         if o.status in [OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value]])
        
        avg_latency = (
            sum(self._latencies) / len(self._latencies)
            if self._latencies else 0.0
        )
        
        return {
            "healthy": True,
            "status": "running",
            "paper_mode": self.paper_mode,
            "open_orders": open_orders,
            "orders_today": self._orders_today,
            "avg_latency_ms": round(avg_latency, 2),
            "update_subscribers": len(self._update_subscribers),
        }


# -----------------------------------------------------------------------------
# gRPC Server
# -----------------------------------------------------------------------------

class OrderServiceGRPC:
    """gRPC server wrapper for OrderService"""
    
    def __init__(self, service: OrderServiceImpl = None, paper_mode: bool = True):
        self.service = service or OrderServiceImpl(paper_mode=paper_mode)
        self.server = None
    
    async def start(self, port: int = 50052):
        """Start gRPC server"""
        self.server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=10)
        )
        
        listen_addr = f"[::]:{port}"
        self.server.add_insecure_port(listen_addr)
        
        await self.server.start()
        logger.info(f"OrderService gRPC server started on {listen_addr}")
        
        # Initialize Redis
        await self.service.init_redis()
    
    async def stop(self):
        """Stop gRPC server"""
        if self.server:
            await self.server.stop(grace=5)
            logger.info("OrderService gRPC server stopped")


# -----------------------------------------------------------------------------
# Standalone Server
# -----------------------------------------------------------------------------

async def serve():
    """Run standalone order service"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    port = int(os.getenv("ORDER_SERVICE_PORT", "50052"))
    paper_mode = os.getenv("PAPER_MODE", "true").lower() == "true"
    
    grpc_server = OrderServiceGRPC(paper_mode=paper_mode)
    await grpc_server.start(port)
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await grpc_server.stop()


if __name__ == "__main__":
    asyncio.run(serve())
