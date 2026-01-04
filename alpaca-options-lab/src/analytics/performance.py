"""
Alpaca Options Lab - Performance Analytics

Comprehensive performance analysis:
- P&L attribution
- Win rate and expectancy
- Sharpe, Sortino, Calmar ratios
- Drawdown analysis
- Trade-level statistics
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Trade:
    """Single trade record."""
    trade_id: str
    symbol: str
    strategy: str
    side: str  # "long" or "short"
    
    # Execution
    entry_time: datetime
    entry_price: float
    quantity: int
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    
    # P&L
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    commission: float = 0.0
    
    # Greeks at entry
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    # Tags
    tags: List[str] = field(default_factory=list)
    
    @property
    def is_closed(self) -> bool:
        return self.exit_time is not None
    
    @property
    def net_pnl(self) -> float:
        return self.realized_pnl - self.commission
    
    @property
    def hold_time_hours(self) -> Optional[float]:
        if not self.is_closed:
            return None
        return (self.exit_time - self.entry_time).total_seconds() / 3600
    
    @property
    def return_pct(self) -> float:
        cost = self.entry_price * self.quantity * 100  # Options multiplier
        if cost == 0:
            return 0
        return (self.realized_pnl / cost) * 100


@dataclass
class DrawdownAnalysis:
    """Drawdown metrics."""
    max_drawdown: float
    max_drawdown_pct: float
    drawdown_duration_days: int
    recovery_time_days: Optional[int]
    
    # Time series
    peak_date: date
    trough_date: date
    recovery_date: Optional[date]
    
    # Current state
    current_drawdown: float
    current_drawdown_pct: float


@dataclass
class TradeAnalysis:
    """Trade-level statistics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    
    win_rate: float
    loss_rate: float
    
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    
    profit_factor: float  # Gross profit / Gross loss
    expectancy: float  # Average P&L per trade
    
    avg_hold_time_hours: float
    avg_winner_hold_time: float
    avg_loser_hold_time: float


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Returns
    total_return: float
    total_return_pct: float
    annualized_return: float
    
    # Risk metrics
    volatility: float  # Annualized
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Drawdown
    max_drawdown: float
    max_drawdown_pct: float
    
    # Trade stats
    trade_analysis: TradeAnalysis
    
    # Time-based
    best_day: float
    worst_day: float
    best_month: float
    worst_month: float
    
    # Risk-adjusted
    var_95: float  # Value at Risk (95%)
    var_99: float
    cvar_95: float  # Conditional VaR
    
    # Period info
    start_date: date
    end_date: date
    trading_days: int


