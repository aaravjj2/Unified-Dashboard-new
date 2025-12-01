"""
Phase 4 - Hybrid Readiness (Azure Stubs & Contracts)

This package provides Azure-compatible interfaces and local stubs for ML operations,
enabling the dashboard to run locally while being architecturally ready for Azure ML.

Key Components:
- azure_contracts: Contract definitions and schemas for Azure ML integration
- local_hybrid_bridge: Routing, telemetry, and compute dispatching

Phase 4 Deliverables:
- Plug-compatible local mocks for all Azure services
- Contract-driven I/O with validation
- Telemetry proxy mirroring Azure Application Insights
- Diagnostic tooling for integration readiness
"""

__version__ = "0.1.0"
__author__ = "Agent 1B - Lead Engineer"
__phase__ = "Phase 4 - Hybrid Readiness"

from phase4_hybrid_stubs.local_hybrid_bridge.hybrid_interface import run_analytics
from phase4_hybrid_stubs.azure_contracts.azure_contract_definitions import (
    ContractInputSpec,
    ContractOutputSpec,
    ModelType,
    ForecastHorizon
)

__all__ = [
    'run_analytics',
    'ContractInputSpec',
    'ContractOutputSpec',
    'ModelType',
    'ForecastHorizon'
]
