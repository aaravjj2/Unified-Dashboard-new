"""
Azure ML Lab - Mode Router (Phase 2 Local Integration)

Routes explainability requests to MockSHAPEngine or Azure ML based on environment.
Provides graceful fallback and environment detection.

Environment Variable:
    AZURE_ML_USE_MOCK = 'true' (default) → MockSHAPEngine
    AZURE_ML_USE_MOCK = 'false' → Azure ML SHAP (Phase 3, not yet implemented)

Phase 2 Scope: MOCK MODE ONLY (enforced)
Phase 3: Will integrate with real Azure ML SHAP service

Author: Unified Financial Dashboard Team
Version: 1.0 (Phase 2)
"""

import os
import logging
from typing import Dict, Optional

from financial_dashboard.tabs.azure_ml_lab.explainability_engine import (
    generate_explanation_summary,
    get_cache_stats,
    reset_cache_stats
)

logger = logging.getLogger(__name__)


# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================

def get_explainability_mode() -> str:
    """
    Detect current explainability mode from environment.
    
    Returns:
        'mock' or 'live' (though 'live' is not yet supported in Phase 2)
    """
    use_mock = os.getenv('AZURE_ML_USE_MOCK', 'true').strip().lower()
    
    if use_mock in ['true', '1', 'yes', 'on']:
        return 'mock'
    elif use_mock in ['false', '0', 'no', 'off']:
        return 'live'
    else:
        logger.warning(
            f"⚠️ Invalid AZURE_ML_USE_MOCK value: '{use_mock}'. Defaulting to 'mock'."
        )
        return 'mock'


def is_mock_mode() -> bool:
    """Check if currently in mock mode."""
    return get_explainability_mode() == 'mock'


def is_live_mode() -> bool:
    """Check if currently in live mode (Azure ML SHAP)."""
    return get_explainability_mode() == 'live'


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def route_explanation_request(
    ticker: str,
    prediction_value: float,
    prediction_target: str = 'return',
    top_n_features: int = 10,
    use_cache: bool = True
) -> Dict:
    """
    Route explanation request to appropriate backend (mock or live).
    
    This is the UNIVERSAL interface for explainability across all modes.
    UI callbacks should call this instead of directly calling engine functions.
    
    Args:
        ticker: Stock symbol (e.g., 'AAPL')
        prediction_value: Predicted return/volatility/sharpe
        prediction_target: What's being predicted ('return', 'volatility', 'sharpe')
        top_n_features: Number of top features to explain
        use_cache: Whether to use LRU cache (only applies to mock mode)
        
    Returns:
        Explanation dictionary with:
        - ticker, prediction_value, prediction_target
        - feature_importance: List of {feature, importance, direction}
        - textual_rationale: Markdown explanation
        - plotly_chart: Plotly Figure (optional)
        - metadata: mode, cache_hit, generation_time_ms
        - error: Error message if mode unavailable
        
    Example:
        >>> # In Phase 2, this always routes to mock
        >>> result = route_explanation_request('AAPL', 0.08, 'return', 10)
        >>> print(result['metadata']['mode'])  # 'mock'
        
        >>> # In Phase 3, with AZURE_ML_USE_MOCK=false:
        >>> result = route_explanation_request('AAPL', 0.08, 'return', 10)
        >>> print(result['metadata']['mode'])  # 'live'
    """
    
    mode = get_explainability_mode()
    logger.info(f"🔀 Routing explanation request for {ticker} to '{mode}' mode")
    
    if mode == 'mock':
        return _route_to_mock(ticker, prediction_value, prediction_target, top_n_features, use_cache)
    elif mode == 'live':
        return _route_to_live(ticker, prediction_value, prediction_target, top_n_features)
    else:
        # Should never reach here due to get_explainability_mode() defaults
        return {
            'error': 'Unknown mode',
            'message': f"Invalid explainability mode: '{mode}'",
            'ticker': ticker,
            'metadata': {'mode': mode}
        }


