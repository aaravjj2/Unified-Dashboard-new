"""
Backtesting & Simulation Module
===============================
Strategy backtesting and simulation tools:
- Strategy backtester
- Monte Carlo simulator
- Walk-forward optimizer
- Scenario analyzer
- Paper trade simulator

Author: AI/ML Options Lab
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class BacktestTrade:
    """Single trade in backtest."""
    entry_date: datetime
    exit_date: datetime
    ticker: str
    strategy: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    holding_days: int
    exit_reason: str


@dataclass
class BacktestResult:
    """Complete backtest results."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    
    # Performance metrics
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Risk metrics
    avg_holding_days: float
    max_consecutive_losses: int
    
    # Trade list
    trades: List[BacktestTrade]
    
    # Equity curve
    equity_curve: List[float]


@dataclass
class MonteCarloResult:
    """Monte Carlo simulation results."""
    strategy_name: str
    num_simulations: int
    
    # Distribution statistics
    mean_return: float
    median_return: float
    std_return: float
    
    # Percentiles
    pct_5: float
    pct_25: float
    pct_75: float
    pct_95: float
    
    # Probabilities
    prob_profit: float
    prob_20pct_gain: float
    prob_20pct_loss: float
    
    # Max drawdown distribution
    median_max_dd: float
    worst_max_dd: float


@dataclass
class WalkForwardResult:
    """Walk-forward optimization results."""
    strategy_name: str
    num_periods: int
    
    # In-sample vs out-of-sample
    avg_is_return: float
    avg_oos_return: float
    oos_degradation: float
    
    # Robustness
    consistency_score: float
    num_profitable_periods: int
    
    # Best parameters per period
    optimal_params_history: List[Dict]


@dataclass
class ScenarioResult:
    """Historical scenario analysis result."""
    scenario_name: str
    start_date: datetime
    end_date: datetime
    
    # Market conditions
    market_return: float
    vix_change: float
    
    # Strategy performance
    strategy_return: float
    max_drawdown: float
    
    # Comparison
    alpha: float
    beta: float


@dataclass
class PaperTrade:
    """Paper trade record."""
    trade_id: str
    timestamp: datetime
    ticker: str
    strategy: str
    action: str  # 'open', 'close', 'adjust'
    
    contracts: int
    fill_price: float
    slippage: float
    
    status: str  # 'open', 'closed'
    pnl: float


# ============================================================
# STRATEGY BACKTESTER
# ============================================================

