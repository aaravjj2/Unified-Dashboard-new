"""
Alpaca Options Lab - Backtesting Engine

Strategy backtesting with:
- Historical data replay
- Realistic execution simulation
- Greeks tracking
- Performance attribution
- Walk-forward optimization
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING
import numpy as np

from src.analytics.performance import PerformanceAnalyzer, Trade, PerformanceMetrics
from src.utils.logging_config import get_logger

if TYPE_CHECKING:
    from src.strategies.base import Strategy

logger = get_logger(__name__)


class BacktestMode(Enum):
    """Backtest execution mode."""
    VECTORIZED = "vectorized"  # Fast, all-at-once
    EVENT_DRIVEN = "event_driven"  # Realistic tick-by-tick


@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    start_date: date
    end_date: date
    
    # Capital
    initial_capital: float = 100000.0
    margin_requirement: float = 0.2  # 20% margin
    
    # Execution
    mode: BacktestMode = BacktestMode.EVENT_DRIVEN
    slippage_bps: float = 5.0  # Basis points
    commission_per_contract: float = 0.65
    
    # Risk
    max_position_size: float = 0.1  # 10% of capital per position
    max_total_risk: float = 0.5  # 50% max capital at risk
    
    # Data
    data_frequency: str = "1min"  # 1min, 5min, 1h, 1d
    use_bid_ask: bool = True  # Use bid/ask for realistic fills
    
    # Output
    verbose: bool = False
    save_trades: bool = True


@dataclass
class TradeLog:
    """Single trade in backtest."""
    trade_id: str
    symbol: str
    strategy: str
    
    # Entry
    entry_time: datetime
    entry_price: float
    entry_side: str  # "buy" or "sell"
    quantity: int
    
    # Exit (if closed)
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""  # "signal", "stop", "target", "expiry"
    
    # P&L
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    
    # Greeks at entry
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    
    @property
    def is_closed(self) -> bool:
        return self.exit_time is not None
    
    @property
    def net_pnl(self) -> float:
        return self.realized_pnl - self.commission - self.slippage


@dataclass
class BacktestResult:
    """Complete backtest results."""
    # Configuration
    config: BacktestConfig
    strategy_name: str
    
    # Performance
    metrics: PerformanceMetrics
    
    # Equity curve (date -> equity)
    equity_curve: Dict[date, float] = field(default_factory=dict)
    
    # Trade log
    trades: List[TradeLog] = field(default_factory=list)
    
    # Greeks over time
    delta_series: Dict[date, float] = field(default_factory=dict)
    theta_series: Dict[date, float] = field(default_factory=dict)
    
    # Execution quality
    total_slippage: float = 0.0
    total_commission: float = 0.0
    avg_fill_deviation: float = 0.0
    
    # Metadata
    run_time_seconds: float = 0.0
    data_points_processed: int = 0


@dataclass
class MarketSnapshot:
    """Market data at a point in time."""
    timestamp: datetime
    symbol: str
    
    # Price data
    bid: float
    ask: float
    last: float
    
    # Greeks (for options)
    iv: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    
    # Underlying
    underlying_price: float = 0.0
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid


class BacktestEngine:
    """
    Options strategy backtesting engine.
    
    Features:
    - Historical data replay
    - Realistic execution with slippage
    - Greeks tracking
    - Position management
    - Performance analysis
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
        # State
        self._capital = config.initial_capital
        self._positions: Dict[str, TradeLog] = {}
        self._closed_trades: List[TradeLog] = []
        
        # Time series
        self._equity_curve: Dict[date, float] = {}
        self._delta_series: Dict[date, float] = {}
        self._theta_series: Dict[date, float] = {}
        
        # Market data
        self._market_data: Dict[str, List[MarketSnapshot]] = {}
        self._current_time: Optional[datetime] = None
        
        # Counters
        self._trade_counter = 0
        self._data_points = 0
        
        logger.info(
            f"BacktestEngine initialized: {config.start_date} to {config.end_date}, "
            f"capital=${config.initial_capital:,.0f}"
        )
    
    # -------------------- Data Loading --------------------
    
    def load_market_data(
        self,
        symbol: str,
        data: List[MarketSnapshot],
    ) -> None:
        """Load market data for a symbol."""
        self._market_data[symbol] = sorted(data, key=lambda x: x.timestamp)
        logger.info(f"Loaded {len(data)} data points for {symbol}")
    
    def load_data_from_dict(
        self,
        symbol: str,
        data: List[Dict[str, Any]],
    ) -> None:
        """Load market data from list of dicts."""
        snapshots = []
        
        for d in data:
            timestamp = d.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            
            snapshot = MarketSnapshot(
                timestamp=timestamp,
                symbol=symbol,
                bid=d.get("bid", d.get("close", 0)),
                ask=d.get("ask", d.get("close", 0) * 1.001),
                last=d.get("last", d.get("close", 0)),
                iv=d.get("iv", d.get("implied_volatility", 0)),
                delta=d.get("delta", 0),
                gamma=d.get("gamma", 0),
                theta=d.get("theta", 0),
                vega=d.get("vega", 0),
                underlying_price=d.get("underlying_price", d.get("spot", 0)),
            )
            snapshots.append(snapshot)
        
        self.load_market_data(symbol, snapshots)
    
    # -------------------- Backtest Execution --------------------
    
    async def run(
        self,
        strategy: "Strategy",
    ) -> BacktestResult:
        """
        Run backtest with given strategy.
        
        Args:
            strategy: Strategy instance to backtest
        
        Returns:
            BacktestResult with performance metrics
        """
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting backtest: {strategy.__class__.__name__}")
        
        # Reset state
        self._reset()
        
        # Get all timestamps
        all_timestamps = self._get_all_timestamps()
        
        if not all_timestamps:
            raise ValueError("No market data loaded")
        
        # Initialize strategy
        await strategy.on_start()
        
        # Process each timestamp
        for timestamp in all_timestamps:
            self._current_time = timestamp
            current_date = timestamp.date()
            
            # Skip if outside backtest range
            if current_date < self.config.start_date:
                continue
            if current_date > self.config.end_date:
                break
            
            self._data_points += 1
            
            # Get market snapshot for all symbols
            snapshots = self._get_snapshots_at_time(timestamp)
            
            # Update positions with current prices
            self._update_positions(snapshots)
            
            # Send market data to strategy
            for symbol, snapshot in snapshots.items():
                from src.strategies.base import MarketEvent
                event = MarketEvent(
                    symbol=symbol,
                    timestamp=timestamp,
                    bid=snapshot.bid,
                    ask=snapshot.ask,
                    last=snapshot.last,
                    iv=snapshot.iv,
                    underlying_price=snapshot.underlying_price,
                )
                
                signals = await strategy.on_market_data(event)
                
                # Process signals
                for signal in signals:
                    await self._process_signal(signal, snapshot)
            
            # Record daily metrics at end of day
            if self._is_end_of_day(timestamp, all_timestamps):
                self._record_daily_metrics(current_date)
        
        # Close remaining positions
        await self._close_all_positions("backtest_end")
        
        # Stop strategy
        await strategy.on_stop()
        
        # Calculate final metrics
        run_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Build performance metrics
        analyzer = PerformanceAnalyzer(self.config.initial_capital)
        for trade in self._closed_trades:
            analyzer.add_trade(Trade(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                strategy=trade.strategy,
                side=trade.entry_side,
                entry_time=trade.entry_time,
                entry_price=trade.entry_price,
                quantity=trade.quantity,
                exit_time=trade.exit_time,
                exit_price=trade.exit_price,
                realized_pnl=trade.realized_pnl,
                commission=trade.commission,
            ))
        analyzer.set_equity_curve(self._equity_curve)
        
        metrics = analyzer.analyze()
        
        result = BacktestResult(
            config=self.config,
            strategy_name=strategy.__class__.__name__,
            metrics=metrics,
            equity_curve=self._equity_curve.copy(),
            trades=self._closed_trades.copy(),
            delta_series=self._delta_series.copy(),
            theta_series=self._theta_series.copy(),
            total_slippage=sum(t.slippage for t in self._closed_trades),
            total_commission=sum(t.commission for t in self._closed_trades),
            run_time_seconds=run_time,
            data_points_processed=self._data_points,
        )
        
        logger.info(
            f"Backtest complete: {len(self._closed_trades)} trades, "
            f"return={metrics.total_return_pct:.2f}%, "
            f"sharpe={metrics.sharpe_ratio:.2f}"
        )
        
        return result
    
    def _reset(self) -> None:
        """Reset backtest state."""
        self._capital = self.config.initial_capital
        self._positions.clear()
        self._closed_trades.clear()
        self._equity_curve.clear()
        self._delta_series.clear()
        self._theta_series.clear()
        self._trade_counter = 0
        self._data_points = 0
    
    def _get_all_timestamps(self) -> List[datetime]:
        """Get sorted list of all unique timestamps."""
        timestamps = set()
        for snapshots in self._market_data.values():
            for snapshot in snapshots:
                timestamps.add(snapshot.timestamp)
        return sorted(timestamps)
    
    def _get_snapshots_at_time(
        self,
        timestamp: datetime,
    ) -> Dict[str, MarketSnapshot]:
        """Get market snapshots at specific time."""
        snapshots = {}
        
        for symbol, data in self._market_data.items():
            # Find closest snapshot at or before timestamp
            for snapshot in reversed(data):
                if snapshot.timestamp <= timestamp:
                    snapshots[symbol] = snapshot
                    break
        
        return snapshots
    
    def _is_end_of_day(
        self,
        timestamp: datetime,
        all_timestamps: List[datetime],
    ) -> bool:
        """Check if timestamp is end of trading day."""
        current_date = timestamp.date()
        
        # Find next timestamp
        idx = all_timestamps.index(timestamp)
        if idx >= len(all_timestamps) - 1:
            return True
        
        next_date = all_timestamps[idx + 1].date()
        return next_date != current_date
    
    def _update_positions(self, snapshots: Dict[str, MarketSnapshot]) -> None:
        """Update position mark-to-market."""
        for symbol, trade in self._positions.items():
            if symbol in snapshots:
                snapshot = snapshots[symbol]
                current_price = snapshot.mid
                
                # Update unrealized P&L
                if trade.entry_side == "buy":
                    trade.unrealized_pnl = (current_price - trade.entry_price) * trade.quantity * 100
                else:
                    trade.unrealized_pnl = (trade.entry_price - current_price) * trade.quantity * 100
    
    def _record_daily_metrics(self, current_date: date) -> None:
        """Record end-of-day metrics."""
        # Calculate total equity
        total_unrealized = sum(t.unrealized_pnl for t in self._positions.values())
        total_realized = sum(t.net_pnl for t in self._closed_trades)
        equity = self.config.initial_capital + total_realized + total_unrealized
        
        self._equity_curve[current_date] = equity
        
        # Record Greeks
        total_delta = sum(t.delta * t.quantity for t in self._positions.values())
        total_theta = sum(t.theta * t.quantity for t in self._positions.values())
        
        self._delta_series[current_date] = total_delta
        self._theta_series[current_date] = total_theta
    
    # -------------------- Order Execution --------------------
    
    async def _process_signal(
        self,
        signal: Any,
        snapshot: MarketSnapshot,
    ) -> None:
        """Process strategy signal."""
        from src.strategies.base import Signal
        
        if not isinstance(signal, Signal):
            return
        
        for leg in signal.legs:
            symbol = leg.symbol
            
            # Determine fill price with slippage
            if leg.side.value in ("buy", "buy_to_open"):
                fill_price = snapshot.ask * (1 + self.config.slippage_bps / 10000)
            else:
                fill_price = snapshot.bid * (1 - self.config.slippage_bps / 10000)
            
            slippage = abs(fill_price - snapshot.mid) * leg.quantity * 100
            commission = leg.quantity * self.config.commission_per_contract
            
            # Check if opening or closing
            if symbol in self._positions:
                # Closing trade
                await self._close_position(symbol, fill_price, slippage, commission, "signal")
            else:
                # Opening trade
                await self._open_position(
                    symbol=symbol,
                    side="buy" if leg.side.value in ("buy", "buy_to_open") else "sell",
                    quantity=leg.quantity,
                    fill_price=fill_price,
                    slippage=slippage,
                    commission=commission,
                    strategy=signal.strategy,
                    snapshot=snapshot,
                )
    
    async def _open_position(
        self,
        symbol: str,
        side: str,
        quantity: int,
        fill_price: float,
        slippage: float,
        commission: float,
        strategy: str,
        snapshot: MarketSnapshot,
    ) -> None:
        """Open a new position."""
        self._trade_counter += 1
        trade_id = f"BT-{self._trade_counter:06d}"
        
        trade = TradeLog(
            trade_id=trade_id,
            symbol=symbol,
            strategy=strategy,
            entry_time=self._current_time,
            entry_price=fill_price,
            entry_side=side,
            quantity=quantity,
            commission=commission,
            slippage=slippage,
            delta=snapshot.delta,
            gamma=snapshot.gamma,
            theta=snapshot.theta,
            vega=snapshot.vega,
        )
        
        self._positions[symbol] = trade
        
        if self.config.verbose:
            logger.info(f"Opened {side} {quantity}x {symbol} @ {fill_price:.2f}")
    
    async def _close_position(
        self,
        symbol: str,
        fill_price: float,
        slippage: float,
        commission: float,
        reason: str,
    ) -> None:
        """Close an existing position."""
        if symbol not in self._positions:
            return
        
        trade = self._positions.pop(symbol)
        trade.exit_time = self._current_time
        trade.exit_price = fill_price
        trade.exit_reason = reason
        trade.slippage += slippage
        trade.commission += commission
        
        # Calculate realized P&L
        if trade.entry_side == "buy":
            trade.realized_pnl = (fill_price - trade.entry_price) * trade.quantity * 100
        else:
            trade.realized_pnl = (trade.entry_price - fill_price) * trade.quantity * 100
        
        self._closed_trades.append(trade)
        
        if self.config.verbose:
            logger.info(
                f"Closed {symbol} @ {fill_price:.2f}, P&L: ${trade.net_pnl:.2f}"
            )
    
    async def _close_all_positions(self, reason: str) -> None:
        """Close all open positions."""
        for symbol in list(self._positions.keys()):
            # Get last known price
            if symbol in self._market_data and self._market_data[symbol]:
                last_snapshot = self._market_data[symbol][-1]
                fill_price = last_snapshot.mid
            else:
                trade = self._positions[symbol]
                fill_price = trade.entry_price  # Fallback
            
            await self._close_position(
                symbol=symbol,
                fill_price=fill_price,
                slippage=0,
                commission=self.config.commission_per_contract * self._positions[symbol].quantity,
                reason=reason,
            )
    
    # -------------------- Results --------------------
    
    def get_equity_curve_df(self) -> Any:
        """Export equity curve as DataFrame."""
        try:
            import pandas as pd
            return pd.Series(self._equity_curve, name="equity").sort_index()
        except ImportError:
            return self._equity_curve
    
    def get_trades_df(self) -> Any:
        """Export trades as DataFrame."""
        try:
            import pandas as pd
            
            data = [
                {
                    "trade_id": t.trade_id,
                    "symbol": t.symbol,
                    "strategy": t.strategy,
                    "side": t.entry_side,
                    "entry_time": t.entry_time,
                    "entry_price": t.entry_price,
                    "exit_time": t.exit_time,
                    "exit_price": t.exit_price,
                    "quantity": t.quantity,
                    "pnl": t.net_pnl,
                    "exit_reason": t.exit_reason,
                }
                for t in self._closed_trades
            ]
            
            return pd.DataFrame(data)
        except ImportError:
            return self._closed_trades
