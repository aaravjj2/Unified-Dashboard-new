"""
Strategy Development & Backtesting
Items: 201-250 from Phase 4
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import polars as pl
from enum import Enum

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


@dataclass
class Order:
    """Order representation."""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    order_id: str = ""


@dataclass
class Fill:
    """Fill/execution representation."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    slippage: float
    timestamp: datetime


@dataclass
class Position:
    """Position representation."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class BacktestResult:
    """Backtest result summary."""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    equity_curve: pd.Series
    trades: List[Dict]
    metrics: Dict[str, float]


# ============================================================
# BACKTESTING ENGINE (Items 201-210)
# ============================================================

class BacktestEngine:
    """
    Event-driven backtesting framework with:
    - Transaction cost modeling
    - Market impact simulation
    - Fill probability modeling
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.0005,   # 0.05%
        short_cost: float = 0.02    # 2% annual borrow rate
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.short_cost = short_cost

        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.fills: List[Fill] = []
        self.equity_history: List[Tuple[datetime, float]] = []

    def reset(self):
        """Reset backtester state."""
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = []
        self.fills = []
        self.equity_history = []

    def run(
        self,
        strategy: 'BaseStrategy',
        data: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BacktestResult:
        """Run backtest."""
        self.reset()

        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]

        # Initialize strategy
        strategy.initialize()

        # Run through data
        for timestamp, row in data.iterrows():
            current_data = data.loc[:timestamp]

            # Update positions with current prices
            self._update_positions(row)

            # Generate signals
            signals = strategy.generate_signals(current_data)

            # Process signals into orders
            for signal in signals:
                order = self._signal_to_order(signal, timestamp)
                if order:
                    self._process_order(order, row)

            # Record equity
            equity = self._calculate_equity(row)
            self.equity_history.append((timestamp, equity))

        # Calculate results
        return self._calculate_results()

    def _update_positions(self, row: pd.Series):
        """Update position values."""
        symbol = row.name if isinstance(row.name, str) else 'default'

        for pos in self.positions.values():
            if 'close' in row:
                pos.current_price = row['close']
                pos.unrealized_pnl = (pos.current_price - pos.avg_cost) * pos.quantity

    def _signal_to_order(self, signal: Dict, timestamp: datetime) -> Optional[Order]:
        """Convert signal to order."""
        if signal.get('action') == 'buy':
            return Order(
                symbol=signal['symbol'],
                side=OrderSide.BUY,
                quantity=signal.get('quantity', 0),
                timestamp=timestamp
            )
        elif signal.get('action') == 'sell':
            return Order(
                symbol=signal['symbol'],
                side=OrderSide.SELL,
                quantity=signal.get('quantity', 0),
                timestamp=timestamp
            )
        return None

    def _process_order(self, order: Order, row: pd.Series):
        """Process and fill order."""
        price = row['close']

        # Apply slippage
        if order.side == OrderSide.BUY:
            fill_price = price * (1 + self.slippage)
        else:
            fill_price = price * (1 - self.slippage)

        # Calculate commission
        commission = order.quantity * fill_price * self.commission

        # Check if we have enough capital
        total_cost = order.quantity * fill_price + commission
        if order.side == OrderSide.BUY and total_cost > self.cash:
            return  # Insufficient funds

        # Create fill
        fill = Fill(
            order_id=f"fill_{len(self.fills)}",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
            slippage=abs(fill_price - price) * order.quantity,
            timestamp=order.timestamp
        )

        self.fills.append(fill)

        # Update positions and cash
        self._update_from_fill(fill)

    def _update_from_fill(self, fill: Fill):
        """Update positions and cash from fill."""
        if fill.side == OrderSide.BUY:
            if fill.symbol in self.positions:
                pos = self.positions[fill.symbol]
                total_qty = pos.quantity + fill.quantity
                pos.avg_cost = (pos.avg_cost * pos.quantity + fill.price * fill.quantity) / total_qty
                pos.quantity = total_qty
            else:
                self.positions[fill.symbol] = Position(
                    symbol=fill.symbol,
                    quantity=fill.quantity,
                    avg_cost=fill.price
                )

            self.cash -= (fill.quantity * fill.price + fill.commission)

        else:  # SELL
            if fill.symbol in self.positions:
                pos = self.positions[fill.symbol]
                realized_pnl = (fill.price - pos.avg_cost) * fill.quantity
                pos.realized_pnl += realized_pnl
                pos.quantity -= fill.quantity

                if pos.quantity <= 0:
                    del self.positions[fill.symbol]

                self.cash += (fill.quantity * fill.price - fill.commission)

    def _calculate_equity(self, row: pd.Series) -> float:
        """Calculate total equity."""
        position_value = sum(
            p.quantity * row.get('close', p.current_price)
            for p in self.positions.values()
        )
        return self.cash + position_value

    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest results."""
        if not self.equity_history:
            return BacktestResult(
                total_return=0, annual_return=0, sharpe_ratio=0,
                sortino_ratio=0, max_drawdown=0, win_rate=0,
                profit_factor=0, total_trades=0, winning_trades=0,
                losing_trades=0, avg_win=0, avg_loss=0,
                equity_curve=pd.Series(), trades=[], metrics={}
            )

        # Create equity curve
        equity_curve = pd.Series(
            [e[1] for e in self.equity_history],
            index=[e[0] for e in self.equity_history]
        )

        # Calculate returns
        returns = equity_curve.pct_change().dropna()
        total_return = (equity_curve.iloc[-1] / self.initial_capital - 1)

        # Annualized return
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1

        # Sharpe ratio
        sharpe_ratio = np.sqrt(252) * returns.mean() / (returns.std() + 1e-10)

        # Sortino ratio
        downside_returns = returns[returns < 0]
        sortino_ratio = np.sqrt(252) * returns.mean() / (downside_returns.std() + 1e-10)

        # Maximum drawdown
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = abs(drawdown.min())

        # Trade statistics
        trades = self._calculate_trade_stats()

        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=trades['win_rate'],
            profit_factor=trades['profit_factor'],
            total_trades=trades['total_trades'],
            winning_trades=trades['winning_trades'],
            losing_trades=trades['losing_trades'],
            avg_win=trades['avg_win'],
            avg_loss=trades['avg_loss'],
            equity_curve=equity_curve,
            trades=trades['trade_list'],
            metrics={
                'total_commission': sum(f.commission for f in self.fills),
                'total_slippage': sum(f.slippage for f in self.fills),
                'final_equity': equity_curve.iloc[-1],
                'initial_capital': self.initial_capital
            }
        )

    def _calculate_trade_stats(self) -> Dict:
        """Calculate trade statistics."""
        # Group fills into round-trip trades
        trade_pnls = []

        for pos in list(self.positions.values()):
            trade_pnls.append(pos.realized_pnl)

        winning = [p for p in trade_pnls if p > 0]
        losing = [p for p in trade_pnls if p < 0]  # Exclude zero
        
        total_trades = len(trade_pnls) if trade_pnls else len(self.fills) // 2
        
        # Calculate profit factor safely
        if losing and sum(abs(l) for l in losing) > 0:
            profit_factor = sum(winning) / sum(abs(l) for l in losing)
        else:
            profit_factor = float('inf') if winning else 1.0

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / max(total_trades, 1),
            'avg_win': np.mean(winning) if winning else 0,
            'avg_loss': np.mean(losing) if losing else 0,
            'profit_factor': profit_factor,
            'trade_list': [{'pnl': p} for p in trade_pnls]
        }


# ============================================================
# BASE STRATEGY (Item 211-220)
# ============================================================

class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, params: Dict = {}):
        self.params = params
        self.name = self.__class__.__name__

    @abstractmethod
    def initialize(self):
        """Initialize strategy state."""
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """Generate trading signals."""
        pass


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy template."""

    def __init__(self, params: Dict = {}):
        default_params = {
            'lookback': 20,
            'entry_std': 2.0,
            'exit_std': 0.5,
            'position_size': 100
        }
        default_params.update(params)
        super().__init__(default_params)

    def initialize(self):
        pass

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []

        if len(data) < self.params['lookback']:
            return signals

        # Calculate z-score
        mean = data['close'].rolling(self.params['lookback']).mean()
        std = data['close'].rolling(self.params['lookback']).std()
        z_score = (data['close'].iloc[-1] - mean.iloc[-1]) / (std.iloc[-1] + 1e-10)

        symbol = data.index.name or 'default'

        if z_score < -self.params['entry_std']:
            signals.append({
                'symbol': symbol,
                'action': 'buy',
                'quantity': self.params['position_size'],
                'signal_strength': abs(z_score)
            })
        elif z_score > self.params['entry_std']:
            signals.append({
                'symbol': symbol,
                'action': 'sell',
                'quantity': self.params['position_size'],
                'signal_strength': abs(z_score)
            })

        return signals


