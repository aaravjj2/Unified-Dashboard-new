"""
Strategy Orchestrator — Phase 9C Integration Layer
==================================================

Unified integration layer coordinating Strategy Bot Framework (Phase 6-8)
with Backtesting & Validation Engine (Phase 9) for deterministic trading simulation.

Features:
- Unified execution flow: Strategy Bot → Backtester → Reporting
- Consistent data contracts with canonical JSON schema
- Deterministic coupling with unified random seed
- Performance SLA validation across portfolio tiers
- Comprehensive multi-format reporting
- Dashboard API integration

Architecture:
- StrategyOrchestrator: Main integration coordinator
- SignalSchema: Canonical signal data contract
- IntegrationValidator: Cross-system validation
- PerformanceMonitor: SLA tracking and profiling
- UnifiedReporter: Multi-format report generation

Performance SLAs:
- Small (5 tickers): ≤ 200 ms
- Medium (25 tickers): ≤ 800 ms  
- Large (100 tickers): ≤ 2 seconds

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0
Date: October 29, 2025
"""

import json
import hashlib
import logging
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import numpy as np
import pandas as pd

# Import Phase 6-8 Strategy Bot components
from strategy_bot import (
    StrategyBot, StrategyMode, SignalGenerator,
    RiskManager, ExecutionEngine, RiskLimits,
    PortfolioMetrics, TradeResult
)

# Import Phase 9 Backtesting components
from strategy_backtester import (
    StrategyBacktester, PortfolioSize,
    BacktestReport, BacktestIteration,
    DeterministicMockExecutor, RiskCalculator,
    ReportGenerator, GreeksMetrics, RiskMetrics
)

# Import broker and signal components
from broker_connector import (
    MockBrokerConnector, OrderType, OrderSide, OrderStatus
)
from tradingview_connector import (
    TradeSignal, SignalType, AlertSource, SignalPriority
)