class PerformanceAnalyzer:
    """
    Performance analysis engine.
    
    Analyzes trade history and equity curves to produce
    comprehensive performance metrics.
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        risk_free_rate: float = 0.05,
    ):
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        
        # Trade history
        self._trades: List[Trade] = []
        
        # Daily equity curve
        self._equity_curve: Dict[date, float] = {}
        self._daily_returns: List[float] = []
        
        logger.info(f"PerformanceAnalyzer initialized: capital={initial_capital}")
    
    # -------------------- Data Input --------------------
    
    def add_trade(self, trade: Trade) -> None:
        """Add a trade to history."""
        self._trades.append(trade)
    
    def add_trades(self, trades: List[Trade]) -> None:
        """Add multiple trades."""
        self._trades.extend(trades)
    
    def set_equity_curve(self, curve: Dict[date, float]) -> None:
        """Set daily equity curve."""
        self._equity_curve = curve
        self._calculate_daily_returns()
    
    def add_equity_point(self, dt: date, equity: float) -> None:
        """Add single equity point."""
        self._equity_curve[dt] = equity
    
    def _calculate_daily_returns(self) -> None:
        """Calculate daily returns from equity curve."""
        if len(self._equity_curve) < 2:
            return
        
        sorted_dates = sorted(self._equity_curve.keys())
        self._daily_returns = []
        
        for i in range(1, len(sorted_dates)):
            prev_equity = self._equity_curve[sorted_dates[i - 1]]
            curr_equity = self._equity_curve[sorted_dates[i]]
            
            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                self._daily_returns.append(daily_return)
    
    # -------------------- Analysis --------------------
    
    def analyze(self) -> PerformanceMetrics:
        """
        Perform comprehensive performance analysis.
        
        Returns:
            PerformanceMetrics with all statistics
        """
        # Calculate daily returns if not done
        if not self._daily_returns and self._equity_curve:
            self._calculate_daily_returns()
        
        # Get date range
        if self._equity_curve:
            sorted_dates = sorted(self._equity_curve.keys())
            start_date = sorted_dates[0]
            end_date = sorted_dates[-1]
            trading_days = len(sorted_dates)
        else:
            start_date = end_date = datetime.now(timezone.utc).date()
            trading_days = 0
        
        # Total return
        if self._equity_curve:
            final_equity = self._equity_curve[end_date]
            total_return = final_equity - self.initial_capital
            total_return_pct = (total_return / self.initial_capital) * 100
        else:
            total_return = sum(t.net_pnl for t in self._trades if t.is_closed)
            total_return_pct = (total_return / self.initial_capital) * 100
            final_equity = self.initial_capital + total_return
        
        # Annualized return
        years = trading_days / 252 if trading_days > 0 else 1
        annualized_return = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # Volatility
        if self._daily_returns:
            volatility = np.std(self._daily_returns) * np.sqrt(252)
        else:
            volatility = 0
        
        # Risk ratios
        sharpe = self._calculate_sharpe()
        sortino = self._calculate_sortino()
        
        # Drawdown
        drawdown = self._analyze_drawdown()
        max_dd = drawdown.max_drawdown_pct if drawdown else 0
        
        # Calmar ratio
        calmar = annualized_return / max_dd if max_dd > 0 else 0
        
        # Trade analysis
        trade_analysis = self._analyze_trades()
        
        # Best/worst periods
        best_day, worst_day = self._best_worst_day()
        best_month, worst_month = self._best_worst_month()
        
        # VaR
        var_95, var_99, cvar_95 = self._calculate_var()
        
        return PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            volatility=volatility * 100,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=drawdown.max_drawdown if drawdown else 0,
            max_drawdown_pct=max_dd,
            trade_analysis=trade_analysis,
            best_day=best_day,
            worst_day=worst_day,
            best_month=best_month,
            worst_month=worst_month,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
        )
    
    def _calculate_sharpe(self) -> float:
        """Calculate Sharpe ratio."""
        if not self._daily_returns or len(self._daily_returns) < 2:
            return 0
        
        excess_returns = np.array(self._daily_returns) - self.risk_free_rate / 252
        
        if np.std(excess_returns) == 0:
            return 0
        
        return (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252)
    
    def _calculate_sortino(self) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if not self._daily_returns or len(self._daily_returns) < 2:
            return 0
        
        excess_returns = np.array(self._daily_returns) - self.risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0
        
        downside_std = np.std(downside_returns)
        return (np.mean(excess_returns) / downside_std) * np.sqrt(252)
    
    def _analyze_drawdown(self) -> Optional[DrawdownAnalysis]:
        """Analyze drawdowns."""
        if not self._equity_curve:
            return None
        
        sorted_dates = sorted(self._equity_curve.keys())
        equities = [self._equity_curve[d] for d in sorted_dates]
        
        # Calculate running max and drawdown
        running_max = equities[0]
        max_drawdown = 0
        max_dd_pct = 0
        peak_idx = 0
        trough_idx = 0
        
        for i, equity in enumerate(equities):
            if equity > running_max:
                running_max = equity
                peak_idx = i
            
            drawdown = running_max - equity
            dd_pct = (drawdown / running_max) * 100 if running_max > 0 else 0
            
            if dd_pct > max_dd_pct:
                max_drawdown = drawdown
                max_dd_pct = dd_pct
                trough_idx = i
        
        # Find recovery
        recovery_idx = None
        if trough_idx < len(equities) - 1:
            recovery_equity = equities[peak_idx]
            for i in range(trough_idx + 1, len(equities)):
                if equities[i] >= recovery_equity:
                    recovery_idx = i
                    break
        
        # Current drawdown
        current_dd = running_max - equities[-1]
        current_dd_pct = (current_dd / running_max) * 100 if running_max > 0 else 0
        
        # Duration
        dd_duration = (sorted_dates[trough_idx] - sorted_dates[peak_idx]).days
        recovery_time = None
        if recovery_idx:
            recovery_time = (sorted_dates[recovery_idx] - sorted_dates[trough_idx]).days
        
        return DrawdownAnalysis(
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_dd_pct,
            drawdown_duration_days=dd_duration,
            recovery_time_days=recovery_time,
            peak_date=sorted_dates[peak_idx],
            trough_date=sorted_dates[trough_idx],
            recovery_date=sorted_dates[recovery_idx] if recovery_idx else None,
            current_drawdown=current_dd,
            current_drawdown_pct=current_dd_pct,
        )
    
    def _analyze_trades(self) -> TradeAnalysis:
        """Analyze trade statistics."""
        closed_trades = [t for t in self._trades if t.is_closed]
        
        if not closed_trades:
            return TradeAnalysis(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                loss_rate=0,
                avg_win=0,
                avg_loss=0,
                largest_win=0,
                largest_loss=0,
                profit_factor=0,
                expectancy=0,
                avg_hold_time_hours=0,
                avg_winner_hold_time=0,
                avg_loser_hold_time=0,
            )
        
        # Categorize trades
        winners = [t for t in closed_trades if t.net_pnl > 0]
        losers = [t for t in closed_trades if t.net_pnl < 0]
        
        total = len(closed_trades)
        num_winners = len(winners)
        num_losers = len(losers)
        
        # Win/loss rates
        win_rate = num_winners / total if total > 0 else 0
        loss_rate = num_losers / total if total > 0 else 0
        
        # Average P&L
        avg_win = np.mean([t.net_pnl for t in winners]) if winners else 0
        avg_loss = np.mean([t.net_pnl for t in losers]) if losers else 0
        
        # Extremes
        all_pnl = [t.net_pnl for t in closed_trades]
        largest_win = max(all_pnl) if all_pnl else 0
        largest_loss = min(all_pnl) if all_pnl else 0
        
        # Profit factor
        gross_profit = sum(t.net_pnl for t in winners)
        gross_loss = abs(sum(t.net_pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expectancy
        expectancy = np.mean(all_pnl) if all_pnl else 0
        
        # Hold times
        hold_times = [t.hold_time_hours for t in closed_trades if t.hold_time_hours]
        winner_times = [t.hold_time_hours for t in winners if t.hold_time_hours]
        loser_times = [t.hold_time_hours for t in losers if t.hold_time_hours]
        
        return TradeAnalysis(
            total_trades=total,
            winning_trades=num_winners,
            losing_trades=num_losers,
            win_rate=win_rate * 100,
            loss_rate=loss_rate * 100,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_hold_time_hours=np.mean(hold_times) if hold_times else 0,
            avg_winner_hold_time=np.mean(winner_times) if winner_times else 0,
            avg_loser_hold_time=np.mean(loser_times) if loser_times else 0,
        )
    
    def _best_worst_day(self) -> Tuple[float, float]:
        """Get best and worst daily returns."""
        if not self._daily_returns:
            return 0, 0
        
        return max(self._daily_returns) * 100, min(self._daily_returns) * 100
    
    def _best_worst_month(self) -> Tuple[float, float]:
        """Get best and worst monthly returns."""
        if not self._equity_curve:
            return 0, 0
        
        # Group by month
        monthly_returns = {}
        sorted_dates = sorted(self._equity_curve.keys())
        
        for i in range(1, len(sorted_dates)):
            curr_date = sorted_dates[i]
            prev_date = sorted_dates[i - 1]
            
            month_key = (curr_date.year, curr_date.month)
            
            if month_key not in monthly_returns:
                monthly_returns[month_key] = []
            
            prev_eq = self._equity_curve[prev_date]
            curr_eq = self._equity_curve[curr_date]
            
            if prev_eq > 0:
                monthly_returns[month_key].append((curr_eq - prev_eq) / prev_eq)
        
        # Sum monthly returns
        monthly_totals = [sum(rets) * 100 for rets in monthly_returns.values()]
        
        if not monthly_totals:
            return 0, 0
        
        return max(monthly_totals), min(monthly_totals)
    
    def _calculate_var(self) -> Tuple[float, float, float]:
        """Calculate Value at Risk."""
        if not self._daily_returns or len(self._daily_returns) < 10:
            return 0, 0, 0
        
        returns = np.array(self._daily_returns)
        
        # Historical VaR
        var_95 = np.percentile(returns, 5) * 100
        var_99 = np.percentile(returns, 1) * 100
        
        # Conditional VaR (Expected Shortfall)
        tail_returns = returns[returns <= np.percentile(returns, 5)]
        cvar_95 = np.mean(tail_returns) * 100 if len(tail_returns) > 0 else var_95
        
        return var_95, var_99, cvar_95
    
    # -------------------- Reports --------------------
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        metrics = self.analyze()
        
        return {
            "total_return": f"${metrics.total_return:,.2f}",
            "total_return_pct": f"{metrics.total_return_pct:.2f}%",
            "annualized_return": f"{metrics.annualized_return:.2f}%",
            "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}",
            "sortino_ratio": f"{metrics.sortino_ratio:.2f}",
            "max_drawdown": f"{metrics.max_drawdown_pct:.2f}%",
            "win_rate": f"{metrics.trade_analysis.win_rate:.1f}%",
            "profit_factor": f"{metrics.trade_analysis.profit_factor:.2f}",
            "total_trades": metrics.trade_analysis.total_trades,
            "trading_days": metrics.trading_days,
        }
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Export trade history."""
        return [
            {
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "strategy": t.strategy,
                "side": t.side,
                "entry_time": t.entry_time.isoformat(),
                "entry_price": t.entry_price,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "exit_price": t.exit_price,
                "pnl": t.net_pnl,
                "return_pct": t.return_pct,
            }
            for t in sorted(self._trades, key=lambda x: x.entry_time)
        ]
    
    def clear(self) -> None:
        """Clear all data."""
        self._trades.clear()
        self._equity_curve.clear()
        self._daily_returns.clear()
