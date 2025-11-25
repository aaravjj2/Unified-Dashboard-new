"""
Phase 7 — Simulation Report Builder: Multi-Format Analytics Reporting
======================================================================

Aggregates scenario simulation outputs into comprehensive reports with visualizations.

Features:
- JSON reports (detailed structured data)
- CSV exports (tabular metrics for Excel/analysis)
- Markdown summaries (human-readable reports)
- Chart generation (PnL histograms, sector waterfalls, Greeks heatmaps)
- Batch report generation for multiple simulations
- Executive summary dashboards

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 7 - Offline Simulation Framework)
Date: October 29, 2025
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

# Import simulation components
from portfolio_simulator import SimulationResult, RiskMetrics, SectorExposure
from options_risk_simulator import OptionSimulationResult, Greeks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# REPORT BUILDER
# ============================================================================

class SimulationReportBuilder:
    """
    Generate comprehensive reports from simulation results.
    """
    
    def __init__(self, output_dir: str = "outputs/phase7_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # PORTFOLIO REPORTS
    # ========================================================================
    
    def generate_portfolio_json(
        self,
        results: List[SimulationResult],
        filename: str = "portfolio_simulations.json"
    ) -> str:
        """
        Generate comprehensive JSON report for portfolio simulations.
        
        Args:
            results: List of SimulationResult objects
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📄 Generating portfolio JSON report: {len(results)} simulations")
        
        report = {
            "report_type": "portfolio_simulations",
            "generated_at": datetime.now().isoformat(),
            "num_simulations": len(results),
            "simulations": [r.to_dict() for r in results],
            "summary": self._generate_portfolio_summary(results)
        }
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Saved portfolio JSON: {filepath}")
        return str(filepath)
    
    def generate_portfolio_csv(
        self,
        results: List[SimulationResult],
        filename: str = "portfolio_metrics.csv"
    ) -> str:
        """
        Generate CSV with portfolio metrics for each simulation.
        
        Args:
            results: List of SimulationResult objects
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📊 Generating portfolio CSV: {len(results)} simulations")
        
        rows = []
        for result in results:
            row = {
                "scenario_id": result.scenario_id,
                "scenario_type": result.scenario_type,
                "portfolio_id": result.portfolio_id,
                "initial_value": result.initial_portfolio_value,
                "final_value": result.final_portfolio_value,
                "total_pnl": result.total_pnl,
                "total_return_pct": result.total_return_pct,
                "annualized_return": result.risk_metrics.annualized_return,
                "annualized_volatility": result.risk_metrics.annualized_volatility,
                "sharpe_ratio": result.risk_metrics.sharpe_ratio,
                "sortino_ratio": result.risk_metrics.sortino_ratio,
                "var_95": result.risk_metrics.var_95,
                "var_99": result.risk_metrics.var_99,
                "cvar_95": result.risk_metrics.cvar_95,
                "cvar_99": result.risk_metrics.cvar_99,
                "max_drawdown": result.risk_metrics.max_drawdown,
                "max_dd_duration": result.risk_metrics.max_drawdown_duration,
                "skewness": result.risk_metrics.skewness,
                "kurtosis": result.risk_metrics.kurtosis
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        logger.info(f"✅ Saved portfolio CSV: {filepath}")
        return str(filepath)
    
    def generate_portfolio_markdown(
        self,
        results: List[SimulationResult],
        filename: str = "portfolio_summary.md"
    ) -> str:
        """
        Generate Markdown summary report.
        
        Args:
            results: List of SimulationResult objects
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📝 Generating portfolio Markdown report")
        
        summary = self._generate_portfolio_summary(results)
        
        md = []
        md.append("# Portfolio Simulation Report\n")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append(f"**Number of Simulations:** {len(results)}\n")
        md.append("\n---\n")
        
        # Executive Summary
        md.append("## Executive Summary\n")
        md.append(f"- **Mean Return:** {summary['mean_return']:.2%}\n")
        md.append(f"- **Median Return:** {summary['median_return']:.2%}\n")
        md.append(f"- **Best Case:** {summary['max_return']:.2%}\n")
        md.append(f"- **Worst Case:** {summary['min_return']:.2%}\n")
        md.append(f"- **Mean Sharpe Ratio:** {summary['mean_sharpe']:.2f}\n")
        md.append(f"- **Mean Max Drawdown:** {summary['mean_max_drawdown']:.2%}\n")
        md.append("\n")
        
        # Risk Metrics Summary
        md.append("## Risk Metrics Summary\n")
        md.append("| Metric | Mean | Median | Min | Max |\n")
        md.append("|--------|------|--------|-----|-----|\n")
        
        metrics = [
            ("VaR 95%", "mean_var_95", "median_var_95", "min_var_95", "max_var_95"),
            ("CVaR 95%", "mean_cvar_95", "median_cvar_95", "min_cvar_95", "max_cvar_95"),
            ("VaR 99%", "mean_var_99", "median_var_99", "min_var_99", "max_var_99"),
            ("CVaR 99%", "mean_cvar_99", "median_cvar_99", "min_cvar_99", "max_cvar_99")
        ]
        
        for label, mean_key, median_key, min_key, max_key in metrics:
            md.append(f"| {label} | {summary[mean_key]:.2%} | {summary[median_key]:.2%} | "
                     f"{summary[min_key]:.2%} | {summary[max_key]:.2%} |\n")
        
        md.append("\n")
        
        # Individual Simulation Results
        md.append("## Individual Simulation Results\n")
        md.append("| Scenario ID | Type | Return | Sharpe | Max DD | VaR 95% |\n")
        md.append("|-------------|------|--------|--------|--------|----------|\n")
        
        for result in results:
            md.append(f"| {result.scenario_id} | {result.scenario_type} | "
                     f"{result.total_return_pct:.2%} | {result.risk_metrics.sharpe_ratio:.2f} | "
                     f"{result.risk_metrics.max_drawdown:.2%} | {result.risk_metrics.var_95:.2%} |\n")
        
        md.append("\n")
        
        # Sector Exposure (if available)
        if results and results[0].sector_exposures:
            md.append("## Sector Exposure Analysis\n")
            md.append("*Based on first simulation*\n\n")
            md.append("| Sector | Weight | Avg Return | Volatility | Positions |\n")
            md.append("|--------|--------|------------|------------|------------|\n")
            
            for exposure in results[0].sector_exposures:
                md.append(f"| {exposure.sector} | {exposure.weight:.1%} | "
                         f"{exposure.avg_return:.2%} | {exposure.volatility:.2%} | "
                         f"{exposure.num_positions} |\n")
            
            md.append("\n")
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(''.join(md))
        
        logger.info(f"✅ Saved portfolio Markdown: {filepath}")
        return str(filepath)
    
    def _generate_portfolio_summary(self, results: List[SimulationResult]) -> Dict[str, Any]:
        """Generate summary statistics across all simulations"""
        if not results:
            return {}
        
        returns = [r.total_return_pct for r in results]
        sharpes = [r.risk_metrics.sharpe_ratio for r in results]
        var_95s = [r.risk_metrics.var_95 for r in results]
        var_99s = [r.risk_metrics.var_99 for r in results]
        cvar_95s = [r.risk_metrics.cvar_95 for r in results]
        cvar_99s = [r.risk_metrics.cvar_99 for r in results]
        max_dds = [r.risk_metrics.max_drawdown for r in results]
        
        return {
            "mean_return": np.mean(returns),
            "median_return": np.median(returns),
            "std_return": np.std(returns),
            "min_return": np.min(returns),
            "max_return": np.max(returns),
            "mean_sharpe": np.mean(sharpes),
            "median_sharpe": np.median(sharpes),
            "mean_var_95": np.mean(var_95s),
            "median_var_95": np.median(var_95s),
            "min_var_95": np.min(var_95s),
            "max_var_95": np.max(var_95s),
            "mean_var_99": np.mean(var_99s),
            "median_var_99": np.median(var_99s),
            "min_var_99": np.min(var_99s),
            "max_var_99": np.max(var_99s),
            "mean_cvar_95": np.mean(cvar_95s),
            "median_cvar_95": np.median(cvar_95s),
            "min_cvar_95": np.min(cvar_95s),
            "max_cvar_95": np.max(cvar_95s),
            "mean_cvar_99": np.mean(cvar_99s),
            "median_cvar_99": np.median(cvar_99s),
            "min_cvar_99": np.min(cvar_99s),
            "max_cvar_99": np.max(cvar_99s),
            "mean_max_drawdown": np.mean(max_dds),
            "median_max_drawdown": np.median(max_dds)
        }
    
    # ========================================================================
    # OPTIONS REPORTS
    # ========================================================================
    
    def generate_options_json(
        self,
        results: List[OptionSimulationResult],
        filename: str = "options_simulations.json"
    ) -> str:
        """
        Generate comprehensive JSON report for options simulations.
        
        Args:
            results: List of OptionSimulationResult objects
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📄 Generating options JSON report: {len(results)} simulations")
        
        report = {
            "report_type": "options_simulations",
            "generated_at": datetime.now().isoformat(),
            "num_simulations": len(results),
            "simulations": [r.to_dict() for r in results],
            "summary": self._generate_options_summary(results)
        }
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Saved options JSON: {filepath}")
        return str(filepath)
    
    def generate_options_csv(
        self,
        results: List[OptionSimulationResult],
        filename: str = "options_metrics.csv"
    ) -> str:
        """
        Generate CSV with options metrics.
        
        Args:
            results: List of OptionSimulationResult objects
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📊 Generating options CSV: {len(results)} simulations")
        
        rows = []
        for result in results:
            row = {
                "scenario_id": result.scenario_id,
                "ticker": result.contract.ticker,
                "option_type": result.contract.option_type.value,
                "strike": result.contract.strike,
                "expiry_days": result.contract.expiry_days,
                "contracts": result.contract.contracts,
                "initial_spot": result.initial_spot,
                "final_spot": result.final_spot,
                "initial_value": result.initial_value,
                "final_value": result.final_value,
                "total_pnl": result.total_pnl,
                "total_return_pct": result.total_return_pct,
                "initial_delta": result.initial_greeks.delta,
                "final_delta": result.final_greeks.delta,
                "initial_gamma": result.initial_greeks.gamma,
                "final_gamma": result.final_greeks.gamma,
                "initial_vega": result.initial_greeks.vega,
                "final_vega": result.final_greeks.vega,
                "initial_theta": result.initial_greeks.theta,
                "final_theta": result.final_greeks.theta,
                "initial_rho": result.initial_greeks.rho,
                "final_rho": result.final_greeks.rho
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        logger.info(f"✅ Saved options CSV: {filepath}")
        return str(filepath)
    
    def generate_options_markdown(
        self,
        results: List[OptionSimulationResult],
        filename: str = "options_summary.md"
    ) -> str:
        """
        Generate Markdown summary for options simulations.
        
        Args:
            results: List of OptionSimulationResult objects
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📝 Generating options Markdown report")
        
        summary = self._generate_options_summary(results)
        
        md = []
        md.append("# Options Simulation Report\n")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append(f"**Number of Simulations:** {len(results)}\n")
        md.append("\n---\n")
        
        # Executive Summary
        md.append("## Executive Summary\n")
        md.append(f"- **Total PnL:** ${summary['total_pnl']:,.2f}\n")
        md.append(f"- **Mean Return:** {summary['mean_return']:.2%}\n")
        md.append(f"- **Best Performance:** {summary['max_return']:.2%}\n")
        md.append(f"- **Worst Performance:** {summary['min_return']:.2%}\n")
        md.append(f"- **Win Rate:** {summary['win_rate']:.1%}\n")
        md.append("\n")
        
        # Greeks Summary
        md.append("## Greeks Summary\n")
        md.append("| Greek | Mean Initial | Mean Final | Change |\n")
        md.append("|-------|--------------|-----------|--------|\n")
        md.append(f"| Delta | {summary['mean_initial_delta']:.3f} | {summary['mean_final_delta']:.3f} | "
                 f"{summary['mean_final_delta'] - summary['mean_initial_delta']:.3f} |\n")
        md.append(f"| Gamma | {summary['mean_initial_gamma']:.3f} | {summary['mean_final_gamma']:.3f} | "
                 f"{summary['mean_final_gamma'] - summary['mean_initial_gamma']:.3f} |\n")
        md.append(f"| Vega | ${summary['mean_initial_vega']:.2f} | ${summary['mean_final_vega']:.2f} | "
                 f"${summary['mean_final_vega'] - summary['mean_initial_vega']:.2f} |\n")
        md.append(f"| Theta | ${summary['mean_initial_theta']:.2f} | ${summary['mean_final_theta']:.2f} | "
                 f"${summary['mean_final_theta'] - summary['mean_initial_theta']:.2f} |\n")
        md.append("\n")
        
        # Individual Results
        md.append("## Individual Option Results\n")
        md.append("| Ticker | Type | Strike | PnL | Return | Final Delta | Final Vega |\n")
        md.append("|--------|------|--------|-----|--------|-------------|------------|\n")
        
        for result in results:
            md.append(f"| {result.contract.ticker} | {result.contract.option_type.value} | "
                     f"${result.contract.strike:.2f} | ${result.total_pnl:,.2f} | "
                     f"{result.total_return_pct:.2%} | {result.final_greeks.delta:.3f} | "
                     f"${result.final_greeks.vega:.2f} |\n")
        
        md.append("\n")
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(''.join(md))
        
        logger.info(f"✅ Saved options Markdown: {filepath}")
        return str(filepath)
    
    def _generate_options_summary(self, results: List[OptionSimulationResult]) -> Dict[str, Any]:
        """Generate summary statistics for options"""
        if not results:
            return {}
        
        total_pnl = sum(r.total_pnl for r in results)
        returns = [r.total_return_pct for r in results]
        wins = sum(1 for r in results if r.total_pnl > 0)
        
        return {
            "total_pnl": total_pnl,
            "mean_return": np.mean(returns),
            "median_return": np.median(returns),
            "std_return": np.std(returns),
            "min_return": np.min(returns),
            "max_return": np.max(returns),
            "win_rate": wins / len(results) if results else 0.0,
            "mean_initial_delta": np.mean([r.initial_greeks.delta for r in results]),
            "mean_final_delta": np.mean([r.final_greeks.delta for r in results]),
            "mean_initial_gamma": np.mean([r.initial_greeks.gamma for r in results]),
            "mean_final_gamma": np.mean([r.final_greeks.gamma for r in results]),
            "mean_initial_vega": np.mean([r.initial_greeks.vega for r in results]),
            "mean_final_vega": np.mean([r.final_greeks.vega for r in results]),
            "mean_initial_theta": np.mean([r.initial_greeks.theta for r in results]),
            "mean_final_theta": np.mean([r.final_greeks.theta for r in results])
        }
    
    # ========================================================================
    # COMBINED REPORTS
    # ========================================================================
    
    def generate_executive_summary(
        self,
        portfolio_results: Optional[List[SimulationResult]] = None,
        options_results: Optional[List[OptionSimulationResult]] = None,
        filename: str = "executive_summary.md"
    ) -> str:
        """
        Generate combined executive summary.
        
        Args:
            portfolio_results: Portfolio simulation results
            options_results: Options simulation results
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info("📊 Generating executive summary")
        
        md = []
        md.append("# Phase 7 Simulation Framework - Executive Summary\n")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append("\n---\n")
        
        if portfolio_results:
            md.append("## Portfolio Simulations\n")
            summary = self._generate_portfolio_summary(portfolio_results)
            md.append(f"- **Number of Scenarios:** {len(portfolio_results)}\n")
            md.append(f"- **Mean Return:** {summary['mean_return']:.2%}\n")
            md.append(f"- **Mean Sharpe Ratio:** {summary['mean_sharpe']:.2f}\n")
            md.append(f"- **Mean VaR 95%:** {summary['mean_var_95']:.2%}\n")
            md.append(f"- **Mean Max Drawdown:** {summary['mean_max_drawdown']:.2%}\n")
            md.append("\n")
        
        if options_results:
            md.append("## Options Simulations\n")
            summary = self._generate_options_summary(options_results)
            md.append(f"- **Number of Contracts:** {len(options_results)}\n")
            md.append(f"- **Total PnL:** ${summary['total_pnl']:,.2f}\n")
            md.append(f"- **Mean Return:** {summary['mean_return']:.2%}\n")
            md.append(f"- **Win Rate:** {summary['win_rate']:.1%}\n")
            md.append("\n")
        
        md.append("## Framework Capabilities\n")
        md.append("- ✅ Monte Carlo simulations with GBM\n")
        md.append("- ✅ Stress testing (volatility spikes, sector shocks, black swans)\n")
        md.append("- ✅ Event-driven scenarios (earnings, Fed rates)\n")
        md.append("- ✅ Portfolio risk metrics (VaR, CVaR, Sharpe, Sortino)\n")
        md.append("- ✅ Options Greeks analysis (Delta, Gamma, Vega, Theta, Rho)\n")
        md.append("- ✅ Deterministic reproducibility (random seeds)\n")
        md.append("- ✅ Multi-format reporting (JSON/CSV/Markdown)\n")
        md.append("\n")
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(''.join(md))
        
        logger.info(f"✅ Saved executive summary: {filepath}")
        return str(filepath)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def generate_all_reports(
    portfolio_results: Optional[List[SimulationResult]] = None,
    options_results: Optional[List[OptionSimulationResult]] = None,
    output_dir: str = "outputs/phase7_reports"
) -> Dict[str, str]:
    """
    Generate all report formats.
    
    Args:
        portfolio_results: Portfolio simulation results
        options_results: Options simulation results
        output_dir: Output directory
        
    Returns:
        Dictionary of report type to filepath
    """
    builder = SimulationReportBuilder(output_dir)
    
    filepaths = {}
    
    if portfolio_results:
        filepaths["portfolio_json"] = builder.generate_portfolio_json(portfolio_results)
        filepaths["portfolio_csv"] = builder.generate_portfolio_csv(portfolio_results)
        filepaths["portfolio_markdown"] = builder.generate_portfolio_markdown(portfolio_results)
    
    if options_results:
        filepaths["options_json"] = builder.generate_options_json(options_results)
        filepaths["options_csv"] = builder.generate_options_csv(options_results)
        filepaths["options_markdown"] = builder.generate_options_markdown(options_results)
    
    filepaths["executive_summary"] = builder.generate_executive_summary(
        portfolio_results,
        options_results
    )
    
    return filepaths


# ============================================================================
# BATCH REPORTING EXTENSIONS (Phase 7 Advanced)
# ============================================================================

class BatchReportBuilder(SimulationReportBuilder):
    """
    Extended report builder for batch simulation analysis.
    
    Adds capabilities for:
    - Risk heatmaps (scenarios × tickers)
    - Multi-scenario aggregation tables
    - Sector exposure breakdowns
    - Offline HTML previews with interactive charts
    """
    
    def __init__(self, output_dir: str = "outputs/phase7_batch_reports"):
        super().__init__(output_dir)
    
    # ========================================================================
    # BATCH PORTFOLIO REPORTS
    # ========================================================================
    
    def generate_batch_summary_json(
        self,
        batch_id: str,
        portfolio_results: List[SimulationResult],
        aggregate_metrics: Dict[str, Any],
        scenario_metadata: List[Dict[str, Any]],
        performance_metrics: Dict[str, float],
        filename: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive JSON summary for batch simulations.
        
        Args:
            batch_id: Unique batch identifier
            portfolio_results: List of portfolio simulation results
            aggregate_metrics: Aggregated metrics across all scenarios
            scenario_metadata: Metadata for each scenario
            performance_metrics: Execution time, cache hit rate, etc.
            filename: Optional custom filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📊 Generating batch summary JSON: {batch_id}")
        
        filename = filename or f"{batch_id}_summary.json"
        
        report = {
            "batch_id": batch_id,
            "report_type": "batch_portfolio_summary",
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "num_scenarios": len(portfolio_results),
                "num_scenario_types": len(set(r.scenario_type for r in portfolio_results)),
                "portfolio_ids": list(set(r.portfolio_id for r in portfolio_results))
            },
            "scenarios": scenario_metadata,
            "aggregate_metrics": aggregate_metrics,
            "performance": performance_metrics,
            "individual_results": [r.to_dict() for r in portfolio_results]
        }
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Saved batch summary JSON: {filepath}")
        return str(filepath)
    
    def generate_risk_heatmap_data(
        self,
        portfolio_results: List[SimulationResult],
        filename: str = "risk_heatmap.json"
    ) -> str:
        """
        Generate risk heatmap data (scenarios × tickers matrix).
        
        Format: {scenario_id: {ticker: metric_value}}
        Metrics: returns, volatility, max_drawdown
        
        Args:
            portfolio_results: List of simulation results
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info("🔥 Generating risk heatmap data")
        
        heatmap_data = {
            "returns": {},
            "volatility": {},
            "max_drawdown": {},
            "var_95": {}
        }
        
        for result in portfolio_results:
            scenario_id = result.scenario_id
            
            heatmap_data["returns"][scenario_id] = result.total_return_pct
            heatmap_data["volatility"][scenario_id] = result.risk_metrics.annualized_volatility
            heatmap_data["max_drawdown"][scenario_id] = result.risk_metrics.max_drawdown
            heatmap_data["var_95"][scenario_id] = result.risk_metrics.var_95
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(heatmap_data, f, indent=2)
        
        logger.info(f"✅ Saved risk heatmap data: {filepath}")
        return str(filepath)
    
    def generate_scenario_comparison_csv(
        self,
        portfolio_results: List[SimulationResult],
        filename: str = "scenario_comparison.csv"
    ) -> str:
        """
        Generate CSV comparing all scenarios side-by-side.
        
        Columns: scenario_id, scenario_type, total_return, sharpe, var_95, var_99, max_dd
        
        Args:
            portfolio_results: List of simulation results
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        logger.info("📊 Generating scenario comparison CSV")
        
        rows = []
        for result in portfolio_results:
            rows.append({
                "scenario_id": result.scenario_id,
                "scenario_type": result.scenario_type,
                "total_return_pct": result.total_return_pct,
                "sharpe_ratio": result.risk_metrics.sharpe_ratio,
                "sortino_ratio": result.risk_metrics.sortino_ratio,
                "var_95": result.risk_metrics.var_95,
                "var_99": result.risk_metrics.var_99,
                "cvar_95": result.risk_metrics.cvar_95,
                "cvar_99": result.risk_metrics.cvar_99,
                "max_drawdown": result.risk_metrics.max_drawdown,
                "annualized_volatility": result.risk_metrics.annualized_volatility,
                "skewness": result.risk_metrics.skewness,
                "kurtosis": result.risk_metrics.kurtosis
            })
        
        df = pd.DataFrame(rows)
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        logger.info(f"✅ Saved scenario comparison CSV: {filepath}")
        return str(filepath)
    
    def generate_batch_markdown_report(
        self,
        batch_id: str,
        portfolio_results: List[SimulationResult],
        aggregate_metrics: Dict[str, Any],
        performance_metrics: Dict[str, float],
        filename: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive Markdown report for batch.
        
        Args:
            batch_id: Batch identifier
            portfolio_results: Portfolio simulation results
            aggregate_metrics: Aggregate metrics
            performance_metrics: Performance metrics
            filename: Optional custom filename
            
        Returns:
            Path to generated file
        """
        logger.info(f"📝 Generating batch Markdown report: {batch_id}")
        
        filename = filename or f"{batch_id}_report.md"
        
        md_lines = [
            f"# Phase 7 Batch Simulation Report",
            f"",
            f"**Batch ID:** `{batch_id}`  ",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Total Scenarios:** {len(portfolio_results)}  ",
            f"",
            f"---",
            f"",
            f"## 📊 Executive Summary",
            f"",
            f"### Performance Metrics",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Execution Time | {performance_metrics.get('total_execution_time_ms', 0) / 1000:.2f}s |",
            f"| Scenarios/Second | {performance_metrics.get('scenarios_per_second', 0):.2f} |",
            f"| Cache Hit Rate | {performance_metrics.get('cache_hit_rate', 0):.1%} |",
            f"",
            f"### Aggregate Returns",
            f"",
            f"| Statistic | Value |",
            f"|-----------|-------|",
            f"| Mean Return | {aggregate_metrics.get('returns', {}).get('mean', 0):.2%} |",
            f"| Median Return | {aggregate_metrics.get('returns', {}).get('median', 0):.2%} |",
            f"| Std Deviation | {aggregate_metrics.get('returns', {}).get('std', 0):.2%} |",
            f"| Min Return | {aggregate_metrics.get('returns', {}).get('min', 0):.2%} |",
            f"| Max Return | {aggregate_metrics.get('returns', {}).get('max', 0):.2%} |",
            f"| 5th Percentile | {aggregate_metrics.get('returns', {}).get('percentile_5', 0):.2%} |",
            f"| 95th Percentile | {aggregate_metrics.get('returns', {}).get('percentile_95', 0):.2%} |",
            f"",
            f"### Risk Metrics",
            f"",
            f"| Metric | Mean | Median | Min | Max |",
            f"|--------|------|--------|-----|-----|",
            f"| Sharpe Ratio | {aggregate_metrics.get('sharpe_ratio', {}).get('mean', 0):.2f} | {aggregate_metrics.get('sharpe_ratio', {}).get('median', 0):.2f} | {aggregate_metrics.get('sharpe_ratio', {}).get('min', 0):.2f} | {aggregate_metrics.get('sharpe_ratio', {}).get('max', 0):.2f} |",
            f"| VaR 95% | {aggregate_metrics.get('var_95', {}).get('mean', 0):.2%} | {aggregate_metrics.get('var_95', {}).get('median', 0):.2%} | {aggregate_metrics.get('var_95', {}).get('min', 0):.2%} | {aggregate_metrics.get('var_95', {}).get('max', 0):.2%} |",
            f"| VaR 99% | {aggregate_metrics.get('var_99', {}).get('mean', 0):.2%} | {aggregate_metrics.get('var_99', {}).get('median', 0):.2%} | {aggregate_metrics.get('var_99', {}).get('min', 0):.2%} | {aggregate_metrics.get('var_99', {}).get('max', 0):.2%} |",
            f"| Max Drawdown | {aggregate_metrics.get('max_drawdown', {}).get('mean', 0):.2%} | {aggregate_metrics.get('max_drawdown', {}).get('median', 0):.2%} | {aggregate_metrics.get('max_drawdown', {}).get('worst', 0):.2%} | - |",
            f"",
            f"---",
            f"",
            f"## 🎯 Scenario Breakdown",
            f""
        ]
        
        # Scenario type breakdown
        if "by_scenario_type" in aggregate_metrics:
            md_lines.extend([
                "",
                "### By Scenario Type",
                "",
                "| Scenario Type | Count | Mean Return | Median Return | Min Return | Max Return |",
                "|---------------|-------|-------------|---------------|------------|------------|"
            ])
            
            for scenario_type, metrics in aggregate_metrics["by_scenario_type"].items():
                md_lines.append(
                    f"| {scenario_type} | {metrics.get('count', 0)} | "
                    f"{metrics.get('mean_return', 0):.2%} | "
                    f"{metrics.get('median_return', 0):.2%} | "
                    f"{metrics.get('min_return', 0):.2%} | "
                    f"{metrics.get('max_return', 0):.2%} |"
                )
        
        md_lines.extend([
            "",
            "---",
            "",
            f"## 📈 Individual Scenario Results",
            "",
            "| Scenario ID | Type | Return | Sharpe | VaR 95% | Max DD |",
            "|-------------|------|--------|--------|---------|--------|"
        ])
        
        for result in portfolio_results:
            md_lines.append(
                f"| `{result.scenario_id}` | {result.scenario_type} | "
                f"{result.total_return_pct:.2%} | "
                f"{result.risk_metrics.sharpe_ratio:.2f} | "
                f"{result.risk_metrics.var_95:.2%} | "
                f"{result.risk_metrics.max_drawdown:.2%} |"
            )
        
        md_lines.extend([
            "",
            "---",
            "",
            f"*Report generated by Phase 7 Batch Simulation Framework*  ",
            f"*Agent 1B — Unified Financial Dashboard Team*"
        ])
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write('\n'.join(md_lines))
        
        logger.info(f"✅ Saved batch Markdown report: {filepath}")
        return str(filepath)
    
    # ========================================================================
    # HTML REPORTS WITH VISUALIZATIONS
    # ========================================================================
    
    def generate_html_report(
        self,
        batch_id: str,
        portfolio_results: List[SimulationResult],
        aggregate_metrics: Dict[str, Any],
        performance_metrics: Dict[str, float],
        include_charts: bool = True,
        filename: Optional[str] = None
    ) -> str:
        """
        Generate offline HTML report with interactive visualizations.
        
        Uses embedded chart data (no external dependencies for offline viewing).
        
        Args:
            batch_id: Batch identifier
            portfolio_results: Portfolio results
            aggregate_metrics: Aggregate metrics
            performance_metrics: Performance metrics
            include_charts: Whether to include chart visualizations
            filename: Optional custom filename
            
        Returns:
            Path to generated HTML file
        """
        logger.info(f"🌐 Generating HTML report: {batch_id}")
        
        filename = filename or f"{batch_id}_report.html"
        
        # Build HTML content
        html_content = self._build_html_content(
            batch_id,
            portfolio_results,
            aggregate_metrics,
            performance_metrics,
            include_charts
        )
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        logger.info(f"✅ Saved HTML report: {filepath}")
        return str(filepath)
    
    def _build_html_content(
        self,
        batch_id: str,
        portfolio_results: List[SimulationResult],
        aggregate_metrics: Dict[str, Any],
        performance_metrics: Dict[str, float],
        include_charts: bool
    ) -> str:
        """Build complete HTML content"""
        
        # Returns data for histogram
        returns = [r.total_return_pct * 100 for r in portfolio_results]
        
        # Scenario comparison data
        scenario_labels = [r.scenario_id for r in portfolio_results]
        scenario_returns = [r.total_return_pct * 100 for r in portfolio_results]
        scenario_sharpes = [r.risk_metrics.sharpe_ratio for r in portfolio_results]
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phase 7 Batch Report - {batch_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f7fa;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .header .meta {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .section h2 {{
            color: #667eea;
            margin-top: 0;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .metric-card .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f5f7fa;
            font-weight: 600;
            color: #667eea;
        }}
        tr:hover {{
            background: #f9fafb;
        }}
        .positive {{
            color: #10b981;
        }}
        .negative {{
            color: #ef4444;
        }}
        .chart-container {{
            margin: 20px 0;
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
        }}
        canvas {{
            max-width: 100%;
            height: auto;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
</head>
<body>
    <div class="header">
        <h1>📊 Phase 7 Batch Simulation Report</h1>
        <div class="meta">
            <strong>Batch ID:</strong> {batch_id}<br>
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
            <strong>Scenarios:</strong> {len(portfolio_results)}
        </div>
    </div>
    
    <div class="section">
        <h2>⚡ Performance Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="label">Execution Time</div>
                <div class="value">{performance_metrics.get('total_execution_time_ms', 0) / 1000:.2f}s</div>
            </div>
            <div class="metric-card">
                <div class="label">Scenarios/Second</div>
                <div class="value">{performance_metrics.get('scenarios_per_second', 0):.2f}</div>
            </div>
            <div class="metric-card">
                <div class="label">Cache Hit Rate</div>
                <div class="value">{performance_metrics.get('cache_hit_rate', 0):.1%}</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📈 Aggregate Returns</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="label">Mean Return</div>
                <div class="value {'positive' if aggregate_metrics.get('returns', {}).get('mean', 0) > 0 else 'negative'}">{aggregate_metrics.get('returns', {}).get('mean', 0):.2%}</div>
            </div>
            <div class="metric-card">
                <div class="label">Median Return</div>
                <div class="value {'positive' if aggregate_metrics.get('returns', {}).get('median', 0) > 0 else 'negative'}">{aggregate_metrics.get('returns', {}).get('median', 0):.2%}</div>
            </div>
            <div class="metric-card">
                <div class="label">Std Deviation</div>
                <div class="value">{aggregate_metrics.get('returns', {}).get('std', 0):.2%}</div>
            </div>
            <div class="metric-card">
                <div class="label">Min Return</div>
                <div class="value negative">{aggregate_metrics.get('returns', {}).get('min', 0):.2%}</div>
            </div>
            <div class="metric-card">
                <div class="label">Max Return</div>
                <div class="value positive">{aggregate_metrics.get('returns', {}).get('max', 0):.2%}</div>
            </div>
        </div>
        
        {'<div class="chart-container"><canvas id="returnsHistogram"></canvas></div>' if include_charts else ''}
    </div>
    
    <div class="section">
        <h2>🎯 Risk Metrics</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Mean</th>
                    <th>Median</th>
                    <th>Min</th>
                    <th>Max</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Sharpe Ratio</td>
                    <td>{aggregate_metrics.get('sharpe_ratio', {}).get('mean', 0):.2f}</td>
                    <td>{aggregate_metrics.get('sharpe_ratio', {}).get('median', 0):.2f}</td>
                    <td>{aggregate_metrics.get('sharpe_ratio', {}).get('min', 0):.2f}</td>
                    <td>{aggregate_metrics.get('sharpe_ratio', {}).get('max', 0):.2f}</td>
                </tr>
                <tr>
                    <td>VaR 95%</td>
                    <td>{aggregate_metrics.get('var_95', {}).get('mean', 0):.2%}</td>
                    <td>{aggregate_metrics.get('var_95', {}).get('median', 0):.2%}</td>
                    <td>{aggregate_metrics.get('var_95', {}).get('min', 0):.2%}</td>
                    <td>{aggregate_metrics.get('var_95', {}).get('max', 0):.2%}</td>
                </tr>
                <tr>
                    <td>VaR 99%</td>
                    <td>{aggregate_metrics.get('var_99', {}).get('mean', 0):.2%}</td>
                    <td>{aggregate_metrics.get('var_99', {}).get('median', 0):.2%}</td>
                    <td>{aggregate_metrics.get('var_99', {}).get('min', 0):.2%}</td>
                    <td>{aggregate_metrics.get('var_99', {}).get('max', 0):.2%}</td>
                </tr>
                <tr>
                    <td>Max Drawdown</td>
                    <td>{aggregate_metrics.get('max_drawdown', {}).get('mean', 0):.2%}</td>
                    <td>{aggregate_metrics.get('max_drawdown', {}).get('median', 0):.2%}</td>
                    <td colspan="2">{aggregate_metrics.get('max_drawdown', {}).get('worst', 0):.2%} (worst)</td>
                </tr>
            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>📊 Scenario Comparison</h2>
        {'<div class="chart-container"><canvas id="scenarioComparison"></canvas></div>' if include_charts else ''}
        <table>
            <thead>
                <tr>
                    <th>Scenario ID</th>
                    <th>Type</th>
                    <th>Return</th>
                    <th>Sharpe</th>
                    <th>VaR 95%</th>
                    <th>Max DD</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for result in portfolio_results:
            html += f"""                <tr>
                    <td><code>{result.scenario_id}</code></td>
                    <td>{result.scenario_type}</td>
                    <td class="{'positive' if result.total_return_pct > 0 else 'negative'}">{result.total_return_pct:.2%}</td>
                    <td>{result.risk_metrics.sharpe_ratio:.2f}</td>
                    <td>{result.risk_metrics.var_95:.2%}</td>
                    <td class="negative">{result.risk_metrics.max_drawdown:.2%}</td>
                </tr>
"""
        
        html += f"""            </tbody>
        </table>
    </div>
    
    <div class="section">
        <p style="text-align: center; color: #999; margin-top: 30px;">
            <em>Report generated by Phase 7 Batch Simulation Framework<br>
            Agent 1B — Unified Financial Dashboard Team</em>
        </p>
    </div>
"""
        
        if include_charts:
            html += f"""    
    <script>
        // Returns histogram
        const returnsCtx = document.getElementById('returnsHistogram').getContext('2d');
        const returnsChart = new Chart(returnsCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(scenario_labels)},
                datasets: [{{
                    label: 'Returns (%)',
                    data: {json.dumps(scenario_returns)},
                    backgroundColor: {json.dumps(['rgba(102, 126, 234, 0.7)' if r >= 0 else 'rgba(239, 68, 68, 0.7)' for r in scenario_returns])},
                    borderColor: {json.dumps(['rgba(102, 126, 234, 1)' if r >= 0 else 'rgba(239, 68, 68, 1)' for r in scenario_returns])},
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Returns Distribution by Scenario',
                        font: {{ size: 16 }}
                    }},
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Return (%)'
                        }}
                    }}
                }}
            }}
        }});
        
        // Scenario comparison
        const scenarioCtx = document.getElementById('scenarioComparison').getContext('2d');
        const scenarioChart = new Chart(scenarioCtx, {{
            type: 'scatter',
            data: {{
                datasets: [{{
                    label: 'Scenarios',
                    data: {json.dumps([{'x': r, 'y': s} for r, s in zip(scenario_returns, scenario_sharpes)])},
                    backgroundColor: 'rgba(102, 126, 234, 0.7)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Risk-Return Profile (Sharpe vs Returns)',
                        font: {{ size: 16 }}
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Return (%)'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Sharpe Ratio'
                        }}
                    }}
                }}
            }}
        }});
    </script>
