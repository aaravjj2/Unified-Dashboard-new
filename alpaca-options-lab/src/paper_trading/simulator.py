"""
Alpaca Options Lab - Order Simulator

Realistic order fill simulation:
- Slippage modeling
- Partial fills
- Latency simulation
- Fill probability
"""
from __future__ import annotations

import random
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SlippageModel(Enum):
    """Slippage model type."""
    FIXED = "fixed"  # Fixed basis points
    VOLUME_BASED = "volume_based"  # Larger orders = more slippage
    VOLATILITY_BASED = "volatility_based"  # Higher vol = more slippage
    MARKET_IMPACT = "market_impact"  # Square root market impact


@dataclass
class FillSimulation:
    """Result of fill simulation."""
    filled: bool = False
    fill_price: float = 0.0
    filled_quantity: float = 0.0
    slippage: float = 0.0
    slippage_bps: float = 0.0
    latency_ms: float = 0.0
    partial: bool = False
    
    # Details
    market_price: float = 0.0
    order_type: str = ""
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filled": self.filled,
            "fill_price": self.fill_price,
            "filled_quantity": self.filled_quantity,
            "slippage": self.slippage,
            "slippage_bps": self.slippage_bps,
            "latency_ms": self.latency_ms,
            "partial": self.partial,
            "market_price": self.market_price,
            "reason": self.reason,
        }


@dataclass
class SlippageConfig:
    """Slippage configuration."""
    model: SlippageModel = SlippageModel.FIXED
    base_bps: float = 5.0  # Base slippage in basis points
    
    # Volume-based parameters
    volume_impact: float = 0.1  # Impact per 1% of ADV
    
    # Volatility-based parameters
    vol_multiplier: float = 1.0
    
    # Market impact parameters
    impact_coefficient: float = 0.1
    
    # Limits
    max_slippage_bps: float = 50.0


@dataclass
class LatencyConfig:
    """Latency simulation configuration."""
    min_ms: float = 1.0
    max_ms: float = 10.0
    spike_probability: float = 0.01  # 1% chance of spike
    spike_multiplier: float = 10.0


