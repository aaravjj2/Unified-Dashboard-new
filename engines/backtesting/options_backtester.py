"""
Options Spread Backtester Engine
Phase 7 - Backtesting & Simulation (Items 511-530)

Fast vectorized backtesting engine for options spreads using numpy/pandas.
Provides:
- Vectorized PnL calculations
- Walk-forward optimization
- Monte Carlo simulations
- Performance metrics (Sharpe, Sortino, Max Drawdown)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Union
from enum import Enum
from datetime import datetime, timedelta
import warnings
import logging

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Options strategy types supported for backtesting."""
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    COVERED_CALL = "covered_call"
    CASH_SECURED_PUT = "cash_secured_put"
    CALL_SPREAD = "call_spread"
    PUT_SPREAD = "put_spread"
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    CALENDAR = "calendar"
    BUTTERFLY = "butterfly"
    JADE_LIZARD = "jade_lizard"


@dataclass
class BacktestConfig:
    """Configuration for backtest run."""
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    position_size_pct: float = 0.05  # 5% per trade
    max_positions: int = 10
    slippage_pct: float = 0.001  # 0.1%
    commission_per_contract: float = 0.65
    min_days_to_expiry: int = 7
    max_days_to_expiry: int = 45
    delta_target: float = 0.30
    iv_rank_min: float = 25.0
    profit_target_pct: float = 50.0  # Close at 50% profit
    stop_loss_pct: float = 200.0  # Close at 200% loss
    use_walk_forward: bool = False
    walk_forward_window: int = 252  # 1 year
    walk_forward_step: int = 21  # 1 month
    monte_carlo_runs: int = 1000
    random_seed: int = 42


@dataclass
class TradeResult:
    """Single trade result."""
    trade_id: int
    entry_date: datetime
    exit_date: datetime
    strategy: StrategyType
    ticker: str
    entry_price: float
    exit_price: float
    contracts: int
    pnl: float
    pnl_pct: float
    days_held: int
    exit_reason: str
    max_profit: float
    max_loss: float
    entry_iv: float
    exit_iv: float


@dataclass
class BacktestResult:
    """Complete backtest results."""
    config: BacktestConfig
    trades: List[TradeResult]
    equity_curve: pd.Series
    daily_returns: pd.Series
    
    # Performance metrics
    total_return: float = 0.0
    cagr: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_days_held: float = 0.0
    
    # Risk metrics
    var_95: float = 0.0
    cvar_95: float = 0.0
    calmar_ratio: float = 0.0
    
    # Monthly/yearly breakdown
    monthly_returns: Optional[pd.Series] = None
    yearly_returns: Optional[pd.Series] = None