class StrategyBacktester:
    """
    Backtest options strategies on historical data.
    """
    
    def __init__(self):
        self.commission = 0.65  # Per contract
        self.slippage_pct = 0.005  # 0.5% slippage
    
    def backtest(self, strategy_name: str, ticker: str,
                 start_date: datetime, end_date: datetime,
                 strategy_params: Dict = None) -> BacktestResult:
        """Run backtest for a strategy."""
        try:
            # Get historical data
            price_data = self._get_historical_data(ticker, start_date, end_date)
            
            if price_data.empty:
                price_data = self._generate_synthetic_data(start_date, end_date)
            
            # Run strategy
            trades = self._simulate_strategy(strategy_name, price_data, strategy_params)
            
            # Calculate metrics
            return self._calculate_metrics(strategy_name, trades, start_date, end_date)
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return self._empty_result(strategy_name, start_date, end_date)
    
    def _get_historical_data(self, ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Get historical price data."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            
            days = (end - start).days
            bars = client.get_historical_bars(ticker, '1Day', limit=days)
            return bars
        except:
            return pd.DataFrame()
    
    def _generate_synthetic_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Generate synthetic price data."""
        days = (end - start).days
        dates = [start + timedelta(days=i) for i in range(days)]
        
        # Random walk
        returns = np.random.normal(0.0003, 0.015, days)
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'date': dates,
            'c': prices,
            'h': prices * 1.01,
            'l': prices * 0.99,
            'v': np.random.exponential(1000000, days)
        })
    
    def _simulate_strategy(self, strategy: str, data: pd.DataFrame,
                           params: Dict = None) -> List[BacktestTrade]:
        """Simulate strategy on data."""
        trades = []
        
        if params is None:
            params = {'dte': 30, 'profit_target': 50, 'stop_loss': 100}
        
        prices = data['c'].values if 'c' in data else data.iloc[:, 0].values
        dates = data['date'].values if 'date' in data else [datetime.now() + timedelta(days=i) for i in range(len(prices))]
        
        # Simple entry logic: enter every 30 days
        entry_interval = params.get('entry_interval', 30)
        profit_target = params.get('profit_target', 50) / 100
        stop_loss = params.get('stop_loss', 100) / 100
        holding_days = params.get('dte', 30)
        
        i = 0
        while i < len(prices) - holding_days:
            entry_price = prices[i]
            entry_date = dates[i]
            
            # Simulate option behavior (simplified)
            max_pnl = 0
            min_pnl = 0
            exit_day = min(i + holding_days, len(prices) - 1)
            exit_reason = 'expiration'
            
            for j in range(i, exit_day):
                price_change = (prices[j] - entry_price) / entry_price
                
                # Premium selling strategies profit from theta + limited directional
                if strategy in ['iron_condor', 'bull_put_spread', 'bear_call_spread']:
                    # Start with credit, decay helps
                    days_held = j - i
                    theta_decay = 1 - (holding_days - days_held) / holding_days
                    
                    # Directional impact
                    if abs(price_change) < 0.05:  # Stay in range
                        current_pnl = theta_decay * profit_target
                    else:
                        current_pnl = -abs(price_change) * 2  # Loss when out of range
                else:
                    # Buying strategies - directional
                    current_pnl = price_change
                
                max_pnl = max(max_pnl, current_pnl)
                min_pnl = min(min_pnl, current_pnl)
                
                # Check exits
                if current_pnl >= profit_target:
                    exit_day = j
                    exit_reason = 'profit_target'
                    break
                elif current_pnl <= -stop_loss:
                    exit_day = j
                    exit_reason = 'stop_loss'
                    break
            
            # Calculate final P&L
            final_pnl = max_pnl if exit_reason == 'profit_target' else min_pnl if exit_reason == 'stop_loss' else theta_decay * profit_target * 0.7
            
            trades.append(BacktestTrade(
                entry_date=entry_date if isinstance(entry_date, datetime) else datetime.now(),
                exit_date=dates[exit_day] if isinstance(dates[exit_day], datetime) else datetime.now(),
                ticker='SPY',
                strategy=strategy,
                entry_price=entry_price,
                exit_price=prices[exit_day],
                pnl=final_pnl * 100,  # Dollar P&L on $100 position
                pnl_pct=final_pnl * 100,
                holding_days=exit_day - i,
                exit_reason=exit_reason
            ))
            
            i = exit_day + 1
        
        return trades
    
    def _calculate_metrics(self, strategy: str, trades: List[BacktestTrade],
                           start: datetime, end: datetime) -> BacktestResult:
        """Calculate backtest metrics."""
        if not trades:
            return self._empty_result(strategy, start, end)
        
        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        total_return = sum(pnls)
        days = (end - start).days
        ann_return = (1 + total_return/1000) ** (365/days) - 1 if days > 0 else 0
        
        # Sharpe (simplified)
        if len(pnls) > 1:
            sharpe = np.mean(pnls) / (np.std(pnls) + 0.01) * np.sqrt(12)  # Monthly trades
            sortino = np.mean(pnls) / (np.std([p for p in pnls if p < 0]) + 0.01) * np.sqrt(12)
        else:
            sharpe = sortino = 0
        
        # Max drawdown
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative)
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Win rate
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0
        
        # Consecutive losses
        max_consec = 0
        current_consec = 0
        for p in pnls:
            if p < 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0
        
        return BacktestResult(
            strategy_name=strategy,
            start_date=start,
            end_date=end,
            total_return=round(total_return, 2),
            annualized_return=round(ann_return * 100, 2),
            sharpe_ratio=round(sharpe, 3),
            sortino_ratio=round(sortino, 3),
            max_drawdown=round(max_dd, 2),
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=round(win_rate, 3),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 3),
            avg_holding_days=round(np.mean([t.holding_days for t in trades]), 1),
            max_consecutive_losses=max_consec,
            trades=trades,
            equity_curve=list(np.cumsum(pnls))
        )
    
    def _empty_result(self, strategy: str, start: datetime, end: datetime) -> BacktestResult:
        return BacktestResult(
            strategy_name=strategy,
            start_date=start,
            end_date=end,
            total_return=0,
            annualized_return=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            max_drawdown=0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            avg_win=0,
            avg_loss=0,
            profit_factor=0,
            avg_holding_days=0,
            max_consecutive_losses=0,
            trades=[],
            equity_curve=[]
        )


# ============================================================
# MONTE CARLO SIMULATOR
# ============================================================

class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy outcomes.
    """
    
    def __init__(self, num_simulations: int = 10000):
        self.num_simulations = num_simulations
    
    def simulate(self, strategy_name: str,
                 win_rate: float, avg_win: float, avg_loss: float,
                 trades_per_year: int = 50) -> MonteCarloResult:
        """Run Monte Carlo simulation."""
        try:
            results = []
            max_dds = []
            
            for _ in range(self.num_simulations):
                # Simulate one year
                pnls = []
                for _ in range(trades_per_year):
                    if np.random.random() < win_rate:
                        pnl = avg_win * (1 + np.random.normal(0, 0.2))
                    else:
                        pnl = -avg_loss * (1 + np.random.normal(0, 0.2))
                    pnls.append(pnl)
                
                total_return = sum(pnls)
                results.append(total_return)
                
                # Max drawdown
                cumulative = np.cumsum(pnls)
                peak = np.maximum.accumulate(cumulative)
                dd = peak - cumulative
                max_dds.append(np.max(dd))
            
            results = np.array(results)
            max_dds = np.array(max_dds)
            
            return MonteCarloResult(
                strategy_name=strategy_name,
                num_simulations=self.num_simulations,
                mean_return=round(np.mean(results), 2),
                median_return=round(np.median(results), 2),
                std_return=round(np.std(results), 2),
                pct_5=round(np.percentile(results, 5), 2),
                pct_25=round(np.percentile(results, 25), 2),
                pct_75=round(np.percentile(results, 75), 2),
                pct_95=round(np.percentile(results, 95), 2),
                prob_profit=round(np.mean(results > 0), 3),
                prob_20pct_gain=round(np.mean(results > 20), 3),
                prob_20pct_loss=round(np.mean(results < -20), 3),
                median_max_dd=round(np.median(max_dds), 2),
                worst_max_dd=round(np.max(max_dds), 2)
            )
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {e}")
            return MonteCarloResult(
                strategy_name=strategy_name,
                num_simulations=0,
                mean_return=0,
                median_return=0,
                std_return=0,
                pct_5=0,
                pct_25=0,
                pct_75=0,
                pct_95=0,
                prob_profit=0.5,
                prob_20pct_gain=0,
                prob_20pct_loss=0,
                median_max_dd=0,
                worst_max_dd=0
            )


# ============================================================
# WALK-FORWARD OPTIMIZER
# ============================================================

class WalkForwardOptimizer:
    """
    Walk-forward optimization for robust parameter selection.
    """
    
    def __init__(self, is_period: int = 180, oos_period: int = 60):
        self.is_period = is_period  # In-sample days
        self.oos_period = oos_period  # Out-of-sample days
    
    def optimize(self, strategy_name: str, ticker: str,
                 param_ranges: Dict = None) -> WalkForwardResult:
        """Run walk-forward optimization."""
        try:
            if param_ranges is None:
                param_ranges = {
                    'profit_target': [30, 50, 70],
                    'stop_loss': [75, 100, 150],
                    'dte': [21, 30, 45]
                }
            
            backtester = StrategyBacktester()
            
            # Simulate multiple periods
            num_periods = 4
            is_returns = []
            oos_returns = []
            optimal_params = []
            
            for period in range(num_periods):
                # Generate period dates
                is_start = datetime.now() - timedelta(days=(num_periods-period)*(self.is_period+self.oos_period) + self.is_period)
                is_end = is_start + timedelta(days=self.is_period)
                oos_start = is_end
                oos_end = oos_start + timedelta(days=self.oos_period)
                
                # Find best params in-sample
                best_return = -float('inf')
                best_params = {}
                
                for pt in param_ranges.get('profit_target', [50]):
                    for sl in param_ranges.get('stop_loss', [100]):
                        for dte in param_ranges.get('dte', [30]):
                            params = {'profit_target': pt, 'stop_loss': sl, 'dte': dte}
                            result = backtester.backtest(strategy_name, ticker, is_start, is_end, params)
                            
                            if result.total_return > best_return:
                                best_return = result.total_return
                                best_params = params
                
                is_returns.append(best_return)
                optimal_params.append(best_params)
                
                # Test out-of-sample
                oos_result = backtester.backtest(strategy_name, ticker, oos_start, oos_end, best_params)
                oos_returns.append(oos_result.total_return)
            
            # Calculate metrics
            avg_is = np.mean(is_returns)
            avg_oos = np.mean(oos_returns)
            degradation = (avg_is - avg_oos) / avg_is * 100 if avg_is != 0 else 0
            
            consistency = np.mean([1 if oos > 0 else 0 for oos in oos_returns])
            
            return WalkForwardResult(
                strategy_name=strategy_name,
                num_periods=num_periods,
                avg_is_return=round(avg_is, 2),
                avg_oos_return=round(avg_oos, 2),
                oos_degradation=round(degradation, 2),
                consistency_score=round(consistency, 3),
                num_profitable_periods=sum(1 for r in oos_returns if r > 0),
                optimal_params_history=optimal_params
            )
            
        except Exception as e:
            logger.error(f"Walk-forward optimization failed: {e}")
            return WalkForwardResult(
                strategy_name=strategy_name,
                num_periods=0,
                avg_is_return=0,
                avg_oos_return=0,
                oos_degradation=0,
                consistency_score=0,
                num_profitable_periods=0,
                optimal_params_history=[]
            )


# ============================================================
# SCENARIO ANALYZER
# ============================================================

class ScenarioAnalyzer:
    """
    Analyze strategy performance in historical scenarios.
    """
    
    def __init__(self):
        self.scenarios = {
            'covid_crash': {'start': '2020-02-19', 'end': '2020-03-23', 'desc': 'COVID-19 Crash'},
            'covid_recovery': {'start': '2020-03-23', 'end': '2020-08-18', 'desc': 'V-shaped Recovery'},
            '2022_bear': {'start': '2022-01-03', 'end': '2022-10-12', 'desc': '2022 Bear Market'},
            'vix_spike_2018': {'start': '2018-02-01', 'end': '2018-02-09', 'desc': 'Volmageddon'},
            'bull_run_2021': {'start': '2021-01-04', 'end': '2021-12-31', 'desc': '2021 Bull Market'}
        }
    
    def analyze_scenario(self, strategy_name: str, scenario_name: str,
                         strategy_params: Dict = None) -> ScenarioResult:
        """Analyze strategy in specific scenario."""
        try:
            scenario = self.scenarios.get(scenario_name)
            if not scenario:
                scenario = {'start': '2023-01-01', 'end': '2023-12-31', 'desc': 'Custom'}
            
            start = datetime.strptime(scenario['start'], '%Y-%m-%d')
            end = datetime.strptime(scenario['end'], '%Y-%m-%d')
            
            # Run backtest
            backtester = StrategyBacktester()
            result = backtester.backtest(strategy_name, 'SPY', start, end, strategy_params)
            
            # Calculate market return (simplified)
            days = (end - start).days
            if 'crash' in scenario_name:
                market_return = -35
                vix_change = 200
            elif 'recovery' in scenario_name or 'bull' in scenario_name:
                market_return = 50
                vix_change = -30
            elif 'bear' in scenario_name:
                market_return = -25
                vix_change = 50
            else:
                market_return = 10
                vix_change = 0
            
            # Alpha and beta (simplified)
            alpha = result.total_return - market_return
            beta = result.total_return / market_return if market_return != 0 else 1
            
            return ScenarioResult(
                scenario_name=scenario['desc'],
                start_date=start,
                end_date=end,
                market_return=market_return,
                vix_change=vix_change,
                strategy_return=result.total_return,
                max_drawdown=result.max_drawdown,
                alpha=round(alpha, 2),
                beta=round(beta, 3)
            )
            
        except Exception as e:
            logger.error(f"Scenario analysis failed: {e}")
            return ScenarioResult(
                scenario_name='Unknown',
                start_date=datetime.now(),
                end_date=datetime.now(),
                market_return=0,
                vix_change=0,
                strategy_return=0,
                max_drawdown=0,
                alpha=0,
                beta=1
            )
    
    def stress_test_all(self, strategy_name: str) -> List[ScenarioResult]:
        """Run strategy through all scenarios."""
        results = []
        for scenario_name in self.scenarios:
            result = self.analyze_scenario(strategy_name, scenario_name)
            results.append(result)
        return results


# ============================================================
# PAPER TRADE SIMULATOR
# ============================================================

class PaperTradeSimulator:
    """
    Realistic paper trading simulation.
    """
    
    def __init__(self):
        self.trades: List[PaperTrade] = []
        self.positions: Dict[str, PaperTrade] = {}
        self.trade_counter = 0
    
    def open_trade(self, ticker: str, strategy: str,
                   contracts: int, target_price: float) -> PaperTrade:
        """Open a paper trade with realistic fill."""
        self.trade_counter += 1
        trade_id = f"PT{self.trade_counter:05d}"
        
        # Simulate slippage
        slippage = target_price * np.random.uniform(0.002, 0.008)
        fill_price = target_price + slippage
        
        trade = PaperTrade(
            trade_id=trade_id,
            timestamp=datetime.now(),
            ticker=ticker,
            strategy=strategy,
            action='open',
            contracts=contracts,
            fill_price=round(fill_price, 2),
            slippage=round(slippage, 2),
            status='open',
            pnl=0
        )
        
        self.trades.append(trade)
        self.positions[trade_id] = trade
        
        return trade
    
    def close_trade(self, trade_id: str, target_price: float) -> Optional[PaperTrade]:
        """Close a paper trade."""
        if trade_id not in self.positions:
            return None
        
        open_trade = self.positions[trade_id]
        
        # Simulate slippage on exit
        slippage = target_price * np.random.uniform(0.002, 0.008)
        fill_price = target_price - slippage  # Worse on exit
        
        # Calculate P&L
        pnl = (fill_price - open_trade.fill_price) * open_trade.contracts * 100
        
        close_trade = PaperTrade(
            trade_id=trade_id,
            timestamp=datetime.now(),
            ticker=open_trade.ticker,
            strategy=open_trade.strategy,
            action='close',
            contracts=open_trade.contracts,
            fill_price=round(fill_price, 2),
            slippage=round(slippage, 2),
            status='closed',
            pnl=round(pnl, 2)
        )
        
        self.trades.append(close_trade)
        del self.positions[trade_id]
        
        return close_trade
    
    def get_open_positions(self) -> List[PaperTrade]:
        """Get all open positions."""
        return list(self.positions.values())
    
    def get_trade_history(self) -> List[PaperTrade]:
        """Get all trade history."""
        return self.trades
    
    def get_statistics(self) -> Dict:
        """Get paper trading statistics."""
        closed = [t for t in self.trades if t.action == 'close']
        
        if not closed:
            return {'total_trades': 0, 'total_pnl': 0, 'win_rate': 0}
        
        pnls = [t.pnl for t in closed]
        wins = [p for p in pnls if p > 0]
        
        return {
            'total_trades': len(closed),
            'total_pnl': round(sum(pnls), 2),
            'win_rate': round(len(wins) / len(closed), 3),
            'avg_pnl': round(np.mean(pnls), 2),
            'avg_slippage': round(np.mean([t.slippage for t in closed]), 2),
            'open_positions': len(self.positions)
        }


# ============================================================
# UNIFIED BACKTESTING ENGINE
# ============================================================

class BacktestingEngine:
    """Unified backtesting and simulation engine."""
    
    def __init__(self):
        self.backtester = StrategyBacktester()
        self.monte_carlo = MonteCarloSimulator()
        self.walk_forward = WalkForwardOptimizer()
        self.scenario_analyzer = ScenarioAnalyzer()
        self.paper_trader = PaperTradeSimulator()
    
    def full_analysis(self, strategy_name: str, ticker: str = 'SPY') -> Dict:
        """Complete backtesting analysis."""
        # Standard backtest
        end = datetime.now()
        start = end - timedelta(days=365)
        backtest = self.backtester.backtest(strategy_name, ticker, start, end)
        
        # Monte Carlo
        mc = self.monte_carlo.simulate(
            strategy_name,
            backtest.win_rate,
            backtest.avg_win,
            backtest.avg_loss
        )
        
        # Walk-forward
        wf = self.walk_forward.optimize(strategy_name, ticker)
        
        # Scenario stress test
        scenarios = self.scenario_analyzer.stress_test_all(strategy_name)
        
        return {
            'strategy': strategy_name,
            'ticker': ticker,
            'backtest': {
                'total_return': backtest.total_return,
                'sharpe': backtest.sharpe_ratio,
                'win_rate': backtest.win_rate,
                'max_drawdown': backtest.max_drawdown,
                'total_trades': backtest.total_trades
            },
            'monte_carlo': {
                'mean_return': mc.mean_return,
                'prob_profit': mc.prob_profit,
                'worst_case': mc.pct_5,
                'best_case': mc.pct_95
            },
            'walk_forward': {
                'oos_return': wf.avg_oos_return,
                'degradation': wf.oos_degradation,
                'consistency': wf.consistency_score
            },
            'scenarios': {
                'num_tested': len(scenarios),
                'avg_return': round(np.mean([s.strategy_return for s in scenarios]), 2),
                'worst_scenario': min(scenarios, key=lambda x: x.strategy_return).scenario_name
            },
            'generated_at': datetime.now().isoformat()
        }


# ============================================================
# SINGLETON GETTER
# ============================================================

_backtesting_engine = None

def get_backtesting_engine() -> BacktestingEngine:
    """Get singleton instance."""
    global _backtesting_engine
    if _backtesting_engine is None:
        _backtesting_engine = BacktestingEngine()
    return _backtesting_engine
