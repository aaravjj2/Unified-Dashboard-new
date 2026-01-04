"""
Alpaca Options Lab - Paper Trading Engine

Main orchestrator for paper trading:
- Strategy execution
- Order management
- Portfolio tracking
- Performance monitoring
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TradingMode(Enum):
    """Trading mode."""
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"


class EngineState(Enum):
    """Engine state."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class EngineConfig:
    """Engine configuration."""
    # Trading mode
    mode: TradingMode = TradingMode.PAPER
    
    # Initial capital
    initial_capital: float = 100000.0
    
    # Trading hours (EST)
    market_open: time = time(9, 30)
    market_close: time = time(16, 0)
    extended_hours: bool = False
    
    # Risk limits
    max_position_size: float = 10000.0
    max_daily_loss: float = 5000.0
    max_positions: int = 20
    
    # Order settings
    default_slippage_bps: float = 5.0  # Basis points
    fill_probability: float = 0.95
    partial_fill_enabled: bool = True
    
    # Performance
    update_interval_ms: int = 100
    
    # Persistence
    persist_trades: bool = True
    trade_log_path: str = "trades.json"


@dataclass
class EngineMetrics:
    """Real-time engine metrics."""
    # Status
    state: EngineState = EngineState.STOPPED
    uptime_seconds: float = 0.0
    
    # Performance
    orders_submitted: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    
    # Portfolio
    portfolio_value: float = 0.0
    cash: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Risk
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    open_positions: int = 0
    
    # Timestamps
    started_at: Optional[datetime] = None
    last_update: Optional[datetime] = None