class VectorizedBacktester:
    """
    Fast vectorized backtester for options spreads.
    
    Uses numpy/pandas for vectorized calculations where possible.
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        np.random.seed(config.random_seed)
        self._trades: List[TradeResult] = []
        self._equity = config.initial_capital
        self._equity_history: List[Tuple[datetime, float]] = []
        
    def run_backtest(
        self,
        price_data: pd.DataFrame,
        iv_data: pd.DataFrame,
        strategy: StrategyType,
        entry_signals: pd.Series,
        custom_sizing: Optional[Callable] = None,
    ) -> BacktestResult:
        """
        Run vectorized backtest.
        
        Args:
            price_data: DataFrame with OHLCV data
            iv_data: DataFrame with IV data (columns: iv, iv_rank, iv_percentile)
            strategy: Strategy type to backtest
            entry_signals: Boolean series indicating entry points
            custom_sizing: Optional custom position sizing function
            
        Returns:
            BacktestResult with all metrics
        """
        logger.info(f"Running backtest for {strategy.value} from {self.config.start_date} to {self.config.end_date}")
        
        # Filter data to date range
        price_data = price_data.loc[self.config.start_date:self.config.end_date].copy()
        iv_data = iv_data.loc[self.config.start_date:self.config.end_date].copy()
        
        # Reset state
        self._trades = []
        self._equity = self.config.initial_capital
        self._equity_history = [(price_data.index[0], self._equity)]
        
        # Track open positions
        open_positions = []
        trade_id = 0
        
        # Vectorized entry signal processing
        entry_dates = entry_signals[entry_signals].index
        
        for current_date in price_data.index:
            current_price = price_data.loc[current_date, 'close']
            current_iv = iv_data.loc[current_date, 'iv'] if current_date in iv_data.index else 0.2
            current_iv_rank = iv_data.loc[current_date, 'iv_rank'] if current_date in iv_data.index else 50.0
            
            # Check exits for open positions
            positions_to_close = []
            for pos in open_positions:
                pnl_pct = self._calculate_position_pnl_pct(pos, current_price, current_iv)
                days_held = (current_date - pos['entry_date']).days
                
                # Check exit conditions
                exit_reason = None
                if pnl_pct >= self.config.profit_target_pct:
                    exit_reason = "profit_target"
                elif pnl_pct <= -self.config.stop_loss_pct:
                    exit_reason = "stop_loss"
                elif days_held >= pos['dte']:
                    exit_reason = "expiration"
                
                if exit_reason:
                    positions_to_close.append((pos, current_date, current_price, current_iv, exit_reason))
            
            # Close positions
            for pos, exit_date, exit_price, exit_iv, exit_reason in positions_to_close:
                self._close_position(pos, exit_date, exit_price, exit_iv, exit_reason)
                open_positions.remove(pos)
            
            # Check entries
            if current_date in entry_dates and len(open_positions) < self.config.max_positions:
                if current_iv_rank >= self.config.iv_rank_min:
                    trade_id += 1
                    position = self._open_position(
                        trade_id, current_date, current_price, current_iv, 
                        current_iv_rank, strategy, custom_sizing
                    )
                    if position:
                        open_positions.append(position)
            
            # Update equity history
            position_value = sum(
                self._calculate_position_value(pos, current_price, current_iv)
                for pos in open_positions
            )
            total_equity = self._equity + position_value
            self._equity_history.append((current_date, total_equity))
        
        # Close any remaining open positions at end
        final_date = price_data.index[-1]
        final_price = price_data.iloc[-1]['close']
        final_iv = iv_data.iloc[-1]['iv'] if len(iv_data) > 0 else 0.2
        
        for pos in open_positions:
            self._close_position(pos, final_date, final_price, final_iv, "end_of_backtest")
        
        # Calculate results
        return self._calculate_results()
    
    def _open_position(
        self,
        trade_id: int,
        entry_date: datetime,
        price: float,
        iv: float,
        iv_rank: float,
        strategy: StrategyType,
        custom_sizing: Optional[Callable] = None,
    ) -> Optional[Dict]:
        """Open a new position."""
        
        # Calculate position size
        if custom_sizing:
            contracts = custom_sizing(self._equity, price, iv)
        else:
            position_value = self._equity * self.config.position_size_pct
            # Approximate contracts based on notional
            contracts = max(1, int(position_value / (price * 100)))
        
        # Estimate entry premium based on strategy
        entry_premium = self._estimate_option_premium(price, iv, strategy)
        
        # Apply slippage
        entry_premium *= (1 + self.config.slippage_pct)
        
        # Calculate commission
        commission = contracts * self.config.commission_per_contract
        if strategy in [StrategyType.IRON_CONDOR, StrategyType.IRON_BUTTERFLY]:
            commission *= 4  # 4 legs
        elif strategy in [StrategyType.CALL_SPREAD, StrategyType.PUT_SPREAD, StrategyType.STRADDLE]:
            commission *= 2  # 2 legs
        
        # Update equity
        if self._is_credit_strategy(strategy):
            self._equity += entry_premium * contracts * 100 - commission
        else:
            self._equity -= entry_premium * contracts * 100 + commission
        
        return {
            'trade_id': trade_id,
            'entry_date': entry_date,
            'strategy': strategy,
            'entry_price': entry_premium,
            'contracts': contracts,
            'entry_iv': iv,
            'underlying_price': price,
            'dte': np.random.randint(self.config.min_days_to_expiry, self.config.max_days_to_expiry),
            'commission': commission,
            'max_profit': 0,
            'max_loss': 0,
        }
    
    def _close_position(
        self,
        position: Dict,
        exit_date: datetime,
        exit_price: float,
        exit_iv: float,
        exit_reason: str,
    ):
        """Close an existing position."""
        
        # Calculate exit premium
        exit_premium = self._calculate_exit_premium(position, exit_price, exit_iv)
        
        # Apply slippage
        exit_premium *= (1 - self.config.slippage_pct)
        
        # Calculate P&L
        contracts = position['contracts']
        if self._is_credit_strategy(position['strategy']):
            pnl = (position['entry_price'] - exit_premium) * contracts * 100
        else:
            pnl = (exit_premium - position['entry_price']) * contracts * 100
        
        # Subtract closing commission
        commission = position['commission']
        pnl -= commission
        
        # Update equity
        self._equity += pnl
        
        # Calculate P&L percentage
        if self._is_credit_strategy(position['strategy']):
            max_risk = self._calculate_max_risk(position)
            pnl_pct = (pnl / max_risk) * 100 if max_risk > 0 else 0
        else:
            initial_investment = position['entry_price'] * contracts * 100
            pnl_pct = (pnl / initial_investment) * 100 if initial_investment > 0 else 0
        
        # Create trade result
        trade = TradeResult(
            trade_id=position['trade_id'],
            entry_date=position['entry_date'],
            exit_date=exit_date,
            strategy=position['strategy'],
            ticker="SPY",  # Default for now
            entry_price=position['entry_price'],
            exit_price=exit_premium,
            contracts=contracts,
            pnl=pnl,
            pnl_pct=pnl_pct,
            days_held=(exit_date - position['entry_date']).days,
            exit_reason=exit_reason,
            max_profit=position['max_profit'],
            max_loss=position['max_loss'],
            entry_iv=position['entry_iv'],
            exit_iv=exit_iv,
        )
        self._trades.append(trade)
    
    def _calculate_position_pnl_pct(self, position: Dict, price: float, iv: float) -> float:
        """Calculate current P&L percentage for a position."""
        current_premium = self._calculate_exit_premium(position, price, iv)
        
        if self._is_credit_strategy(position['strategy']):
            pnl = (position['entry_price'] - current_premium)
            max_risk = self._calculate_max_risk(position)
            return (pnl / max_risk) * 100 if max_risk > 0 else 0
        else:
            pnl = (current_premium - position['entry_price'])
            return (pnl / position['entry_price']) * 100 if position['entry_price'] > 0 else 0
    
    def _calculate_position_value(self, position: Dict, price: float, iv: float) -> float:
        """Calculate current position value."""
        current_premium = self._calculate_exit_premium(position, price, iv)
        contracts = position['contracts']
        
        if self._is_credit_strategy(position['strategy']):
            return -current_premium * contracts * 100
        else:
            return current_premium * contracts * 100
    
    def _estimate_option_premium(self, price: float, iv: float, strategy: StrategyType) -> float:
        """Estimate option premium based on strategy type."""
        # Simplified Black-Scholes approximation for ATM options
        atm_premium = price * iv * np.sqrt(30/365) * 0.4  # ~30 DTE
        
        if strategy in [StrategyType.LONG_CALL, StrategyType.LONG_PUT]:
            return atm_premium
        elif strategy in [StrategyType.SHORT_CALL, StrategyType.SHORT_PUT]:
            return atm_premium
        elif strategy in [StrategyType.CALL_SPREAD, StrategyType.PUT_SPREAD]:
            return atm_premium * 0.5  # Spread captures ~50% of single leg
        elif strategy == StrategyType.IRON_CONDOR:
            return atm_premium * 0.4  # IC collects ~40% of straddle
        elif strategy == StrategyType.IRON_BUTTERFLY:
            return atm_premium * 0.6  # IB collects more premium
        elif strategy in [StrategyType.STRADDLE, StrategyType.STRANGLE]:
            return atm_premium * 1.8  # Two legs
        else:
            return atm_premium
    
    def _calculate_exit_premium(self, position: Dict, price: float, iv: float) -> float:
        """Calculate current option premium for exit."""
        strategy = position['strategy']
        entry_price = position['underlying_price']
        
        # Price change effect
        price_change_pct = (price - entry_price) / entry_price
        
        # IV change effect
        iv_change = iv - position['entry_iv']
        
        # Time decay (simplified)
        entry_date = position['entry_date']
        dte = position['dte']
        days_elapsed = min(dte, 30)  # Cap at original DTE
        theta_decay = 1 - (days_elapsed / dte) ** 0.5  # Square root decay
        
        # Base premium adjusted for changes
        base_premium = position['entry_price']
        
        if strategy in [StrategyType.LONG_CALL, StrategyType.SHORT_CALL]:
            premium = base_premium * theta_decay * (1 + price_change_pct * 0.5) * (1 + iv_change)
        elif strategy in [StrategyType.LONG_PUT, StrategyType.SHORT_PUT]:
            premium = base_premium * theta_decay * (1 - price_change_pct * 0.5) * (1 + iv_change)
        elif strategy == StrategyType.IRON_CONDOR:
            # IC loses value as underlying moves away from center
            move = abs(price_change_pct)
            premium = base_premium * theta_decay * (1 - move * 0.3) * (1 + iv_change * 0.5)
        else:
            premium = base_premium * theta_decay * (1 + iv_change * 0.5)
        
        return max(0, premium)
    
    def _calculate_max_risk(self, position: Dict) -> float:
        """Calculate maximum risk for a position."""
        strategy = position['strategy']
        contracts = position['contracts']
        price = position['underlying_price']
        
        if strategy == StrategyType.IRON_CONDOR:
            # Width minus premium
            spread_width = price * 0.05  # ~5% spread width
            return (spread_width - position['entry_price']) * contracts * 100
        elif strategy in [StrategyType.CALL_SPREAD, StrategyType.PUT_SPREAD]:
            spread_width = price * 0.03  # ~3% spread width
            return (spread_width - position['entry_price']) * contracts * 100
        elif strategy in [StrategyType.SHORT_CALL, StrategyType.SHORT_PUT]:
            return price * contracts * 100  # Unlimited risk approximated
        else:
            return position['entry_price'] * contracts * 100
    
    def _is_credit_strategy(self, strategy: StrategyType) -> bool:
        """Check if strategy is credit-based."""
        credit_strategies = [
            StrategyType.SHORT_CALL,
            StrategyType.SHORT_PUT,
            StrategyType.COVERED_CALL,
            StrategyType.CASH_SECURED_PUT,
            StrategyType.IRON_CONDOR,
            StrategyType.IRON_BUTTERFLY,
        ]
        # Credit spreads
        if "spread" in strategy.value.lower():
            return True  # Assuming selling spreads
        return strategy in credit_strategies
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate all performance metrics."""
        
        # Create equity curve
        equity_df = pd.DataFrame(self._equity_history, columns=['date', 'equity'])
        equity_df.set_index('date', inplace=True)
        equity_curve = equity_df['equity']
        
        # Daily returns
        daily_returns = equity_curve.pct_change().dropna()
        
        # Basic metrics
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
        
        # CAGR
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365
        cagr = ((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        
        # Sortino ratio
        downside_returns = daily_returns[daily_returns < 0]
        sortino = np.sqrt(252) * daily_returns.mean() / downside_returns.std() if len(downside_returns) > 0 else 0
        
        # Max drawdown
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        # Max drawdown duration
        in_drawdown = drawdown < 0
        dd_groups = (~in_drawdown).cumsum()
        dd_durations = in_drawdown.groupby(dd_groups).sum()
        max_drawdown_duration = int(dd_durations.max()) if len(dd_durations) > 0 else 0
        
        # Trade statistics
        if self._trades:
            wins = [t for t in self._trades if t.pnl > 0]
            losses = [t for t in self._trades if t.pnl <= 0]
            
            win_rate = len(wins) / len(self._trades) * 100
            avg_win = np.mean([t.pnl for t in wins]) if wins else 0
            avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
            
            total_wins = sum(t.pnl for t in wins) if wins else 0
            total_losses = abs(sum(t.pnl for t in losses)) if losses else 1
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
            avg_days_held = np.mean([t.days_held for t in self._trades])
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            expectancy = 0
            avg_days_held = 0
            wins = []
            losses = []
        
        # VaR and CVaR
        var_95 = np.percentile(daily_returns, 5) * 100 if len(daily_returns) > 0 else 0
        cvar_95 = daily_returns[daily_returns <= np.percentile(daily_returns, 5)].mean() * 100 if len(daily_returns) > 0 else 0
        
        # Calmar ratio
        calmar = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Monthly returns
        monthly_returns = daily_returns.resample('ME').apply(lambda x: (1 + x).prod() - 1) * 100
        
        # Yearly returns
        yearly_returns = daily_returns.resample('YE').apply(lambda x: (1 + x).prod() - 1) * 100
        
        return BacktestResult(
            config=self.config,
            trades=self._trades,
            equity_curve=equity_curve,
            daily_returns=daily_returns,
            total_return=total_return,
            cagr=cagr,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            total_trades=len(self._trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            avg_days_held=avg_days_held,
            var_95=var_95,
            cvar_95=cvar_95,
            calmar_ratio=calmar,
            monthly_returns=monthly_returns,
            yearly_returns=yearly_returns,
        )


class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy robustness testing.
    
    Performs bootstrap resampling of trade returns to generate
    distribution of possible outcomes.
    """
    
    def __init__(self, n_simulations: int = 1000, random_seed: int = 42):
        self.n_simulations = n_simulations
        np.random.seed(random_seed)
    
    def run_simulation(
        self,
        trade_results: List[TradeResult],
        initial_capital: float = 100000,
        n_trades_per_sim: Optional[int] = None,
    ) -> Dict:
        """
        Run Monte Carlo simulation.
        
        Args:
            trade_results: List of historical trade results
            initial_capital: Starting capital
            n_trades_per_sim: Number of trades per simulation (default: same as historical)
            
        Returns:
            Dictionary with simulation results
        """
        if not trade_results:
            return {"error": "No trades to simulate"}
        
        n_trades = n_trades_per_sim or len(trade_results)
        returns = np.array([t.pnl for t in trade_results])
        
        # Run simulations
        final_equities = []
        max_drawdowns = []
        
        for _ in range(self.n_simulations):
            # Bootstrap sample trades
            sampled_returns = np.random.choice(returns, size=n_trades, replace=True)
            
            # Build equity curve
            equity = initial_capital
            equity_curve = [equity]
            
            for ret in sampled_returns:
                equity += ret
                equity_curve.append(equity)
            
            equity_curve = np.array(equity_curve)
            final_equities.append(equity_curve[-1])
            
            # Calculate max drawdown
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (equity_curve - peak) / peak
            max_drawdowns.append(drawdown.min() * 100)
        
        final_equities = np.array(final_equities)
        max_drawdowns = np.array(max_drawdowns)
        
        return {
            "median_final_equity": np.median(final_equities),
            "mean_final_equity": np.mean(final_equities),
            "std_final_equity": np.std(final_equities),
            "percentile_5": np.percentile(final_equities, 5),
            "percentile_25": np.percentile(final_equities, 25),
            "percentile_75": np.percentile(final_equities, 75),
            "percentile_95": np.percentile(final_equities, 95),
            "probability_profit": (final_equities > initial_capital).mean() * 100,
            "probability_double": (final_equities > initial_capital * 2).mean() * 100,
            "probability_ruin": (final_equities < initial_capital * 0.5).mean() * 100,
            "median_max_drawdown": np.median(max_drawdowns),
            "worst_max_drawdown": np.min(max_drawdowns),
            "best_max_drawdown": np.max(max_drawdowns),
            "all_final_equities": final_equities.tolist(),
        }


class WalkForwardOptimizer:
    """
    Walk-forward optimization for strategy parameters.
    
    Splits data into in-sample (training) and out-of-sample (testing)
    windows to avoid overfitting.
    """
    
    def __init__(
        self,
        window_size: int = 252,  # Trading days
        step_size: int = 21,  # Month
        min_trades: int = 10,
    ):
        self.window_size = window_size
        self.step_size = step_size
        self.min_trades = min_trades
    
    def optimize(
        self,
        price_data: pd.DataFrame,
        iv_data: pd.DataFrame,
        strategy: StrategyType,
        param_grid: Dict[str, List],
        objective: str = "sharpe",  # sharpe, sortino, profit_factor
    ) -> Dict:
        """
        Run walk-forward optimization.
        
        Args:
            price_data: Historical price data
            iv_data: Historical IV data
            strategy: Strategy to optimize
            param_grid: Parameter grid to search
            objective: Optimization objective
            
        Returns:
            Optimization results with best parameters
        """
        results = []
        dates = price_data.index
        
        # Walk-forward windows
        for start_idx in range(0, len(dates) - self.window_size, self.step_size):
            train_end = start_idx + self.window_size
            test_end = min(train_end + self.step_size, len(dates))
            
            train_dates = dates[start_idx:train_end]
            test_dates = dates[train_end:test_end]
            
            if len(test_dates) < 5:
                continue
            
            # In-sample optimization
            best_params = None
            best_score = float('-inf')
            
            for params in self._generate_param_combinations(param_grid):
                config = BacktestConfig(
                    start_date=str(train_dates[0].date()),
                    end_date=str(train_dates[-1].date()),
                    **params
                )
                
                backtester = VectorizedBacktester(config)
                
                # Simple entry signal for optimization
                entry_signals = pd.Series(False, index=dates)
                entry_signals.iloc[::5] = True  # Entry every 5 days
                
                result = backtester.run_backtest(
                    price_data, iv_data, strategy, entry_signals
                )
                
                if result.total_trades >= self.min_trades:
                    score = getattr(result, objective + "_ratio" if objective in ["sharpe", "sortino"] else objective, 0)
                    if score > best_score:
                        best_score = score
                        best_params = params
            
            # Out-of-sample test with best params
            if best_params:
                config = BacktestConfig(
                    start_date=str(test_dates[0].date()),
                    end_date=str(test_dates[-1].date()),
                    **best_params
                )
                
                backtester = VectorizedBacktester(config)
                entry_signals = pd.Series(False, index=dates)
                entry_signals.iloc[::5] = True
                
                oos_result = backtester.run_backtest(
                    price_data, iv_data, strategy, entry_signals
                )
                
                results.append({
                    'train_start': train_dates[0],
                    'train_end': train_dates[-1],
                    'test_start': test_dates[0],
                    'test_end': test_dates[-1],
                    'best_params': best_params,
                    'in_sample_score': best_score,
                    'out_of_sample_return': oos_result.total_return,
                    'out_of_sample_sharpe': oos_result.sharpe_ratio,
                })
        
        return {
            'windows': results,
            'avg_oos_return': np.mean([r['out_of_sample_return'] for r in results]) if results else 0,
            'avg_oos_sharpe': np.mean([r['out_of_sample_sharpe'] for r in results]) if results else 0,
        }
    
    def _generate_param_combinations(self, param_grid: Dict[str, List]) -> List[Dict]:
        """Generate all parameter combinations."""
        from itertools import product
        
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        combinations = []
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))
        
        return combinations


# Utility functions for quick backtesting
def quick_backtest(
    ticker: str = "SPY",
    strategy: StrategyType = StrategyType.IRON_CONDOR,
    start_date: str = "2023-01-01",
    end_date: str = "2024-12-31",
    initial_capital: float = 100000,
) -> BacktestResult:
    """
    Quick backtest with synthetic data.
    
    Args:
        ticker: Stock ticker
        strategy: Strategy to test
        start_date: Start date
        end_date: End date
        initial_capital: Starting capital
        
    Returns:
        BacktestResult
    """
    # Generate synthetic price data
    dates = pd.date_range(start_date, end_date, freq='B')
    n_days = len(dates)
    
    # Random walk price
    returns = np.random.normal(0.0005, 0.012, n_days)  # ~12% annual vol
    price = 450 * np.cumprod(1 + returns)  # Start at 450
    
    price_data = pd.DataFrame({
        'open': price * (1 + np.random.uniform(-0.002, 0.002, n_days)),
        'high': price * (1 + np.random.uniform(0, 0.01, n_days)),
        'low': price * (1 - np.random.uniform(0, 0.01, n_days)),
        'close': price,
        'volume': np.random.randint(50000000, 150000000, n_days),
    }, index=dates)
    
    # Synthetic IV data
    base_iv = 0.18
    iv = base_iv + np.random.normal(0, 0.03, n_days)
    iv = np.clip(iv, 0.10, 0.50)
    
    iv_data = pd.DataFrame({
        'iv': iv,
        'iv_rank': np.random.uniform(20, 80, n_days),
        'iv_percentile': np.random.uniform(20, 80, n_days),
    }, index=dates)
    
    # Entry signals - enter when IV rank > 30
    entry_signals = iv_data['iv_rank'] > 30
    
    # Run backtest
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )
    
    backtester = VectorizedBacktester(config)
    return backtester.run_backtest(price_data, iv_data, strategy, entry_signals)


if __name__ == "__main__":
    # Example usage
    print("Running quick backtest...")
    result = quick_backtest(strategy=StrategyType.IRON_CONDOR)
    
    print(f"\n=== Backtest Results ===")
    print(f"Total Return: {result.total_return:.2f}%")
    print(f"CAGR: {result.cagr:.2f}%")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio: {result.sortino_ratio:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.2f}%")
    print(f"Win Rate: {result.win_rate:.2f}%")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    print(f"Total Trades: {result.total_trades}")
    print(f"Avg Days Held: {result.avg_days_held:.1f}")
    
    # Monte Carlo
    print("\n=== Monte Carlo Simulation ===")
    mc = MonteCarloSimulator(n_simulations=1000)
    mc_results = mc.run_simulation(result.trades)
    
    print(f"Probability of Profit: {mc_results['probability_profit']:.1f}%")
    print(f"Probability of Doubling: {mc_results['probability_double']:.1f}%")
    print(f"Probability of Ruin (50% loss): {mc_results['probability_ruin']:.1f}%")
    print(f"Median Final Equity: ${mc_results['median_final_equity']:,.0f}")