class OrderSimulator:
    """
    Realistic order fill simulator.
    
    Features:
    - Multiple slippage models
    - Partial fills
    - Latency simulation
    - Fill probability
    """
    
    def __init__(
        self,
        slippage_bps: float = 5.0,
        fill_probability: float = 0.95,
        partial_fill_enabled: bool = True,
    ):
        # Configuration
        self.slippage_config = SlippageConfig(base_bps=slippage_bps)
        self.latency_config = LatencyConfig()
        self.fill_probability = fill_probability
        self.partial_fill_enabled = partial_fill_enabled
        
        # Symbol-specific overrides
        self._symbol_configs: Dict[str, SlippageConfig] = {}
        
        # Volume tracking for market impact
        self._daily_volumes: Dict[str, int] = {}
        self._order_volumes: Dict[str, int] = {}
        
        # Statistics
        self._fills: List[FillSimulation] = []
        self._total_slippage = 0.0
        
        logger.info("OrderSimulator initialized")
    
    # -------------------- Configuration --------------------
    
    def configure_symbol(
        self,
        symbol: str,
        config: SlippageConfig,
    ) -> None:
        """Configure slippage for specific symbol."""
        self._symbol_configs[symbol] = config
    
    def set_slippage_model(self, model: SlippageModel) -> None:
        """Set global slippage model."""
        self.slippage_config.model = model
    
    def set_daily_volume(self, symbol: str, volume: int) -> None:
        """Set average daily volume for symbol."""
        self._daily_volumes[symbol] = volume
    
    # -------------------- Fill Simulation --------------------
    
    async def simulate_fill(
        self,
        order,
        market_price: float,
        volatility: Optional[float] = None,
    ) -> FillSimulation:
        """
        Simulate order fill.
        
        Args:
            order: Order to simulate
            market_price: Current market price
            volatility: Current volatility (optional)
        
        Returns:
            FillSimulation with fill details
        """
        result = FillSimulation(
            market_price=market_price,
            order_type=order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
        )
        
        # Simulate latency
        latency = await self._simulate_latency()
        result.latency_ms = latency
        
        # Check fill probability
        if random.random() > self.fill_probability:
            result.filled = False
            result.reason = "Order not filled (random rejection)"
            return result
        
        # Get slippage config for symbol
        config = self._symbol_configs.get(order.symbol, self.slippage_config)
        
        # Calculate slippage
        slippage_bps = self._calculate_slippage(
            config=config,
            order=order,
            market_price=market_price,
            volatility=volatility,
        )
        
        # Apply slippage
        slippage = market_price * slippage_bps / 10000
        
        # Determine fill direction (adverse to order)
        if order.side.value == "buy":
            fill_price = market_price + slippage
        else:
            fill_price = market_price - slippage
        
        # Simulate partial fill
        filled_quantity = order.quantity
        partial = False
        
        if self.partial_fill_enabled and random.random() < 0.1:  # 10% partial fills
            fill_pct = random.uniform(0.3, 0.9)
            filled_quantity = int(order.quantity * fill_pct)
            partial = True
        
        result.filled = True
        result.fill_price = fill_price
        result.filled_quantity = filled_quantity
        result.slippage = abs(fill_price - market_price)
        result.slippage_bps = slippage_bps
        result.partial = partial
        result.reason = "Filled" if not partial else f"Partial fill ({filled_quantity}/{order.quantity})"
        
        # Track statistics
        self._fills.append(result)
        self._total_slippage += result.slippage * filled_quantity
        
        # Track order volume
        self._order_volumes[order.symbol] = (
            self._order_volumes.get(order.symbol, 0) + int(filled_quantity)
        )
        
        return result
    
    def _calculate_slippage(
        self,
        config: SlippageConfig,
        order,
        market_price: float,
        volatility: Optional[float],
    ) -> float:
        """Calculate slippage in basis points."""
        model = config.model
        
        if model == SlippageModel.FIXED:
            slippage_bps = config.base_bps
        
        elif model == SlippageModel.VOLUME_BASED:
            # Larger orders have more market impact
            adv = self._daily_volumes.get(order.symbol, 1000000)
            order_pct = (order.quantity * market_price) / (adv * market_price) * 100
            slippage_bps = config.base_bps * (1 + config.volume_impact * order_pct)
        
        elif model == SlippageModel.VOLATILITY_BASED:
            # Higher volatility = more slippage
            vol = volatility or 0.02
            slippage_bps = config.base_bps * (1 + config.vol_multiplier * vol * 10)
        
        elif model == SlippageModel.MARKET_IMPACT:
            # Square root market impact model
            adv = self._daily_volumes.get(order.symbol, 1000000)
            order_value = order.quantity * market_price
            participation_rate = order_value / (adv * market_price)
            
            impact = config.impact_coefficient * (participation_rate ** 0.5)
            slippage_bps = config.base_bps + impact * 10000
        
        else:
            slippage_bps = config.base_bps
        
        # Add random component
        slippage_bps *= random.uniform(0.8, 1.2)
        
        # Apply maximum
        slippage_bps = min(slippage_bps, config.max_slippage_bps)
        
        return slippage_bps
    
    async def _simulate_latency(self) -> float:
        """Simulate network/processing latency."""
        config = self.latency_config
        
        # Base latency
        latency = random.uniform(config.min_ms, config.max_ms)
        
        # Occasional spike
        if random.random() < config.spike_probability:
            latency *= config.spike_multiplier
        
        # Actually wait (optional, for realism)
        # await asyncio.sleep(latency / 1000)
        
        return latency
    
    # -------------------- Price Generation --------------------
    
    async def generate_price(
        self,
        symbol: str,
        base_price: Optional[float] = None,
        spread_bps: float = 10.0,
    ) -> float:
        """Generate a simulated price for a symbol."""
        # Use stored price or generate random
        if base_price is None:
            base_price = random.uniform(50, 200)
        
        # Add small random variation
        variation = random.uniform(-0.001, 0.001)
        price = base_price * (1 + variation)
        
        return price
    
    def generate_quote(
        self,
        symbol: str,
        mid_price: float,
        spread_bps: float = 10.0,
    ) -> Dict[str, float]:
        """Generate bid/ask quote."""
        spread = mid_price * spread_bps / 10000
        
        return {
            "bid": mid_price - spread / 2,
            "ask": mid_price + spread / 2,
            "mid": mid_price,
            "spread": spread,
        }
    
    # -------------------- Statistics --------------------
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        if not self._fills:
            return {"total_fills": 0}
        
        fills = self._fills
        filled = [f for f in fills if f.filled]
        partial = [f for f in fills if f.partial]
        
        avg_slippage = (
            sum(f.slippage_bps for f in filled) / len(filled)
            if filled else 0
        )
        
        avg_latency = (
            sum(f.latency_ms for f in fills) / len(fills)
            if fills else 0
        )
        
        return {
            "total_fills": len(fills),
            "successful_fills": len(filled),
            "partial_fills": len(partial),
            "fill_rate": len(filled) / len(fills) if fills else 0,
            "average_slippage_bps": avg_slippage,
            "total_slippage": self._total_slippage,
            "average_latency_ms": avg_latency,
            "order_volumes_by_symbol": dict(self._order_volumes),
        }
    
    def reset_statistics(self) -> None:
        """Reset simulation statistics."""
        self._fills.clear()
        self._total_slippage = 0.0
        self._order_volumes.clear()