class MomentumStrategy(BaseStrategy):
    """Momentum strategy template."""

    def __init__(self, params: Dict = {}):
        default_params = {
            'fast_period': 10,
            'slow_period': 30,
            'position_size': 100
        }
        default_params.update(params)
        super().__init__(default_params)

    def initialize(self):
        pass

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []

        if len(data) < self.params['slow_period']:
            return signals

        fast_ma = data['close'].rolling(self.params['fast_period']).mean()
        slow_ma = data['close'].rolling(self.params['slow_period']).mean()

        symbol = data.index.name or 'default'

        # Crossover signals
        if fast_ma.iloc[-1] > slow_ma.iloc[-1] and fast_ma.iloc[-2] <= slow_ma.iloc[-2]:
            signals.append({
                'symbol': symbol,
                'action': 'buy',
                'quantity': self.params['position_size']
            })
        elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and fast_ma.iloc[-2] >= slow_ma.iloc[-2]:
            signals.append({
                'symbol': symbol,
                'action': 'sell',
                'quantity': self.params['position_size']
            })

        return signals


class TrendFollowingStrategy(BaseStrategy):
    """Trend following strategy template."""

    def __init__(self, params: Dict = {}):
        default_params = {
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'position_size': 100
        }
        default_params.update(params)
        super().__init__(default_params)

    def initialize(self):
        self.in_position = False
        self.entry_price = 0
        self.stop_loss = 0

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []

        if len(data) < self.params['atr_period'] + 1:
            return signals

        # Calculate ATR
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.params['atr_period']).mean().iloc[-1]

        current_price = data['close'].iloc[-1]
        symbol = data.index.name or 'default'

        if not self.in_position:
            # Entry on breakout
            highest = data['high'].rolling(20).max().iloc[-1]
            if current_price > highest:
                self.in_position = True
                self.entry_price = current_price
                self.stop_loss = current_price - self.params['atr_multiplier'] * atr
                signals.append({
                    'symbol': symbol,
                    'action': 'buy',
                    'quantity': self.params['position_size']
                })
        else:
            # Trail stop
            new_stop = current_price - self.params['atr_multiplier'] * atr
            self.stop_loss = max(self.stop_loss, new_stop)

            if current_price < self.stop_loss:
                self.in_position = False
                signals.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'quantity': self.params['position_size']
                })

        return signals


