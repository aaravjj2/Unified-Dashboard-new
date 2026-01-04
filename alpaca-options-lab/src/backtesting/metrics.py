"""
Alpaca Options Lab - Performance Metrics and Analysis

Production-grade performance analysis with:
- Standard metrics (Sharpe, Sortino, Calmar)
- Options-specific metrics (theta capture, gamma scalping)
- Trade-level analysis
- Risk decomposition

Metrics Categories:
1. Return Metrics: Total, CAGR, Alpha, Beta
2. Risk Metrics: Volatility, VaR, CVaR, Max Drawdown
3. Risk-Adjusted: Sharpe, Sortino, Calmar, Information Ratio
4. Trade Metrics: Win rate, Profit factor, Avg win/loss
5. Options Metrics: Theta capture, Gamma P&L, Vega exposure

Usage:
    from src.backtesting.metrics import PerformanceAnalyzer
    
    analyzer = PerformanceAnalyzer(risk_free_rate=0.05)
    
    metrics = analyzer.calculate_metrics(
        equity_curve=equity_curve,
        trades=trades,
        benchmark_returns=spy_returns,
    )
    
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {metrics.max_drawdown:.1%}")
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Return metrics
    total_return: float = 0.0
    total_return_pct: float = 0.0
    cagr: float = 0.0  # Compound annual growth rate
    
    # Risk metrics
    volatility: float = 0.0       # Annualized
    downside_volatility: float = 0.0
    var_95: float = 0.0           # Value at Risk (95%)
    var_99: float = 0.0           # Value at Risk (99%)
    cvar_95: float = 0.0          # Conditional VaR (Expected Shortfall)
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # Days
    avg_drawdown: float = 0.0
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    treynor_ratio: float = 0.0
    
    # Benchmark comparison
    alpha: float = 0.0
    beta: float = 0.0
    correlation: float = 0.0
    tracking_error: float = 0.0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    payoff_ratio: float = 0.0    # Avg win / Avg loss
    expectancy: float = 0.0       # Expected value per trade
    
    # Trade P&L
    avg_trade_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Consistency
    profitable_months: int = 0
    total_months: int = 0
    monthly_win_rate: float = 0.0
    best_month: float = 0.0
    worst_month: float = 0.0
    
    # Options-specific (if applicable)
    theta_capture_ratio: float = 0.0
    gamma_pnl: float = 0.0
    vega_pnl: float = 0.0
    
    # Timing
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    trading_days: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_return": round(self.total_return, 2),
            "total_return_pct": round(self.total_return_pct * 100, 2),
            "cagr": round(self.cagr * 100, 2),
            "volatility": round(self.volatility * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "sortino_ratio": round(self.sortino_ratio, 3),
            "calmar_ratio": round(self.calmar_ratio, 3),
            "max_drawdown": round(self.max_drawdown * 100, 2),
            "var_95": round(self.var_95 * 100, 2),
            "alpha": round(self.alpha * 100, 2),
            "beta": round(self.beta, 3),
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate * 100, 2),
            "profit_factor": round(self.profit_factor, 3),
            "avg_trade_pnl": round(self.avg_trade_pnl, 2),
            "trading_days": self.trading_days,
        }
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            "=" * 50,
            "PERFORMANCE SUMMARY",
            "=" * 50,
            f"Total Return: ${self.total_return:,.2f} ({self.total_return_pct:.2%})",
            f"CAGR: {self.cagr:.2%}",
            "",
            "Risk Metrics:",
            f"  Volatility: {self.volatility:.2%}",
            f"  Max Drawdown: {self.max_drawdown:.2%}",
            f"  VaR (95%): {self.var_95:.2%}",
            "",
            "Risk-Adjusted:",
            f"  Sharpe Ratio: {self.sharpe_ratio:.3f}",
            f"  Sortino Ratio: {self.sortino_ratio:.3f}",
            f"  Calmar Ratio: {self.calmar_ratio:.3f}",
            "",
            "Trade Statistics:",
            f"  Total Trades: {self.total_trades}",
            f"  Win Rate: {self.win_rate:.2%}",
            f"  Profit Factor: {self.profit_factor:.3f}",
            f"  Avg Trade: ${self.avg_trade_pnl:.2f}",
            "=" * 50,
        ]
        return "\n".join(lines)


@dataclass
class TradeAnalysis:
    """Detailed analysis of individual trades."""
    trade_id: str
    symbol: str
    side: str
    
    # Entry
    entry_time: datetime
    entry_price: float
    quantity: int
    
    # Exit
    exit_time: Optional[datetime] = None
    exit_price: float = 0.0
    
    # P&L
    gross_pnl: float = 0.0
    commission: float = 0.0
    net_pnl: float = 0.0
    return_pct: float = 0.0
    
    # Duration
    holding_period_days: float = 0.0
    
    # Risk
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0    # MAE
    
    # Context
    market_return: float = 0.0  # Benchmark return during trade
    relative_return: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 4),
            "exit_price": round(self.exit_price, 4),
            "net_pnl": round(self.net_pnl, 2),
            "return_pct": round(self.return_pct * 100, 2),
            "holding_period_days": round(self.holding_period_days, 1),
        }


class PerformanceAnalyzer:
    """
    Comprehensive performance analysis engine.
    
    Calculates all standard and options-specific metrics
    for backtest evaluation and comparison.
    
    Example:
        analyzer = PerformanceAnalyzer(
            risk_free_rate=0.05,
            trading_days_per_year=252,
        )
        
        # From equity curve
        metrics = analyzer.calculate_metrics(
            equity_curve=[(datetime, equity), ...],
            trades=trade_list,
            benchmark_returns=spy_daily_returns,
        )
        
        print(metrics.summary())
        
        # Trade analysis
        trade_analyses = analyzer.analyze_trades(trades)
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.05,
        trading_days_per_year: int = 252,
    ) -> None:
        """
        Initialize performance analyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate
            trading_days_per_year: Trading days per year for annualization
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days_per_year
        
        self._daily_rf = risk_free_rate / trading_days_per_year
    
    def calculate_metrics(
        self,
        equity_curve: List[Tuple[datetime, float]],
        trades: Optional[List[Dict[str, Any]]] = None,
        benchmark_returns: Optional[List[float]] = None,
        initial_capital: Optional[float] = None,
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            equity_curve: List of (timestamp, equity) tuples
            trades: List of trade dictionaries
            benchmark_returns: Daily benchmark returns
            initial_capital: Starting capital
            
        Returns:
            PerformanceMetrics with all metrics
        """
        if not equity_curve:
            return PerformanceMetrics()
        
        # Extract data
        timestamps, equities = zip(*equity_curve)
        equities = np.array(equities)
        
        initial = initial_capital or equities[0]
        final = equities[-1]
        
        # Calculate returns
        daily_returns = np.diff(equities) / equities[:-1]
        
        # Basic return metrics
        metrics = PerformanceMetrics()
        metrics.total_return = final - initial
        metrics.total_return_pct = metrics.total_return / initial
        
        # Dates
        metrics.start_date = timestamps[0].date() if hasattr(timestamps[0], 'date') else timestamps[0]
        metrics.end_date = timestamps[-1].date() if hasattr(timestamps[-1], 'date') else timestamps[-1]
        metrics.trading_days = len(equity_curve)
        
        # CAGR
        years = metrics.trading_days / self.trading_days
        if years > 0 and initial > 0:
            metrics.cagr = (final / initial) ** (1 / years) - 1
        
        # Volatility
        if len(daily_returns) > 1:
            metrics.volatility = float(np.std(daily_returns) * np.sqrt(self.trading_days))
            
            # Downside volatility
            downside = daily_returns[daily_returns < 0]
            if len(downside) > 0:
                metrics.downside_volatility = float(np.std(downside) * np.sqrt(self.trading_days))
        
        # VaR and CVaR
        if len(daily_returns) > 0:
            metrics.var_95 = float(-np.percentile(daily_returns, 5))
            metrics.var_99 = float(-np.percentile(daily_returns, 1))
            
            tail_returns = daily_returns[daily_returns <= -metrics.var_95]
            if len(tail_returns) > 0:
                metrics.cvar_95 = float(-np.mean(tail_returns))
        
        # Drawdown analysis
        drawdowns, max_dd, max_dd_duration = self._calculate_drawdowns(equities)
        metrics.max_drawdown = max_dd
        metrics.max_drawdown_duration = max_dd_duration
        metrics.avg_drawdown = float(np.mean(drawdowns)) if len(drawdowns) > 0 else 0
        
        # Risk-adjusted metrics
        if metrics.volatility > 0:
            excess_return = metrics.cagr - self.risk_free_rate
            metrics.sharpe_ratio = excess_return / metrics.volatility
        
        if metrics.downside_volatility > 0:
            metrics.sortino_ratio = (metrics.cagr - self.risk_free_rate) / metrics.downside_volatility
        
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.cagr / metrics.max_drawdown
        
        # Benchmark comparison
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            bm_returns = np.array(benchmark_returns[:len(daily_returns)])
            
            if len(bm_returns) == len(daily_returns):
                # Beta
                cov_matrix = np.cov(daily_returns, bm_returns)
                if cov_matrix.shape == (2, 2) and cov_matrix[1, 1] > 0:
                    metrics.beta = cov_matrix[0, 1] / cov_matrix[1, 1]
                
                # Alpha
                bm_annual = float(np.mean(bm_returns) * self.trading_days)
                metrics.alpha = metrics.cagr - (self.risk_free_rate + metrics.beta * (bm_annual - self.risk_free_rate))
                
                # Correlation
                metrics.correlation = float(np.corrcoef(daily_returns, bm_returns)[0, 1])
                
                # Tracking error
                tracking = daily_returns - bm_returns
                metrics.tracking_error = float(np.std(tracking) * np.sqrt(self.trading_days))
                
                # Information ratio
                if metrics.tracking_error > 0:
                    active_return = metrics.cagr - bm_annual
                    metrics.information_ratio = active_return / metrics.tracking_error
                
                # Treynor ratio
                if metrics.beta > 0:
                    metrics.treynor_ratio = (metrics.cagr - self.risk_free_rate) / metrics.beta
        
        # Trade statistics
        if trades:
            metrics = self._calculate_trade_metrics(metrics, trades)
        
        # Monthly statistics
        metrics = self._calculate_monthly_metrics(metrics, equity_curve)
        
        return metrics
    
    def _calculate_drawdowns(
        self,
        equities: np.ndarray,
    ) -> Tuple[np.ndarray, float, int]:
        """Calculate drawdown series and max drawdown."""
        peak = np.maximum.accumulate(equities)
        drawdown = (peak - equities) / peak
        
        max_dd = float(np.max(drawdown))
        
        # Calculate max drawdown duration
        max_duration = 0
        current_duration = 0
        in_drawdown = False
        
        for i, dd in enumerate(drawdown):
            if dd > 0:
                if not in_drawdown:
                    in_drawdown = True
                    current_duration = 1
                else:
                    current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                in_drawdown = False
                current_duration = 0
        
        return drawdown, max_dd, max_duration
    
    def _calculate_trade_metrics(
        self,
        metrics: PerformanceMetrics,
        trades: List[Dict[str, Any]],
    ) -> PerformanceMetrics:
        """Calculate trade-level metrics."""
        if not trades:
            return metrics
        
        # Extract P&L from trades
        pnls = []
        for trade in trades:
            pnl = trade.get("pnl", trade.get("net_pnl", 0))
            if pnl != 0:
                pnls.append(pnl)
        
        if not pnls:
            return metrics
        
        metrics.total_trades = len(pnls)
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        metrics.win_rate = len(wins) / len(pnls) if pnls else 0
        
        # P&L metrics
        metrics.avg_trade_pnl = float(np.mean(pnls))
        metrics.avg_win = float(np.mean(wins)) if wins else 0
        metrics.avg_loss = float(np.mean(losses)) if losses else 0
        metrics.largest_win = float(max(wins)) if wins else 0
        metrics.largest_loss = float(min(losses)) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Payoff ratio
        if metrics.avg_loss != 0:
            metrics.payoff_ratio = abs(metrics.avg_win / metrics.avg_loss)
        
        # Expectancy
        metrics.expectancy = (
            metrics.win_rate * metrics.avg_win +
            (1 - metrics.win_rate) * metrics.avg_loss
        )
        
        return metrics
    
    def _calculate_monthly_metrics(
        self,
        metrics: PerformanceMetrics,
        equity_curve: List[Tuple[datetime, float]],
    ) -> PerformanceMetrics:
        """Calculate monthly performance statistics."""
        if len(equity_curve) < 20:  # Need at least ~1 month
            return metrics
        
        # Group by month
        monthly_equity: Dict[str, List[float]] = {}
        
        for timestamp, equity in equity_curve:
            if hasattr(timestamp, 'strftime'):
                month_key = timestamp.strftime("%Y-%m")
            else:
                month_key = str(timestamp)[:7]
            
            if month_key not in monthly_equity:
                monthly_equity[month_key] = []
            monthly_equity[month_key].append(equity)
        
        # Calculate monthly returns
        monthly_returns = []
        prev_end = None
        
        for month in sorted(monthly_equity.keys()):
            equities = monthly_equity[month]
            if prev_end is not None and equities:
                month_return = (equities[-1] - prev_end) / prev_end
                monthly_returns.append(month_return)
            if equities:
                prev_end = equities[-1]
        
        if monthly_returns:
            metrics.total_months = len(monthly_returns)
            metrics.profitable_months = sum(1 for r in monthly_returns if r > 0)
            metrics.monthly_win_rate = metrics.profitable_months / metrics.total_months
            metrics.best_month = float(max(monthly_returns))
            metrics.worst_month = float(min(monthly_returns))
        
        return metrics
    
    def analyze_trades(
        self,
        trades: List[Dict[str, Any]],
        price_series: Optional[Dict[str, List[Tuple[datetime, float]]]] = None,
    ) -> List[TradeAnalysis]:
        """
        Perform detailed analysis of individual trades.
        
        Args:
            trades: List of trade dictionaries
            price_series: Optional price data for MFE/MAE calculation
            
        Returns:
            List of TradeAnalysis objects
        """
        analyses = []
        
        for i, trade in enumerate(trades):
            analysis = TradeAnalysis(
                trade_id=trade.get("id", f"trade_{i}"),
                symbol=trade.get("symbol", ""),
                side=trade.get("side", ""),
                entry_time=trade.get("entry_time", trade.get("timestamp")),
                entry_price=trade.get("entry_price", trade.get("price", 0)),
                quantity=trade.get("quantity", 0),
                exit_time=trade.get("exit_time"),
                exit_price=trade.get("exit_price", 0),
                gross_pnl=trade.get("gross_pnl", trade.get("pnl", 0)),
                commission=trade.get("commission", 0),
            )
            
            # Calculate net P&L
            analysis.net_pnl = analysis.gross_pnl - analysis.commission
            
            # Return percentage
            if analysis.entry_price > 0 and analysis.quantity != 0:
                cost_basis = analysis.entry_price * abs(analysis.quantity) * 100
                analysis.return_pct = analysis.net_pnl / cost_basis
            
            # Holding period
            if analysis.entry_time and analysis.exit_time:
                delta = analysis.exit_time - analysis.entry_time
                analysis.holding_period_days = delta.total_seconds() / 86400
            
            analyses.append(analysis)
        
        return analyses
    
    def calculate_rolling_metrics(
        self,
        equity_curve: List[Tuple[datetime, float]],
        window: int = 252,
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """
        Calculate rolling performance metrics.
        
        Args:
            equity_curve: List of (timestamp, equity) tuples
            window: Rolling window size in days
            
        Returns:
            Dict of metric name -> [(timestamp, value), ...]
        """
        if len(equity_curve) < window:
            return {}
        
        timestamps, equities = zip(*equity_curve)
        equities = np.array(equities)
        daily_returns = np.diff(equities) / equities[:-1]
        
        rolling_sharpe = []
        rolling_vol = []
        rolling_return = []
        
        for i in range(window, len(daily_returns) + 1):
            window_returns = daily_returns[i-window:i]
            
            # Rolling return (annualized)
            cumulative = np.prod(1 + window_returns)
            annual_return = cumulative ** (self.trading_days / window) - 1
            rolling_return.append((timestamps[i], annual_return))
            
            # Rolling volatility
            vol = np.std(window_returns) * np.sqrt(self.trading_days)
            rolling_vol.append((timestamps[i], vol))
            
            # Rolling Sharpe
            if vol > 0:
                sharpe = (annual_return - self.risk_free_rate) / vol
            else:
                sharpe = 0
            rolling_sharpe.append((timestamps[i], sharpe))
        
        return {
            "rolling_return": rolling_return,
            "rolling_volatility": rolling_vol,
            "rolling_sharpe": rolling_sharpe,
        }
    
    def compare_strategies(
        self,
        results: Dict[str, PerformanceMetrics],
    ) -> Dict[str, Any]:
        """
        Compare multiple strategy results.
        
        Args:
            results: Dict mapping strategy name to PerformanceMetrics
            
        Returns:
            Comparison summary
        """
        if not results:
            return {}
        
        comparison = {
            "strategies": list(results.keys()),
            "metrics": {},
        }
        
        # Compare key metrics
        metric_names = [
            "total_return_pct", "cagr", "volatility", "sharpe_ratio",
            "sortino_ratio", "max_drawdown", "win_rate", "profit_factor"
        ]
        
        for metric in metric_names:
            values = {}
            for name, perf in results.items():
                values[name] = getattr(perf, metric, 0)
            
            comparison["metrics"][metric] = {
                "values": values,
                "best": max(values.items(), key=lambda x: x[1] if metric != "max_drawdown" else -x[1])[0],
                "worst": min(values.items(), key=lambda x: x[1] if metric != "max_drawdown" else -x[1])[0],
            }
        
        # Rankings
        rankings = {}
        for name in results:
            score = 0
            for metric in ["sharpe_ratio", "sortino_ratio", "cagr"]:
                if comparison["metrics"][metric]["best"] == name:
                    score += 1
            rankings[name] = score
        
        comparison["rankings"] = dict(sorted(rankings.items(), key=lambda x: -x[1]))
        
        return comparison
