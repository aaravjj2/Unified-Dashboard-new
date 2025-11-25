"""
Local Hybrid Bridge Module

Provides routing, telemetry, and compute dispatching for hybrid local/cloud execution.
"""

from phase4_hybrid_stubs.local_hybrid_bridge.hybrid_interface import (
    run_analytics,
    run_forecast,
    run_backtest,
    run_risk_analysis,
    run_explainability
)
from phase4_hybrid_stubs.local_hybrid_bridge.compute_router import (
    ComputeRouter,
    get_router
)
from phase4_hybrid_stubs.local_hybrid_bridge.telemetry_proxy import (
    TelemetryProxy,
    get_telemetry
)
from phase4_hybrid_stubs.local_hybrid_bridge.hybrid_diagnostics import run_diagnostics

__all__ = [
    'run_analytics',
    'run_forecast',
    'run_backtest',
    'run_risk_analysis',
    'run_explainability',
    'ComputeRouter',
    'get_router',
    'TelemetryProxy',
    'get_telemetry',
    'run_diagnostics'
]