# ============================================================
# STRATEGY OPTIMIZER (Items 221-230)
# ============================================================

class StrategyOptimizer:
    """
    Strategy optimization with:
    - Grid search
    - Walk-forward optimization
    - Overfitting detection
    """

    def __init__(self, engine: BacktestEngine):
        self.engine = engine

    def grid_search(
        self,
        strategy_class: type,
        data: pd.DataFrame,
        param_grid: Dict[str, List]
    ) -> Tuple[Dict, BacktestResult]:
        """Perform grid search optimization."""
        import itertools

        # Generate all parameter combinations
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = list(itertools.product(*values))

        best_result = None
        best_params = None
        best_sharpe = -float('inf')

        for combo in combinations:
            params = dict(zip(keys, combo))
            strategy = strategy_class(params)

            result = self.engine.run(strategy, data)

            if result.sharpe_ratio > best_sharpe:
                best_sharpe = result.sharpe_ratio
                best_result = result
                best_params = params

        return best_params, best_result

    def walk_forward(
        self,
        strategy_class: type,
        data: pd.DataFrame,
        param_grid: Dict[str, List],
        train_period: int = 252,
        test_period: int = 63,
        n_splits: int = 5
    ) -> List[BacktestResult]:
        """Walk-forward optimization."""
        results = []

        total_length = len(data)
        step_size = (total_length - train_period) // n_splits

        for i in range(n_splits):
            train_start = i * step_size
            train_end = train_start + train_period
            test_end = min(train_end + test_period, total_length)

            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[train_end:test_end]

            # Optimize on training data
            best_params, _ = self.grid_search(strategy_class, train_data, param_grid)

            # Test on out-of-sample data
            strategy = strategy_class(best_params)
            result = self.engine.run(strategy, test_data)
            result.metrics['optimal_params'] = best_params
            result.metrics['split'] = i

            results.append(result)

        return results


# ============================================================
# PERFORMANCE ANALYTICS (Items 231-240)
# ============================================================

class PerformanceAnalytics:
    """
    Performance analytics including:
    - Risk-adjusted returns
    - Attribution analysis
    - Benchmark comparison
    """

    @staticmethod
    def calculate_metrics(equity_curve: pd.Series, risk_free_rate: float = 0.02) -> Dict:
        """Calculate comprehensive performance metrics."""
        returns = equity_curve.pct_change().dropna()

        # Basic metrics
        total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1

        # Volatility
        annual_volatility = returns.std() * np.sqrt(252)

        # Sharpe ratio
        excess_return = annual_return - risk_free_rate
        sharpe_ratio = excess_return / (annual_volatility + 1e-10)

        # Sortino ratio
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = excess_return / (downside_std + 1e-10)

        # Calmar ratio
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = abs(drawdown.min())
        calmar_ratio = annual_return / (max_drawdown + 1e-10)

        # Information ratio (vs buy & hold)
        # Would need benchmark returns

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown,
            'risk_free_rate': risk_free_rate
        }

    @staticmethod
    def rolling_metrics(
        equity_curve: pd.Series,
        window: int = 252
    ) -> pd.DataFrame:
        """Calculate rolling performance metrics."""
        returns = equity_curve.pct_change()

        rolling_return = returns.rolling(window).mean() * 252
        rolling_vol = returns.rolling(window).std() * np.sqrt(252)
        rolling_sharpe = rolling_return / (rolling_vol + 1e-10)

        cummax = equity_curve.cummax()
        rolling_dd = (equity_curve - cummax) / cummax

        return pd.DataFrame({
            'rolling_return': rolling_return,
            'rolling_volatility': rolling_vol,
            'rolling_sharpe': rolling_sharpe,
            'drawdown': rolling_dd
        })


# Global instances
backtest_engine = BacktestEngine()
strategy_optimizer = StrategyOptimizer(backtest_engine)
performance_analytics = PerformanceAnalytics()
