"""
Alpaca Options Lab - Backtesting Engine Core

Production-grade event-driven backtesting with:
- Priority event queue
- Multi-asset support
- Position and P&L tracking
- Strategy callbacks

Event Types:
1. MARKET_DATA: New price bar
2. SIGNAL: Strategy generates signal
3. ORDER: Order submitted
4. FILL: Order filled
5. EXPIRATION: Option expiration
6. ASSIGNMENT: Option assignment
7. DIVIDEND: Ex-dividend event

Usage:
    from src.backtesting.engine import BacktestEngine, BacktestConfig
    
    config = BacktestConfig(
        initial_capital=100000,
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
    )
    
    engine = BacktestEngine(config)
    
    @engine.on_bar
    def handle_bar(timestamp, data):
        if data["AAPL"]["close"] > data["AAPL"]["sma20"]:
            engine.submit_order("AAPL", 100, "buy")
    
    result = engine.run(market_data)
    print(f"Total Return: {result.total_return:.2%}")
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from src.utils.logging_config import get_logger
from src.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


class EventType(Enum):
    """Types of backtest events."""
    MARKET_DATA = auto()    # New price data
    SIGNAL = auto()         # Strategy signal
    ORDER = auto()          # Order submitted
    FILL = auto()           # Order filled
    EXPIRATION = auto()     # Option expiration
    ASSIGNMENT = auto()     # Option assignment
    DIVIDEND = auto()       # Dividend event
    SPLIT = auto()          # Stock split
    REBALANCE = auto()      # Portfolio rebalance
    CUSTOM = auto()         # User-defined


@dataclass(order=True)
class Event:
    """
    Event in the backtest event queue.
    
    Events are ordered by timestamp (earliest first),
    with type priority as tiebreaker.
    """
    timestamp: datetime
    event_type: EventType = field(compare=False)
    data: Dict[str, Any] = field(compare=False, default_factory=dict)
    priority: int = field(default=0)  # Higher = more urgent
    
    def __post_init__(self):
        # Set default priorities by type
        type_priorities = {
            EventType.EXPIRATION: 100,
            EventType.ASSIGNMENT: 90,
            EventType.DIVIDEND: 80,
            EventType.FILL: 70,
            EventType.ORDER: 60,
            EventType.MARKET_DATA: 50,
            EventType.SIGNAL: 40,
        }
        if self.priority == 0:
            self.priority = type_priorities.get(self.event_type, 0)


@dataclass
class BacktestConfig:
    """Configuration for backtest."""
    initial_capital: float = 100000.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Trading settings
    commission_per_contract: float = 0.65
    min_commission: float = 0.0
    slippage_pct: float = 0.001  # 0.1% slippage
    
    # Options settings
    option_multiplier: int = 100
    margin_requirement: float = 0.20
    
    # Execution settings
    fill_delay_seconds: int = 0
    partial_fills: bool = False
    
    # Risk settings
    max_position_pct: float = 0.20  # Max 20% in single position
    stop_on_margin_call: bool = True
    
    # Data settings
    data_frequency: str = "1min"  # 1min, 5min, 1h, 1d
    
    # Benchmark
    benchmark_symbol: Optional[str] = "SPY"


@dataclass
class Position:
    """Backtest position tracking."""
    symbol: str
    quantity: int
    entry_price: float
    entry_time: datetime
    
    # Tracking
    current_price: float = 0.0
    realized_pnl: float = 0.0
    
    # Cost basis
    total_cost: float = 0.0
    total_commission: float = 0.0
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L."""
        return (self.current_price - self.entry_price) * self.quantity * 100  # Options
    
    @property
    def market_value(self) -> float:
        """Current market value."""
        return self.current_price * abs(self.quantity) * 100
    
    @property
    def cost_basis(self) -> float:
        """Cost basis per contract."""
        if self.quantity == 0:
            return 0.0
        return self.total_cost / abs(self.quantity)


@dataclass
class Order:
    """Backtest order."""
    id: str
    symbol: str
    quantity: int  # Positive = buy, negative = sell
    order_type: str = "market"  # market, limit, stop
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # State
    status: str = "pending"  # pending, filled, partially_filled, cancelled, rejected
    filled_quantity: int = 0
    filled_price: float = 0.0
    
    # Metadata
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    # Summary
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # Days
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Capital
    initial_capital: float = 0.0
    final_capital: float = 0.0
    max_capital: float = 0.0
    min_capital: float = 0.0
    
    # Timing
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    trading_days: int = 0
    
    # Detailed data
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_return": round(self.total_return, 2),
            "total_return_pct": round(self.total_return_pct, 4),
            "annualized_return": round(self.annualized_return, 4),
            "volatility": round(self.volatility, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "sortino_ratio": round(self.sortino_ratio, 3),
            "max_drawdown": round(self.max_drawdown, 4),
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 3),
            "trading_days": self.trading_days,
        }


