"""
Alpaca Options Lab - Market Data Feed

Market data simulation and management:
- Price feeds
- Quote generation
- Bar aggregation
- Real-time simulation
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class MarketDataSource(Enum):
    """Market data source."""
    SIMULATED = "simulated"
    ALPACA = "alpaca"
    POLYGON = "polygon"
    YAHOO = "yahoo"


@dataclass
class Quote:
    """Market quote."""
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
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
        if self.mid == 0:
            return 0.0
        return self.spread / self.mid * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "mid": self.mid,
            "spread": self.spread,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Trade:
    """Market trade."""
    symbol: str
    price: float
    size: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exchange: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "size": self.size,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
        }


@dataclass
class Bar:
    """OHLCV bar."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    trade_count: Optional[int] = None
    
    @property
    def range(self) -> float:
        """Price range."""
        return self.high - self.low
    
    @property
    def body(self) -> float:
        """Candle body size."""
        return abs(self.close - self.open)
    
    @property
    def is_green(self) -> bool:
        """Is bullish candle."""
        return self.close >= self.open
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "vwap": self.vwap,
        }


@dataclass
class SymbolConfig:
    """Configuration for simulated symbol."""
    symbol: str
    base_price: float
    volatility: float = 0.02  # Daily volatility (2%)
    spread_bps: float = 10.0  # Spread in basis points
    avg_volume: int = 1000000
    
    # Price drift
    drift: float = 0.0  # Daily drift (0% = random walk)
    
    # Mean reversion
    mean_reversion: float = 0.0  # 0 = none, 1 = full


