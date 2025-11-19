"""Phase 3: Offline Portfolio Analytics Engine

Provides comprehensive portfolio analysis including:
- Risk metrics (volatility, Sharpe, beta, VaR)
- Sector allocation analysis
- Benchmark comparisons
- Attribution analysis
- Report generation

All modules operate fully offline using local CSV/JSON data sources.
"""

__version__ = "3.0.0"

from .offline_portfolio_engine import PortfolioAnalyticsEngine
from .risk_metrics_computer import compute_risk_metrics
from .sector_allocation_analyzer import SectorAllocationAnalyzer
from .benchmark_comparator import BenchmarkComparator
from .portfolio_report_builder import PortfolioReportBuilder

__all__ = [
    "PortfolioAnalyticsEngine",
    "compute_risk_metrics",
    "SectorAllocationAnalyzer",
    "BenchmarkComparator",
    "PortfolioReportBuilder",
]