class BacktestEngine:
    """
    Event-driven backtesting engine.
    
    Architecture:
    - Priority event queue orders events by timestamp
    - Strategy callbacks process events
    - Order management with fill simulation
    - Position and P&L tracking
    
    Example:
        engine = BacktestEngine(config)
        
        # Register strategy
        @engine.on_bar
        def strategy(timestamp, data):
            # Your logic here
            if should_buy:
                engine.submit_order(symbol, qty, "buy")
        
        # Run backtest
        result = engine.run(historical_data)
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        """Initialize backtest engine."""
        self.config = config or BacktestConfig()
        
        # State
        self._cash = self.config.initial_capital
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Order] = {}
        self._order_counter = 0
        
        # Event queue (min heap by timestamp)
        self._event_queue: List[Event] = []
        
        # Current time
        self._current_time: Optional[datetime] = None
        
        # Callbacks
        self._on_bar_callbacks: List[Callable] = []
        self._on_fill_callbacks: List[Callable] = []
        self._on_order_callbacks: List[Callable] = []
        
        # History
        self._equity_curve: List[Tuple[datetime, float]] = []
        self._trades: List[Dict[str, Any]] = []
        self._daily_equity: Dict[date, float] = {}
        
        # Execution simulator (will be injected)
        self._execution_simulator: Optional[Any] = None
        
        logger.info("BacktestEngine initialized", config=vars(self.config))
    
    # =========================================================================
    # CALLBACK DECORATORS
    # =========================================================================
    
    def on_bar(self, callback: Callable) -> Callable:
        """Register callback for market data events."""
        self._on_bar_callbacks.append(callback)
        return callback
    
    def on_fill(self, callback: Callable) -> Callable:
        """Register callback for order fill events."""
        self._on_fill_callbacks.append(callback)
        return callback
    
    def on_order(self, callback: Callable) -> Callable:
        """Register callback for order submission events."""
        self._on_order_callbacks.append(callback)
        return callback
    
    # =========================================================================
    # ORDER MANAGEMENT
    # =========================================================================
    
    def submit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> str:
        """
        Submit an order.
        
        Args:
            symbol: Instrument symbol
            quantity: Number of contracts (positive)
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', or 'stop'
            limit_price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            
        Returns:
            Order ID
        """
        self._order_counter += 1
        order_id = f"order_{self._order_counter}"
        
        # Adjust quantity sign based on side
        qty = quantity if side == "buy" else -quantity
        
        order = Order(
            id=order_id,
            symbol=symbol,
            quantity=qty,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            status="pending",
            submitted_at=self._current_time,
        )
        
        self._orders[order_id] = order
        
        # Queue order event
        self._push_event(Event(
            timestamp=self._current_time or datetime.now(timezone.utc),
            event_type=EventType.ORDER,
            data={"order_id": order_id},
        ))
        
        # Fire callbacks
        for cb in self._on_order_callbacks:
            try:
                cb(order)
            except Exception as e:
                logger.error(f"Order callback error: {e}")
        
        return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status == "pending":
                order.status = "cancelled"
                return True
        return False
    
    def _process_order(self, order: Order, market_data: Dict[str, Any]) -> None:
        """Process an order and generate fill if applicable."""
        if order.status != "pending":
            return
        
        symbol_data = market_data.get(order.symbol)
        if symbol_data is None:
            return
        
        # Get fill price
        if order.order_type == "market":
            fill_price = self._get_fill_price(
                order.quantity,
                symbol_data.get("bid", symbol_data.get("close")),
                symbol_data.get("ask", symbol_data.get("close")),
            )
            self._execute_fill(order, fill_price, abs(order.quantity))
            
        elif order.order_type == "limit":
            if order.limit_price is None:
                return
                
            # Check if limit is hit
            if order.quantity > 0:  # Buy
                if symbol_data.get("ask", symbol_data.get("low")) <= order.limit_price:
                    self._execute_fill(order, order.limit_price, abs(order.quantity))
            else:  # Sell
                if symbol_data.get("bid", symbol_data.get("high")) >= order.limit_price:
                    self._execute_fill(order, order.limit_price, abs(order.quantity))
    
    def _get_fill_price(
        self,
        quantity: int,
        bid: float,
        ask: float,
    ) -> float:
        """Calculate fill price with slippage."""
        if quantity > 0:  # Buy
            base_price = ask
            slippage = base_price * self.config.slippage_pct
            return base_price + slippage
        else:  # Sell
            base_price = bid
            slippage = base_price * self.config.slippage_pct
            return base_price - slippage
    
    def _execute_fill(
        self,
        order: Order,
        fill_price: float,
        fill_qty: int,
    ) -> None:
        """Execute a fill and update positions."""
        # Calculate commission
        commission = max(
            fill_qty * self.config.commission_per_contract,
            self.config.min_commission,
        )
        
        # Calculate value
        value = fill_price * fill_qty * self.config.option_multiplier
        
        if order.quantity > 0:  # Buy
            # Check cash
            total_cost = value + commission
            if total_cost > self._cash:
                order.status = "rejected"
                return
            
            self._cash -= total_cost
            self._update_position_buy(order.symbol, fill_qty, fill_price, commission)
        else:  # Sell
            self._cash += value - commission
            self._update_position_sell(order.symbol, fill_qty, fill_price, commission)
        
        # Update order
        order.filled_quantity = fill_qty
        order.filled_price = fill_price
        order.status = "filled"
        order.filled_at = self._current_time
        
        # Queue fill event
        self._push_event(Event(
            timestamp=self._current_time or datetime.now(timezone.utc),
            event_type=EventType.FILL,
            data={
                "order_id": order.id,
                "symbol": order.symbol,
                "quantity": order.quantity,
                "fill_price": fill_price,
                "commission": commission,
            },
        ))
        
        # Fire callbacks
        for cb in self._on_fill_callbacks:
            try:
                cb(order, fill_price, commission)
            except Exception as e:
                logger.error(f"Fill callback error: {e}")
        
        # Record trade
        self._trades.append({
            "timestamp": self._current_time,
            "symbol": order.symbol,
            "side": "buy" if order.quantity > 0 else "sell",
            "quantity": fill_qty,
            "price": fill_price,
            "commission": commission,
            "value": value,
        })
    
    def _update_position_buy(
        self,
        symbol: str,
        quantity: int,
        price: float,
        commission: float,
    ) -> None:
        """Update position after buy."""
        if symbol in self._positions:
            pos = self._positions[symbol]
            # Average in
            total_value = pos.total_cost + price * quantity * self.config.option_multiplier
            pos.quantity += quantity
            pos.total_cost = total_value
            pos.total_commission += commission
            pos.entry_price = total_value / (pos.quantity * self.config.option_multiplier)
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                entry_time=self._current_time or datetime.now(timezone.utc),
                current_price=price,
                total_cost=price * quantity * self.config.option_multiplier,
                total_commission=commission,
            )
    
    def _update_position_sell(
        self,
        symbol: str,
        quantity: int,
        price: float,
        commission: float,
    ) -> None:
        """Update position after sell."""
        if symbol not in self._positions:
            # Short sale
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=-quantity,
                entry_price=price,
                entry_time=self._current_time or datetime.now(timezone.utc),
                current_price=price,
                total_cost=-price * quantity * self.config.option_multiplier,
                total_commission=commission,
            )
        else:
            pos = self._positions[symbol]
            
            # Calculate realized P&L
            pnl = (price - pos.entry_price) * quantity * self.config.option_multiplier
            pos.realized_pnl += pnl
            pos.quantity -= quantity
            pos.total_commission += commission
            
            # Remove if flat
            if pos.quantity == 0:
                del self._positions[symbol]
    
    # =========================================================================
    # EVENT QUEUE
    # =========================================================================
    
    def _push_event(self, event: Event) -> None:
        """Add event to priority queue."""
        # Use negative priority so higher priority events come first
        heapq.heappush(
            self._event_queue,
            (event.timestamp, -event.priority, event)
        )
    
    def _pop_event(self) -> Optional[Event]:
        """Get next event from queue."""
        if self._event_queue:
            _, _, event = heapq.heappop(self._event_queue)
            return event
        return None
    
    # =========================================================================
    # PORTFOLIO STATE
    # =========================================================================
    
    @property
    def cash(self) -> float:
        """Current cash balance."""
        return self._cash
    
    @property
    def equity(self) -> float:
        """Total portfolio equity."""
        position_value = sum(
            pos.market_value * (1 if pos.quantity > 0 else -1)
            for pos in self._positions.values()
        )
        return self._cash + position_value
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        return self._positions.get(symbol)
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions."""
        return dict(self._positions)
    
    # =========================================================================
    # MAIN LOOP
    # =========================================================================
    
    def run(
        self,
        market_data: Iterator[Tuple[datetime, Dict[str, Dict[str, float]]]],
    ) -> BacktestResult:
        """
        Run the backtest.
        
        Args:
            market_data: Iterator yielding (timestamp, {symbol: {ohlcv}}) tuples
            
        Returns:
            BacktestResult with performance metrics
        """
        logger.info("Starting backtest")
        
        # Reset state
        self._cash = self.config.initial_capital
        self._positions.clear()
        self._orders.clear()
        self._event_queue.clear()
        self._equity_curve.clear()
        self._trades.clear()
        self._daily_equity.clear()
        
        # Process market data
        for timestamp, data in market_data:
            self._current_time = timestamp
            
            # Filter by date range
            if self.config.start_date and timestamp.date() < self.config.start_date:
                continue
            if self.config.end_date and timestamp.date() > self.config.end_date:
                break
            
            # Update position prices
            self._update_position_prices(data)
            
            # Process pending orders
            for order in list(self._orders.values()):
                if order.status == "pending":
                    self._process_order(order, data)
            
            # Queue market data event
            self._push_event(Event(
                timestamp=timestamp,
                event_type=EventType.MARKET_DATA,
                data={"bars": data},
            ))
            
            # Process event queue
            while self._event_queue:
                event = self._pop_event()
                if event is None:
                    break
                
                # Process based on type
                if event.event_type == EventType.MARKET_DATA:
                    for cb in self._on_bar_callbacks:
                        try:
                            cb(timestamp, data)
                        except Exception as e:
                            logger.error(f"Bar callback error: {e}")
            
            # Record equity
            current_equity = self.equity
            self._equity_curve.append((timestamp, current_equity))
            self._daily_equity[timestamp.date()] = current_equity
        
        # Calculate results
        return self._calculate_results()
    
    def _update_position_prices(self, data: Dict[str, Dict[str, float]]) -> None:
        """Update position current prices."""
        for symbol, pos in self._positions.items():
            if symbol in data:
                pos.current_price = data[symbol].get("close", pos.current_price)
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest performance metrics."""
        if not self._equity_curve:
            return BacktestResult(initial_capital=self.config.initial_capital)
        
        initial = self.config.initial_capital
        final = self._equity_curve[-1][1]
        
        # Daily returns
        daily_values = list(self._daily_equity.values())
        daily_returns = []
        for i in range(1, len(daily_values)):
            if daily_values[i-1] > 0:
                ret = (daily_values[i] - daily_values[i-1]) / daily_values[i-1]
                daily_returns.append(ret)
        
        # Calculate metrics
        total_return = final - initial
        total_return_pct = total_return / initial if initial > 0 else 0
        
        trading_days = len(self._daily_equity)
        years = trading_days / 252
        annualized_return = (1 + total_return_pct) ** (1/years) - 1 if years > 0 else 0
        
        # Volatility
        import math
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
            volatility = math.sqrt(variance) * math.sqrt(252)
        else:
            volatility = 0
        
        # Sharpe ratio
        risk_free = 0.05 / 252  # Daily risk-free
        if volatility > 0:
            excess_return = annualized_return - 0.05
            sharpe = excess_return / volatility
        else:
            sharpe = 0
        
        # Max drawdown
        max_equity = initial
        max_drawdown = 0
        for _, equity in self._equity_curve:
            max_equity = max(max_equity, equity)
            drawdown = (max_equity - equity) / max_equity
            max_drawdown = max(max_drawdown, drawdown)
        
        # Trade statistics
        total_trades = len(self._trades)
        winning = [t for t in self._trades if t.get("pnl", 0) > 0]
        losing = [t for t in self._trades if t.get("pnl", 0) < 0]
        win_rate = len(winning) / total_trades if total_trades > 0 else 0
        
        return BacktestResult(
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            initial_capital=initial,
            final_capital=final,
            max_capital=max(e for _, e in self._equity_curve),
            min_capital=min(e for _, e in self._equity_curve),
            start_date=self._equity_curve[0][0].date() if self._equity_curve else None,
            end_date=self._equity_curve[-1][0].date() if self._equity_curve else None,
            trading_days=trading_days,
            equity_curve=self._equity_curve,
            trades=self._trades,
            daily_returns=daily_returns,
        )
