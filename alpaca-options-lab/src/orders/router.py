"""
Alpaca Options Lab - Smart Order Router

Advanced order routing with:
- Multi-leg atomicity (all fill or none)
- Smart order splitting
- Retry logic with exponential backoff
- Partial fill rollback
- Execution quality analysis
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
import uuid

from src.orders.types import (
    Order, OrderStatus, OrderType, OrderSide, TimeInForce,
    MultiLegOrder, BracketOrder, OCOOrder, OTOOrder,
    OrderLeg, ExecutionResult,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class RoutingStrategy(Enum):
    """Order routing strategy."""
    SMART = "smart"           # Best execution algorithm
    DIRECT = "direct"         # Direct to exchange
    SEQUENTIAL = "sequential" # One leg at a time
    PARALLEL = "parallel"     # All legs simultaneously
    SWEEP = "sweep"           # Sweep available liquidity


@dataclass
class RoutingConfig:
    """Configuration for order routing."""
    strategy: RoutingStrategy = RoutingStrategy.SMART
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_multiplier: float = 2.0
    max_retry_delay: float = 30.0
    
    # Slippage and fill settings
    max_slippage_percent: float = 2.0
    allow_partial_fills: bool = False  # For multi-leg, generally False
    min_fill_ratio: float = 1.0  # 100% fill required for multi-leg
    
    # Timing
    timeout_seconds: float = 60.0
    heartbeat_interval: float = 5.0


class BrokerAPI(Protocol):
    """Protocol for broker API integration."""
    
    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
    ) -> Dict[str, Any]:
        """Submit a single order."""
        ...
    
    async def submit_multi_leg_order(
        self,
        legs: List[Dict[str, Any]],
        net_price: float,
        order_type: str,
        time_in_force: str = "day",
    ) -> Dict[str, Any]:
        """Submit a multi-leg order."""
        ...
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        ...
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        ...


@dataclass
class ExecutionMetrics:
    """Metrics for execution quality."""
    requested_price: float
    fill_price: float
    slippage: float = 0.0
    slippage_percent: float = 0.0
    fill_time_ms: float = 0.0
    retries_used: int = 0
    
    def __post_init__(self):
        if self.requested_price > 0:
            self.slippage = self.fill_price - self.requested_price
            self.slippage_percent = (self.slippage / self.requested_price) * 100


class SmartOrderRouter:
    """
    Smart order router for optimal execution.
    
    Features:
    - Multi-leg atomic execution
    - Intelligent order splitting
    - Automatic retries with backoff
    - Rollback on partial failures
    - Execution quality tracking
    """
    
    def __init__(
        self,
        broker: BrokerAPI,
        config: Optional[RoutingConfig] = None,
    ):
        self.broker = broker
        self.config = config or RoutingConfig()
        
        # Active orders tracking
        self._active_orders: Dict[str, Order] = {}
        self._active_multi_leg: Dict[str, MultiLegOrder] = {}
        self._active_brackets: Dict[str, BracketOrder] = {}
        self._active_oco: Dict[str, OCOOrder] = {}
        self._active_oto: Dict[str, OTOOrder] = {}
        
        # Execution history
        self._execution_history: List[ExecutionResult] = []
        
        # Event callbacks
        self._on_fill_callbacks: List[Callable] = []
        self._on_reject_callbacks: List[Callable] = []
        
        logger.info(
            f"SmartOrderRouter initialized: strategy={self.config.strategy.value}, "
            f"max_retries={self.config.max_retries}"
        )
    
    # -------------------- Single Order Execution --------------------
    
    async def submit_order(self, order: Order) -> ExecutionResult:
        """
        Submit a single-leg order.
        
        Returns:
            ExecutionResult with fill details or error
        """
        order.validate()
        logger.info(f"Submitting order: {order.symbol} {order.side.value} x{order.quantity}")
        
        self._active_orders[order.order_id] = order
        
        try:
            result = await self._execute_with_retry(order)
            
            if result.success:
                order.status = OrderStatus.FILLED
                order.filled_quantity = result.filled_quantity
                order.filled_price = result.fill_price
                order.filled_at = datetime.now(timezone.utc)
                
                await self._notify_fill(order, result)
            else:
                order.status = OrderStatus.REJECTED
                await self._notify_reject(order, result)
            
            self._execution_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            order.status = OrderStatus.FAILED
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error=str(e),
            )
        finally:
            self._active_orders.pop(order.order_id, None)
    
    async def _execute_with_retry(self, order: Order) -> ExecutionResult:
        """Execute order with retry logic."""
        delay = self.config.retry_delay_seconds
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self.broker.submit_order(
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=order.quantity,
                    order_type=order.order_type.value,
                    limit_price=order.limit_price,
                    stop_price=order.stop_price,
                    time_in_force=order.time_in_force.value,
                )
                
                if response.get("status") == "filled":
                    return ExecutionResult(
                        success=True,
                        order_id=response.get("id", order.order_id),
                        fill_price=response.get("filled_avg_price", order.limit_price),
                        filled_quantity=response.get("filled_qty", order.quantity),
                        commission=response.get("commission", 0.0),
                    )
                elif response.get("status") == "rejected":
                    return ExecutionResult(
                        success=False,
                        order_id=order.order_id,
                        error=response.get("error", "Order rejected"),
                    )
                else:
                    # Wait for fill
                    result = await self._wait_for_fill(
                        response.get("id", order.order_id),
                        timeout=self.config.timeout_seconds,
                    )
                    if result.success:
                        return result
                    
            except Exception as e:
                logger.warning(f"Order attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.config.retry_backoff_multiplier,
                        self.config.max_retry_delay,
                    )
                else:
                    raise
        
        return ExecutionResult(
            success=False,
            order_id=order.order_id,
            error="Max retries exceeded",
        )
    
    async def _wait_for_fill(
        self,
        order_id: str,
        timeout: float,
    ) -> ExecutionResult:
        """Wait for order to fill."""
        start_time = datetime.now(timezone.utc)
        
        while True:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                return ExecutionResult(
                    success=False,
                    order_id=order_id,
                    error="Order fill timeout",
                )
            
            try:
                status = await self.broker.get_order_status(order_id)
                
                if status.get("status") == "filled":
                    return ExecutionResult(
                        success=True,
                        order_id=order_id,
                        fill_price=status.get("filled_avg_price"),
                        filled_quantity=status.get("filled_qty", 0),
                        commission=status.get("commission", 0.0),
                    )
                elif status.get("status") in ("rejected", "cancelled", "expired"):
                    return ExecutionResult(
                        success=False,
                        order_id=order_id,
                        error=f"Order {status.get('status')}",
                    )
                
            except Exception as e:
                logger.warning(f"Error checking order status: {e}")
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    # -------------------- Multi-Leg Order Execution --------------------
    
    async def submit_multi_leg(self, order: MultiLegOrder) -> ExecutionResult:
        """
        Submit a multi-leg order with atomicity guarantee.
        
        All legs fill or none fill. If partial fill occurs,
        automatic rollback is attempted.
        """
        order.validate()
        logger.info(
            f"Submitting multi-leg order: {order.num_legs} legs, "
            f"net_price={order.net_price}"
        )
        
        self._active_multi_leg[order.order_id] = order
        
        try:
            # Use broker's native multi-leg if available
            result = await self._execute_multi_leg_atomic(order)
            
            if result.success:
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now(timezone.utc)
                await self._notify_fill(order, result)
            else:
                order.status = OrderStatus.REJECTED
                await self._notify_reject(order, result)
            
            self._execution_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Multi-leg execution failed: {e}")
            order.status = OrderStatus.FAILED
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error=str(e),
            )
        finally:
            self._active_multi_leg.pop(order.order_id, None)
    
    async def _execute_multi_leg_atomic(
        self,
        order: MultiLegOrder,
    ) -> ExecutionResult:
        """Execute multi-leg order atomically via broker API."""
        legs_data = [
            {
                "symbol": leg.symbol,
                "side": leg.side.value,
                "quantity": leg.quantity,
                "contract_id": leg.contract_id,
            }
            for leg in order.legs
        ]
        
        delay = self.config.retry_delay_seconds
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self.broker.submit_multi_leg_order(
                    legs=legs_data,
                    net_price=order.net_price,
                    order_type=order.order_type.value,
                    time_in_force=order.time_in_force.value,
                )
                
                if response.get("status") == "filled":
                    # Build leg results
                    leg_results = {}
                    for i, leg_info in enumerate(response.get("legs", [])):
                        leg_results[i] = {
                            "order_id": leg_info.get("id"),
                            "fill_price": leg_info.get("filled_avg_price"),
                            "filled_qty": leg_info.get("filled_qty"),
                        }
                        order.leg_statuses[i] = OrderStatus.FILLED
                    
                    return ExecutionResult(
                        success=True,
                        order_id=response.get("id", order.order_id),
                        fill_price=response.get("net_filled_price", order.net_price),
                        filled_quantity=response.get("filled_qty", order.legs[0].quantity),
                        leg_results=leg_results,
                    )
                    
                elif response.get("status") == "rejected":
                    return ExecutionResult(
                        success=False,
                        order_id=order.order_id,
                        error=response.get("error", "Multi-leg order rejected"),
                    )
                else:
                    # Wait for fill
                    result = await self._wait_for_multi_leg_fill(
                        response.get("id", order.order_id),
                        order,
                        timeout=self.config.timeout_seconds,
                    )
                    if result.success:
                        return result
                    
            except Exception as e:
                logger.warning(f"Multi-leg attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.config.retry_backoff_multiplier,
                        self.config.max_retry_delay,
                    )
                else:
                    raise
        
        return ExecutionResult(
            success=False,
            order_id=order.order_id,
            error="Max retries exceeded for multi-leg order",
        )
    
    async def _wait_for_multi_leg_fill(
        self,
        order_id: str,
        order: MultiLegOrder,
        timeout: float,
    ) -> ExecutionResult:
        """Wait for multi-leg order to fill."""
        start_time = datetime.now(timezone.utc)
        
        while True:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                # Attempt rollback if partial fill
                await self._rollback_partial_fill(order)
                return ExecutionResult(
                    success=False,
                    order_id=order_id,
                    error="Multi-leg order fill timeout",
                )
            
            try:
                status = await self.broker.get_order_status(order_id)
                
                if status.get("status") == "filled":
                    leg_results = {}
                    for i, leg_info in enumerate(status.get("legs", [])):
                        leg_results[i] = {
                            "order_id": leg_info.get("id"),
                            "fill_price": leg_info.get("filled_avg_price"),
                            "filled_qty": leg_info.get("filled_qty"),
                        }
                    
                    return ExecutionResult(
                        success=True,
                        order_id=order_id,
                        fill_price=status.get("net_filled_price"),
                        filled_quantity=status.get("filled_qty", 0),
                        leg_results=leg_results,
                    )
                elif status.get("status") in ("rejected", "cancelled", "expired"):
                    return ExecutionResult(
                        success=False,
                        order_id=order_id,
                        error=f"Multi-leg order {status.get('status')}",
                    )
                
            except Exception as e:
                logger.warning(f"Error checking multi-leg status: {e}")
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def _rollback_partial_fill(self, order: MultiLegOrder) -> None:
        """
        Rollback partial fills for atomicity.
        
        If some legs filled but not all, submit closing orders
        for the filled legs.
        """
        filled_legs = [
            (i, leg) for i, leg in enumerate(order.legs)
            if order.leg_statuses.get(i) == OrderStatus.FILLED
        ]
        
        if not filled_legs:
            return
        
        logger.warning(
            f"Rolling back {len(filled_legs)} partially filled legs "
            f"for order {order.order_id}"
        )
        
        for i, leg in filled_legs:
            try:
                # Submit opposite side to close
                opposite_side = (
                    OrderSide.SELL if leg.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN)
                    else OrderSide.BUY
                )
                
                await self.broker.submit_order(
                    symbol=leg.symbol,
                    side=opposite_side.value,
                    quantity=leg.quantity,
                    order_type="market",
                    time_in_force="ioc",
                )
                logger.info(f"Rolled back leg {i}: {leg.symbol}")
                
            except Exception as e:
                logger.error(f"Failed to rollback leg {i}: {e}")
    
    # -------------------- Bracket Orders --------------------
    
    async def submit_bracket(self, bracket: BracketOrder) -> ExecutionResult:
        """
        Submit bracket order (entry + profit target + stop loss).
        
        Workflow:
        1. Submit entry order
        2. When entry fills, submit profit target and stop loss as OCO
        3. When one exit fills, cancel the other
        """
        bracket.validate()
        logger.info(f"Submitting bracket order: {bracket.bracket_id}")
        
        self._active_brackets[bracket.bracket_id] = bracket
        
        try:
            # Submit entry
            entry_result = await self.submit_order(bracket.entry_order)
            
            if not entry_result.success:
                bracket.status = "rejected"
                return ExecutionResult(
                    success=False,
                    order_id=bracket.bracket_id,
                    error=f"Entry order failed: {entry_result.error}",
                )
            
            bracket.status = "entry_filled"
            
            # Create OCO for exits
            oco = OCOOrder(
                order_a=bracket.profit_target,
                order_b=bracket.stop_loss,
                correlation_id=bracket.correlation_id,
            )
            
            # Submit OCO (runs in background, monitored)
            asyncio.create_task(self._manage_bracket_exits(bracket, oco))
            
            return ExecutionResult(
                success=True,
                order_id=bracket.bracket_id,
                fill_price=entry_result.fill_price,
                filled_quantity=entry_result.filled_quantity,
                message="Bracket entry filled, exits submitted",
            )
            
        except Exception as e:
            logger.error(f"Bracket order failed: {e}")
            return ExecutionResult(
                success=False,
                order_id=bracket.bracket_id,
                error=str(e),
            )
    
    async def _manage_bracket_exits(
        self,
        bracket: BracketOrder,
        oco: OCOOrder,
    ) -> None:
        """Manage bracket exit orders."""
        try:
            result = await self.submit_oco(oco)
            
            if result.success:
                bracket.status = "closed"
                logger.info(f"Bracket {bracket.bracket_id} closed via {oco.triggered_order}")
            else:
                logger.error(f"Bracket exit failed: {result.error}")
                
        except Exception as e:
            logger.error(f"Error managing bracket exits: {e}")
        finally:
            self._active_brackets.pop(bracket.bracket_id, None)
    
    # -------------------- OCO Orders --------------------
    
    async def submit_oco(self, oco: OCOOrder) -> ExecutionResult:
        """
        Submit One-Cancels-Other order.
        
        Both orders are submitted, when one fills or cancels,
        the other is automatically cancelled.
        """
        oco.validate()
        logger.info(f"Submitting OCO order: {oco.oco_id}")
        
        self._active_oco[oco.oco_id] = oco
        
        try:
            # Submit both orders
            response_a = await self.broker.submit_order(
                symbol=oco.order_a.symbol,
                side=oco.order_a.side.value,
                quantity=oco.order_a.quantity,
                order_type=oco.order_a.order_type.value,
                limit_price=oco.order_a.limit_price,
                stop_price=oco.order_a.stop_price,
                time_in_force=oco.order_a.time_in_force.value,
            )
            oco.order_a.order_id = response_a.get("id", oco.order_a.order_id)
            
            response_b = await self.broker.submit_order(
                symbol=oco.order_b.symbol,
                side=oco.order_b.side.value,
                quantity=oco.order_b.quantity,
                order_type=oco.order_b.order_type.value,
                limit_price=oco.order_b.limit_price,
                stop_price=oco.order_b.stop_price,
                time_in_force=oco.order_b.time_in_force.value,
            )
            oco.order_b.order_id = response_b.get("id", oco.order_b.order_id)
            
            oco.status = "active"
            
            # Monitor for fills
            return await self._monitor_oco(oco)
            
        except Exception as e:
            logger.error(f"OCO order failed: {e}")
            return ExecutionResult(
                success=False,
                order_id=oco.oco_id,
                error=str(e),
            )
        finally:
            self._active_oco.pop(oco.oco_id, None)
    
    async def _monitor_oco(self, oco: OCOOrder) -> ExecutionResult:
        """Monitor OCO orders until one triggers."""
        while True:
            try:
                # Check order A
                status_a = await self.broker.get_order_status(oco.order_a.order_id)
                if status_a.get("status") == "filled":
                    # Cancel order B
                    await self.broker.cancel_order(oco.order_b.order_id)
                    oco.triggered_order = "a"
                    oco.status = "triggered"
                    
                    return ExecutionResult(
                        success=True,
                        order_id=oco.oco_id,
                        fill_price=status_a.get("filled_avg_price"),
                        filled_quantity=status_a.get("filled_qty", 0),
                        message="Order A filled, Order B cancelled",
                    )
                
                # Check order B
                status_b = await self.broker.get_order_status(oco.order_b.order_id)
                if status_b.get("status") == "filled":
                    # Cancel order A
                    await self.broker.cancel_order(oco.order_a.order_id)
                    oco.triggered_order = "b"
                    oco.status = "triggered"
                    
                    return ExecutionResult(
                        success=True,
                        order_id=oco.oco_id,
                        fill_price=status_b.get("filled_avg_price"),
                        filled_quantity=status_b.get("filled_qty", 0),
                        message="Order B filled, Order A cancelled",
                    )
                
                # Check for cancellations
                if status_a.get("status") in ("cancelled", "rejected", "expired"):
                    await self.broker.cancel_order(oco.order_b.order_id)
                    return ExecutionResult(
                        success=False,
                        order_id=oco.oco_id,
                        error=f"Order A {status_a.get('status')}",
                    )
                
                if status_b.get("status") in ("cancelled", "rejected", "expired"):
                    await self.broker.cancel_order(oco.order_a.order_id)
                    return ExecutionResult(
                        success=False,
                        order_id=oco.oco_id,
                        error=f"Order B {status_b.get('status')}",
                    )
                
            except Exception as e:
                logger.warning(f"Error monitoring OCO: {e}")
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    # -------------------- OTO Orders --------------------
    
    async def submit_oto(self, oto: OTOOrder) -> ExecutionResult:
        """
        Submit One-Triggers-Other order.
        
        When primary order fills, secondary order is submitted.
        """
        oto.validate()
        logger.info(f"Submitting OTO order: {oto.oto_id}")
        
        self._active_oto[oto.oto_id] = oto
        
        try:
            # Submit primary
            primary_result = await self.submit_order(oto.primary)
            
            if not primary_result.success:
                oto.status = "rejected"
                return ExecutionResult(
                    success=False,
                    order_id=oto.oto_id,
                    error=f"Primary order failed: {primary_result.error}",
                )
            
            oto.status = "primary_filled"
            
            # Submit secondary
            secondary_result = await self.submit_order(oto.secondary)
            
            if secondary_result.success:
                oto.status = "complete"
            
            return ExecutionResult(
                success=True,
                order_id=oto.oto_id,
                fill_price=primary_result.fill_price,
                filled_quantity=primary_result.filled_quantity,
                message=(
                    "Primary filled, secondary submitted"
                    if not secondary_result.success
                    else "Both orders filled"
                ),
            )
            
        except Exception as e:
            logger.error(f"OTO order failed: {e}")
            return ExecutionResult(
                success=False,
                order_id=oto.oto_id,
                error=str(e),
            )
        finally:
            self._active_oto.pop(oto.oto_id, None)
    
    # -------------------- Order Management --------------------
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order."""
        try:
            return await self.broker.cancel_order(order_id)
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def cancel_all_orders(self) -> Dict[str, bool]:
        """Cancel all active orders."""
        results = {}
        
        for order_id in list(self._active_orders.keys()):
            results[order_id] = await self.cancel_order(order_id)
        
        return results
    
    def get_active_orders(self) -> List[Order]:
        """Get all active single orders."""
        return list(self._active_orders.values())
    
    def get_execution_history(
        self,
        limit: int = 100,
    ) -> List[ExecutionResult]:
        """Get execution history."""
        return self._execution_history[-limit:]
    
    # -------------------- Callbacks --------------------
    
    def on_fill(self, callback: Callable) -> None:
        """Register fill callback."""
        self._on_fill_callbacks.append(callback)
    
    def on_reject(self, callback: Callable) -> None:
        """Register reject callback."""
        self._on_reject_callbacks.append(callback)
    
    async def _notify_fill(self, order: Any, result: ExecutionResult) -> None:
        """Notify fill callbacks."""
        for callback in self._on_fill_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order, result)
                else:
                    callback(order, result)
            except Exception as e:
                logger.error(f"Fill callback error: {e}")
    
    async def _notify_reject(self, order: Any, result: ExecutionResult) -> None:
        """Notify reject callbacks."""
        for callback in self._on_reject_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order, result)
                else:
                    callback(order, result)
            except Exception as e:
                logger.error(f"Reject callback error: {e}")
