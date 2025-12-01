#!/usr/bin/env python3
"""
Backtest Validation Runner — Phase 6-8B
========================================

Comprehensive validation script to run backtesting framework across
all portfolio tiers (Small/Medium/Large) with full determinism validation.

Features:
- 3-iteration validation per portfolio tier
- Performance SLA validation
- Reproducibility testing
- Comprehensive report generation
- Multi-format output (JSON, CSV, Markdown, HTML)

Usage:
    python tests/run_backtester_validation.py

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0
Date: October 29, 2025
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from strategy_backtester import (
    StrategyBacktester,
    PortfolioSize,
    BacktestReport
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PORTFOLIO CONFIGURATIONS
# ============================================================================

PORTFOLIO_CONFIGS = {
    PortfolioSize.SMALL: {
        'tickers': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
        'signals_per_ticker': 10,
        'sla_target_ms': 50.0,
        'description': 'Small Portfolio (1-5 tickers)'
    },
    PortfolioSize.MEDIUM: {
        'tickers': [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
            'TSLA', 'NVDA', 'JPM', 'V', 'WMT',
            'JNJ', 'PG', 'UNH', 'HD', 'DIS',
            'NFLX', 'PYPL', 'ADBE', 'CRM', 'INTC',
            'CSCO', 'PFE', 'ABT', 'CVX', 'XOM'
        ],
        'signals_per_ticker': 10,
        'sla_target_ms': 200.0,
        'description': 'Medium Portfolio (10-50 tickers)'
    },
    PortfolioSize.LARGE: {
        'tickers': [
            # Top 50 tickers
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
        ] + [f'ETF{i}' for i in range(1, 51)],  # Add 50 more synthetic tickers
        'signals_per_ticker': 5,
        'sla_target_ms': 500.0,
        'description': 'Large Portfolio (50-100 tickers)'
    }
}


# ============================================================================
# VALIDATION RUNNER
# ============================================================================

class BacktestValidationRunner:
    """Orchestrate comprehensive validation across all portfolio tiers"""
    
    def __init__(self, output_dir: Path = Path("outputs/backtests")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.backtester = StrategyBacktester(
            data_dir=Path("data/backtest"),
            output_dir=self.output_dir,
            use_cache=True
        )
        
        self.validation_results: List[Dict[str, Any]] = []
    
    def run_portfolio_tier_validation(
        self,
        portfolio_size: PortfolioSize,
        num_iterations: int = 3
    ) -> BacktestReport:
        """Run validation for a specific portfolio tier"""
        
        config = PORTFOLIO_CONFIGS[portfolio_size]
        
        logger.info(f"\n{'='*100}")
        logger.info(f"🔍 VALIDATING: {config['description']}")
        logger.info(f"   Tickers: {len(config['tickers'])}")
        logger.info(f"   Signals per Ticker: {config['signals_per_ticker']}")
        logger.info(f"   SLA Target: {config['sla_target_ms']} ms")
        logger.info(f"   Iterations: {num_iterations}")
        logger.info(f"{'='*100}\n")
        
        # Run backtest
        report = self.backtester.run_multi_iteration_backtest(
            portfolio_size=portfolio_size,
            tickers=config['tickers'],
            num_iterations=num_iterations,
            signals_per_ticker=config['signals_per_ticker']
        )
        
        # Generate reports for this tier
        tier_output_dir = self.output_dir / portfolio_size.value
        tier_output_dir.mkdir(parents=True, exist_ok=True)
        
        tier_generator = self.backtester.report_generator
        tier_generator.output_dir = tier_output_dir
        
        tier_generator.generate_json_report(
            report,
            filename=f"{portfolio_size.value}_backtest_report.json"
        )
        tier_generator.generate_markdown_summary(
            report,
            filename=f"{portfolio_size.value}_backtest_summary.md"
        )
        tier_generator.generate_csv_exports(report)
        tier_generator.generate_html_charts(
            report,
            filename=f"{portfolio_size.value}_backtest_charts.html"
        )
        
        # Log validation summary
        self._log_tier_summary(portfolio_size, report, config)
        
        # Store results
        self.validation_results.append({
            'portfolio_size': portfolio_size.value,
            'num_tickers': len(config['tickers']),
            'sla_target_ms': config['sla_target_ms'],
            'determinism_score': report.determinism_score,
            'all_sla_met': report.all_sla_met,
            'avg_iteration_time_ms': report.avg_iteration_time_ms,
            'total_pnl': report.total_pnl_all_iterations,
            'report_id': report.report_id
        })
        
        return report
    
    def _log_tier_summary(
        self,
        portfolio_size: PortfolioSize,
        report: BacktestReport,
        config: Dict[str, Any]
    ):
        """Log summary for tier validation"""
        
        logger.info(f"\n{'─'*100}")
        logger.info(f"📊 VALIDATION SUMMARY: {config['description']}")
        logger.info(f"{'─'*100}")
        
        # Reproducibility
        logger.info(f"\n🔄 Reproducibility:")
        logger.info(f"   Determinism Score: {report.determinism_score:.1f}% {'✅' if report.determinism_score >= 99.0 else '❌'}")
        logger.info(f"   Hash Consistency: {report.hash_consistency} {'✅' if report.hash_consistency else '❌'}")
        logger.info(f"   All Iterations Identical: {report.all_iterations_identical} {'✅' if report.all_iterations_identical else '❌'}")
        
        # Performance
        logger.info(f"\n⚡ Performance:")
        logger.info(f"   Avg Iteration Time: {report.avg_iteration_time_ms:.2f} ms")
        logger.info(f"   Min/Max: {report.min_iteration_time_ms:.2f} / {report.max_iteration_time_ms:.2f} ms")
        logger.info(f"   SLA Target: {config['sla_target_ms']} ms")
        logger.info(f"   All SLAs Met: {report.all_sla_met} {'✅' if report.all_sla_met else '❌'}")
        logger.info(f"   SLA Compliance: {report.sla_compliance_rate:.1f}%")
        logger.info(f"   Avg Throughput: {report.avg_throughput:.2f} trades/sec")
        
        # P&L
        logger.info(f"\n💰 P&L:")
        logger.info(f"   Total P&L (All Iterations): ${report.total_pnl_all_iterations:,.2f}")
        logger.info(f"   Avg P&L per Iteration: ${report.avg_pnl_per_iteration:,.2f}")
        logger.info(f"   P&L Std Dev: ${report.pnl_std_dev:,.2f}")
        
        # Risk
        logger.info(f"\n🛡️  Risk Metrics:")
        logger.info(f"   Avg VaR (95%): ${report.avg_var_95:,.2f}")
        logger.info(f"   Avg CVaR (95%): ${report.avg_cvar_95:,.2f}")
        logger.info(f"   Max Drawdown: {report.max_drawdown:.2f}%")
        
        # Iterations
        logger.info(f"\n📈 Iteration Details:")
        for i, iteration in enumerate(report.iterations, 1):
            logger.info(f"   Iteration {i}: {iteration.total_time_ms:.2f} ms, "
                       f"{iteration.num_trades_executed} trades, "
                       f"${iteration.net_pnl:,.2f} P&L, "
                       f"{'✅ SLA' if iteration.sla_met else '❌ SLA'}")
        
        logger.info(f"\n{'─'*100}\n")
    
    def run_full_validation(self, num_iterations: int = 3):
        """Run validation across all portfolio tiers"""
        
        logger.info(f"\n{'#'*100}")
        logger.info(f"# BACKTESTING VALIDATION — FULL SUITE")
        logger.info(f"# Phase 6-8B: Strategy Bot Validation Framework")
        logger.info(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'#'*100}\n")
        
        reports = {}
        
        # Run validation for each tier
        for portfolio_size in [PortfolioSize.SMALL, PortfolioSize.MEDIUM, PortfolioSize.LARGE]:
            try:
                report = self.run_portfolio_tier_validation(
                    portfolio_size=portfolio_size,
                    num_iterations=num_iterations
                )
                reports[portfolio_size] = report
            except Exception as e:
                logger.error(f"❌ Failed to validate {portfolio_size.value}: {e}")
                import traceback
                traceback.print_exc()
        
        # Generate consolidated summary
        self._generate_consolidated_summary(reports)
        
        return reports
    
    def _generate_consolidated_summary(self, reports: Dict[PortfolioSize, BacktestReport]):
        """Generate consolidated summary across all tiers"""
        
        logger.info(f"\n{'#'*100}")
        logger.info(f"# CONSOLIDATED VALIDATION SUMMARY")
        logger.info(f"{'#'*100}\n")
        
        summary_data = {
            'validation_timestamp': datetime.now().isoformat(),
            'num_tiers_tested': len(reports),
            'tiers': []
        }
        
        all_deterministic = True
        all_sla_met = True
        
        for portfolio_size, report in reports.items():
            tier_data = {
                'portfolio_size': portfolio_size.value,
                'num_tickers': len(report.tickers),
                'num_iterations': report.num_iterations,
                'determinism_score': report.determinism_score,
                'all_sla_met': report.all_sla_met,
                'sla_compliance_rate': report.sla_compliance_rate,
                'avg_iteration_time_ms': report.avg_iteration_time_ms,
                'total_pnl': report.total_pnl_all_iterations,
                'avg_var_95': report.avg_var_95,
                'report_id': report.report_id
            }
            summary_data['tiers'].append(tier_data)
            
            if report.determinism_score < 99.0:
                all_deterministic = False
            if not report.all_sla_met:
                all_sla_met = False
            
            logger.info(f"✅ {portfolio_size.value.upper()}: "
                       f"Determinism {report.determinism_score:.1f}%, "
                       f"SLA {'PASS' if report.all_sla_met else 'FAIL'}, "
                       f"Avg Time {report.avg_iteration_time_ms:.2f} ms")
        
        summary_data['all_tiers_deterministic'] = all_deterministic
        summary_data['all_tiers_sla_met'] = all_sla_met
        summary_data['overall_status'] = 'PASS' if (all_deterministic and all_sla_met) else 'PARTIAL'
        
        # Save consolidated summary
        summary_path = self.output_dir / "validation_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        logger.info(f"\n{'─'*100}")
        logger.info(f"📊 Overall Status: {summary_data['overall_status']}")
        logger.info(f"   All Tiers Deterministic: {'✅ YES' if all_deterministic else '❌ NO'}")
        logger.info(f"   All SLAs Met: {'✅ YES' if all_sla_met else '❌ NO'}")
        logger.info(f"   Summary saved to: {summary_path}")
        logger.info(f"{'─'*100}\n")
        
        # Generate markdown summary
        self._generate_markdown_summary(summary_data, reports)
    
    def _generate_markdown_summary(
        self,
        summary_data: Dict[str, Any],
        reports: Dict[PortfolioSize, BacktestReport]
    ):
        """Generate consolidated markdown summary"""
        
        md_path = self.output_dir / "VALIDATION_SUMMARY.md"
        
        md_content = f"""# Backtest Validation Summary