class MarketDataFeed:
    """
    Market data feed for paper trading.
    
    Features:
    - Price simulation
    - Quote generation
    - Trade simulation
    - Bar aggregation
    """
    
    def __init__(self, source: MarketDataSource = MarketDataSource.SIMULATED):
        self.source = source
        
        # Symbol configurations
        self._configs: Dict[str, SymbolConfig] = {}
        
        # Current prices
        self._prices: Dict[str, float] = {}
        self._quotes: Dict[str, Quote] = {}
        self._last_trades: Dict[str, Trade] = {}
        
        # Bar history
        self._bars: Dict[str, List[Bar]] = {}
        self._bar_period = 60  # 1 minute bars
        self._current_bar: Dict[str, Bar] = {}
        
        # Subscriptions
        self._subscriptions: Set[str] = set()
        self._quote_handlers: List[Callable] = []
        self._trade_handlers: List[Callable] = []
        self._bar_handlers: List[Callable] = []
        
        # Simulation
        self._running = False
        self._sim_task: Optional[asyncio.Task] = None
        self._tick_interval = 0.1  # 100ms
        
        logger.info(f"MarketDataFeed initialized ({source.value})")
    
    # -------------------- Configuration --------------------
    
    def configure_symbol(
        self,
        symbol: str,
        base_price: float,
        volatility: float = 0.02,
        spread_bps: float = 10.0,
        **kwargs,
    ) -> None:
        """Configure symbol for simulation."""
        self._configs[symbol] = SymbolConfig(
            symbol=symbol,
            base_price=base_price,
            volatility=volatility,
            spread_bps=spread_bps,
            **kwargs,
        )
        self._prices[symbol] = base_price
        
        # Initialize bar
        self._bars[symbol] = []
        self._start_new_bar(symbol, base_price)
    
    def configure_symbols(self, configs: List[Dict[str, Any]]) -> None:
        """Configure multiple symbols."""
        for config in configs:
            self.configure_symbol(**config)
    
    # -------------------- Subscriptions --------------------
    
    def subscribe(self, symbols: List[str]) -> None:
        """Subscribe to symbols."""
        for symbol in symbols:
            self._subscriptions.add(symbol)
            
            # Auto-configure if not configured
            if symbol not in self._configs:
                self.configure_symbol(
                    symbol=symbol,
                    base_price=100.0 + random.uniform(-20, 20),
                )
    
    def unsubscribe(self, symbols: List[str]) -> None:
        """Unsubscribe from symbols."""
        for symbol in symbols:
            self._subscriptions.discard(symbol)
    
    def on_quote(self, handler: Callable) -> None:
        """Register quote handler."""
        self._quote_handlers.append(handler)
    
    def on_trade(self, handler: Callable) -> None:
        """Register trade handler."""
        self._trade_handlers.append(handler)
    
    def on_bar(self, handler: Callable) -> None:
        """Register bar handler."""
        self._bar_handlers.append(handler)
    
    # -------------------- Data Access --------------------
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Get last price for symbol."""
        return self._prices.get(symbol)
    
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current quote for symbol."""
        return self._quotes.get(symbol)
    
    def get_last_trade(self, symbol: str) -> Optional[Trade]:
        """Get last trade for symbol."""
        return self._last_trades.get(symbol)
    
    def get_bars(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[Bar]:
        """Get bar history for symbol."""
        bars = self._bars.get(symbol, [])
        return bars[-limit:]
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get all current prices."""
        return dict(self._prices)
    
    # -------------------- Lifecycle --------------------
    
    async def start(self) -> None:
        """Start market data feed."""
        if self._running:
            return
        
        self._running = True
        
        if self.source == MarketDataSource.SIMULATED:
            self._sim_task = asyncio.create_task(self._simulation_loop())
        
        logger.info("Market data feed started")
    
    async def stop(self) -> None:
        """Stop market data feed."""
        self._running = False
        
        if self._sim_task:
            self._sim_task.cancel()
            try:
                await self._sim_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Market data feed stopped")
    
    # -------------------- Simulation --------------------
    
    async def _simulation_loop(self) -> None:
        """Main simulation loop."""
        while self._running:
            try:
                # Generate ticks for all subscribed symbols
                for symbol in self._subscriptions:
                    await self._generate_tick(symbol)
                
                await asyncio.sleep(self._tick_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Simulation error: {e}")
    
    async def _generate_tick(self, symbol: str) -> None:
        """Generate a price tick for a symbol."""
        config = self._configs.get(symbol)
        if not config:
            return
        
        current_price = self._prices.get(symbol, config.base_price)
        
        # Generate price change using geometric Brownian motion
        dt = self._tick_interval / 86400  # Convert to daily fraction
        drift = config.drift * dt
        volatility = config.volatility * (dt ** 0.5)
        
        # Random component
        random_return = random.gauss(0, 1) * volatility
        
        # Mean reversion (optional)
        if config.mean_reversion > 0:
            reversion = config.mean_reversion * (config.base_price - current_price) / config.base_price * dt
            drift += reversion
        
        # New price
        new_price = current_price * (1 + drift + random_return)
        new_price = max(0.01, new_price)  # Floor at 1 cent
        
        self._prices[symbol] = new_price
        
        # Generate quote
        spread = new_price * config.spread_bps / 10000
        quote = Quote(
            symbol=symbol,
            bid=new_price - spread / 2,
            ask=new_price + spread / 2,
            bid_size=random.randint(100, 1000),
            ask_size=random.randint(100, 1000),
        )
        self._quotes[symbol] = quote
        
        # Generate trade (with probability)
        if random.random() < 0.3:  # 30% chance of trade per tick
            trade = Trade(
                symbol=symbol,
                price=new_price + random.uniform(-spread/4, spread/4),
                size=random.randint(10, 500),
            )
            self._last_trades[symbol] = trade
            
            # Update current bar
            self._update_bar(symbol, trade)
            
            # Notify trade handlers
            await self._notify_trade(trade)
        
        # Notify quote handlers
        await self._notify_quote(quote)
    
    def _start_new_bar(self, symbol: str, price: float) -> None:
        """Start a new bar."""
        now = datetime.now(timezone.utc)
        
        self._current_bar[symbol] = Bar(
            symbol=symbol,
            timestamp=now,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=0,
        )
    
    def _update_bar(self, symbol: str, trade: Trade) -> None:
        """Update current bar with trade."""
        bar = self._current_bar.get(symbol)
        if not bar:
            self._start_new_bar(symbol, trade.price)
            bar = self._current_bar[symbol]
        
        # Update OHLC
        bar.high = max(bar.high, trade.price)
        bar.low = min(bar.low, trade.price)
        bar.close = trade.price
        bar.volume += trade.size
        
        # Check if bar period is complete
        now = datetime.now(timezone.utc)
        bar_age = (now - bar.timestamp).total_seconds()
        
        if bar_age >= self._bar_period:
            # Finalize bar
            self._bars[symbol].append(bar)
            
            # Notify bar handlers
            asyncio.create_task(self._notify_bar(bar))
            
            # Start new bar
            self._start_new_bar(symbol, trade.price)
    
    # -------------------- Notifications --------------------
    
    async def _notify_quote(self, quote: Quote) -> None:
        """Notify quote handlers."""
        for handler in self._quote_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(quote)
                else:
                    handler(quote)
            except Exception as e:
                logger.error(f"Quote handler error: {e}")
    
    async def _notify_trade(self, trade: Trade) -> None:
        """Notify trade handlers."""
        for handler in self._trade_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(trade)
                else:
                    handler(trade)
            except Exception as e:
                logger.error(f"Trade handler error: {e}")
    
    async def _notify_bar(self, bar: Bar) -> None:
        """Notify bar handlers."""
        for handler in self._bar_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(bar)
                else:
                    handler(bar)
            except Exception as e:
                logger.error(f"Bar handler error: {e}")
    
    # -------------------- Utilities --------------------
    
    def set_price(self, symbol: str, price: float) -> None:
        """Manually set price (for testing)."""
        self._prices[symbol] = price
    
    def set_tick_interval(self, seconds: float) -> None:
        """Set simulation tick interval."""
        self._tick_interval = max(0.01, seconds)
    
    def set_bar_period(self, seconds: int) -> None:
        """Set bar aggregation period."""
        self._bar_period = max(1, seconds)
    
    def get_status(self) -> Dict[str, Any]:
        """Get feed status."""
        return {
            "source": self.source.value,
            "running": self._running,
            "subscribed_symbols": len(self._subscriptions),
            "configured_symbols": len(self._configs),
            "tick_interval": self._tick_interval,
            "bar_period": self._bar_period,
        }
