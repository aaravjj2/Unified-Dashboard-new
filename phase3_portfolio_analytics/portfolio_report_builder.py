"""Portfolio Report Builder

Generates comprehensive portfolio analytics reports in multiple formats:
- JSON export for programmatic consumption
- Markdown summary for human readability
- Structured data for visualization integration

Merges outputs from risk metrics, sector analysis, and benchmark comparison.
"""
from __future__ import annotations
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class PortfolioReportBuilder:
    """Builds comprehensive portfolio analytics reports."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize report builder.
        
        Args:
            output_dir: Directory for output files (default: data/)
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / 'data'
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def build_report(self, 
                    portfolio_id: str,
                    risk_metrics: Dict,
                    sector_analysis: Dict,
                    benchmark_comparison: Dict,
                    metadata: Optional[Dict] = None) -> Dict:
        """Build comprehensive analytics report.
        
        Args:
            portfolio_id: Identifier for the portfolio
            risk_metrics: Risk metrics from risk_metrics_computer
            sector_analysis: Sector analysis from sector_allocation_analyzer
            benchmark_comparison: Benchmark comparison results
            metadata: Optional metadata (dataset hash, run timestamp, etc.)
        
        Returns:
            Complete report dictionary
        """
        timestamp = datetime.now().isoformat()
        
        if metadata is None:
            metadata = {}
        
        report = {
            "report_metadata": {
                "portfolio_id": portfolio_id,
                "generated_at": timestamp,
                "report_version": "3.0.0",
                **metadata
            },
            "summary": self._build_summary(risk_metrics, sector_analysis, benchmark_comparison),
            "risk_metrics": risk_metrics,
            "sector_analysis": sector_analysis,
            "benchmark_comparison": benchmark_comparison
        }
        
        return report
    
    def _build_summary(self, risk_metrics: Dict, sector_analysis: Dict, 
                      benchmark_comparison: Dict) -> Dict:
        """Build executive summary section."""
        summary = {
            "total_value": sector_analysis.get('total_value', 0.0),
            "num_holdings": sum(s.get('num_holdings', 0) for s in sector_analysis.get('sectors', [])),
            "num_sectors": sector_analysis.get('num_sectors', 0),
            "annualized_return": risk_metrics.get('annualized_return', 0.0),
            "volatility": risk_metrics.get('volatility', 0.0),
            "sharpe_ratio": risk_metrics.get('sharpe_ratio', 0.0),
            "max_drawdown": risk_metrics.get('max_drawdown', 0.0)
        }
        
        # Add benchmark comparison if available
        if 'relative' in benchmark_comparison:
            summary['alpha'] = benchmark_comparison['relative'].get('alpha', 0.0)
            summary['correlation'] = benchmark_comparison['relative'].get('correlation', 0.0)
        
        return summary
    
    def export_json(self, report: Dict, filename: str = 'portfolio_analytics_summary.json') -> Path:
        """Export report as JSON file.
        
        Args:
            report: Report dictionary
            filename: Output filename
        
        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf8') as f:
            json.dump(report, f, indent=2)
        
        return output_path
    
    def export_markdown(self, report: Dict, filename: str = 'PORTFOLIO_ANALYTICS_REPORT.md') -> Path:
        """Export report as Markdown file.
        
        Args:
            report: Report dictionary
            filename: Output filename
        
        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename
        
        md = self._generate_markdown(report)
        
        with open(output_path, 'w', encoding='utf8') as f:
            f.write(md)
        
        return output_path
    
    def _generate_markdown(self, report: Dict) -> str:
        """Generate markdown content from report."""
        metadata = report.get('report_metadata', {})
        summary = report.get('summary', {})
        risk = report.get('risk_metrics', {})
        sectors = report.get('sector_analysis', {})
        benchmark = report.get('benchmark_comparison', {})
        
        lines = [
            "# Portfolio Analytics Report",
            "",
            f"**Portfolio ID:** {metadata.get('portfolio_id', 'N/A')}  ",
            f"**Generated:** {metadata.get('generated_at', 'N/A')}  ",
            f"**Report Version:** {metadata.get('report_version', 'N/A')}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Value:** ${summary.get('total_value', 0):,.2f}",
            f"- **Number of Holdings:** {summary.get('num_holdings', 0)}",
            f"- **Number of Sectors:** {summary.get('num_sectors', 0)}",
            f"- **Annualized Return:** {summary.get('annualized_return', 0)*100:.2f}%",
            f"- **Volatility:** {summary.get('volatility', 0)*100:.2f}%",
            f"- **Sharpe Ratio:** {summary.get('sharpe_ratio', 0):.2f}",
            f"- **Max Drawdown:** {summary.get('max_drawdown', 0)*100:.2f}%",
            ""
        ]
        
        if 'alpha' in summary:
            lines.extend([
                f"- **Alpha vs Benchmark:** {summary.get('alpha', 0)*100:.2f}%",
                f"- **Correlation:** {summary.get('correlation', 0):.3f}",
                ""
            ])
        
        lines.extend([
            "## Risk Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|"
        ])
        
        for key, value in risk.items():
            if value is not None:
                if isinstance(value, float):
                    if 'ratio' in key.lower() or 'beta' in key.lower():
                        lines.append(f"| {key.replace('_', ' ').title()} | {value:.3f} |")
                    else:
                        lines.append(f"| {key.replace('_', ' ').title()} | {value*100:.2f}% |")
        
        lines.extend(["", "## Sector Allocation", ""])
        
        sector_list = sectors.get('sectors', [])
        if sector_list:
            lines.extend([
                "| Sector | Allocation | Value | Holdings |",
                "|--------|------------|-------|----------|"
            ])
            
            for s in sector_list:
                lines.append(
                    f"| {s.get('sector', 'Unknown')} | "
                    f"{s.get('allocation_pct', 0):.1f}% | "
                    f"${s.get('value', 0):,.2f} | "
                    f"{s.get('num_holdings', 0)} |"
                )
        
        lines.extend(["", f"**Concentration (HHI):** {sectors.get('concentration_hhi', 0):.3f}", ""])
        
        if 'error' not in benchmark:
            lines.extend([
                "## Benchmark Comparison",
                "",
                f"**Period:** {benchmark.get('period_start', 'N/A')} to {benchmark.get('period_end', 'N/A')}",
                ""
            ])
            
            port = benchmark.get('portfolio', {})
            bench = benchmark.get('benchmark', {})
            rel = benchmark.get('relative', {})
            
            lines.extend([
                "| Metric | Portfolio | Benchmark |",
                "|--------|-----------|-----------|",
                f"| Total Return | {port.get('total_return', 0)*100:.2f}% | {bench.get('total_return', 0)*100:.2f}% |",
                f"| Annualized Return | {port.get('annualized_return', 0)*100:.2f}% | {bench.get('annualized_return', 0)*100:.2f}% |",
                f"| Max Drawdown | {port.get('max_drawdown', 0)*100:.2f}% | {bench.get('max_drawdown', 0)*100:.2f}% |",
                "",
                "### Relative Performance",
                "",
                f"- **Alpha:** {rel.get('alpha', 0)*100:.2f}%",
                f"- **Correlation:** {rel.get('correlation', 0):.3f}",
                f"- **Up Capture Ratio:** {rel.get('up_capture', 0):.2f}",
                f"- **Down Capture Ratio:** {rel.get('down_capture', 0):.2f}",
                f"- **Outperformance:** {rel.get('outperformance_pct', 0):.2f}%",
                ""
            ])
        
        lines.extend([
            "---",
            "",
            f"*Report generated by Phase 3 Portfolio Analytics Engine v{metadata.get('report_version', '3.0.0')}*",
            ""
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def compute_dataset_hash(data: str) -> str:
        """Compute SHA256 hash of dataset for versioning.
        
        Args:
            data: String representation of dataset
        
        Returns:
            Hex digest of hash
        """
        return hashlib.sha256(data.encode('utf8')).hexdigest()[:16]


if __name__ == '__main__':
    # Test with sample data
    builder = PortfolioReportBuilder()
    
    sample_risk = {
        "annualized_return": 0.12,
        "volatility": 0.18,
        "sharpe_ratio": 0.67,
        "max_drawdown": 0.15
    }
    
    sample_sector = {
        "total_value": 500000.0,
        "num_sectors": 5,
        "concentration_hhi": 0.24,
        "sectors": [
            {"sector": "Technology", "allocation_pct": 40.0, "value": 200000.0, "num_holdings": 5},
            {"sector": "Healthcare", "allocation_pct": 25.0, "value": 125000.0, "num_holdings": 3}
        ]
    }
    
    sample_benchmark = {
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "portfolio": {"total_return": 0.15, "annualized_return": 0.15, "max_drawdown": 0.12},
        "benchmark": {"total_return": 0.10, "annualized_return": 0.10, "max_drawdown": 0.10},
        "relative": {"alpha": 0.05, "correlation": 0.85, "up_capture": 1.1, "down_capture": 0.9, "outperformance_pct": 5.0}
    }
    
    report = builder.build_report("TEST001", sample_risk, sample_sector, sample_benchmark)
    print("Sample report structure:")
    print(json.dumps(report, indent=2)[:500] + "...")
