"""
Alpaca Options Lab - Execution Simulator

Production-grade execution simulation with:
- Realistic slippage models
- Partial fill simulation
- Volume-based impact
- Latency modeling

Slippage Models:
1. Fixed: Constant slippage percentage
2. Proportional: Slippage proportional to trade size
3. Volume Impact: Based on volume participation
4. Spread-based: Uses bid-ask spread

Usage:
    from src.backtesting.execution import ExecutionSimulator, SlippageModel
    
    simulator = ExecutionSimulator(
        slippage_model=SlippageModel.VOLUME_IMPACT,
        base_slippage=0.001,
        impact_factor=0.1,
    )
    
    fill = simulator.simulate_fill(
        symbol="AAPL240119C00150000",
        quantity=10,
        side="buy",
        market_data={"bid": 3.50, "ask": 3.60, "volume": 1000},
    )
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SlippageModel(Enum):
    """Types of slippage models."""
    NONE = "none"               # No slippage (unrealistic)
    FIXED = "fixed"             # Fixed percentage
    PROPORTIONAL = "proportional"  # Size-proportional
    VOLUME_IMPACT = "volume_impact"  # Market impact model
    SPREAD_BASED = "spread_based"  # Based on bid-ask spread


class FillModel(Enum):
    """Types of fill models."""
    IMMEDIATE = "immediate"     # Always filled immediately
    PROBABILISTIC = "probabilistic"  # Probability-based
    VOLUME_WEIGHTED = "volume_weighted"  # Based on volume


@dataclass
class Fill:
    """Represents an order fill."""
    order_id: str
    symbol: str
    quantity: int
    side: str  # 'buy' or 'sell'
    
    # Execution details
    fill_price: float
    fill_quantity: int
    slippage: float  # Actual slippage experienced
    commission: float
    
    # Market context
    market_bid: float = 0.0
    market_ask: float = 0.0
    market_volume: int = 0
    
    # Status
    is_partial: bool = False
    remaining_quantity: int = 0
    
    # Timing
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    latency_ms: float = 0.0
    
    @property
    def total_value(self) -> float:
        """Total fill value."""
        return self.fill_price * self.fill_quantity * 100  # Options multiplier
    
    @property
    def total_cost(self) -> float:
        """Total cost including commission."""
        base = self.total_value
        return base + self.commission if self.side == "buy" else base - self.commission
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "fill_price": round(self.fill_price, 4),
            "fill_quantity": self.fill_quantity,
            "slippage": round(self.slippage, 6),
            "commission": round(self.commission, 2),
            "is_partial": self.is_partial,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class MarketConditions:
    """Current market conditions for execution simulation."""
    bid: float
    ask: float
    mid: float
    spread: float
    spread_pct: float
    
    volume: int = 0
    avg_daily_volume: int = 0
    
    volatility: float = 0.0
    
    # Order book depth (optional)
    bid_size: int = 0
    ask_size: int = 0
    
    @classmethod
    def from_market_data(
        cls,
        data: Dict[str, Any],
    ) -> "MarketConditions":
        """Create from market data dict."""
        bid = data.get("bid", data.get("close", 0))
        ask = data.get("ask", data.get("close", 0))
        
        # Handle case where bid/ask not available
        if bid == 0 and ask == 0:
            close = data.get("close", 0)
            bid = close * 0.999
            ask = close * 1.001
        
        mid = (bid + ask) / 2
        spread = ask - bid
        spread_pct = spread / mid if mid > 0 else 0
        
        return cls(
            bid=bid,
            ask=ask,
            mid=mid,
            spread=spread,
            spread_pct=spread_pct,
            volume=data.get("volume", 0),
            avg_daily_volume=data.get("avg_volume", data.get("volume", 0)),
            volatility=data.get("iv", data.get("volatility", 0.3)),
            bid_size=data.get("bid_size", 0),
            ask_size=data.get("ask_size", 0),
        )


class ExecutionSimulator:
    """
    Realistic order execution simulator.
    
    Features:
    - Multiple slippage models
    - Market impact estimation
    - Partial fill simulation
    - Latency modeling
    - Commission calculation
    
    Slippage Calculation:
    - FIXED: base_slippage * price
    - PROPORTIONAL: base_slippage * sqrt(quantity / avg_volume)
    - VOLUME_IMPACT: impact_factor * (quantity / volume) ^ power
    - SPREAD_BASED: 0.5 * spread + slippage_factor * volatility
    
    Example:
        simulator = ExecutionSimulator(
            slippage_model=SlippageModel.VOLUME_IMPACT,
            base_slippage=0.001,
            commission_per_contract=0.65,
        )
        
        fill = simulator.simulate_fill(
            order_id="order_123",
            symbol="AAPL240119C00150000",
            quantity=10,
            side="buy",
            market_data={"bid": 3.50, "ask": 3.60, "volume": 500},
        )
    """
    
    def __init__(
        self,
        slippage_model: SlippageModel = SlippageModel.SPREAD_BASED,
        fill_model: FillModel = FillModel.IMMEDIATE,
        base_slippage: float = 0.001,
        impact_factor: float = 0.1,
        impact_power: float = 0.5,
        commission_per_contract: float = 0.65,
        min_commission: float = 0.0,
        latency_mean_ms: float = 50.0,
        latency_std_ms: float = 20.0,
        partial_fill_probability: float = 0.0,
        option_multiplier: int = 100,
    ) -> None:
        """
        Initialize execution simulator.
        
        Args:
            slippage_model: Type of slippage model to use
            fill_model: Type of fill model to use
            base_slippage: Base slippage percentage
            impact_factor: Market impact factor
            impact_power: Power for impact calculation (usually 0.5-1.0)
            commission_per_contract: Commission per option contract
            min_commission: Minimum commission per order
            latency_mean_ms: Mean execution latency in milliseconds
            latency_std_ms: Std dev of execution latency
            partial_fill_probability: Probability of partial fill
            option_multiplier: Option contract multiplier
        """
        self.slippage_model = slippage_model
        self.fill_model = fill_model
        self.base_slippage = base_slippage
        self.impact_factor = impact_factor
        self.impact_power = impact_power
        self.commission_per_contract = commission_per_contract
        self.min_commission = min_commission
        self.latency_mean_ms = latency_mean_ms
        self.latency_std_ms = latency_std_ms
        self.partial_fill_probability = partial_fill_probability
        self.option_multiplier = option_multiplier
        
        # Statistics
        self._total_fills = 0
        self._total_slippage = 0.0
        self._total_commission = 0.0
        
        logger.info(
            "ExecutionSimulator initialized",
            slippage_model=slippage_model.value,
            fill_model=fill_model.value,
        )
    
    def simulate_fill(
        self,
        order_id: str,
        symbol: str,
        quantity: int,
        side: str,
        market_data: Dict[str, Any],
        submitted_at: Optional[datetime] = None,
    ) -> Fill:
        """
        Simulate order execution.
        
        Args:
            order_id: Order identifier
            symbol: Instrument symbol
            quantity: Number of contracts
            side: 'buy' or 'sell'
            market_data: Current market data
            submitted_at: Order submission time
            
        Returns:
            Fill object with execution details
        """
        submitted_at = submitted_at or datetime.now(timezone.utc)
        
        # Parse market conditions
        conditions = MarketConditions.from_market_data(market_data)
        
        # Calculate latency
        latency_ms = max(0, random.gauss(self.latency_mean_ms, self.latency_std_ms))
        filled_at = submitted_at + timedelta(milliseconds=latency_ms)
        
        # Determine fill quantity
        fill_qty, is_partial = self._determine_fill_quantity(
            quantity,
            conditions,
        )
        
        # Calculate slippage
        slippage = self._calculate_slippage(
            quantity=fill_qty,
            side=side,
            conditions=conditions,
        )
        
        # Calculate fill price
        if side == "buy":
            base_price = conditions.ask
            fill_price = base_price + slippage
        else:
            base_price = conditions.bid
            fill_price = base_price - slippage
        
        # Ensure price is positive
        fill_price = max(0.01, fill_price)
        
        # Calculate commission
        commission = self._calculate_commission(fill_qty)
        
        # Update statistics
        self._total_fills += 1
        self._total_slippage += abs(slippage) * fill_qty
        self._total_commission += commission
        
        return Fill(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            side=side,
            fill_price=fill_price,
            fill_quantity=fill_qty,
            slippage=slippage,
            commission=commission,
            market_bid=conditions.bid,
            market_ask=conditions.ask,
            market_volume=conditions.volume,
            is_partial=is_partial,
            remaining_quantity=quantity - fill_qty,
            submitted_at=submitted_at,
            filled_at=filled_at,
            latency_ms=latency_ms,
        )
    
    def _calculate_slippage(
        self,
        quantity: int,
        side: str,
        conditions: MarketConditions,
    ) -> float:
        """Calculate slippage based on model."""
        if self.slippage_model == SlippageModel.NONE:
            return 0.0
        
        elif self.slippage_model == SlippageModel.FIXED:
            return conditions.mid * self.base_slippage
        
        elif self.slippage_model == SlippageModel.PROPORTIONAL:
            # Slippage increases with sqrt of participation rate
            adv = max(conditions.avg_daily_volume, 1)
            participation = quantity / adv
            size_factor = (participation ** 0.5) if participation < 1 else participation
            return conditions.mid * self.base_slippage * (1 + size_factor)
        
        elif self.slippage_model == SlippageModel.VOLUME_IMPACT:
            # Market impact model
            volume = max(conditions.volume, 1)
            impact = self.impact_factor * ((quantity / volume) ** self.impact_power)
            return conditions.mid * impact
        
        elif self.slippage_model == SlippageModel.SPREAD_BASED:
            # Half spread + volatility-based component
            half_spread = conditions.spread / 2
            vol_component = conditions.mid * conditions.volatility * 0.01
            return half_spread + vol_component
        
        return 0.0
    
    def _determine_fill_quantity(
        self,
        quantity: int,
        conditions: MarketConditions,
    ) -> Tuple[int, bool]:
        """Determine actual fill quantity."""
        if self.fill_model == FillModel.IMMEDIATE:
            return quantity, False
        
        elif self.fill_model == FillModel.PROBABILISTIC:
            if random.random() < self.partial_fill_probability:
                # Random partial fill (50-99% of order)
                fill_pct = random.uniform(0.5, 0.99)
                fill_qty = max(1, int(quantity * fill_pct))
                return fill_qty, True
            return quantity, False
        
        elif self.fill_model == FillModel.VOLUME_WEIGHTED:
            # Limit fill to available volume
            if conditions.volume > 0:
                max_fill = max(1, int(conditions.volume * 0.1))  # Max 10% of volume
                fill_qty = min(quantity, max_fill)
                return fill_qty, fill_qty < quantity
            return quantity, False
        
        return quantity, False
    
    def _calculate_commission(self, quantity: int) -> float:
        """Calculate commission for trade."""
        commission = quantity * self.commission_per_contract
        return max(commission, self.min_commission)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        avg_slippage = (
            self._total_slippage / self._total_fills
            if self._total_fills > 0 else 0
        )
        avg_commission = (
            self._total_commission / self._total_fills
            if self._total_fills > 0 else 0
        )
        
        return {
            "total_fills": self._total_fills,
            "total_slippage": round(self._total_slippage, 4),
            "average_slippage": round(avg_slippage, 6),
            "total_commission": round(self._total_commission, 2),
            "average_commission": round(avg_commission, 4),
        }
    
    def reset_statistics(self) -> None:
        """Reset execution statistics."""
        self._total_fills = 0
        self._total_slippage = 0.0
        self._total_commission = 0.0


class OrderBookSimulator:
    """
    Simulates order book for more realistic execution.
    
    Models bid/ask depth and order queue position.
    """
    
    def __init__(
        self,
        levels: int = 5,
        base_size: int = 100,
        size_decay: float = 0.8,
        tick_size: float = 0.01,
    ) -> None:
        """
        Initialize order book simulator.
        
        Args:
            levels: Number of price levels to simulate
            base_size: Size at best bid/ask
            size_decay: Size decay factor per level
            tick_size: Minimum price increment
        """
        self.levels = levels
        self.base_size = base_size
        self.size_decay = size_decay
        self.tick_size = tick_size
    
    def generate_book(
        self,
        mid_price: float,
        spread: float,
    ) -> Dict[str, List[Tuple[float, int]]]:
        """
        Generate simulated order book.
        
        Returns:
            Dict with 'bids' and 'asks', each a list of (price, size) tuples
        """
        half_spread = spread / 2
        best_bid = mid_price - half_spread
        best_ask = mid_price + half_spread
        
        bids = []
        asks = []
        
        for i in range(self.levels):
            size = int(self.base_size * (self.size_decay ** i))
            size = max(1, size + random.randint(-size//4, size//4))
            
            bid_price = best_bid - i * self.tick_size
            ask_price = best_ask + i * self.tick_size
            
            bids.append((round(bid_price, 2), size))
            asks.append((round(ask_price, 2), size))
        
        return {"bids": bids, "asks": asks}
    
    def estimate_fill_price(
        self,
        book: Dict[str, List[Tuple[float, int]]],
        quantity: int,
        side: str,
    ) -> Tuple[float, int]:
        """
        Estimate fill price walking the book.
        
        Returns:
            Tuple of (average_fill_price, filled_quantity)
        """
        levels = book["asks"] if side == "buy" else book["bids"]
        
        remaining = quantity
        total_value = 0.0
        filled = 0
        
        for price, size in levels:
            fill_at_level = min(remaining, size)
            total_value += price * fill_at_level
            filled += fill_at_level
            remaining -= fill_at_level
            
            if remaining <= 0:
                break
        
        if filled > 0:
            avg_price = total_value / filled
            return avg_price, filled
        
        # No fills possible
        return 0.0, 0
