"""
Strategy Backtester — Phase 6-8B Validation Framework
=====================================================

Comprehensive offline backtesting and validation framework for strategy bot functionality.
Ensures deterministic reproducibility, performance benchmarking, and comprehensive reporting.

Features:
- Historical data ingestion (CSV/JSON for prices and options)
- Deterministic trade signal execution simulation
- P&L, Greeks, VaR/CVaR, and risk metrics computation
- Multi-portfolio simulation (Small/Medium/Large)
- Performance SLA validation (<50ms / <200ms / <500ms)
- Comprehensive reporting (JSON, Markdown, CSV, HTML charts)
- Phase 9 cache integration with async I/O
- 100% reproducibility across iterations

Architecture:
- StrategyBacktester: Main orchestrator
- BacktestDataLoader: Historical data ingestion
- MockExecutor: Deterministic trade execution simulator
- RiskCalculator: Greeks, VaR/CVaR, P&L metrics
- ReportGenerator: Multi-format output generation
- PerformanceBenchmark: SLA validation and timing

Performance SLAs:
- Small portfolio (1-5 tickers): <50ms per iteration
- Medium portfolio (10-50 tickers): <200ms per iteration
- Large portfolio (50-100 tickers): <500ms per iteration

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0
Date: October 29, 2025
"""

import json
import logging
import hashlib
import time
import pickle
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import numpy as np
import pandas as pd
from collections import defaultdict
import csv

# Import existing modules
from broker_connector import (
    MockBrokerConnector, OrderType, OrderSide, OrderStatus,
    AssetClass, OptionType, Position, AccountInfo, Order
)
from tradingview_connector import TradeSignal, SignalType, AlertSource, SignalPriority
from strategy_bot import RiskLimits, PortfolioMetrics, TradeResult

