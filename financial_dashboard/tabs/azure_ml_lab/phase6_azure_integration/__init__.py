"""
Phase 6 — Azure ML SHAP Integration & Forecast Enhancements
============================================================

Production Azure ML integration module for SHAP explainability and options forecasting.

Replaces ALL mock SHAP/forecast engines with real Azure ML endpoint calls.

Modules:
- explainability_azure: AzureMLSHAPClient for SHAP explanations
- options_forecast_azure: AzureMLOptionsClient for Black-Scholes options forecasting
- phase6_batch_explain: BatchSHAPOrchestrator for portfolio-wide SHAP analysis
- phase6_ui_callbacks: Dash callbacks for Model Insights and Market Forecast tabs

Dependencies:
- Phase 3.5: ExplainabilityContract, ForecastContract, CacheRouter
- Azure ML: Endpoints, authentication, scoring pipeline

Author: Agent 1A — Unified Financial Dashboard Team
Version: 1.0 (Phase 6)
"""

from .explainability_azure import (
    AzureMLSHAPClient,
    create_azure_shap_client,
    AZURE_ML_FEATURES
)

from .options_forecast_azure import (
    AzureMLOptionsClient,
    create_azure_options_client,
    OptionContract,
    OptionChain
)

from .phase6_batch_explain import (
    BatchSHAPOrchestrator,
    create_batch_orchestrator,
    BatchSHAPResult,
    load_portfolio_from_phase3,
    load_portfolio_from_csv
)

from .phase6_ui_callbacks import (
    handle_explain_portfolio,
    handle_fetch_options,
    get_shap_client,
    get_options_client,
    get_batch_orchestrator,
    reset_clients
)

from .phase6_cache_config import (
    Phase6CacheConfig,
    Phase6CacheKeyGenerator,
    Phase6CacheInvalidator,
    CacheTelemetry,
    create_phase6_cache_config,
    create_cache_key_generator,
    create_cache_invalidator
)

__all__ = [
    # SHAP Explainability
    'AzureMLSHAPClient',
    'create_azure_shap_client',
    'AZURE_ML_FEATURES',
    
    # Options Forecasting
    'AzureMLOptionsClient',
    'create_azure_options_client',
    'OptionContract',
    'OptionChain',
    
    # Batch Orchestration
    'BatchSHAPOrchestrator',
    'create_batch_orchestrator',
    'BatchSHAPResult',
    'load_portfolio_from_phase3',
    'load_portfolio_from_csv',
    
    # UI Callbacks
    'handle_explain_portfolio',
    'handle_fetch_options',
    'get_shap_client',
    'get_options_client',
    'get_batch_orchestrator',
    'reset_clients',
    
    # Cache Optimization
    'Phase6CacheConfig',
    'Phase6CacheKeyGenerator',
    'Phase6CacheInvalidator',
    'CacheTelemetry',
    'create_phase6_cache_config',
    'create_cache_key_generator',
    'create_cache_invalidator'
]

__version__ = "1.0.0"
__author__ = "Agent 1A — Unified Financial Dashboard Team"