def _route_to_mock(
    ticker: str,
    prediction_value: float,
    prediction_target: str,
    top_n_features: int,
    use_cache: bool
) -> Dict:
    """
    Route to MockSHAPEngine (Phase 1/2 implementation).
    
    This uses the local explainability_engine.py with deterministic outputs.
    """
    try:
        result = generate_explanation_summary(
            ticker=ticker,
            prediction_value=prediction_value,
            prediction_target=prediction_target,
            top_n_features=top_n_features,
            use_cache=use_cache
        )
        
        # Augment metadata to indicate mode
        if 'metadata' not in result:
            result['metadata'] = {}
        result['metadata']['mode'] = 'mock'
        result['metadata']['backend'] = 'MockSHAPEngine (local)'
        
        return result
        
    except Exception as e:
        logger.exception(f"Mock mode error for {ticker}: {e}")
        return {
            'error': 'Mock mode failure',
            'message': str(e),
            'ticker': ticker,
            'metadata': {'mode': 'mock', 'backend': 'MockSHAPEngine (local)'}
        }


def _route_to_live(
    ticker: str,
    prediction_value: float,
    prediction_target: str,
    top_n_features: int
) -> Dict:
    """
    Route to Azure ML SHAP service (Phase 3 - NOT YET IMPLEMENTED).
    
    This is a placeholder that will be implemented in Phase 3 when we integrate
    with real Azure ML SHAP endpoints. For now, it returns a friendly error.
    """
    logger.warning(
        f"⚠️ Live mode requested for {ticker} but not yet available (Phase 3 feature)"
    )
    
    return {
        'error': 'Live mode unavailable',
        'message': (
            'Azure ML SHAP integration is planned for Phase 3. '
            'Please set AZURE_ML_USE_MOCK=true to use local mock mode.'
        ),
        'ticker': ticker,
        'prediction_value': prediction_value,
        'prediction_target': prediction_target,
        'metadata': {
            'mode': 'live',
            'backend': 'Azure ML SHAP (not implemented)',
            'phase': 'Phase 3 (future)'
        }
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_mode_info() -> Dict:
    """
    Get current mode configuration and capabilities.
    
    Returns:
        Dictionary with:
        - current_mode: 'mock' or 'live'
        - mock_available: bool
        - live_available: bool (False in Phase 2)
        - env_var: Value of AZURE_ML_USE_MOCK
        - cache_stats: Cache statistics (if mock mode)
    """
    mode = get_explainability_mode()
    env_var = os.getenv('AZURE_ML_USE_MOCK', 'true')
    
    info = {
        'current_mode': mode,
        'mock_available': True,
        'live_available': False,  # Phase 3 feature
        'env_var': env_var,
        'phase': 'Phase 2 (local integration)',
        'supported_modes': ['mock']
    }
    
    # Add cache stats if in mock mode
    if mode == 'mock':
        try:
            info['cache_stats'] = get_cache_stats()
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            info['cache_stats'] = {'error': str(e)}
    
    return info


def set_mock_mode(enable: bool = True) -> None:
    """
    Programmatically set mock mode (useful for testing).
    
    Args:
        enable: If True, set AZURE_ML_USE_MOCK=true. If False, set to false.
        
    Note:
        This only affects the current process. For persistent configuration,
        set the environment variable in your .env file or system settings.
    """
    os.environ['AZURE_ML_USE_MOCK'] = 'true' if enable else 'false'
    mode = get_explainability_mode()
    logger.info(f"🔀 Mode set to: '{mode}' (AZURE_ML_USE_MOCK={'true' if enable else 'false'})")


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Log current mode on import
_current_mode = get_explainability_mode()
logger.info(f"✓ Mode Router initialized (current mode: '{_current_mode}')")

if _current_mode == 'live':
    logger.warning(
        "⚠️ Live mode selected but not yet available (Phase 3). "
        "Requests will fail unless switched to mock mode."
    )