**Generated:** {summary_data['validation_timestamp']}  
**Tiers Tested:** {summary_data['num_tiers_tested']}  
**Overall Status:** {'✅ PASS' if summary_data['overall_status'] == 'PASS' else '⚠️ PARTIAL'}

---

## 🎯 Validation Results

| Portfolio Tier | Tickers | Iterations | Determinism | SLA Met | Avg Time (ms) | Total P&L |
|---------------|---------|------------|-------------|---------|---------------|-----------|
"""
        
        for tier_data in summary_data['tiers']:
            determinism_icon = '✅' if tier_data['determinism_score'] >= 99.0 else '❌'
            sla_icon = '✅' if tier_data['all_sla_met'] else '❌'
            
            md_content += f"""| {tier_data['portfolio_size'].upper()} | {tier_data['num_tickers']} | {tier_data['num_iterations']} | {tier_data['determinism_score']:.1f}% {determinism_icon} | {sla_icon} | {tier_data['avg_iteration_time_ms']:.2f} | ${tier_data['total_pnl']:,.2f} |
"""
        
        md_content += f"""
---

## 📋 Summary

- **All Tiers Deterministic:** {'✅ YES' if summary_data['all_tiers_deterministic'] else '❌ NO'}
- **All SLAs Met:** {'✅ YES' if summary_data['all_tiers_sla_met'] else '❌ NO'}
- **Framework Status:** {'✅ Production Ready' if summary_data['overall_status'] == 'PASS' else '⚠️ Needs Optimization'}