class PaperTradingEngine:
    """
    Paper trading orchestration engine.
    
    Coordinates:
    - Market data feeds
    - Strategy execution
    - Order simulation
    - Portfolio management
    - Risk monitoring
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        
        # State
        self._state = EngineState.STOPPED
        self._metrics = EngineMetrics()
        
        # Components (lazy loaded)
        self._portfolio = None
        self._market_data = None
        self._order_simulator = None
        
        # Strategies
        self._strategies: Dict[str, Any] = {}
        self._active_strategies: Set[str] = set()
        
        # Event handlers
        self._on_order_fill: List[Callable] = []
        self._on_position_change: List[Callable] = []
        self._on_risk_breach: List[Callable] = []
        
        # Tasks
        self._main_task: Optional[asyncio.Task] = None
        self._market_task: Optional[asyncio.Task] = None
        
        # High watermark for drawdown
        self._high_watermark = self.config.initial_capital
        
        logger.info(f"PaperTradingEngine initialized ({self.config.mode.value} mode)")
    
    # -------------------- Properties --------------------
    
    @property
    def state(self) -> EngineState:
        """Current engine state."""
        return self._state
    
    @property
    def metrics(self) -> EngineMetrics:
        """Current metrics."""
        return self._metrics
    
    @property
    def is_running(self) -> bool:
        """Check if engine is running."""
        return self._state == EngineState.RUNNING
    
    @property
    def portfolio(self):
        """Get portfolio (lazy load)."""
        if self._portfolio is None:
            from src.paper_trading.portfolio import SimulatedPortfolio
            self._portfolio = SimulatedPortfolio(self.config.initial_capital)
        return self._portfolio
    
    @property
    def market_data(self):
        """Get market data feed (lazy load)."""
        if self._market_data is None:
            from src.paper_trading.market_data import MarketDataFeed
            self._market_data = MarketDataFeed()
        return self._market_data
    
    @property
    def order_simulator(self):
        """Get order simulator (lazy load)."""
        if self._order_simulator is None:
            from src.paper_trading.simulator import OrderSimulator
            self._order_simulator = OrderSimulator(
                slippage_bps=self.config.default_slippage_bps,
                fill_probability=self.config.fill_probability,
            )
        return self._order_simulator
    
    # -------------------- Lifecycle --------------------
    
    async def start(self) -> bool:
        """Start the paper trading engine."""
        if self._state not in (EngineState.STOPPED, EngineState.ERROR):
            logger.warning(f"Cannot start engine in state: {self._state}")
            return False
        
        try:
            self._state = EngineState.STARTING
            logger.info("Starting paper trading engine...")
            
            # Initialize components
            _ = self.portfolio
            _ = self.market_data
            _ = self.order_simulator
            
            # Start market data
            await self.market_data.start()
            
            # Start main loop
            self._main_task = asyncio.create_task(self._main_loop())
            
            # Update metrics
            self._metrics.state = EngineState.RUNNING
            self._metrics.started_at = datetime.now(timezone.utc)
            self._metrics.cash = self.config.initial_capital
            self._metrics.portfolio_value = self.config.initial_capital
            
            self._state = EngineState.RUNNING
            logger.info("Paper trading engine started")
            
            return True
            
        except Exception as e:
            self._state = EngineState.ERROR
            logger.error(f"Failed to start engine: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the paper trading engine."""
        if self._state not in (EngineState.RUNNING, EngineState.PAUSED):
            return
        
        self._state = EngineState.STOPPING
        logger.info("Stopping paper trading engine...")
        
        # Cancel all pending orders
        await self._cancel_all_pending_orders()
        
        # Stop tasks
        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        
        # Stop market data
        await self.market_data.stop()
        
        # Save state if configured
        if self.config.persist_trades:
            await self._save_trade_log()
        
        self._state = EngineState.STOPPED
        self._metrics.state = EngineState.STOPPED
        logger.info("Paper trading engine stopped")
    
    async def pause(self) -> None:
        """Pause trading (keep monitoring)."""
        if self._state == EngineState.RUNNING:
            self._state = EngineState.PAUSED
            self._metrics.state = EngineState.PAUSED
            logger.info("Engine paused")
    
    async def resume(self) -> None:
        """Resume trading."""
        if self._state == EngineState.PAUSED:
            self._state = EngineState.RUNNING
            self._metrics.state = EngineState.RUNNING
            logger.info("Engine resumed")
    
    # -------------------- Order Management --------------------
    
    async def submit_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        quantity: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Submit an order.
        
        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity
            order_type: market, limit, stop, stop_limit
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
            time_in_force: day, gtc, ioc, fok
            **kwargs: Additional order parameters
        
        Returns:
            Order result dictionary
        """
        if self._state != EngineState.RUNNING:
            return {
                "success": False,
                "error": f"Engine not running (state: {self._state.value})",
            }
        
        # Validate
        validation = self._validate_order(symbol, side, quantity, limit_price)
        if not validation["valid"]:
            self._metrics.orders_rejected += 1
            return {"success": False, "error": validation["reason"]}
        
        # Create order
        from src.paper_trading.portfolio import SimulatedOrder, OrderSide, OrderType, OrderStatus
        
        order = SimulatedOrder(
            order_id=str(uuid.uuid4())[:12],
            symbol=symbol,
            side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
            quantity=quantity,
            order_type=OrderType(order_type.lower()),
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )
        
        # Add to portfolio
        self.portfolio.add_order(order)
        self._metrics.orders_submitted += 1
        
        # Simulate fill for market orders
        if order.order_type == OrderType.MARKET:
            await self._process_market_order(order)
        
        logger.info(f"Order submitted: {order.order_id} {side} {quantity} {symbol}")
        
        return {
            "success": True,
            "order_id": order.order_id,
            "status": order.status.value,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        order = self.portfolio.get_order(order_id)
        
        if not order:
            return False
        
        from src.paper_trading.portfolio import OrderStatus
        
        if order.status not in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED):
            return False
        
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(timezone.utc)
        
        logger.info(f"Order cancelled: {order_id}")
        return True
    
    async def _cancel_all_pending_orders(self) -> int:
        """Cancel all pending orders."""
        count = 0
        for order in self.portfolio.get_pending_orders():
            if await self.cancel_order(order.order_id):
                count += 1
        return count
    
    def _validate_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        limit_price: Optional[float],
    ) -> Dict[str, Any]:
        """Validate order before submission."""
        # Basic validation
        if quantity <= 0:
            return {"valid": False, "reason": "Quantity must be positive"}
        
        if side.lower() not in ("buy", "sell"):
            return {"valid": False, "reason": "Invalid side"}
        
        # Position limits
        if self._metrics.open_positions >= self.config.max_positions:
            if side.lower() == "buy":
                return {"valid": False, "reason": "Max positions reached"}
        
        # Daily loss limit
        if self._metrics.daily_pnl < -self.config.max_daily_loss:
            return {"valid": False, "reason": "Daily loss limit reached"}
        
        # Position size limit
        price = limit_price or self.market_data.get_last_price(symbol) or 0
        value = quantity * price
        
        if value > self.config.max_position_size:
            return {"valid": False, "reason": "Exceeds max position size"}
        
        # Buying power check
        if side.lower() == "buy":
            if value > self.portfolio.buying_power:
                return {"valid": False, "reason": "Insufficient buying power"}
        
        return {"valid": True, "reason": ""}
    
    async def _process_market_order(self, order) -> None:
        """Process and fill a market order."""
        # Get current price
        price = self.market_data.get_last_price(order.symbol)
        
        if not price:
            # Generate simulated price
            price = await self.order_simulator.generate_price(order.symbol)
        
        # Simulate fill with slippage
        fill_result = await self.order_simulator.simulate_fill(
            order=order,
            market_price=price,
        )
        
        if fill_result.filled:
            # Update order
            from src.paper_trading.portfolio import OrderStatus
            
            order.filled_quantity = fill_result.filled_quantity
            order.filled_price = fill_result.fill_price
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.now(timezone.utc)
            
            # Update portfolio
            self.portfolio.process_fill(order)
            
            # Update metrics
            self._metrics.orders_filled += 1
            
            # Notify handlers
            await self._notify_fill(order)
            
            logger.info(
                f"Order filled: {order.order_id} @ {fill_result.fill_price:.2f}"
            )
    
    # -------------------- Strategy Management --------------------
    
    def register_strategy(self, strategy_id: str, strategy: Any) -> None:
        """Register a trading strategy."""
        self._strategies[strategy_id] = strategy
        logger.info(f"Strategy registered: {strategy_id}")
    
    def activate_strategy(self, strategy_id: str) -> bool:
        """Activate a strategy."""
        if strategy_id not in self._strategies:
            return False
        
        self._active_strategies.add(strategy_id)
        logger.info(f"Strategy activated: {strategy_id}")
        return True
    
    def deactivate_strategy(self, strategy_id: str) -> bool:
        """Deactivate a strategy."""
        if strategy_id in self._active_strategies:
            self._active_strategies.remove(strategy_id)
            logger.info(f"Strategy deactivated: {strategy_id}")
            return True
        return False
    
    # -------------------- Main Loop --------------------
    
    async def _main_loop(self) -> None:
        """Main engine loop."""
        while self._state in (EngineState.RUNNING, EngineState.PAUSED):
            try:
                # Update portfolio values
                await self._update_portfolio()
                
                # Check risk limits
                self._check_risk_limits()
                
                # Run active strategies (if not paused)
                if self._state == EngineState.RUNNING:
                    await self._run_strategies()
                
                # Process pending orders
                await self._process_pending_orders()
                
                # Update metrics
                self._update_metrics()
                
                # Sleep
                await asyncio.sleep(self.config.update_interval_ms / 1000)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(1)
    
    async def _update_portfolio(self) -> None:
        """Update portfolio values from market data."""
        for position in self.portfolio.get_positions():
            price = self.market_data.get_last_price(position.symbol)
            if price:
                position.current_price = price
                position.update_pnl()
    
    async def _run_strategies(self) -> None:
        """Run active strategies."""
        for strategy_id in self._active_strategies:
            strategy = self._strategies.get(strategy_id)
            if strategy and hasattr(strategy, "on_tick"):
                try:
                    signals = await strategy.on_tick(
                        portfolio=self.portfolio,
                        market_data=self.market_data,
                    )
                    
                    # Process signals
                    if signals:
                        for signal in signals:
                            await self._process_signal(signal)
                            
                except Exception as e:
                    logger.error(f"Strategy {strategy_id} error: {e}")
    
    async def _process_signal(self, signal: Dict[str, Any]) -> None:
        """Process a trading signal from a strategy."""
        await self.submit_order(
            symbol=signal.get("symbol", ""),
            side=signal.get("side", "buy"),
            quantity=signal.get("quantity", 0),
            order_type=signal.get("order_type", "market"),
            limit_price=signal.get("limit_price"),
        )
    
    async def _process_pending_orders(self) -> None:
        """Process pending limit/stop orders."""
        for order in self.portfolio.get_pending_orders():
            from src.paper_trading.portfolio import OrderType
            
            price = self.market_data.get_last_price(order.symbol)
            if not price:
                continue
            
            should_fill = False
            
            if order.order_type == OrderType.LIMIT:
                if order.side.value == "buy" and price <= order.limit_price:
                    should_fill = True
                elif order.side.value == "sell" and price >= order.limit_price:
                    should_fill = True
            
            elif order.order_type == OrderType.STOP:
                if order.side.value == "buy" and price >= order.stop_price:
                    should_fill = True
                elif order.side.value == "sell" and price <= order.stop_price:
                    should_fill = True
            
            if should_fill:
                fill_result = await self.order_simulator.simulate_fill(
                    order=order,
                    market_price=price,
                )
                
                if fill_result.filled:
                    from src.paper_trading.portfolio import OrderStatus
                    
                    order.filled_quantity = fill_result.filled_quantity
                    order.filled_price = fill_result.fill_price
                    order.status = OrderStatus.FILLED
                    order.filled_at = datetime.now(timezone.utc)
                    
                    self.portfolio.process_fill(order)
                    self._metrics.orders_filled += 1
                    
                    await self._notify_fill(order)
    
    def _check_risk_limits(self) -> None:
        """Check risk limits and pause if breached."""
        # Daily loss limit
        if self._metrics.daily_pnl < -self.config.max_daily_loss:
            logger.warning("Daily loss limit breached!")
            asyncio.create_task(self._on_risk_breach_async("daily_loss_limit"))
        
        # Update drawdown
        current_value = self.portfolio.total_value
        if current_value > self._high_watermark:
            self._high_watermark = current_value
        
        drawdown = (self._high_watermark - current_value) / self._high_watermark
        if drawdown > self._metrics.max_drawdown:
            self._metrics.max_drawdown = drawdown
    
    def _update_metrics(self) -> None:
        """Update engine metrics."""
        self._metrics.portfolio_value = self.portfolio.total_value
        self._metrics.cash = self.portfolio.cash
        self._metrics.unrealized_pnl = self.portfolio.unrealized_pnl
        self._metrics.realized_pnl = self.portfolio.realized_pnl
        self._metrics.daily_pnl = self.portfolio.daily_pnl
        self._metrics.open_positions = len(self.portfolio.get_positions())
        self._metrics.last_update = datetime.now(timezone.utc)
        
        if self._metrics.started_at:
            self._metrics.uptime_seconds = (
                datetime.now(timezone.utc) - self._metrics.started_at
            ).total_seconds()
    
    # -------------------- Event Handlers --------------------
    
    def on_order_fill(self, handler: Callable) -> None:
        """Register order fill handler."""
        self._on_order_fill.append(handler)
    
    def on_position_change(self, handler: Callable) -> None:
        """Register position change handler."""
        self._on_position_change.append(handler)
    
    def on_risk_breach(self, handler: Callable) -> None:
        """Register risk breach handler."""
        self._on_risk_breach.append(handler)
    
    async def _notify_fill(self, order) -> None:
        """Notify fill handlers."""
        for handler in self._on_order_fill:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(order)
                else:
                    handler(order)
            except Exception as e:
                logger.error(f"Fill handler error: {e}")
    
    async def _on_risk_breach_async(self, breach_type: str) -> None:
        """Handle risk breach."""
        for handler in self._on_risk_breach:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(breach_type)
                else:
                    handler(breach_type)
            except Exception as e:
                logger.error(f"Risk breach handler error: {e}")
    
    # -------------------- Persistence --------------------
    
    async def _save_trade_log(self) -> None:
        """Save trade log to file."""
        import json
        
        trades = [
            order.to_dict()
            for order in self.portfolio.get_all_orders()
        ]
        
        try:
            with open(self.config.trade_log_path, "w") as f:
                json.dump(trades, f, indent=2, default=str)
            logger.info(f"Trade log saved: {self.config.trade_log_path}")
        except Exception as e:
            logger.error(f"Failed to save trade log: {e}")
    
    # -------------------- Status --------------------
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            "state": self._state.value,
            "mode": self.config.mode.value,
            "uptime_seconds": self._metrics.uptime_seconds,
            "portfolio_value": self._metrics.portfolio_value,
            "cash": self._metrics.cash,
            "unrealized_pnl": self._metrics.unrealized_pnl,
            "realized_pnl": self._metrics.realized_pnl,
            "daily_pnl": self._metrics.daily_pnl,
            "max_drawdown": self._metrics.max_drawdown,
            "open_positions": self._metrics.open_positions,
            "orders_submitted": self._metrics.orders_submitted,
            "orders_filled": self._metrics.orders_filled,
            "active_strategies": list(self._active_strategies),
        }