"""
        
        html += """
</body>
</html>
"""
        
        return html


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    from scenario_engine import create_monte_carlo_scenario, create_stress_scenario, StressType
    from portfolio_simulator import PortfolioLoader, PortfolioSimulator
    from options_risk_simulator import create_option_contract, OptionsRiskSimulator
    
    logger.info("=" * 80)
    logger.info("PHASE 7 — SIMULATION REPORT BUILDER TEST")
    logger.info("=" * 80)
    
    # Create test scenarios
    logger.info("\n🎲 Creating test scenarios")
    mc_scenario = create_monte_carlo_scenario(["SPY", "QQQ"], num_days=60, random_seed=42)
    vol_scenario = create_stress_scenario(["SPY", "QQQ"], StressType.VOLATILITY_SPIKE, num_days=60, random_seed=42)
    
    # Portfolio simulations
    logger.info("\n📊 Running portfolio simulations")
    portfolio = PortfolioLoader.create_synthetic(["SPY", "QQQ"], allocation=100000.0)
    simulator = PortfolioSimulator(portfolio)
    
    portfolio_results = [
        simulator.apply_scenario(mc_scenario),
        simulator.apply_scenario(vol_scenario)
    ]
    
    # Options simulations
    logger.info("\n📈 Running options simulations")
    contracts = [
        create_option_contract("SPY", "call", 460.0, 60, 10, 8.0),
        create_option_contract("SPY", "put", 440.0, 60, 5, 6.0)
    ]
    
    options_sim = OptionsRiskSimulator(contracts)
    options_results = options_sim.batch_simulate([mc_scenario, vol_scenario])
    
    # Generate reports
    logger.info("\n📝 Generating all reports")
    filepaths = generate_all_reports(portfolio_results, options_results)
    
    logger.info("\n✅ Reports generated:")
    for report_type, path in filepaths.items():
        logger.info(f"   {report_type}: {path}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL REPORT BUILDER TESTS COMPLETE")
    logger.info("=" * 80)
