"""
Backtest Harness - Vectorized Backtesting for ML Strategies
============================================================
Phase 2 of ML Project Guide implementation.

Provides:
- Vectorized backtest engine with transaction costs
- Performance metrics calculation
- Walk-forward validation
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class BacktestConfig:
    """Configuration for backtest run."""
    initial_capital: float = 100000.0
    commission_pct: float = 0.001  # 0.1% per trade
    slippage_pct: float = 0.001   # 0.1% slippage
    max_position_size: float = 0.1  # Max 10% of capital per position
    risk_free_rate: float = 0.02  # Annual risk-free rate
    trading_days_per_year: int = 252


@dataclass
class Trade:
    """Individual trade record."""
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    config: BacktestConfig
    
    # Time series
    equity_curve: pd.Series = None
    returns: pd.Series = None
    positions: pd.DataFrame = None
    drawdowns: pd.Series = None
    
    # Trade list
    trades: List[Trade] = field(default_factory=list)
    
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0
    num_trades: int = 0
    
    # Turnover
    turnover: float = 0.0
    turnover_adjusted_return: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'calmar_ratio': self.calmar_ratio,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'avg_trade_pnl': self.avg_trade_pnl,
            'num_trades': self.num_trades,
            'turnover': self.turnover,
            'turnover_adjusted_return': self.turnover_adjusted_return,
        }


# ==============================================================================
# BACKTEST ENGINE
# ==============================================================================

def backtest_signals(
    prices: pd.Series,
    signals: pd.Series,
    config: BacktestConfig = None
) -> BacktestResult:
    """
    Run vectorized backtest on signals.
    
    Args:
        prices: Price series (Close prices)
        signals: Signal series (-1, 0, 1 for short, flat, long)
        config: Backtest configuration
        
    Returns:
        BacktestResult with all metrics and equity curve
        
    Example:
        >>> from financial_dashboard.evaluation.backtest import backtest_signals
        >>> perf = backtest_signals(price_series, signals, cost=0.0005, slippage=0.001)
        >>> print(perf.sharpe_ratio, perf.max_drawdown)
    """
    if config is None:
        config = BacktestConfig()
    
    # Align data
    prices = prices.dropna()
    signals = signals.reindex(prices.index).fillna(0)
    
    # Calculate returns
    price_returns = prices.pct_change().fillna(0)
    
    # Calculate position changes (for turnover and costs)
    position_changes = signals.diff().fillna(0).abs()
    
    # Apply transaction costs
    transaction_costs = position_changes * (config.commission_pct + config.slippage_pct)
    
    # Strategy returns (signal * price return - costs)
    strategy_returns = (signals.shift(1) * price_returns) - transaction_costs
    strategy_returns = strategy_returns.fillna(0)
    
    # Calculate equity curve
    equity_curve = (1 + strategy_returns).cumprod() * config.initial_capital
    
    # Calculate drawdowns
    running_max = equity_curve.expanding().max()
    drawdowns = (equity_curve - running_max) / running_max
    
    # Build result
    result = BacktestResult(config=config)
    result.equity_curve = equity_curve
    result.returns = strategy_returns
    result.drawdowns = drawdowns
    
    # Calculate metrics
    result = _calculate_metrics(result, strategy_returns, config)
    
    # Calculate turnover
    result.turnover = position_changes.sum() / len(position_changes) * config.trading_days_per_year
    result.turnover_adjusted_return = result.annualized_return - (
        result.turnover * (config.commission_pct + config.slippage_pct)
    )
    
    return result


def backtest_positions(
    prices: pd.DataFrame,
    positions: pd.DataFrame,
    config: BacktestConfig = None
) -> BacktestResult:
    """
    Run backtest on position weights (for multi-asset portfolios).
    
    Args:
        prices: DataFrame of prices (columns = assets)
        positions: DataFrame of position weights (columns = assets)
        config: Backtest configuration
        
    Returns:
        BacktestResult
    """
    if config is None:
        config = BacktestConfig()
    
    # Align data
    common_idx = prices.index.intersection(positions.index)
    prices = prices.loc[common_idx]
    positions = positions.loc[common_idx]
    
    # Calculate returns
    price_returns = prices.pct_change().fillna(0)
    
    # Calculate position changes
    position_changes = positions.diff().fillna(0).abs()
    
    # Transaction costs per asset
    transaction_costs = (position_changes * (config.commission_pct + config.slippage_pct)).sum(axis=1)
    
    # Portfolio returns
    portfolio_returns = (positions.shift(1) * price_returns).sum(axis=1) - transaction_costs
    portfolio_returns = portfolio_returns.fillna(0)
    
    # Equity curve
    equity_curve = (1 + portfolio_returns).cumprod() * config.initial_capital
    
    # Drawdowns
    running_max = equity_curve.expanding().max()
    drawdowns = (equity_curve - running_max) / running_max
    
    # Build result
    result = BacktestResult(config=config)
    result.equity_curve = equity_curve
    result.returns = portfolio_returns
    result.positions = positions
    result.drawdowns = drawdowns
    
    # Calculate metrics
    result = _calculate_metrics(result, portfolio_returns, config)
    
    # Turnover
    result.turnover = position_changes.sum().sum() / len(position_changes) * config.trading_days_per_year
    
    return result


def _calculate_metrics(
    result: BacktestResult,
    returns: pd.Series,
    config: BacktestConfig
) -> BacktestResult:
    """Calculate performance metrics."""
    
    # Total return
    result.total_return = (1 + returns).prod() - 1
    
    # Annualized return
    n_years = len(returns) / config.trading_days_per_year
    if n_years > 0:
        result.annualized_return = (1 + result.total_return) ** (1 / n_years) - 1
    
    # Volatility (annualized)
    result.volatility = returns.std() * np.sqrt(config.trading_days_per_year)
    
    # Sharpe ratio
    if result.volatility > 0:
        excess_return = result.annualized_return - config.risk_free_rate
        result.sharpe_ratio = excess_return / result.volatility
    
    # Sortino ratio (downside volatility)
    downside_returns = returns[returns < 0]
    if len(downside_returns) > 0:
        downside_vol = downside_returns.std() * np.sqrt(config.trading_days_per_year)
        if downside_vol > 0:
            excess_return = result.annualized_return - config.risk_free_rate
            result.sortino_ratio = excess_return / downside_vol
    
    # Max drawdown
    result.max_drawdown = result.drawdowns.min() if result.drawdowns is not None else 0
    
    # Calmar ratio
    if abs(result.max_drawdown) > 0:
        result.calmar_ratio = result.annualized_return / abs(result.max_drawdown)
    
    return result


# ==============================================================================
# WALK-FORWARD VALIDATION
# ==============================================================================

def walk_forward_backtest(
    prices: pd.Series,
    signal_generator: callable,
    train_window: int = 252,
    test_window: int = 63,
    config: BacktestConfig = None
) -> List[BacktestResult]:
    """
    Run walk-forward backtest.
    
    Args:
        prices: Price series
        signal_generator: Function that takes training data and returns signals
        train_window: Training window in days
        test_window: Test window in days
        config: Backtest configuration
        
    Returns:
        List of BacktestResult for each test period
    """
    if config is None:
        config = BacktestConfig()
    
    results = []
    n = len(prices)
    
    start = 0
    while start + train_window + test_window <= n:
        # Training period
        train_end = start + train_window
        train_prices = prices.iloc[start:train_end]
        
        # Generate signals using training data
        signals = signal_generator(train_prices)
        
        # Test period
        test_start = train_end
        test_end = min(test_start + test_window, n)
        test_prices = prices.iloc[test_start:test_end]
        
        # Reindex signals to test period
        test_signals = signals.reindex(test_prices.index).fillna(0)
        
        # Run backtest on test period
        result = backtest_signals(test_prices, test_signals, config)
        result.test_start = test_prices.index[0]
        result.test_end = test_prices.index[-1]
        results.append(result)
        
        # Move forward
        start += test_window
    
    return results


def aggregate_walk_forward_results(results: List[BacktestResult]) -> Dict:
    """
    Aggregate walk-forward backtest results.
    
    Args:
        results: List of BacktestResult from walk-forward
        
    Returns:
        Dict with aggregated metrics
    """
    if not results:
        return {}
    
    # Combine returns
    all_returns = pd.concat([r.returns for r in results])
    
    # Calculate aggregate metrics
    config = results[0].config
    aggregate = BacktestResult(config=config)
    aggregate.returns = all_returns
    
    # Equity curve
    aggregate.equity_curve = (1 + all_returns).cumprod() * config.initial_capital
    
    # Drawdowns
    running_max = aggregate.equity_curve.expanding().max()
    aggregate.drawdowns = (aggregate.equity_curve - running_max) / running_max
    
    aggregate = _calculate_metrics(aggregate, all_returns, config)
    
    # Per-period statistics
    period_sharpes = [r.sharpe_ratio for r in results]
    period_returns = [r.total_return for r in results]
    
    return {
        'aggregate': aggregate.to_dict(),
        'periods': len(results),
        'avg_period_return': np.mean(period_returns),
        'std_period_return': np.std(period_returns),
        'avg_period_sharpe': np.mean(period_sharpes),
        'pct_positive_periods': np.mean([r > 0 for r in period_returns]) * 100,
    }


# ==============================================================================
# TRADE ANALYSIS
# ==============================================================================

def extract_trades(
    prices: pd.Series,
    signals: pd.Series,
    symbol: str = 'UNKNOWN'
) -> List[Trade]:
    """
    Extract individual trades from signals.
    
    Args:
        prices: Price series
        signals: Signal series
        symbol: Symbol name
        
    Returns:
        List of Trade objects
    """
    trades = []
    
    # Detect position changes
    position_changes = signals.diff().fillna(signals)
    
    # Track open position
    in_position = False
    entry_date = None
    entry_price = None
    entry_signal = 0
    
    for date, change in position_changes.items():
        current_signal = signals.loc[date]
        current_price = prices.loc[date]
        
        if not in_position and current_signal != 0:
            # Open position
            in_position = True
            entry_date = date
            entry_price = current_price
            entry_signal = current_signal
            
        elif in_position and current_signal == 0:
            # Close position
            exit_date = date
            exit_price = current_price
            
            # Calculate P&L
            if entry_signal > 0:  # Long
                pnl_pct = (exit_price - entry_price) / entry_price
                side = 'long'
            else:  # Short
                pnl_pct = (entry_price - exit_price) / entry_price
                side = 'short'
            
            shares = 100  # Placeholder
            pnl = pnl_pct * shares * entry_price
            
            trade = Trade(
                entry_date=entry_date,
                exit_date=exit_date,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=0,
                slippage=0,
            )
            trades.append(trade)
            
            in_position = False
            
        elif in_position and np.sign(current_signal) != np.sign(entry_signal):
            # Flip position
            # First close existing
            exit_date = date
            exit_price = current_price
            
            if entry_signal > 0:
                pnl_pct = (exit_price - entry_price) / entry_price
                side = 'long'
            else:
                pnl_pct = (entry_price - exit_price) / entry_price
                side = 'short'
            
            shares = 100
            pnl = pnl_pct * shares * entry_price
            
            trade = Trade(
                entry_date=entry_date,
                exit_date=exit_date,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=0,
                slippage=0,
            )
            trades.append(trade)
            
            # Open new position
            entry_date = date
            entry_price = current_price
            entry_signal = current_signal
    
    return trades


def analyze_trades(trades: List[Trade]) -> Dict:
    """
    Analyze trade statistics.
    
    Args:
        trades: List of Trade objects
        
    Returns:
        Dict with trade statistics
    """
    if not trades:
        return {'num_trades': 0}
    
    pnls = [t.pnl for t in trades]
    pnl_pcts = [t.pnl_pct for t in trades]
    
    winning_trades = [t for t in trades if t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl <= 0]
    
    stats = {
        'num_trades': len(trades),
        'num_winning': len(winning_trades),
        'num_losing': len(losing_trades),
        'win_rate': len(winning_trades) / len(trades) * 100,
        'avg_pnl': np.mean(pnls),
        'avg_pnl_pct': np.mean(pnl_pcts) * 100,
        'total_pnl': sum(pnls),
        'max_win': max(pnls) if pnls else 0,
        'max_loss': min(pnls) if pnls else 0,
        'avg_win': np.mean([t.pnl for t in winning_trades]) if winning_trades else 0,
        'avg_loss': np.mean([t.pnl for t in losing_trades]) if losing_trades else 0,
    }
    
    # Profit factor
    gross_profit = sum(t.pnl for t in winning_trades)
    gross_loss = abs(sum(t.pnl for t in losing_trades))
    stats['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else np.inf
    
    # Holding period
    holding_periods = [(t.exit_date - t.entry_date).days for t in trades]
    stats['avg_holding_days'] = np.mean(holding_periods)
    
    return stats