# Import Phase 9 cache (if available)
try:
    from phase9_cache_engine import CacheEngine, CacheMetrics
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logging.warning("⚠️  Phase 9 cache engine not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMERATIONS & TYPE DEFINITIONS
# ============================================================================

class OrchestratorMode(Enum):
    """Orchestrator execution mode"""
    PAPER = "paper"  # Live paper trading (Alpaca paper keys)
    MOCK = "mock"  # Deterministic offline simulation
    BACKTEST = "backtest"  # Historical backtest mode


class IntegrationStatus(Enum):
    """Integration validation status"""
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


# ============================================================================
# CANONICAL SIGNAL SCHEMA
# ============================================================================

@dataclass
class SignalSchema:
    """
    Canonical JSON schema for signals shared between Strategy Bot and Backtester.
    
    Schema:
    {
      "signal_id": "uuid",
      "symbol": "AAPL",
      "type": "CALL",
      "expiry": "2026-01-17",
      "strike": 200.0,
      "confidence": 0.87,
      "action": "BUY",
      "quantity": 10,
      "limit_price": 5.50,
      "metadata": {...}
    }
    """
    signal_id: str
    symbol: str
    type: str  # "CALL", "PUT", "STOCK"
    action: str  # "BUY", "SELL"
    quantity: int
    
    # Options-specific (optional)
    expiry: Optional[str] = None  # ISO date "2026-01-17"
    strike: Optional[float] = None
    
    # Analytics metadata
    confidence: float = 0.5  # 0-1
    limit_price: Optional[float] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_trade_signal(self) -> TradeSignal:
        """Convert to TradeSignal object for Strategy Bot"""
        
        # Map action + type to SignalType
        if self.type == "STOCK":
            signal_type = SignalType.BUY_STOCK if self.action == "BUY" else SignalType.SELL_STOCK
        elif self.type == "CALL":
            signal_type = SignalType.BUY_CALL if self.action == "BUY" else SignalType.SELL_CALL
        elif self.type == "PUT":
            signal_type = SignalType.BUY_PUT if self.action == "BUY" else SignalType.SELL_PUT
        else:
            signal_type = SignalType.BUY_STOCK  # Default
        
        return TradeSignal(
            signal_id=self.signal_id,
            signal_type=signal_type,
            symbol=self.symbol,
            qty=float(self.quantity),
            source=AlertSource.STRATEGY_BOT,
            priority=SignalPriority.MEDIUM,
            strike=self.strike,
            expiration=self.expiry,
            limit_price=self.limit_price,
            timestamp=self.timestamp
        )
    
    @staticmethod
    def from_trade_signal(signal: TradeSignal) -> 'SignalSchema':
        """Convert from TradeSignal to canonical schema"""
        
        # Parse signal type
        signal_type_str = signal.signal_type.value
        if "stock" in signal_type_str:
            asset_type = "STOCK"
        elif "call" in signal_type_str:
            asset_type = "CALL"
        elif "put" in signal_type_str:
            asset_type = "PUT"
        else:
            asset_type = "STOCK"
        
        # Parse action
        action = "BUY" if "buy" in signal_type_str else "SELL"
        
        return SignalSchema(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            type=asset_type,
            action=action,
            quantity=int(signal.qty),
            expiry=signal.expiration,
            strike=signal.strike,
            confidence=signal.risk_score / 100.0 if signal.risk_score else 0.5,
            limit_price=signal.limit_price,
            timestamp=signal.timestamp
        )


# ============================================================================
# INTEGRATION VALIDATOR
# ============================================================================

class IntegrationValidator:
    """Validate integration between Strategy Bot and Backtester"""
    
    @staticmethod
    def validate_signal_schema(signal_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate signal matches canonical schema"""
        errors = []
        
        required_fields = ["signal_id", "symbol", "type", "action", "quantity"]
        for field in required_fields:
            if field not in signal_dict:
                errors.append(f"Missing required field: {field}")
        
        # Validate types
        if "type" in signal_dict and signal_dict["type"] not in ["CALL", "PUT", "STOCK"]:
            errors.append(f"Invalid type: {signal_dict['type']}")
        
        if "action" in signal_dict and signal_dict["action"] not in ["BUY", "SELL"]:
            errors.append(f"Invalid action: {signal_dict['action']}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_determinism(
        iterations: List[BacktestIteration]
    ) -> Tuple[bool, float, List[str]]:
        """Validate deterministic execution across iterations"""
        
        if len(iterations) < 2:
            return True, 100.0, []
        
        # Check hash consistency
        hashes = [it.iteration_hash for it in iterations]
        hash_consistent = len(set(hashes)) == 1
        
        # Check P&L consistency
        pnls = [round(it.net_pnl, 2) for it in iterations]
        pnl_consistent = len(set(pnls)) == 1
        
        # Check trade count consistency
        trade_counts = [it.num_trades_executed for it in iterations]
        trade_count_consistent = len(set(trade_counts)) == 1
        
        # Calculate determinism score
        checks = [hash_consistent, pnl_consistent, trade_count_consistent]
        determinism_score = (sum(checks) / len(checks)) * 100.0
        
        # Generate validation messages
        messages = []
        if not hash_consistent:
            messages.append(f"Hash mismatch: {hashes}")
        if not pnl_consistent:
            messages.append(f"P&L mismatch: {pnls}")
        if not trade_count_consistent:
            messages.append(f"Trade count mismatch: {trade_counts}")
        
        all_consistent = hash_consistent and pnl_consistent and trade_count_consistent
        
        return all_consistent, determinism_score, messages


# ============================================================================
# PERFORMANCE MONITOR
# ============================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics for SLA validation"""
    portfolio_tier: str
    num_tickers: int
    num_signals: int
    num_trades: int
    
    # Timing metrics
    total_time_ms: float
    avg_signal_latency_ms: float
    sla_target_ms: float
    sla_met: bool
    
    # Resource metrics
    memory_usage_mb: float
    cpu_utilization_pct: float
    
    # Trading metrics
    total_pnl: float
    win_rate: float
    mean_return: float
    max_drawdown: float
    
    # Risk metrics
    var_95: float
    cvar_95: float
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceMonitor:
    """Monitor and validate performance SLAs"""
    
    # SLA targets per portfolio tier
    SLA_TARGETS = {
        "small": 200.0,  # ms
        "medium": 800.0,  # ms
        "large": 2000.0  # ms
    }
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
    
    def start_monitoring(self, tier: str) -> float:
        """Start monitoring for a tier (returns start time)"""
        return time.perf_counter()
    
    def stop_monitoring(
        self,
        tier: str,
        start_time: float,
        num_tickers: int,
        num_signals: int,
        num_trades: int,
        total_pnl: float,
        win_rate: float,
        mean_return: float,
        max_drawdown: float,
        var_95: float,
        cvar_95: float
    ) -> PerformanceMetrics:
        """Stop monitoring and record metrics"""
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        sla_target = self.SLA_TARGETS.get(tier, 2000.0)
        sla_met = total_time_ms <= sla_target
        
        avg_signal_latency = total_time_ms / num_signals if num_signals > 0 else 0.0
        
        # Estimate memory/CPU (simplified)
        import psutil
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_pct = process.cpu_percent(interval=0.1)
        
        metrics = PerformanceMetrics(
            portfolio_tier=tier,
            num_tickers=num_tickers,
            num_signals=num_signals,
            num_trades=num_trades,
            total_time_ms=total_time_ms,
            avg_signal_latency_ms=avg_signal_latency,
            sla_target_ms=sla_target,
            sla_met=sla_met,
            memory_usage_mb=memory_mb,
            cpu_utilization_pct=cpu_pct,
            total_pnl=total_pnl,
            win_rate=win_rate,
            mean_return=mean_return,
            max_drawdown=max_drawdown,
            var_95=var_95,
            cvar_95=cvar_95
        )
        
        self.metrics.append(metrics)
        return metrics
    
    def get_sla_summary(self) -> Dict[str, Any]:
        """Get SLA compliance summary"""
        if not self.metrics:
            return {}
        
        total_slas = len(self.metrics)
        slas_met = sum(1 for m in self.metrics if m.sla_met)
        compliance_rate = (slas_met / total_slas) * 100.0
        
        return {
            "total_runs": total_slas,
            "slas_met": slas_met,
            "slas_failed": total_slas - slas_met,
            "compliance_rate_pct": compliance_rate,
            "all_slas_met": slas_met == total_slas,
            "metrics_by_tier": {
                tier: [m.to_dict() for m in self.metrics if m.portfolio_tier == tier]
                for tier in ["small", "medium", "large"]
            }
        }


# ============================================================================
# UNIFIED REPORTER
# ============================================================================

class UnifiedReporter:
    """Generate comprehensive multi-format reports"""
    
    def __init__(self, output_dir: Path = Path("outputs/phase9c")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_integration_report(
        self,
        orchestrator_results: Dict[str, Any],
        performance_summary: Dict[str, Any],
        validation_results: Dict[str, Any]
    ) -> Path:
        """Generate phase9c_integration_report.md"""
        
        report_path = self.output_dir / "phase9c_integration_report.md"
        
        md_content = f"""# Phase 9C Integration Report

**Generated:** {datetime.now().isoformat()}  
**Status:** {'✅ PASS' if validation_results.get('all_deterministic', False) and performance_summary.get('all_slas_met', False) else '⚠️ PARTIAL'}

---

## 🎯 Executive Summary

Unified integration of Strategy Bot Framework (Phase 6-8) with Backtesting & Validation Engine (Phase 9).

**Key Achievements:**
- Deterministic execution: {validation_results.get('determinism_score', 0):.1f}%
- SLA compliance: {performance_summary.get('compliance_rate_pct', 0):.1f}%
- Total trades executed: {orchestrator_results.get('total_trades', 0)}
- Total P&L: ${orchestrator_results.get('total_pnl', 0):,.2f}

---

## 📊 Performance Summary

| Tier | Tickers | Trades | Avg Time (ms) | P&L | Deterministic | SLA |
|------|---------|--------|---------------|-----|---------------|-----|
"""
        
        for tier_name in ["small", "medium", "large"]:
            tier_data = orchestrator_results.get('tiers', {}).get(tier_name, {})
            if tier_data:
                md_content += f"| {tier_name.upper()} | {tier_data.get('num_tickers', 0)} | {tier_data.get('total_trades', 0)} | {tier_data.get('avg_time_ms', 0):.2f} | ${tier_data.get('total_pnl', 0):,.2f} | {'✅' if tier_data.get('deterministic', False) else '❌'} | {'✅' if tier_data.get('sla_met', False) else '❌'} |\n"
        
        md_content += f"""
---

## 🔄 Determinism Validation

- **Hash Consistency:** {'✅ PASS' if validation_results.get('hash_consistency', False) else '❌ FAIL'}
- **P&L Consistency:** {'✅ PASS' if validation_results.get('pnl_consistency', False) else '❌ FAIL'}
- **Determinism Score:** {validation_results.get('determinism_score', 0):.1f}%

---

## ⚡ SLA Compliance

- **Total Runs:** {performance_summary.get('total_runs', 0)}
- **SLAs Met:** {performance_summary.get('slas_met', 0)}
- **SLAs Failed:** {performance_summary.get('slas_failed', 0)}
- **Compliance Rate:** {performance_summary.get('compliance_rate_pct', 0):.1f}%

---

## 💰 Trading Performance

- **Total Trades:** {orchestrator_results.get('total_trades', 0)}
- **Win Rate:** {orchestrator_results.get('win_rate', 0):.1f}%
- **Mean Return:** {orchestrator_results.get('mean_return', 0):.2f}%
- **Max Drawdown:** {orchestrator_results.get('max_drawdown', 0):.2f}%

---

**Report Generated by:** Phase 9C Strategy Orchestrator v1.0
"""
        
        with open(report_path, 'w') as f:
            f.write(md_content)
        
        logger.info(f"✅ Integration report saved to: {report_path}")
        return report_path
    
    def generate_results_json(
        self,
        orchestrator_results: Dict[str, Any]
    ) -> Path:
        """Generate phase9c_results.json"""
        
        results_path = self.output_dir / "phase9c_results.json"
        
        with open(results_path, 'w') as f:
            json.dump(orchestrator_results, f, indent=2, sort_keys=True)
        
        logger.info(f"✅ Results JSON saved to: {results_path}")
        return results_path
    
    def generate_performance_csv(
        self,
        performance_metrics: List[PerformanceMetrics]
    ) -> Path:
        """Generate phase9c_performance_summary.csv"""
        
        csv_path = self.output_dir / "phase9c_performance_summary.csv"
        
        if not performance_metrics:
            return csv_path
        
        # Convert to DataFrame
        df = pd.DataFrame([m.to_dict() for m in performance_metrics])
        df.to_csv(csv_path, index=False)
        
        logger.info(f"✅ Performance CSV saved to: {csv_path}")
        return csv_path
    
    def generate_trade_log_html(
        self,
        trades: List[Dict[str, Any]]
    ) -> Path:
        """Generate phase9c_trade_log.html"""
        
        html_path = self.output_dir / "phase9c_trade_log.html"
        
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Phase 9C Trade Log</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; position: sticky; top: 0; }
        tr:hover { background: #f5f5f5; }
        .buy { color: #4CAF50; font-weight: bold; }
        .sell { color: #f44336; font-weight: bold; }
        .profit { color: #4CAF50; }
        .loss { color: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Phase 9C Trade Log</h1>
        <p><strong>Generated:</strong> """ + datetime.now().isoformat() + """</p>
        <p><strong>Total Trades:</strong> """ + str(len(trades)) + """</p>
        
        <table>
            <tr>
                <th>Tier</th>
                <th>Iteration</th>
                <th>Symbol</th>
                <th>Action</th>
                <th>Type</th>
                <th>Qty</th>
                <th>Price</th>
                <th>P&L</th>
                <th>Timestamp</th>
            </tr>
"""
        
        for trade in trades:
            action_class = "buy" if "buy" in trade.get("action", "").lower() else "sell"
            pnl = trade.get("realized_pnl", 0.0)
            pnl_class = "profit" if pnl >= 0 else "loss"
            
            html_content += f"""            <tr>
                <td>{trade.get('tier', 'N/A')}</td>
                <td>{trade.get('iteration', 'N/A')}</td>
                <td><strong>{trade.get('symbol', 'N/A')}</strong></td>
                <td class="{action_class}">{trade.get('action', 'N/A')}</td>
                <td>{trade.get('type', 'N/A')}</td>
                <td>{trade.get('quantity', 0)}</td>
                <td>${trade.get('filled_price', 0):.2f}</td>
                <td class="{pnl_class}">${pnl:,.2f}</td>
                <td>{trade.get('timestamp', 'N/A')[:19]}</td>
            </tr>
"""
        
        html_content += """        </table>
    </div>
</body>
</html>
"""
        
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"✅ Trade log HTML saved to: {html_path}")
        return html_path


# ============================================================================
# STRATEGY ORCHESTRATOR (MAIN INTEGRATION LAYER)
# ============================================================================

class StrategyOrchestrator:
    """
    Main integration layer coordinating Strategy Bot and Backtester.
    
    Responsibilities:
    - Unified execution flow (signals → orders → P&L)
    - Deterministic coupling with unified random seed
    - Performance SLA validation
    - Multi-format reporting
    - Cross-system validation
    """
    
    DETERMINISTIC_SEED = hash("phase9c_deterministic_seed") % (2**32)
    
    def __init__(
        self,
        mode: OrchestratorMode = OrchestratorMode.MOCK,
        output_dir: Path = Path("outputs/phase9c"),
        use_cache: bool = True
    ):
        self.mode = mode
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.validator = IntegrationValidator()
        self.monitor = PerformanceMonitor()
        self.reporter = UnifiedReporter(output_dir)
        
        # Initialize backtester
        self.backtester = StrategyBacktester(
            data_dir=Path("data/backtest"),
            output_dir=output_dir / "backtest",
            use_cache=use_cache
        )
        
        # Set unified random seed for determinism
        np.random.seed(self.DETERMINISTIC_SEED)
        
        # Results storage
        self.all_signals: List[SignalSchema] = []
        self.all_trades: List[Dict[str, Any]] = []
        self.tier_results: Dict[str, Any] = {}
        
        logger.info(f"🎭 StrategyOrchestrator initialized: {mode.value} mode")
        logger.info(f"   Deterministic seed: {self.DETERMINISTIC_SEED}")
        logger.info(f"   Output directory: {output_dir}")
    
    def generate_signals_for_tier(
        self,
        tier: PortfolioSize,
        tickers: List[str],
        signals_per_ticker: int = 10
    ) -> List[SignalSchema]:
        """Generate canonical signals for a portfolio tier"""
        
        signals = []
        
        for ticker in tickers:
            for i in range(signals_per_ticker):
                # Deterministic signal generation
                seed = hash(f"{ticker}_{i}_{self.DETERMINISTIC_SEED}") % (2**32)
                np.random.seed(seed)
                
                # Generate canonical signal
                signal = SignalSchema(
                    signal_id=f"{tier.value}_{ticker}_{i}_{seed}",
                    symbol=ticker,
                    type="STOCK",  # Simplified for determinism
                    action="BUY" if i % 2 == 0 else "SELL",
                    quantity=np.random.randint(1, 10) * 10,
                    confidence=np.random.uniform(0.6, 0.95),
                    limit_price=100.0 + np.random.uniform(-10, 10),
                    metadata={
                        "tier": tier.value,
                        "iteration": 0,
                        "seed": seed
                    }
                )
                
                signals.append(signal)
        
        return signals
    
    def execute_tier(
        self,
        tier: PortfolioSize,
        tickers: List[str],
        signals_per_ticker: int,
        num_iterations: int = 3
    ) -> Dict[str, Any]:
        """Execute full backtest for a portfolio tier with multiple iterations"""
        
        tier_name = tier.value
        logger.info(f"\n{'='*100}")
        logger.info(f"🎯 Executing Tier: {tier_name.upper()}")
        logger.info(f"   Tickers: {len(tickers)}")
        logger.info(f"   Signals per Ticker: {signals_per_ticker}")
        logger.info(f"   Iterations: {num_iterations}")
        logger.info(f"{'='*100}\n")
        
        # Start performance monitoring
        start_time = self.monitor.start_monitoring(tier_name)
        
        # Generate signals (same for all iterations)
        signals = self.generate_signals_for_tier(tier, tickers, signals_per_ticker)
        self.all_signals.extend(signals)
        
        # Convert to TradeSignal objects
        trade_signals = [s.to_trade_signal() for s in signals]
        
        # Run backtest with multiple iterations
        report = self.backtester.run_multi_iteration_backtest(
            portfolio_size=tier,
            tickers=tickers,
            num_iterations=num_iterations,
            signals_per_ticker=signals_per_ticker
        )
        
        # Validate determinism
        deterministic, determinism_score, messages = self.validator.validate_determinism(
            report.iterations
        )
        
        if not deterministic:
            logger.warning(f"⚠️  Determinism check failed for {tier_name}:")
            for msg in messages:
                logger.warning(f"   - {msg}")
        
        # Calculate metrics
        total_trades = sum(it.num_trades_executed for it in report.iterations)
        avg_time_ms = report.avg_iteration_time_ms
        total_pnl = report.total_pnl_all_iterations
        
        # Calculate win rate and mean return
        all_pnls = []
        for iteration in report.iterations:
            for trade in iteration.trades:
                if trade.realized_pnl is not None:
                    all_pnls.append(trade.realized_pnl)
        
        wins = sum(1 for pnl in all_pnls if pnl > 0)
        win_rate = (wins / len(all_pnls) * 100) if all_pnls else 0.0
        mean_return = np.mean(all_pnls) if all_pnls else 0.0
        max_drawdown = min(all_pnls) if all_pnls else 0.0
        
        # Stop performance monitoring
        perf_metrics = self.monitor.stop_monitoring(
            tier=tier_name,
            start_time=start_time,
            num_tickers=len(tickers),
            num_signals=len(signals),
            num_trades=total_trades,
            total_pnl=total_pnl,
            win_rate=win_rate,
            mean_return=mean_return,
            max_drawdown=max_drawdown,
            var_95=report.avg_var_95,
            cvar_95=report.avg_cvar_95
        )
        
        # Store trades for reporting
        for iteration in report.iterations:
            for trade in iteration.trades:
                self.all_trades.append({
                    'tier': tier_name,
                    'iteration': iteration.iteration_id,
                    'symbol': trade.signal.symbol,
                    'action': trade.signal.signal_type.value,
                    'type': 'STOCK',
                    'quantity': trade.signal.qty,
                    'filled_price': trade.filled_price,
                    'realized_pnl': trade.realized_pnl or 0.0,
                    'timestamp': trade.timestamp
                })
        
        # Tier results
        tier_result = {
            'tier': tier_name,
            'num_tickers': len(tickers),
            'num_signals': len(signals),
            'num_iterations': num_iterations,
            'total_trades': total_trades,
            'avg_time_ms': avg_time_ms,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'mean_return': mean_return,
            'max_drawdown': max_drawdown,
            'var_95': report.avg_var_95,
            'cvar_95': report.avg_cvar_95,
            'deterministic': deterministic,
            'determinism_score': determinism_score,
            'sla_met': perf_metrics.sla_met,
            'sla_target_ms': perf_metrics.sla_target_ms,
            'memory_mb': perf_metrics.memory_usage_mb,
            'cpu_pct': perf_metrics.cpu_utilization_pct,
            'report_id': report.report_id
        }
        
        self.tier_results[tier_name] = tier_result
        
        logger.info(f"\n✅ Tier {tier_name.upper()} Complete:")
        logger.info(f"   Total Trades: {total_trades}")
        logger.info(f"   Avg Time: {avg_time_ms:.2f} ms")
        logger.info(f"   Total P&L: ${total_pnl:,.2f}")
        logger.info(f"   Deterministic: {'✅ YES' if deterministic else '❌ NO'}")
        logger.info(f"   SLA Met: {'✅ YES' if perf_metrics.sla_met else '❌ NO'}\n")
        
        return tier_result
    
    def run_full_validation(
        self,
        tiers: List[str] = ["small", "medium", "large"],
        num_iterations: int = 3
    ) -> Dict[str, Any]:
        """Run full validation across all portfolio tiers"""
        
        logger.info(f"\n{'#'*100}")
        logger.info(f"# PHASE 9C INTEGRATION VALIDATION — FULL SUITE")
        logger.info(f"# Mode: {self.mode.value}")
        logger.info(f"# Iterations per Tier: {num_iterations}")
        logger.info(f"# Tiers: {', '.join(tiers)}")
        logger.info(f"{'#'*100}\n")
        
        # Portfolio configurations
        tier_configs = {
            "small": {
                "size": PortfolioSize.SMALL,
                "tickers": ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
                "signals_per_ticker": 10
            },
            "medium": {
                "size": PortfolioSize.MEDIUM,
                "tickers": [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
                    'TSLA', 'NVDA', 'JPM', 'V', 'WMT',
                    'JNJ', 'PG', 'UNH', 'HD', 'DIS',
                    'NFLX', 'PYPL', 'ADBE', 'CRM', 'INTC',
                    'CSCO', 'PFE', 'ABT', 'CVX', 'XOM'
                ],
                "signals_per_ticker": 10
            },
            "large": {
                "size": PortfolioSize.LARGE,
                "tickers": [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
                    'TSLA', 'NVDA', 'JPM', 'V', 'WMT',
                    'JNJ', 'PG', 'UNH', 'HD', 'DIS',
                    'NFLX', 'PYPL', 'ADBE', 'CRM', 'INTC',
                    'CSCO', 'PFE', 'ABT', 'CVX', 'XOM',
                    'T', 'VZ', 'MRK', 'KO', 'PEP',
                    'BA', 'GE', 'CAT', 'MMM', 'HON',
                    'IBM', 'ORCL', 'QCOM', 'TXN', 'AVGO',
                    'AMD', 'MU', 'AMAT', 'LRCX', 'KLAC',
                    'REGN', 'GILD', 'BIIB', 'AMGN', 'VRTX'
                ] + [f'ETF{i}' for i in range(1, 51)],
                "signals_per_ticker": 5
            }
        }
        
        # Execute each tier
        for tier_name in tiers:
            if tier_name not in tier_configs:
                logger.warning(f"⚠️  Unknown tier: {tier_name}, skipping")
                continue
            
            config = tier_configs[tier_name]
            try:
                self.execute_tier(
                    tier=config["size"],
                    tickers=config["tickers"],
                    signals_per_ticker=config["signals_per_ticker"],
                    num_iterations=num_iterations
                )
            except Exception as e:
                logger.error(f"❌ Failed to execute tier {tier_name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Calculate overall results
        total_trades = sum(t.get('total_trades', 0) for t in self.tier_results.values())
        total_pnl = sum(t.get('total_pnl', 0) for t in self.tier_results.values())
        all_deterministic = all(t.get('deterministic', False) for t in self.tier_results.values())
        all_sla_met = all(t.get('sla_met', False) for t in self.tier_results.values())
        
        avg_win_rate = np.mean([t.get('win_rate', 0) for t in self.tier_results.values()])
        avg_mean_return = np.mean([t.get('mean_return', 0) for t in self.tier_results.values()])
        min_drawdown = min([t.get('max_drawdown', 0) for t in self.tier_results.values()], default=0.0)
        
        # Orchestrator results
        orchestrator_results = {
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode.value,
            "deterministic_seed": self.DETERMINISTIC_SEED,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "win_rate": avg_win_rate,
            "mean_return": avg_mean_return,
            "max_drawdown": min_drawdown,
            "all_deterministic": all_deterministic,
            "all_sla_met": all_sla_met,
            "tiers": self.tier_results
        }
        
        # Validation results
        validation_results = {
            "all_deterministic": all_deterministic,
            "determinism_score": np.mean([t.get('determinism_score', 0) for t in self.tier_results.values()]),
            "hash_consistency": all_deterministic,
            "pnl_consistency": all_deterministic
        }
        
        # Performance summary
        performance_summary = self.monitor.get_sla_summary()
        
        # Generate reports
        logger.info(f"\n{'='*100}")
        logger.info("📝 Generating Reports...")
        logger.info(f"{'='*100}\n")
        
        self.reporter.generate_integration_report(
            orchestrator_results,
            performance_summary,
            validation_results
        )
        self.reporter.generate_results_json(orchestrator_results)
        self.reporter.generate_performance_csv(self.monitor.metrics)
        self.reporter.generate_trade_log_html(self.all_trades)
        
        # Print summary table
        self.print_summary_table()
        
        logger.info(f"\n{'#'*100}")
        logger.info(f"# ✅ PHASE 9C INTEGRATION VALIDATION COMPLETE")
        logger.info(f"# Total Trades: {total_trades}")
        logger.info(f"# Total P&L: ${total_pnl:,.2f}")
        logger.info(f"# All Deterministic: {'✅ YES' if all_deterministic else '❌ NO'}")
        logger.info(f"# All SLAs Met: {'✅ YES' if all_sla_met else '❌ NO'}")
        logger.info(f"{'#'*100}\n")
        
        return orchestrator_results
    
    def print_summary_table(self):
        """Print formatted summary table"""
        
        logger.info("\n" + "="*120)
        logger.info("SUMMARY TABLE")
        logger.info("="*120)
        logger.info(f"{'Tier':<10} | {'Trades':<8} | {'Avg Time':<12} | {'P&L':<15} | {'Deterministic':<15} | {'SLA':<5}")
        logger.info("-"*120)
        
        for tier_name in ["small", "medium", "large"]:
            if tier_name in self.tier_results:
                t = self.tier_results[tier_name]
                logger.info(
                    f"{tier_name.upper():<10} | "
                    f"{t.get('total_trades', 0):<8} | "
                    f"{t.get('avg_time_ms', 0):.2f} ms     | "
                    f"${t.get('total_pnl', 0):>12,.2f} | "
                    f"{'✅' if t.get('deterministic', False) else '❌':<15} | "
                    f"{'✅' if t.get('sla_met', False) else '❌':<5}"
                )
        
        logger.info("="*120 + "\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution for testing"""
    
    orchestrator = StrategyOrchestrator(
        mode=OrchestratorMode.MOCK,
        output_dir=Path("outputs/phase9c")
    )
    
    results = orchestrator.run_full_validation(
        tiers=["small", "medium", "large"],
        num_iterations=3
    )
    
    logger.info("🎉 Phase 9C Integration Complete!")


if __name__ == "__main__":
    main()
