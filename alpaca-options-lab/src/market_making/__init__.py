"""
Market Making Engine

High-frequency market making for options:
- Two-sided quoting with dynamic spreads
- Inventory management
- Greeks-based pricing
- Risk controls
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import time

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class QuoteState(Enum):
    """State of a quote"""
    ACTIVE = "active"
    PENDING = "pending"
    CANCELLED = "cancelled"
    FILLED = "filled"
    PARTIAL = "partial"


@dataclass
class Quote:
    """Represents a market making quote"""
    id: str
    symbol: str
    side: str  # bid, ask
    price: float
    quantity: int
    state: QuoteState
    created_at: datetime
    updated_at: datetime
    fills: List[Dict] = field(default_factory=list)
    
    @property
    def filled_quantity(self) -> int:
        return sum(f["quantity"] for f in self.fills)
        
    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity


@dataclass
class Instrument:
    """Option instrument being quoted"""
    symbol: str
    underlying: str
    strike: float
    expiry: str
    option_type: str  # call, put
    multiplier: int = 100
    
    # Greeks
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    
    # Market data
    bid: float = 0.0
    ask: float = 0.0
    mid: float = 0.0
    last: float = 0.0
    volume: int = 0
    open_interest: int = 0


@dataclass
class InventoryPosition:
    """Market maker inventory position"""
    symbol: str
    quantity: int
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float
    
    # Greeks exposure from this position
    delta_exposure: float = 0.0
    gamma_exposure: float = 0.0
    theta_exposure: float = 0.0
    vega_exposure: float = 0.0


class SpreadCalculator:
    """
    Calculates optimal bid-ask spreads based on market conditions.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Base spread parameters
        self.min_spread_bps = self.config.get("min_spread_bps", 50)  # 0.5%
        self.max_spread_bps = self.config.get("max_spread_bps", 500)  # 5%
        self.base_spread_bps = self.config.get("base_spread_bps", 100)  # 1%
        
        # Adjustment factors
        self.volatility_factor = self.config.get("volatility_factor", 0.5)
        self.inventory_factor = self.config.get("inventory_factor", 0.3)
        self.time_decay_factor = self.config.get("time_decay_factor", 0.2)
        
    def calculate_spread(
        self,
        instrument: Instrument,
        inventory: int,
        max_inventory: int,
        market_volatility: float,
    ) -> Tuple[float, float]:
        """
        Calculate optimal bid and ask spread.
        
        Returns:
            Tuple of (bid_spread, ask_spread) in dollars
        """
        mid_price = instrument.mid or (instrument.bid + instrument.ask) / 2
        if mid_price <= 0:
            return 0.05, 0.05  # Default minimum
            
        # Base spread
        spread_bps = self.base_spread_bps
        
        # Volatility adjustment
        # Higher volatility = wider spread
        vol_adjustment = market_volatility * self.volatility_factor * 100
        spread_bps += vol_adjustment
        
        # Inventory adjustment
        # Skew spread based on inventory
        inventory_ratio = inventory / max_inventory if max_inventory > 0 else 0
        inventory_skew = abs(inventory_ratio) * self.inventory_factor * 100
        spread_bps += inventory_skew
        
        # Time decay adjustment for near-expiry options
        # (Would need DTE information)
        
        # Clamp to bounds
        spread_bps = max(self.min_spread_bps, min(self.max_spread_bps, spread_bps))
        
        # Convert to dollar spread
        half_spread = mid_price * (spread_bps / 10000) / 2
        
        # Apply inventory skew
        # If long inventory, tighten ask / widen bid
        # If short inventory, tighten bid / widen ask
        skew_factor = inventory_ratio * 0.3
        bid_spread = half_spread * (1 + skew_factor)
        ask_spread = half_spread * (1 - skew_factor)
        
        # Minimum spread
        min_spread = 0.01  # $0.01 minimum
        bid_spread = max(min_spread, bid_spread)
        ask_spread = max(min_spread, ask_spread)
        
        return bid_spread, ask_spread
        
    def calculate_fair_value(
        self,
        instrument: Instrument,
        theoretical_price: float,
        inventory: int,
    ) -> float:
        """
        Calculate fair value incorporating inventory risk.
        """
        # Start with theoretical price
        fair_value = theoretical_price
        
        # Adjust for inventory risk
        # If long, lower fair value to encourage sells
        # If short, raise fair value to encourage buys
        inventory_adjustment = -inventory * instrument.delta * 0.001
        fair_value += inventory_adjustment
        
        return fair_value


