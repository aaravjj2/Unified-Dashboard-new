"""
Phase 2 Local Integration Package
==================================

This package contains the UI callback integration layer for the Azure ML Lab
explainability features. It wires the Model Insight Explorer UI to the
local mock explainability engine.

Modules:
- callbacks_insight.py: Dash callbacks for UI interaction
- mode_router.py: Mock/Live mode routing logic
- batch_explain.py: Portfolio-wide batch processing

Phase 2 Scope: LOCAL CALLBACKS ONLY (uses MockSHAPEngine)
Phase 3: Will integrate with real Azure ML SHAP endpoints

Author: Unified Financial Dashboard Team
Version: 1.0 (Phase 2)
"""

__version__ = '1.0.0'
__phase__ = 'Phase 2 - Local Integration'

# Make key functions available at package level
from financial_dashboard.tabs.azure_ml_lab.phase2_local_integration.mode_router import (
    route_explanation_request,
    get_mode_info,
    is_mock_mode,
    is_live_mode,
    set_mock_mode
)

from financial_dashboard.tabs.azure_ml_lab.phase2_local_integration.batch_explain import (
    generate_batch_explanations,
    generate_portfolio_comparison,
    load_batch_report,
    summarize_batch_report
)

from financial_dashboard.tabs.azure_ml_lab.phase2_local_integration.callbacks_insight import (
    register_insight_callbacks
)

__all__ = [
    # Mode routing
    'route_explanation_request',
    'get_mode_info',
    'is_mock_mode',
    'is_live_mode',
    'set_mock_mode',
    
    # Batch processing
    'generate_batch_explanations',
    'generate_portfolio_comparison',
    'load_batch_report',
    'summarize_batch_report',
    
    # Callbacks
    'register_insight_callbacks'
]