class OptionsOrderSimulator(OrderSimulator):
    """
    Extended order simulator for options.
    
    Additional features:
    - Wider spreads for options
    - Delta-based slippage
    - Volatility surface awareness
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Options-specific defaults
        self.slippage_config.base_bps = 20.0  # Higher for options
        self.slippage_config.max_slippage_bps = 100.0
        
        # Delta impact
        self._delta_impact_enabled = True
        self._delta_multiplier = 2.0
    
    async def simulate_fill(
        self,
        order,
        market_price: float,
        volatility: Optional[float] = None,
        delta: Optional[float] = None,
    ) -> FillSimulation:
        """
        Simulate options order fill.
        
        Adds delta-based slippage adjustment.
        """
        # Adjust slippage based on delta
        if self._delta_impact_enabled and delta is not None:
            # ITM options (high delta) have tighter spreads
            # OTM options (low delta) have wider spreads
            abs_delta = abs(delta)
            
            if abs_delta < 0.2:  # Deep OTM
                self.slippage_config.base_bps *= 2.0
            elif abs_delta < 0.4:  # OTM
                self.slippage_config.base_bps *= 1.5
            elif abs_delta > 0.8:  # Deep ITM
                self.slippage_config.base_bps *= 0.8
        
        return await super().simulate_fill(order, market_price, volatility)
    
    def calculate_options_spread(
        self,
        underlying_price: float,
        strike: float,
        option_price: float,
        days_to_expiry: int,
        is_call: bool = True,
    ) -> float:
        """Calculate realistic options spread."""
        # Base spread
        spread_pct = 0.05  # 5% base spread
        
        # Moneyness adjustment
        if is_call:
            moneyness = underlying_price / strike
        else:
            moneyness = strike / underlying_price
        
        if moneyness < 0.9:  # Deep OTM
            spread_pct *= 2.5
        elif moneyness < 0.95:  # OTM
            spread_pct *= 1.5
        elif moneyness > 1.1:  # Deep ITM
            spread_pct *= 1.2
        
        # Time decay adjustment (nearer expiry = tighter spreads for ITM)
        if days_to_expiry < 7 and moneyness > 1.0:
            spread_pct *= 0.8
        elif days_to_expiry > 60:
            spread_pct *= 1.3
        
        # Minimum spread
        min_spread = 0.05  # $0.05 minimum
        spread = max(min_spread, option_price * spread_pct)
        
        return spread
