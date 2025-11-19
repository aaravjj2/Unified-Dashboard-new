"""
Phase 8 — Analytics Package
============================

Advanced analytics modules for the Unified Financial Dashboard.

Modules:
- trend_analyzer: Trend detection and correlation analysis
- volatility_heatmap: Volatility heatmaps and IV surfaces
- risk_dashboard: Unified risk dashboard with PSI
- cache_telemetry: Cache performance telemetry

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 8)
"""

__version__ = "1.0.0"
__author__ = "Agent 1B — Unified Financial Dashboard Team"

# Import key classes for convenience
from phase8_analytics.trend_analyzer import (
    TrendAnalyzer,
    TrendSignal,
    TrendAnalysisResult,
    load_forecast_data_from_json,
    save_trend_analysis
)

from phase8_analytics.volatility_heatmap import (
    VolatilityHeatmap,
    VolatilityMetrics,
    HeatmapData,
    save_volatility_metrics
)

from phase8_analytics.risk_dashboard import (
    RiskDashboard,
    PortfolioStabilityIndex,
    RiskDashboardSnapshot,
    save_dashboard_snapshot
)

from phase8_analytics.cache_telemetry import (
    CacheTelemetryCollector,
    CacheTelemetryReport,
    CacheHitMetrics,
    LatencyMetrics,
    DeterminismRecord,
    save_telemetry_report,
    save_determinism_log_csv
)

__all__ = [
    # Trend Analyzer
    'TrendAnalyzer',
    'TrendSignal',
    'TrendAnalysisResult',
    'load_forecast_data_from_json',
    'save_trend_analysis',
    
    # Volatility Heatmap
    'VolatilityHeatmap',
    'VolatilityMetrics',
    'HeatmapData',
    'save_volatility_metrics',
    
    # Risk Dashboard
    'RiskDashboard',
    'PortfolioStabilityIndex',
    'RiskDashboardSnapshot',
    'save_dashboard_snapshot',
    
    # Cache Telemetry
    'CacheTelemetryCollector',
    'CacheTelemetryReport',
    'CacheHitMetrics',
    'LatencyMetrics',
    'DeterminismRecord',
    'save_telemetry_report',
    'save_determinism_log_csv',
]