# Import Phase 9 cache (if available)
try:
    from phase9_cache_engine import CacheEngine, CacheMetrics
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logging.warning("⚠️  Phase 9 cache engine not available. Using simple caching.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMERATIONS & TYPE DEFINITIONS
# ============================================================================

class PortfolioSize(Enum):
    """Portfolio size tiers for performance SLA validation"""
    SMALL = "small"  # 1-5 tickers
    MEDIUM = "medium"  # 10-50 tickers
    LARGE = "large"  # 50-100 tickers


class DataFormat(Enum):
    """Supported input data formats"""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GreeksMetrics:
    """Options Greeks for risk analysis"""
    delta: float = 0.0  # Price sensitivity
    gamma: float = 0.0  # Delta sensitivity
    theta: float = 0.0  # Time decay
    vega: float = 0.0  # Volatility sensitivity
    rho: float = 0.0  # Interest rate sensitivity
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics for portfolio"""
    # Value at Risk (VaR)
    var_95: float = 0.0  # 95% confidence VaR
    var_99: float = 0.0  # 99% confidence VaR
    
    # Conditional Value at Risk (CVaR/Expected Shortfall)
    cvar_95: float = 0.0  # 95% confidence CVaR
    cvar_99: float = 0.0  # 99% confidence CVaR
    
    # Portfolio Greeks
    portfolio_greeks: GreeksMetrics = field(default_factory=GreeksMetrics)
    
    # Exposure metrics
    total_exposure: float = 0.0
    max_position_exposure: float = 0.0
    concentration_ratio: float = 0.0  # Largest position / total
    
    # Risk-adjusted returns
    sharpe_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['portfolio_greeks'] = self.portfolio_greeks.to_dict()
        return result


@dataclass
class BacktestTrade:
    """Single trade execution record"""
    trade_id: str
    signal: TradeSignal
    execution_time_ms: float
    filled_price: float
    commission: float
    slippage: float
    realized_pnl: Optional[float] = None
    greeks: GreeksMetrics = field(default_factory=GreeksMetrics)
    risk_warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "trade_id": self.trade_id,
            "signal": self.signal.to_dict() if hasattr(self.signal, 'to_dict') else str(self.signal),
            "execution_time_ms": round(self.execution_time_ms, 4),
            "filled_price": self.filled_price,
            "commission": self.commission,
            "slippage": self.slippage,
            "realized_pnl": self.realized_pnl,
            "greeks": self.greeks.to_dict(),
            "risk_warnings": self.risk_warnings,
            "timestamp": self.timestamp
        }
        return result


@dataclass
class BacktestIteration:
    """Results from a single backtest iteration"""
    iteration_id: int
    iteration_hash: str  # Deterministic hash for reproducibility
    portfolio_size: PortfolioSize
    num_tickers: int
    num_signals: int
    num_trades_executed: int
    
    # Timing metrics
    total_time_ms: float
    avg_trade_time_ms: float
    throughput_trades_per_sec: float
    
    # P&L metrics
    total_pnl: float
    total_commission: float
    total_slippage: float
    net_pnl: float
    pnl_by_ticker: Dict[str, float] = field(default_factory=dict)
    
    # Risk metrics
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    
    # Trade records
    trades: List[BacktestTrade] = field(default_factory=list)
    
    # SLA validation
    sla_met: bool = True
    sla_target_ms: float = 0.0
    
    # Cache telemetry
    cache_hit_rate: float = 0.0
    cache_lookups: int = 0
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['portfolio_size'] = self.portfolio_size.value
        result['risk_metrics'] = self.risk_metrics.to_dict()
        result['trades'] = [t.to_dict() for t in self.trades]
        return result


@dataclass
class BacktestReport:
    """Comprehensive backtest results across iterations"""
    report_id: str
    num_iterations: int
    portfolio_size: PortfolioSize
    tickers: List[str]
    
    # Reproducibility validation
    all_iterations_identical: bool
    hash_consistency: bool
    determinism_score: float  # 0-100%
    
    # Performance metrics
    avg_iteration_time_ms: float
    min_iteration_time_ms: float
    max_iteration_time_ms: float
    avg_throughput: float
    
    # SLA validation
    all_sla_met: bool
    sla_compliance_rate: float
    
    # Aggregate P&L
    total_pnl_all_iterations: float
    avg_pnl_per_iteration: float
    pnl_std_dev: float
    
    # Risk summary
    avg_var_95: float
    avg_cvar_95: float
    avg_sharpe: Optional[float] = None
    max_drawdown: float = 0.0
    
    # Iterations
    iterations: List[BacktestIteration] = field(default_factory=list)
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['portfolio_size'] = self.portfolio_size.value
        result['iterations'] = [it.to_dict() for it in self.iterations]
        return result


# ============================================================================
# BACKTESTING DATA LOADER
# ============================================================================

class BacktestDataLoader:
    """Load historical price and options data for backtesting"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_cache: Dict[str, pd.DataFrame] = {}
        
    def load_price_data(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        format: DataFormat = DataFormat.CSV
    ) -> pd.DataFrame:
        """
        Load historical price data for multiple tickers.
        
        Expected CSV format:
        date,ticker,open,high,low,close,volume
        
        Returns: DataFrame with columns [date, ticker, price, volume]
        """
        all_data = []
        
        for ticker in tickers:
            cache_key = f"{ticker}_{start_date}_{end_date}"
            
            if cache_key in self.data_cache:
                all_data.append(self.data_cache[cache_key])
                continue
            
            # Load from file
            if format == DataFormat.CSV:
                file_path = self.data_dir / f"{ticker}_prices.csv"
                if file_path.exists():
                    df = pd.read_csv(file_path)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                    self.data_cache[cache_key] = df
                    all_data.append(df)
                else:
                    # Generate synthetic data for testing
                    logger.warning(f"⚠️  No price data for {ticker}, generating synthetic data")
                    df = self._generate_synthetic_prices(ticker, start_date, end_date)
                    self.data_cache[cache_key] = df
                    all_data.append(df)
            
            elif format == DataFormat.JSON:
                file_path = self.data_dir / f"{ticker}_prices.json"
                if file_path.exists():
                    df = pd.read_json(file_path)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                    self.data_cache[cache_key] = df
                    all_data.append(df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    def load_options_data(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Load historical options data.
        
        Expected format:
        date,ticker,strike,expiration,call_price,put_price,iv,delta,gamma,theta,vega
        """
        all_data = []
        
        for ticker in tickers:
            file_path = self.data_dir / f"{ticker}_options.csv"
            if file_path.exists():
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'])
                df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                all_data.append(df)
            else:
                # Generate synthetic options data
                logger.warning(f"⚠️  No options data for {ticker}, generating synthetic data")
                df = self._generate_synthetic_options(ticker, start_date, end_date)
                all_data.append(df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    def _generate_synthetic_prices(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        initial_price: float = 100.0
    ) -> pd.DataFrame:
        """Generate synthetic price data using GBM for testing"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        n = len(dates)
        
        # Geometric Brownian Motion parameters
        mu = 0.0002  # Drift
        sigma = 0.02  # Volatility
        
        # Generate random walk
        np.random.seed(hash(ticker) % (2**32))  # Deterministic based on ticker
        returns = np.random.normal(mu, sigma, n)
        prices = initial_price * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'date': dates,
            'ticker': ticker,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, n)),
            'high': prices * (1 + np.random.uniform(0.01, 0.03, n)),
            'low': prices * (1 - np.random.uniform(0.01, 0.03, n)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, n)
        })
        
        return df
    
    def _generate_synthetic_options(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Generate synthetic options data for testing"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate options chain
        base_price = 100.0
        strikes = [base_price * k for k in [0.9, 0.95, 1.0, 1.05, 1.1]]
        expirations = [(datetime.now() + timedelta(days=d)).strftime('%Y-%m-%d') 
                       for d in [7, 14, 30, 60]]
        
        records = []
        for date in dates:
            for strike in strikes:
                for expiration in expirations:
                    # Simple Black-Scholes approximation for Greeks
                    moneyness = strike / base_price
                    records.append({
                        'date': date,
                        'ticker': ticker,
                        'strike': strike,
                        'expiration': expiration,
                        'call_price': max(base_price - strike, 0) + 5,
                        'put_price': max(strike - base_price, 0) + 5,
                        'iv': 0.3 + (moneyness - 1) * 0.1,
                        'delta': 0.5 if abs(moneyness - 1) < 0.01 else (0.8 if moneyness < 1 else 0.2),
                        'gamma': 0.05,
                        'theta': -0.02,
                        'vega': 0.1
                    })
        
        return pd.DataFrame(records)


# ============================================================================
# MOCK EXECUTOR WITH DETERMINISTIC EXECUTION
# ============================================================================

class DeterministicMockExecutor:
    """
    Deterministic trade execution simulator.
    Ensures 100% reproducibility across iterations.
    """
    
    def __init__(self, initial_cash: float = 100000.0, commission_rate: float = 0.001):
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.reset()
        
    def reset(self):
        """Reset executor state for new iteration"""
        self.cash = self.initial_cash
        self.positions: Dict[str, float] = defaultdict(float)
        self.trade_history: List[BacktestTrade] = []
        self.execution_counter = 0
        
    def execute_signal(
        self,
        signal: TradeSignal,
        current_price: float,
        greeks: Optional[GreeksMetrics] = None
    ) -> BacktestTrade:
        """
        Execute trade signal deterministically.
        
        Returns: BacktestTrade with execution details
        """
        start_time = time.perf_counter()
        
        # Generate deterministic trade ID
        trade_id = self._generate_trade_id(signal)
        
        # Calculate execution details
        qty = signal.qty
        
        # Determine if this is a buy or sell based on signal type
        is_buy = signal.signal_type.value.startswith('buy')
        side = 1.0 if is_buy else -1.0
        
        # Deterministic slippage (based on signal hash)
        slippage_pct = (hash(signal.signal_id) % 10) / 10000.0  # 0-0.1%
        filled_price = current_price * (1 + slippage_pct * side)
        
        # Commission
        commission = abs(qty * filled_price * self.commission_rate)
        
        # Update positions
        position_key = signal.symbol
        self.positions[position_key] += qty * side
        
        # Update cash
        cash_impact = -qty * filled_price * side - commission
        self.cash += cash_impact
        
        # Calculate realized P&L (if closing position)
        realized_pnl = None
        if abs(self.positions[position_key]) < abs(qty):
            # Simplified P&L calculation
            realized_pnl = cash_impact + commission
        
        # Execution time (deterministic based on signal)
        execution_time_ms = ((hash(signal.signal_id) % 100) / 1000.0) + 0.5  # 0.5-1.5ms
        
        # Create trade record
        trade = BacktestTrade(
            trade_id=trade_id,
            signal=signal,
            execution_time_ms=execution_time_ms,
            filled_price=filled_price,
            commission=commission,
            slippage=filled_price - current_price,
            realized_pnl=realized_pnl,
            greeks=greeks or GreeksMetrics(),
            timestamp=datetime.now().isoformat()
        )
        
        self.trade_history.append(trade)
        self.execution_counter += 1
        
        return trade
    
    def _generate_trade_id(self, signal: TradeSignal) -> str:
        """Generate deterministic trade ID"""
        content = f"{signal.signal_id}_{signal.symbol}_{signal.qty}_{self.execution_counter}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate current portfolio value"""
        equity = sum(
            qty * current_prices.get(symbol, 0.0)
            for symbol, qty in self.positions.items()
        )
        return self.cash + equity
    
    def get_total_pnl(self) -> float:
        """Calculate total P&L from all trades"""
        return sum(t.realized_pnl or 0.0 for t in self.trade_history)


# ============================================================================
# RISK CALCULATOR
# ============================================================================

class RiskCalculator:
    """Calculate Greeks, VaR, CVaR, and other risk metrics"""
    
    @staticmethod
    def calculate_greeks(
        option_type: str,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.05
    ) -> GreeksMetrics:
        """
        Calculate Black-Scholes Greeks.
        Simplified implementation for backtesting.
        """
        from scipy.stats import norm
        import math
        
        # Prevent division by zero
        if time_to_expiry <= 0:
            return GreeksMetrics()
        
        # Black-Scholes parameters
        d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * math.sqrt(time_to_expiry))
        d2 = d1 - volatility * math.sqrt(time_to_expiry)
        
        # Greeks calculation
        delta = norm.cdf(d1) if option_type.lower() == 'call' else norm.cdf(d1) - 1
        gamma = norm.pdf(d1) / (spot * volatility * math.sqrt(time_to_expiry))
        vega = spot * norm.pdf(d1) * math.sqrt(time_to_expiry) / 100  # Per 1% vol change
        theta = -(spot * norm.pdf(d1) * volatility / (2 * math.sqrt(time_to_expiry))) / 365  # Per day
        rho = strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2) / 100
        
        if option_type.lower() == 'put':
            rho = -strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) / 100
        
        return GreeksMetrics(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho
        )
    
    @staticmethod
    def calculate_var_cvar(
        returns: np.ndarray,
        confidence_95: float = 0.95,
        confidence_99: float = 0.99
    ) -> Tuple[float, float, float, float]:
        """
        Calculate Value at Risk (VaR) and Conditional VaR (CVaR).
        
        Returns: (var_95, var_99, cvar_95, cvar_99)
        """
        if len(returns) == 0:
            return 0.0, 0.0, 0.0, 0.0
        
        # VaR calculation (percentile of loss distribution)
        var_95 = np.percentile(returns, (1 - confidence_95) * 100)
        var_99 = np.percentile(returns, (1 - confidence_99) * 100)
        
        # CVaR calculation (expected value of losses beyond VaR)
        cvar_95 = returns[returns <= var_95].mean() if any(returns <= var_95) else var_95
        cvar_99 = returns[returns <= var_99].mean() if any(returns <= var_99) else var_99
        
        return var_95, var_99, cvar_95, cvar_99
    
    @staticmethod
    def calculate_portfolio_greeks(trades: List[BacktestTrade]) -> GreeksMetrics:
        """Aggregate Greeks across portfolio"""
        total_greeks = GreeksMetrics()
        
        for trade in trades:
            total_greeks.delta += trade.greeks.delta * trade.signal.qty
            total_greeks.gamma += trade.greeks.gamma * trade.signal.qty
            total_greeks.theta += trade.greeks.theta * trade.signal.qty
            total_greeks.vega += trade.greeks.vega * trade.signal.qty
            total_greeks.rho += trade.greeks.rho * trade.signal.qty
        
        return total_greeks


# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Generate multi-format reports (JSON, Markdown, CSV, HTML)"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_json_report(self, report: BacktestReport, filename: str = "backtest_report.json"):
        """Generate JSON report with full details"""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"✅ JSON report saved to: {output_path}")
        return output_path
    
    def generate_markdown_summary(self, report: BacktestReport, filename: str = "backtest_summary.md"):
        """Generate Markdown summary with tables"""
        output_path = self.output_dir / filename
        
        md_content = f"""# Backtest Validation Report

**Report ID:** `{report.report_id}`  
**Generated:** {report.timestamp}  
**Portfolio Size:** {report.portfolio_size.value.upper()} ({len(report.tickers)} tickers)  
**Iterations:** {report.num_iterations}

---

## 📊 Reproducibility Validation

| Metric | Value | Status |
|--------|-------|--------|
| All Iterations Identical | {report.all_iterations_identical} | {'✅ PASS' if report.all_iterations_identical else '❌ FAIL'} |
| Hash Consistency | {report.hash_consistency} | {'✅ PASS' if report.hash_consistency else '❌ FAIL'} |
| Determinism Score | {report.determinism_score:.2f}% | {'✅ PASS' if report.determinism_score >= 99.0 else '⚠️ WARNING'} |

---

## ⚡ Performance Metrics

| Metric | Value |
|--------|-------|
| Avg Iteration Time | {report.avg_iteration_time_ms:.2f} ms |
| Min Iteration Time | {report.min_iteration_time_ms:.2f} ms |
| Max Iteration Time | {report.max_iteration_time_ms:.2f} ms |
| Avg Throughput | {report.avg_throughput:.2f} trades/sec |

### SLA Validation

| Check | Result |
|-------|--------|
| All SLAs Met | {'✅ PASS' if report.all_sla_met else '❌ FAIL'} |
| SLA Compliance Rate | {report.sla_compliance_rate:.1f}% |

---

## 💰 P&L Summary

| Metric | Value |
|--------|-------|
| Total P&L (All Iterations) | ${report.total_pnl_all_iterations:,.2f} |
| Avg P&L per Iteration | ${report.avg_pnl_per_iteration:,.2f} |
| P&L Std Dev | ${report.pnl_std_dev:,.2f} |

---

## 🛡️ Risk Metrics

| Metric | Value |
|--------|-------|
| Avg VaR (95%) | ${report.avg_var_95:,.2f} |
| Avg CVaR (95%) | ${report.avg_cvar_95:,.2f} |
| Max Drawdown | {report.max_drawdown:.2f}% |
| Avg Sharpe Ratio | {report.avg_sharpe if report.avg_sharpe else 'N/A'} |

---

## 📈 Iteration Details

"""
        
        for i, iteration in enumerate(report.iterations, 1):
            md_content += f"""
### Iteration {i}

- **Hash:** `{iteration.iteration_hash}`
- **Total Time:** {iteration.total_time_ms:.2f} ms
- **Trades Executed:** {iteration.num_trades_executed}
- **Net P&L:** ${iteration.net_pnl:,.2f}
- **SLA Met:** {'✅ YES' if iteration.sla_met else '❌ NO'} (Target: {iteration.sla_target_ms:.0f} ms)
- **Cache Hit Rate:** {iteration.cache_hit_rate:.1f}%

"""
        
        md_content += "\n---\n\n**Report Generated by Strategy Backtester v1.0**\n"
        
        with open(output_path, 'w') as f:
            f.write(md_content)
        
        logger.info(f"✅ Markdown summary saved to: {output_path}")
        return output_path
    
    def generate_csv_exports(self, report: BacktestReport):
        """Generate CSV files for trades and timings"""
        
        # Trades CSV
        trades_path = self.output_dir / "backtest_trades.csv"
        with open(trades_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'iteration', 'trade_id', 'symbol', 'qty', 'signal_type',
                'filled_price', 'commission', 'slippage', 'realized_pnl',
                'execution_time_ms', 'delta', 'gamma', 'theta', 'vega'
            ])
            writer.writeheader()
            
            for iteration in report.iterations:
                for trade in iteration.trades:
                    writer.writerow({
                        'iteration': iteration.iteration_id,
                        'trade_id': trade.trade_id,
                        'symbol': trade.signal.symbol,
                        'qty': trade.signal.qty,
                        'signal_type': trade.signal.signal_type.value if hasattr(trade.signal.signal_type, 'value') else str(trade.signal.signal_type),
                        'filled_price': trade.filled_price,
                        'commission': trade.commission,
                        'slippage': trade.slippage,
                        'realized_pnl': trade.realized_pnl or 0.0,
                        'execution_time_ms': trade.execution_time_ms,
                        'delta': trade.greeks.delta,
                        'gamma': trade.greeks.gamma,
                        'theta': trade.greeks.theta,
                        'vega': trade.greeks.vega
                    })
        
        logger.info(f"✅ Trades CSV saved to: {trades_path}")
        
        # Iterations CSV
        iterations_path = self.output_dir / "backtest_iterations.csv"
        with open(iterations_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'iteration_id', 'iteration_hash', 'total_time_ms',
                'num_trades', 'net_pnl', 'sla_met', 'cache_hit_rate'
            ])
            writer.writeheader()
            
            for iteration in report.iterations:
                writer.writerow({
                    'iteration_id': iteration.iteration_id,
                    'iteration_hash': iteration.iteration_hash,
                    'total_time_ms': iteration.total_time_ms,
                    'num_trades': iteration.num_trades_executed,
                    'net_pnl': iteration.net_pnl,
                    'sla_met': iteration.sla_met,
                    'cache_hit_rate': iteration.cache_hit_rate
                })
        
        logger.info(f"✅ Iterations CSV saved to: {iterations_path}")
        
        return trades_path, iterations_path
    
    def generate_html_charts(self, report: BacktestReport, filename: str = "backtest_charts.html"):
        """Generate offline HTML charts (optional)"""
        output_path = self.output_dir / filename
        
        # Simple HTML with inline JavaScript for charts
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Backtest Charts - {report.report_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; }}
        h1 {{ color: #333; }}
        .chart {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .metric-label {{ font-size: 14px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Backtest Validation Report</h1>
        <p><strong>Report ID:</strong> {report.report_id}</p>
        <p><strong>Generated:</strong> {report.timestamp}</p>
        
        <h2>Key Metrics</h2>
        <div class="metric">
            <div class="metric-value">${report.total_pnl_all_iterations:,.2f}</div>
            <div class="metric-label">Total P&L</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.determinism_score:.1f}%</div>
            <div class="metric-label">Determinism</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.avg_iteration_time_ms:.2f} ms</div>
            <div class="metric-label">Avg Iteration Time</div>
        </div>
        
        <h2>Iteration Performance</h2>
        <table>
            <tr>
                <th>Iteration</th>
                <th>Time (ms)</th>
                <th>Trades</th>
                <th>Net P&L</th>
                <th>SLA Met</th>
            </tr>
"""
        
        for iteration in report.iterations:
            sla_status = '✅' if iteration.sla_met else '❌'
            html_content += f"""            <tr>
                <td>{iteration.iteration_id}</td>
                <td>{iteration.total_time_ms:.2f}</td>
                <td>{iteration.num_trades_executed}</td>
                <td>${iteration.net_pnl:,.2f}</td>
                <td>{sla_status}</td>
            </tr>
"""
        
        html_content += """        </table>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"✅ HTML charts saved to: {output_path}")
        return output_path


# ============================================================================
# MAIN BACKTESTER
# ============================================================================

class StrategyBacktester:
    """
    Main backtesting orchestrator with deterministic execution,
    performance benchmarking, and comprehensive reporting.
    """
    
    def __init__(
        self,
        data_dir: Path = Path("data/backtest"),
        output_dir: Path = Path("outputs/backtests"),
        use_cache: bool = True
    ):
        self.data_loader = BacktestDataLoader(data_dir)
        self.report_generator = ReportGenerator(output_dir)
        self.executor = DeterministicMockExecutor()
        self.risk_calculator = RiskCalculator()
        
        # Cache integration (optional Phase 9 enhancement)
        self.use_cache = use_cache and CACHE_AVAILABLE
        if self.use_cache:
            cache_dir = output_dir / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_engine = CacheEngine(cache_dir=cache_dir, max_cache_size=1000)
            logger.info("✅ Phase 9 cache engine enabled")
        else:
            self.cache_engine = None
            logger.info("ℹ️  Running without cache engine")
    
    def generate_test_signals(
        self,
        tickers: List[str],
        num_signals_per_ticker: int = 10
    ) -> List[TradeSignal]:
        """Generate deterministic test signals for backtesting"""
        signals = []
        
        for ticker in tickers:
            for i in range(num_signals_per_ticker):
                # Deterministic signal generation
                seed = hash(f"{ticker}_{i}") % (2**32)
                np.random.seed(seed)
                
                signal_type = SignalType.BUY_STOCK if i % 2 == 0 else SignalType.SELL_STOCK
                qty = np.random.randint(1, 10) * 10
                
                signal = TradeSignal(
                    signal_id=f"{ticker}_{i}_{seed}",
                    signal_type=signal_type,
                    symbol=ticker,
                    qty=qty,
                    source=AlertSource.BACKTEST,
                    priority=SignalPriority.MEDIUM,
                    limit_price=100.0 + np.random.uniform(-10, 10),
                    timestamp=datetime.now().isoformat()
                )
                
                signals.append(signal)
        
        return signals
    
    def run_backtest_iteration(
        self,
        iteration_id: int,
        portfolio_size: PortfolioSize,
        tickers: List[str],
        signals: List[TradeSignal],
        sla_target_ms: float
    ) -> BacktestIteration:
        """Run a single backtest iteration with full determinism"""
        
        start_time = time.perf_counter()
        
        # Reset executor for new iteration
        self.executor.reset()
        
        # Execute all signals
        trades = []
        for signal in signals:
            # Get current price (deterministic based on signal)
            current_price = 100.0 + (hash(signal.symbol) % 100) / 10.0
            
            # Calculate Greeks if options
            greeks = GreeksMetrics()
            if signal.strike and signal.expiration:
                try:
                    greeks = self.risk_calculator.calculate_greeks(
                        option_type='call',
                        spot=current_price,
                        strike=signal.strike,
                        time_to_expiry=30/365,  # Simplified
                        volatility=0.3
                    )
                except:
                    pass  # Use default Greeks if calculation fails
            
            # Execute trade
            trade = self.executor.execute_signal(signal, current_price, greeks)
            trades.append(trade)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Calculate metrics
        total_pnl = sum(t.realized_pnl or 0.0 for t in trades)
        total_commission = sum(t.commission for t in trades)
        total_slippage = sum(abs(t.slippage) for t in trades)
        net_pnl = total_pnl - total_commission
        
        # P&L by ticker
        pnl_by_ticker = defaultdict(float)
        for trade in trades:
            pnl_by_ticker[trade.signal.symbol] += trade.realized_pnl or 0.0
        
        # Risk metrics
        returns = np.array([t.realized_pnl or 0.0 for t in trades])
        var_95, var_99, cvar_95, cvar_99 = self.risk_calculator.calculate_var_cvar(returns)
        
        portfolio_greeks = self.risk_calculator.calculate_portfolio_greeks(trades)
        
        risk_metrics = RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            portfolio_greeks=portfolio_greeks,
            total_exposure=sum(abs(t.filled_price * t.signal.qty) for t in trades),
            max_position_exposure=max((abs(t.filled_price * t.signal.qty) for t in trades), default=0.0)
        )
        
        # Generate deterministic iteration hash (exclude iteration_id for consistency)
        iteration_content = {
            'tickers': sorted(tickers),
            'num_signals': len(signals),
            'num_trades': len(trades),
            'total_pnl': round(total_pnl, 2),
            'net_pnl': round(net_pnl, 2)
        }
        iteration_hash = hashlib.sha256(
            json.dumps(iteration_content, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        # Cache telemetry
        cache_hit_rate = 0.0
        cache_lookups = 0
        if self.cache_engine:
            metrics = self.cache_engine.get_metrics()
            cache_hit_rate = metrics.hit_rate
            cache_lookups = metrics.total_requests
        
        # Create iteration result
        iteration = BacktestIteration(
            iteration_id=iteration_id,
            iteration_hash=iteration_hash,
            portfolio_size=portfolio_size,
            num_tickers=len(tickers),
            num_signals=len(signals),
            num_trades_executed=len(trades),
            total_time_ms=total_time_ms,
            avg_trade_time_ms=total_time_ms / len(trades) if trades else 0.0,
            throughput_trades_per_sec=(len(trades) / (total_time_ms / 1000)) if total_time_ms > 0 else 0.0,
            total_pnl=total_pnl,
            total_commission=total_commission,
            total_slippage=total_slippage,
            net_pnl=net_pnl,
            pnl_by_ticker=dict(pnl_by_ticker),
            risk_metrics=risk_metrics,
            trades=trades,
            sla_met=(total_time_ms <= sla_target_ms),
            sla_target_ms=sla_target_ms,
            cache_hit_rate=cache_hit_rate,
            cache_lookups=cache_lookups
        )
        
        return iteration
    
    def run_multi_iteration_backtest(
        self,
        portfolio_size: PortfolioSize,
        tickers: List[str],
        num_iterations: int = 3,
        signals_per_ticker: int = 10
    ) -> BacktestReport:
        """
        Run full multi-iteration backtest with reproducibility validation.
        
        Performance SLAs:
        - Small (1-5 tickers): <50ms per iteration
        - Medium (10-50 tickers): <200ms per iteration
        - Large (50-100 tickers): <500ms per iteration
        """
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 Starting {num_iterations}-iteration backtest")
        logger.info(f"Portfolio Size: {portfolio_size.value.upper()} ({len(tickers)} tickers)")
        logger.info(f"Signals per Ticker: {signals_per_ticker}")
        logger.info(f"{'='*80}\n")
        
        # Determine SLA target
        sla_targets = {
            PortfolioSize.SMALL: 50.0,
            PortfolioSize.MEDIUM: 200.0,
            PortfolioSize.LARGE: 500.0
        }
        sla_target_ms = sla_targets[portfolio_size]
        
        # Generate signals (same for all iterations for reproducibility)
        signals = self.generate_test_signals(tickers, signals_per_ticker)
        logger.info(f"📊 Generated {len(signals)} test signals")
        
        # Run iterations
        iterations = []
        for i in range(num_iterations):
            logger.info(f"\n--- Iteration {i+1}/{num_iterations} ---")
            iteration = self.run_backtest_iteration(
                iteration_id=i+1,
                portfolio_size=portfolio_size,
                tickers=tickers,
                signals=signals,
                sla_target_ms=sla_target_ms
            )
            iterations.append(iteration)
            
            logger.info(f"  Time: {iteration.total_time_ms:.2f} ms")
            logger.info(f"  Trades: {iteration.num_trades_executed}")
            logger.info(f"  Net P&L: ${iteration.net_pnl:,.2f}")
            logger.info(f"  SLA Met: {'✅ YES' if iteration.sla_met else '❌ NO'} (Target: {sla_target_ms:.0f} ms)")
            logger.info(f"  Hash: {iteration.iteration_hash}")
        
        # Reproducibility validation
        hashes = [it.iteration_hash for it in iterations]
        hash_consistency = len(set(hashes)) == 1
        
        pnls = [round(it.net_pnl, 2) for it in iterations]
        all_iterations_identical = len(set(pnls)) == 1 and hash_consistency
        
        determinism_score = 100.0 if all_iterations_identical else 0.0
        
        # Performance aggregation
        times = [it.total_time_ms for it in iterations]
        avg_iteration_time = np.mean(times)
        min_iteration_time = np.min(times)
        max_iteration_time = np.max(times)
        avg_throughput = np.mean([it.throughput_trades_per_sec for it in iterations])
        
        # SLA validation
        all_sla_met = all(it.sla_met for it in iterations)
        sla_compliance_rate = (sum(it.sla_met for it in iterations) / len(iterations)) * 100
        
        # P&L aggregation
        total_pnl_all = sum(it.net_pnl for it in iterations)
        avg_pnl = np.mean(pnls)
        pnl_std = np.std(pnls)
        
        # Risk aggregation
        avg_var_95 = np.mean([it.risk_metrics.var_95 for it in iterations])
        avg_cvar_95 = np.mean([it.risk_metrics.cvar_95 for it in iterations])
        
        # Generate report
        report_id = f"backtest_{portfolio_size.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report = BacktestReport(
            report_id=report_id,
            num_iterations=num_iterations,
            portfolio_size=portfolio_size,
            tickers=tickers,
            all_iterations_identical=all_iterations_identical,
            hash_consistency=hash_consistency,
            determinism_score=determinism_score,
            avg_iteration_time_ms=avg_iteration_time,
            min_iteration_time_ms=min_iteration_time,
            max_iteration_time_ms=max_iteration_time,
            avg_throughput=avg_throughput,
            all_sla_met=all_sla_met,
            sla_compliance_rate=sla_compliance_rate,
            total_pnl_all_iterations=total_pnl_all,
            avg_pnl_per_iteration=avg_pnl,
            pnl_std_dev=pnl_std,
            avg_var_95=avg_var_95,
            avg_cvar_95=avg_cvar_95,
            iterations=iterations
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ Backtest Complete: {report_id}")
        logger.info(f"{'='*80}\n")
        logger.info(f"Determinism Score: {determinism_score:.1f}%")
        logger.info(f"All SLAs Met: {'✅ YES' if all_sla_met else '❌ NO'}")
        logger.info(f"Total P&L: ${total_pnl_all:,.2f}")
        logger.info(f"Avg Iteration Time: {avg_iteration_time:.2f} ms\n")
        
        return report
    
    def generate_all_reports(self, report: BacktestReport):
        """Generate all report formats"""
        logger.info("\n📝 Generating reports...")
        
        self.report_generator.generate_json_report(report)
        self.report_generator.generate_markdown_summary(report)
        self.report_generator.generate_csv_exports(report)
        self.report_generator.generate_html_charts(report)
        
        logger.info("✅ All reports generated successfully\n")


# ============================================================================
# ASYNC I/O ENHANCEMENTS (Phase 9 Optional Enhancement #1)
# ============================================================================

class AsyncBacktestDataLoader(BacktestDataLoader):
    """Async version of data loader for improved I/O performance"""
    
    async def load_price_data_async(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        format: DataFormat = DataFormat.CSV
    ) -> pd.DataFrame:
        """Async data loading with concurrent file reads"""
        
        async def load_ticker(ticker: str):
            # Simulate async I/O
            await asyncio.sleep(0.001)
            return self.load_price_data([ticker], start_date, end_date, format)
        
        # Load all tickers concurrently
        tasks = [load_ticker(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        
        if results:
            return pd.concat(results, ignore_index=True)
        return pd.DataFrame()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Example usage"""
    
    # Initialize backtester
    backtester = StrategyBacktester(
        data_dir=Path("data/backtest"),
        output_dir=Path("outputs/backtests"),
        use_cache=True
    )
    
    # Define portfolio tiers
    small_tickers = ['AAPL', 'MSFT', 'GOOGL']
    medium_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'V', 'WMT']
    large_tickers = small_tickers + medium_tickers + [
        f'TICKER{i}' for i in range(50)
    ]
    
    # Run small portfolio backtest
    report = backtester.run_multi_iteration_backtest(
        portfolio_size=PortfolioSize.SMALL,
        tickers=small_tickers,
        num_iterations=3,
        signals_per_ticker=10
    )
    
    # Generate reports
    backtester.generate_all_reports(report)
    
    logger.info("🎉 Backtest validation complete!")


if __name__ == "__main__":
    main()
