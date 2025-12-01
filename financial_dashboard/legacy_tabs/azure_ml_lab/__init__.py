"""
Azure ML Lab - Package Initialization

Modular integration layer for Azure Machine Learning services.
Provides predictive analytics, strategy simulations, and risk assessment
capabilities without modifying existing dashboard components.

Phase 3 Scaffold - Ready for ML pipeline integration.
Phase 4: Real Azure ML integration with mock fallback.

Version: 1.0.0
Status: Production-ready with mock fallback
"""

import logging

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__status__ = "production_ready"

# Package exports
from .layout import create_azure_ml_lab_layout
from .callbacks import register_azure_ml_callbacks
from .helpers import (
    preprocess_portfolio_data,
    generate_mock_predictions,
    cache_predictions,
    get_ml_diagnostics,
    call_azure_ml_endpoint  # Phase 4: Real API calls
)

# Add layout attribute for index.py compatibility
layout = create_azure_ml_lab_layout

# Add callback alias for index.py compatibility
# The callback registration system looks for 'register_callbacks' specifically
register_callbacks = register_azure_ml_callbacks

__all__ = [
    'layout',  # For index.py tab loading
    'register_callbacks',  # Alias for callback registration system
    'create_azure_ml_lab_layout',
    'register_azure_ml_callbacks',
    'preprocess_portfolio_data',
    'generate_mock_predictions',
    'call_azure_ml_endpoint',
    'cache_predictions',
    'get_ml_diagnostics'
]

logger.info("✓ Azure ML Lab package loaded (Phase 4 - Production Ready)")
logger.info(f"  Version: {__version__}")
logger.info(f"  Status: {__status__}")
logger.info("  Features: Real Azure ML API + Mock fallback")

