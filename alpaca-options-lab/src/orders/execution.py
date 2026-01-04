"""
Alpaca Options Lab - Execution Simulator

Paper trading execution simulator for testing strategies
without real money risk.

Features:
- Realistic fill simulation with slippage
- Latency modeling
- Partial fill simulation
- Market impact modeling
- Historical replay mode
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid

from src.orders.types import (
    Order, OrderStatus, OrderType, OrderSide, TimeInForce,
    MultiLegOrder, ExecutionResult, OrderLeg,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FillMode(Enum):
    """Fill simulation mode."""
    INSTANT = "instant"        # Immediate fill at limit
    REALISTIC = "realistic"    # Slippage and latency
    CONSERVATIVE = "conservative"  # Worst case fills
    RANDOM = "random"          # Random within spread


@dataclass
class SimulatorConfig:
    """Execution simulator configuration."""
    fill_mode: FillMode = FillMode.REALISTIC
    
    # Latency simulation (milliseconds)
    min_latency_ms: float = 10.0
    max_latency_ms: float = 100.0
    
    # Slippage simulation
    base_slippage_bps: float = 5.0  # 0.05%
    volatility_slippage_factor: float = 1.5
    
    # Fill probability
    fill_probability: float = 0.95
    partial_fill_probability: float = 0.1
    
    # Market impact
    enable_market_impact: bool = True
    impact_factor: float = 0.001  # Per 100 contracts
    
    # Spread simulation
    default_spread_bps: float = 10.0  # 0.1%
    
    # Commission (per contract)
    commission_per_contract: float = 0.65


@dataclass
class SimulatedQuote:
    """Simulated market quote."""
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    last: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def mid(self) -> float:
        """Mid price."""
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        """Bid-ask spread."""
        return self.ask - self.bid
    
    @property
    def spread_pct(self) -> float:
        """Spread as percentage of mid."""
        return (self.spread / self.mid) * 100 if self.mid > 0 else 0


class ExecutionSimulator:
    """
    Paper trading execution simulator.
    
    Simulates realistic order fills for testing strategies
    without real money.
    """
    
    def __init__(self, config: Optional[SimulatorConfig] = None):
        self.config = config or SimulatorConfig()
        
        # Quote cache for simulation
        self._quotes: Dict[str, SimulatedQuote] = {}
        
        # Order tracking
        self._orders: Dict[str, Order] = {}
        self._fills: List[ExecutionResult] = []
        
        # Position tracking
        self._positions: Dict[str, int] = {}  # symbol -> quantity
        self._cash: float = 100000.0  # Starting cash
        
        # Statistics
        self._total_orders: int = 0
        self._filled_orders: int = 0
        self._rejected_orders: int = 0
        self._total_commission: float = 0.0
        
        logger.info(f"ExecutionSimulator initialized: mode={self.config.fill_mode.value}")
    
    def set_cash(self, amount: float) -> None:
        """Set available cash."""
        self._cash = amount
    
    def update_quote(self, quote: SimulatedQuote) -> None:
        """Update quote for a symbol."""
        self._quotes[quote.symbol] = quote
    
    def set_quote(
        self,
        symbol: str,
        bid: float,
        ask: float,
        bid_size: int = 100,
        ask_size: int = 100,
    ) -> None:
        """Set quote for a symbol."""
        self._quotes[symbol] = SimulatedQuote(
            symbol=symbol,
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            last=(bid + ask) / 2,
        )
    
    def get_quote(self, symbol: str) -> Optional[SimulatedQuote]:
        """Get current quote for symbol."""
        return self._quotes.get(symbol)
    
    # -------------------- Single Order Simulation --------------------
    
    async def simulate_order(self, order: Order) -> ExecutionResult:
        """
        Simulate order execution.
        
        Returns:
            ExecutionResult with simulated fill details
        """
        self._total_orders += 1
        
        # Simulate network latency
        await self._simulate_latency()
        
        # Get quote
        quote = self._quotes.get(order.symbol)
        if not quote:
            # Generate synthetic quote from limit price
            quote = self._generate_synthetic_quote(order)
        
        # Validate order
        validation_result = self._validate_order(order, quote)
        if not validation_result[0]:
            self._rejected_orders += 1
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error=validation_result[1],
            )
        
        # Simulate fill
        fill_price, filled_qty = self._simulate_fill(order, quote)
        
        if fill_price is None:
            self._rejected_orders += 1
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error="Order not filled (price out of range)",
            )
        
        # Calculate commission
        commission = filled_qty * self.config.commission_per_contract
        self._total_commission += commission
        
        # Update position
        self._update_position(order, filled_qty, fill_price)
        
        self._filled_orders += 1
        
        result = ExecutionResult(
            success=True,
            order_id=order.order_id,
            fill_price=fill_price,
            filled_quantity=filled_qty,
            commission=commission,
            message=f"Simulated fill at {fill_price:.2f}",
        )
        
        self._fills.append(result)
        logger.info(
            f"Simulated fill: {order.symbol} {order.side.value} x{filled_qty} @ {fill_price:.2f}"
        )
        
        return result
    
    async def _simulate_latency(self) -> None:
        """Simulate network latency."""
        latency = random.uniform(
            self.config.min_latency_ms,
            self.config.max_latency_ms,
        ) / 1000.0  # Convert to seconds
        await asyncio.sleep(latency)
    
    def _generate_synthetic_quote(self, order: Order) -> SimulatedQuote:
        """Generate synthetic quote from order."""
        if order.limit_price:
            mid = order.limit_price
        else:
            mid = 1.0  # Default for market orders
        
        spread = mid * (self.config.default_spread_bps / 10000)
        
        return SimulatedQuote(
            symbol=order.symbol,
            bid=mid - spread / 2,
            ask=mid + spread / 2,
            bid_size=100,
            ask_size=100,
            last=mid,
        )
    
    def _validate_order(
        self,
        order: Order,
        quote: SimulatedQuote,
    ) -> Tuple[bool, str]:
        """Validate order can be filled."""
        # Check buying power
        if order.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN):
            cost = quote.ask * order.quantity * 100  # Options = 100 shares
            if cost > self._cash:
                return False, f"Insufficient buying power: need {cost:.2f}, have {self._cash:.2f}"
        
        # Check position for closing orders
        if order.side in (OrderSide.SELL_TO_CLOSE, OrderSide.BUY_TO_CLOSE):
            current_position = self._positions.get(order.symbol, 0)
            if order.side == OrderSide.SELL_TO_CLOSE and current_position < order.quantity:
                return False, f"Insufficient position to close: have {current_position}, need {order.quantity}"
        
        # Random rejection simulation
        if random.random() > self.config.fill_probability:
            return False, "Order randomly rejected (simulation)"
        
        return True, ""
    
    def _simulate_fill(
        self,
        order: Order,
        quote: SimulatedQuote,
    ) -> Tuple[Optional[float], int]:
        """
        Simulate fill price and quantity.
        
        Returns:
            (fill_price, filled_quantity) or (None, 0) if not filled
        """
        # Determine base price
        if order.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
            base_price = quote.ask
        else:
            base_price = quote.bid
        
        # Apply slippage based on mode
        if self.config.fill_mode == FillMode.INSTANT:
            fill_price = order.limit_price if order.limit_price else base_price
            
        elif self.config.fill_mode == FillMode.REALISTIC:
            slippage = self._calculate_slippage(order, quote)
            if order.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
                fill_price = base_price + slippage
            else:
                fill_price = base_price - slippage
                
        elif self.config.fill_mode == FillMode.CONSERVATIVE:
            # Worst case: full spread against you
            if order.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
                fill_price = quote.ask + quote.spread * 0.5
            else:
                fill_price = quote.bid - quote.spread * 0.5
                
        else:  # RANDOM
            fill_price = random.uniform(quote.bid, quote.ask)
        
        # Check limit price constraint
        if order.order_type == OrderType.LIMIT and order.limit_price:
            if order.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
                if fill_price > order.limit_price:
                    return None, 0  # Can't fill above limit
                fill_price = min(fill_price, order.limit_price)
            else:
                if fill_price < order.limit_price:
                    return None, 0  # Can't fill below limit
                fill_price = max(fill_price, order.limit_price)
        
        # Apply market impact
        if self.config.enable_market_impact:
            impact = self._calculate_market_impact(order, quote)
            if order.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
                fill_price += impact
            else:
                fill_price -= impact
        
        # Determine fill quantity
        if random.random() < self.config.partial_fill_probability:
            filled_qty = max(1, int(order.quantity * random.uniform(0.5, 0.9)))
        else:
            filled_qty = order.quantity
        
        return round(fill_price, 2), filled_qty
    
    def _calculate_slippage(self, order: Order, quote: SimulatedQuote) -> float:
        """Calculate slippage based on order size and volatility."""
        base_slippage = quote.mid * (self.config.base_slippage_bps / 10000)
        
        # Increase slippage for larger orders
        size_factor = min(2.0, 1 + order.quantity / 100)
        
        # Random component
        random_factor = random.uniform(0.5, 1.5)
        
        return base_slippage * size_factor * random_factor
    
    def _calculate_market_impact(self, order: Order, quote: SimulatedQuote) -> float:
        """Calculate market impact from order size."""
        # Impact increases with order size relative to available liquidity
        size = order.quantity
        liquidity = quote.bid_size if order.side in (OrderSide.SELL, OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE) else quote.ask_size
        
        if liquidity == 0:
            liquidity = 100
        
        impact_ratio = size / liquidity
        impact = quote.mid * self.config.impact_factor * impact_ratio
        
        return impact
    
    def _update_position(self, order: Order, filled_qty: int, fill_price: float) -> None:
        """Update position and cash after fill."""
        multiplier = 100  # Options contract multiplier
        
        if order.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN):
            self._positions[order.symbol] = self._positions.get(order.symbol, 0) + filled_qty
            self._cash -= filled_qty * fill_price * multiplier
            
        elif order.side == OrderSide.BUY_TO_CLOSE:
            self._positions[order.symbol] = self._positions.get(order.symbol, 0) + filled_qty
            self._cash -= filled_qty * fill_price * multiplier
            
        elif order.side in (OrderSide.SELL, OrderSide.SELL_TO_OPEN):
            self._positions[order.symbol] = self._positions.get(order.symbol, 0) - filled_qty
            self._cash += filled_qty * fill_price * multiplier
            
        elif order.side == OrderSide.SELL_TO_CLOSE:
            self._positions[order.symbol] = self._positions.get(order.symbol, 0) - filled_qty
            self._cash += filled_qty * fill_price * multiplier
    
    # -------------------- Multi-Leg Simulation --------------------
    
    async def simulate_multi_leg(self, order: MultiLegOrder) -> ExecutionResult:
        """
        Simulate multi-leg order execution.
        
        Simulates atomic execution of all legs.
        """
        self._total_orders += 1
        
        await self._simulate_latency()
        
        leg_results: Dict[int, Dict[str, Any]] = {}
        total_premium = 0.0
        total_commission = 0.0
        
        # Validate all legs first
        for i, leg in enumerate(order.legs):
            quote = self._quotes.get(leg.symbol)
            if not quote:
                quote = SimulatedQuote(
                    symbol=leg.symbol,
                    bid=abs(order.net_price) if order.net_price else 1.0,
                    ask=abs(order.net_price) * 1.01 if order.net_price else 1.01,
                    bid_size=100,
                    ask_size=100,
                    last=abs(order.net_price) if order.net_price else 1.0,
                )
            
            # Determine fill price for leg
            if leg.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
                fill_price = quote.ask * (1 + random.uniform(0, 0.02))
                premium = -fill_price * leg.quantity
            else:
                fill_price = quote.bid * (1 - random.uniform(0, 0.02))
                premium = fill_price * leg.quantity
            
            commission = leg.quantity * self.config.commission_per_contract
            
            leg_results[i] = {
                "order_id": str(uuid.uuid4())[:12],
                "fill_price": round(fill_price, 2),
                "filled_qty": leg.quantity,
                "commission": commission,
            }
            
            total_premium += premium
            total_commission += commission
            
            # Update position
            if leg.side in (OrderSide.BUY, OrderSide.BUY_TO_OPEN):
                self._positions[leg.symbol] = self._positions.get(leg.symbol, 0) + leg.quantity
            else:
                self._positions[leg.symbol] = self._positions.get(leg.symbol, 0) - leg.quantity
        
        # Update cash
        self._cash += total_premium * 100 - total_commission
        self._total_commission += total_commission
        self._filled_orders += 1
        
        result = ExecutionResult(
            success=True,
            order_id=order.order_id,
            fill_price=round(total_premium, 2),  # Net premium
            filled_quantity=order.legs[0].quantity,
            commission=total_commission,
            message=f"Multi-leg fill: {order.num_legs} legs",
            leg_results=leg_results,
        )
        
        self._fills.append(result)
        logger.info(f"Simulated multi-leg fill: {order.num_legs} legs, net={total_premium:.2f}")
        
        return result
    
    # -------------------- Statistics --------------------
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        fill_rate = (
            self._filled_orders / self._total_orders * 100
            if self._total_orders > 0 else 0
        )
        
        return {
            "total_orders": self._total_orders,
            "filled_orders": self._filled_orders,
            "rejected_orders": self._rejected_orders,
            "fill_rate_pct": round(fill_rate, 2),
            "total_commission": round(self._total_commission, 2),
            "current_cash": round(self._cash, 2),
            "open_positions": len([p for p in self._positions.values() if p != 0]),
        }
    
    def get_positions(self) -> Dict[str, int]:
        """Get current positions."""
        return {k: v for k, v in self._positions.items() if v != 0}
    
    def get_fills(self, limit: int = 100) -> List[ExecutionResult]:
        """Get recent fills."""
        return self._fills[-limit:]
    
    def reset(self) -> None:
        """Reset simulator state."""
        self._orders.clear()
        self._fills.clear()
        self._positions.clear()
        self._cash = 100000.0
        self._total_orders = 0
        self._filled_orders = 0
        self._rejected_orders = 0
        self._total_commission = 0.0
        logger.info("Execution simulator reset")


# -------------------- Broker API Implementation --------------------

class SimulatedBrokerAPI:
    """
    Simulated broker API for paper trading.
    
    Implements BrokerAPI protocol using ExecutionSimulator.
    """
    
    def __init__(self, simulator: Optional[ExecutionSimulator] = None):
        self.simulator = simulator or ExecutionSimulator()
    
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
        order = Order(
            contract_id=0,
            symbol=symbol,
            side=OrderSide(side),
            quantity=quantity,
            order_type=OrderType(order_type),
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=TimeInForce(time_in_force),
        )
        
        result = await self.simulator.simulate_order(order)
        
        return {
            "id": result.order_id,
            "status": "filled" if result.success else "rejected",
            "filled_avg_price": result.fill_price,
            "filled_qty": result.filled_quantity,
            "commission": result.commission,
            "error": result.error,
        }
    
    async def submit_multi_leg_order(
        self,
        legs: List[Dict[str, Any]],
        net_price: float,
        order_type: str,
        time_in_force: str = "day",
    ) -> Dict[str, Any]:
        """Submit a multi-leg order."""
        order_legs = [
            OrderLeg(
                contract_id=leg.get("contract_id", 0),
                symbol=leg["symbol"],
                side=OrderSide(leg["side"]),
                quantity=leg["quantity"],
            )
            for leg in legs
        ]
        
        order = MultiLegOrder(
            legs=order_legs,
            net_price=net_price,
            order_type=OrderType(order_type),
            time_in_force=TimeInForce(time_in_force),
        )
        
        result = await self.simulator.simulate_multi_leg(order)
        
        return {
            "id": result.order_id,
            "status": "filled" if result.success else "rejected",
            "net_filled_price": result.fill_price,
            "filled_qty": result.filled_quantity,
            "legs": [
                {
                    "id": leg_result.get("order_id"),
                    "filled_avg_price": leg_result.get("fill_price"),
                    "filled_qty": leg_result.get("filled_qty"),
                }
                for leg_result in result.leg_results.values()
            ],
            "error": result.error,
        }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        # In simulation, orders are instant
        return {
            "id": order_id,
            "status": "filled",
            "filled_avg_price": 0,
            "filled_qty": 0,
        }
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        # In simulation, orders are instant so nothing to cancel
        return True