class InventoryManager:
    """
    Manages market maker inventory and risk limits.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.positions: Dict[str, InventoryPosition] = {}
        
        # Risk limits
        self.max_position_size = self.config.get("max_position_size", 100)
        self.max_delta_exposure = self.config.get("max_delta_exposure", 500)
        self.max_gamma_exposure = self.config.get("max_gamma_exposure", 50)
        self.max_vega_exposure = self.config.get("max_vega_exposure", 5000)
        self.max_daily_loss = self.config.get("max_daily_loss", 5000)
        
        # Tracking
        self.daily_pnl = 0.0
        self.total_delta = 0.0
        self.total_gamma = 0.0
        self.total_vega = 0.0
        
    def update_position(
        self,
        symbol: str,
        quantity_change: int,
        price: float,
        instrument: Optional[Instrument] = None,
    ):
        """
        Update inventory position after a fill.
        """
        if symbol not in self.positions:
            self.positions[symbol] = InventoryPosition(
                symbol=symbol,
                quantity=0,
                avg_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
            )
            
        pos = self.positions[symbol]
        old_quantity = pos.quantity
        new_quantity = old_quantity + quantity_change
        
        # Update average price
        if quantity_change > 0:
            # Buying - update avg price
            if new_quantity > 0:
                pos.avg_price = (
                    (pos.avg_price * old_quantity + price * quantity_change) /
                    new_quantity
                )
        elif quantity_change < 0:
            # Selling - realize P&L
            realized = abs(quantity_change) * (price - pos.avg_price) * 100
            pos.realized_pnl += realized
            self.daily_pnl += realized
            
        pos.quantity = new_quantity
        
        # Update Greeks exposure
        if instrument:
            pos.delta_exposure = pos.quantity * instrument.delta * 100
            pos.gamma_exposure = pos.quantity * instrument.gamma * 100
            pos.theta_exposure = pos.quantity * instrument.theta * 100
            pos.vega_exposure = pos.quantity * instrument.vega * 100
            
        # Recalculate totals
        self._recalculate_totals()
        
        logger.info(
            "inventory_updated",
            symbol=symbol,
            quantity=new_quantity,
            avg_price=pos.avg_price,
        )
        
    def _recalculate_totals(self):
        """Recalculate total Greeks exposure"""
        self.total_delta = sum(p.delta_exposure for p in self.positions.values())
        self.total_gamma = sum(p.gamma_exposure for p in self.positions.values())
        self.total_vega = sum(p.vega_exposure for p in self.positions.values())
        
    def check_limits(
        self,
        symbol: str,
        side: str,
        quantity: int,
        instrument: Optional[Instrument] = None,
    ) -> Tuple[bool, str]:
        """
        Check if a trade would violate risk limits.
        
        Returns:
            Tuple of (allowed, reason)
        """
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            return False, "Daily loss limit reached"
            
        # Get current position
        current = self.positions.get(symbol, InventoryPosition(
            symbol=symbol, quantity=0, avg_price=0, unrealized_pnl=0, realized_pnl=0
        ))
        
        # Calculate new position
        if side == "bid":  # Buying
            new_quantity = current.quantity + quantity
        else:  # Selling
            new_quantity = current.quantity - quantity
            
        # Check position size
        if abs(new_quantity) > self.max_position_size:
            return False, f"Would exceed max position size ({self.max_position_size})"
            
        # Check delta exposure
        if instrument:
            new_delta = self.total_delta + (quantity if side == "bid" else -quantity) * instrument.delta * 100
            if abs(new_delta) > self.max_delta_exposure:
                return False, f"Would exceed delta limit ({self.max_delta_exposure})"
                
        return True, "OK"
        
    def get_position_summary(self) -> Dict:
        """Get inventory summary"""
        return {
            "positions": len(self.positions),
            "total_delta": round(self.total_delta, 2),
            "total_gamma": round(self.total_gamma, 2),
            "total_vega": round(self.total_vega, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "limit_utilization": {
                "delta": abs(self.total_delta) / self.max_delta_exposure,
                "gamma": abs(self.total_gamma) / self.max_gamma_exposure,
                "vega": abs(self.total_vega) / self.max_vega_exposure,
            },
        }


class MarketMakingEngine:
    """
    Main market making engine for options.
    
    Features:
    - Two-sided quoting
    - Dynamic spread calculation
    - Inventory management
    - Risk controls
    - Quote management
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Components
        self.spread_calculator = SpreadCalculator(config)
        self.inventory_manager = InventoryManager(config)
        
        # Quote tracking
        self.active_quotes: Dict[str, Dict[str, Quote]] = {}  # symbol -> {bid/ask -> Quote}
        self.quote_history: deque = deque(maxlen=10000)
        
        # Instruments being quoted
        self.instruments: Dict[str, Instrument] = {}
        
        # Performance tracking
        self.stats = {
            "quotes_sent": 0,
            "quotes_filled": 0,
            "quotes_cancelled": 0,
            "total_volume": 0,
            "realized_pnl": 0.0,
        }
        
        # State
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        
        # Callbacks
        self._on_quote_update: Optional[Callable] = None
        self._on_fill: Optional[Callable] = None
        
        # Configuration
        self.quote_refresh_ms = self.config.get("quote_refresh_ms", 100)
        self.max_instruments = self.config.get("max_instruments", 20)
        
    async def start(self):
        """Start the market making engine"""
        logger.info("market_making_engine_starting")
        self._running = True
        self._tasks["quote_manager"] = asyncio.create_task(self._quote_manager_loop())
        self._tasks["risk_monitor"] = asyncio.create_task(self._risk_monitor_loop())
        logger.info("market_making_engine_started")
        
    async def stop(self):
        """Stop the market making engine"""
        logger.info("market_making_engine_stopping")
        self._running = False
        
        # Cancel all active quotes
        for symbol in list(self.active_quotes.keys()):
            await self.cancel_quotes(symbol)
            
        # Cancel tasks
        for task in self._tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        logger.info("market_making_engine_stopped")
        
    async def add_instrument(self, instrument: Instrument):
        """Add instrument to quote"""
        if len(self.instruments) >= self.max_instruments:
            logger.warning("max_instruments_reached")
            return
            
        self.instruments[instrument.symbol] = instrument
        self.active_quotes[instrument.symbol] = {}
        
        logger.info(
            "instrument_added",
            symbol=instrument.symbol,
            underlying=instrument.underlying,
        )
        
    async def remove_instrument(self, symbol: str):
        """Remove instrument from quoting"""
        await self.cancel_quotes(symbol)
        
        if symbol in self.instruments:
            del self.instruments[symbol]
        if symbol in self.active_quotes:
            del self.active_quotes[symbol]
            
        logger.info("instrument_removed", symbol=symbol)
        
    async def update_market_data(
        self,
        symbol: str,
        bid: float,
        ask: float,
        last: float,
        volume: int,
    ):
        """Update market data for an instrument"""
        if symbol not in self.instruments:
            return
            
        inst = self.instruments[symbol]
        inst.bid = bid
        inst.ask = ask
        inst.mid = (bid + ask) / 2
        inst.last = last
        inst.volume = volume
        
    async def update_greeks(
        self,
        symbol: str,
        delta: float,
        gamma: float,
        theta: float,
        vega: float,
    ):
        """Update Greeks for an instrument"""
        if symbol not in self.instruments:
            return
            
        inst = self.instruments[symbol]
        inst.delta = delta
        inst.gamma = gamma
        inst.theta = theta
        inst.vega = vega
        
    async def _quote_manager_loop(self):
        """Main quote management loop"""
        while self._running:
            try:
                start_time = time.time()
                
                for symbol, instrument in list(self.instruments.items()):
                    await self._update_quotes(symbol, instrument)
                    
                # Rate limit
                elapsed = (time.time() - start_time) * 1000
                if elapsed < self.quote_refresh_ms:
                    await asyncio.sleep((self.quote_refresh_ms - elapsed) / 1000)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("quote_manager_error", error=str(e))
                await asyncio.sleep(1)
                
    async def _update_quotes(self, symbol: str, instrument: Instrument):
        """Update quotes for a single instrument"""
        # Get current inventory
        position = self.inventory_manager.positions.get(symbol)
        inventory = position.quantity if position else 0
        
        # Calculate spreads
        bid_spread, ask_spread = self.spread_calculator.calculate_spread(
            instrument=instrument,
            inventory=inventory,
            max_inventory=self.inventory_manager.max_position_size,
            market_volatility=0.20,  # Would come from market data
        )
        
        # Calculate quote prices
        mid = instrument.mid or (instrument.bid + instrument.ask) / 2
        if mid <= 0:
            return
            
        bid_price = round(mid - bid_spread, 2)
        ask_price = round(mid + ask_spread, 2)
        
        # Ensure positive prices
        bid_price = max(0.01, bid_price)
        ask_price = max(bid_price + 0.01, ask_price)
        
        # Calculate quantities based on risk limits
        bid_allowed, _ = self.inventory_manager.check_limits(
            symbol, "bid", 10, instrument
        )
        ask_allowed, _ = self.inventory_manager.check_limits(
            symbol, "ask", 10, instrument
        )
        
        bid_qty = 10 if bid_allowed else 0
        ask_qty = 10 if ask_allowed else 0
        
        # Update or create quotes
        current_quotes = self.active_quotes[symbol]
        
        if bid_qty > 0:
            if "bid" in current_quotes:
                old_quote = current_quotes["bid"]
                if abs(old_quote.price - bid_price) > 0.01:
                    await self._modify_quote(old_quote, bid_price, bid_qty)
            else:
                await self._send_quote(symbol, "bid", bid_price, bid_qty)
        else:
            if "bid" in current_quotes:
                await self._cancel_quote(current_quotes["bid"])
                
        if ask_qty > 0:
            if "ask" in current_quotes:
                old_quote = current_quotes["ask"]
                if abs(old_quote.price - ask_price) > 0.01:
                    await self._modify_quote(old_quote, ask_price, ask_qty)
            else:
                await self._send_quote(symbol, "ask", ask_price, ask_qty)
        else:
            if "ask" in current_quotes:
                await self._cancel_quote(current_quotes["ask"])
                
    async def _send_quote(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: int,
    ):
        """Send a new quote"""
        quote_id = f"q_{symbol}_{side}_{time.time():.0f}"
        
        quote = Quote(
            id=quote_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            state=QuoteState.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # In production, this would send to exchange
        # await self.exchange.send_order(...)
        
        self.active_quotes[symbol][side] = quote
        self.stats["quotes_sent"] += 1
        
        if self._on_quote_update:
            await self._on_quote_update(quote)
            
        logger.debug(
            "quote_sent",
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
        )
        
    async def _modify_quote(self, quote: Quote, new_price: float, new_quantity: int):
        """Modify an existing quote"""
        quote.price = new_price
        quote.quantity = new_quantity
        quote.updated_at = datetime.now(timezone.utc)
        
        # In production: await self.exchange.modify_order(...)
        
        if self._on_quote_update:
            await self._on_quote_update(quote)
            
    async def _cancel_quote(self, quote: Quote):
        """Cancel a quote"""
        quote.state = QuoteState.CANCELLED
        quote.updated_at = datetime.now(timezone.utc)
        
        # In production: await self.exchange.cancel_order(...)
        
        if quote.symbol in self.active_quotes:
            if quote.side in self.active_quotes[quote.symbol]:
                del self.active_quotes[quote.symbol][quote.side]
                
        self.stats["quotes_cancelled"] += 1
        self.quote_history.append(quote)
        
    async def cancel_quotes(self, symbol: str):
        """Cancel all quotes for a symbol"""
        if symbol not in self.active_quotes:
            return
            
        for side, quote in list(self.active_quotes[symbol].items()):
            await self._cancel_quote(quote)
            
    async def handle_fill(
        self,
        quote_id: str,
        fill_price: float,
        fill_quantity: int,
    ):
        """Handle a quote fill"""
        # Find the quote
        quote = None
        for symbol_quotes in self.active_quotes.values():
            for q in symbol_quotes.values():
                if q.id == quote_id:
                    quote = q
                    break
                    
        if not quote:
            logger.warning("fill_for_unknown_quote", quote_id=quote_id)
            return
            
        # Record fill
        quote.fills.append({
            "price": fill_price,
            "quantity": fill_quantity,
            "time": datetime.now(timezone.utc),
        })
        
        # Update inventory
        quantity_change = fill_quantity if quote.side == "bid" else -fill_quantity
        instrument = self.instruments.get(quote.symbol)
        
        self.inventory_manager.update_position(
            symbol=quote.symbol,
            quantity_change=quantity_change,
            price=fill_price,
            instrument=instrument,
        )
        
        # Update quote state
        if quote.remaining_quantity <= 0:
            quote.state = QuoteState.FILLED
            if quote.symbol in self.active_quotes:
                if quote.side in self.active_quotes[quote.symbol]:
                    del self.active_quotes[quote.symbol][quote.side]
            self.quote_history.append(quote)
        else:
            quote.state = QuoteState.PARTIAL
            
        # Update stats
        self.stats["quotes_filled"] += 1
        self.stats["total_volume"] += fill_quantity
        self.stats["realized_pnl"] = self.inventory_manager.daily_pnl
        
        if self._on_fill:
            await self._on_fill(quote, fill_price, fill_quantity)
            
        logger.info(
            "quote_filled",
            quote_id=quote_id,
            symbol=quote.symbol,
            side=quote.side,
            price=fill_price,
            quantity=fill_quantity,
        )
        
    async def _risk_monitor_loop(self):
        """Monitor risk limits"""
        while self._running:
            try:
                summary = self.inventory_manager.get_position_summary()
                
                # Check limit utilization
                for limit_name, utilization in summary["limit_utilization"].items():
                    if utilization > 0.8:
                        logger.warning(
                            "limit_warning",
                            limit=limit_name,
                            utilization=utilization,
                        )
                        
                # Check daily P&L
                if summary["daily_pnl"] <= -self.inventory_manager.max_daily_loss * 0.8:
                    logger.warning(
                        "daily_loss_warning",
                        pnl=summary["daily_pnl"],
                        limit=-self.inventory_manager.max_daily_loss,
                    )
                    
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("risk_monitor_error", error=str(e))
                await asyncio.sleep(5)
                
    def get_stats(self) -> Dict:
        """Get engine statistics"""
        return {
            **self.stats,
            "active_quotes": sum(
                len(quotes) for quotes in self.active_quotes.values()
            ),
            "instruments": len(self.instruments),
            "inventory": self.inventory_manager.get_position_summary(),
        }
        
    def set_callbacks(
        self,
        on_quote_update: Optional[Callable] = None,
        on_fill: Optional[Callable] = None,
    ):
        """Set event callbacks"""
        self._on_quote_update = on_quote_update
        self._on_fill = on_fill


# Singleton instance
market_making_engine = MarketMakingEngine()