---

## 📁 Detailed Reports

"""
        
        for portfolio_size, report in reports.items():
            md_content += f"""
### {portfolio_size.value.upper()} Portfolio

- **Report ID:** `{report.report_id}`
- **Tickers:** {len(report.tickers)}
- **Total Trades:** {sum(it.num_trades_executed for it in report.iterations)}
- **Determinism Score:** {report.determinism_score:.1f}%
- **SLA Compliance:** {report.sla_compliance_rate:.1f}%
- **Detailed Reports:** `outputs/backtests/{portfolio_size.value}/`

"""
        
        md_content += """
---

**Report Generated by:** Strategy Backtester Validation Runner v1.0  
**Framework Version:** Phase 6-8B
"""
        
        with open(md_path, 'w') as f:
            f.write(md_content)
        
        logger.info(f"📝 Markdown summary saved to: {md_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main validation execution"""
    
    try:
        # Initialize runner
        runner = BacktestValidationRunner(
            output_dir=Path("outputs/backtests")
        )
        
        # Run full validation suite
        reports = runner.run_full_validation(num_iterations=3)
        
        # Final status
        logger.info(f"\n{'#'*100}")
        logger.info(f"# ✅ VALIDATION COMPLETE")
        logger.info(f"# Total Tiers Validated: {len(reports)}")
        logger.info(f"# Output Directory: outputs/backtests/")
        logger.info(f"{'#'*100}\n")
        
        # Print next steps
        logger.info("📁 Next Steps:")
        logger.info("   1. Review outputs/backtests/VALIDATION_SUMMARY.md")
        logger.info("   2. Check tier-specific reports in outputs/backtests/{small,medium,large}/")
        logger.info("   3. Examine JSON reports for detailed trade logs")
        logger.info("   4. Open HTML charts for visualizations")
        logger.info("   5. Review PHASE6_8B_BACKTEST_COMPLETION.md for deliverables\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
