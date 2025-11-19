"""
Hybrid Interface (Phase 4 - Hybrid Readiness)

Unified entry point for all ML analytics operations.
Routes requests to local stubs or real Azure ML based on configuration.

This is the PRIMARY interface used by dashboard callbacks and modules.

Configuration:
    Set OFFLINE_MODE=True (default) for local stubs
    Set OFFLINE_MODE=False for real Azure ML integration

Usage:
    >>> from phase4_hybrid_stubs.local_hybrid_bridge import run_analytics
    >>> 
    >>> result = run_analytics(
    ...     job_type='forecast',
    ...     payload={'ticker': 'AAPL', 'features': {...}, ...}
    ... )
    >>> print(result['predictions'])
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Literal
from functools import wraps

from phase4_hybrid_stubs.azure_contracts.azure_contract_definitions import (
    ContractInputSpec,
    ContractOutputSpec,
    ModelType,
    ForecastHorizon
)
from phase4_hybrid_stubs.azure_contracts.azure_stub_clients import (
    AzureMLStubClient,
    AzureBlobStubClient,
    AzureMonitorStubClient
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Toggle between local stubs and real Azure ML
# Set to False when Azure credentials are available
OFFLINE_MODE = os.getenv('AZURE_ML_OFFLINE_MODE', 'true').lower() == 'true'

# Workspace configuration
WORKSPACE_CONFIG = {
    'subscription_id': os.getenv('AZURE_SUBSCRIPTION_ID', 'stub-subscription'),
    'resource_group': os.getenv('AZURE_RESOURCE_GROUP', 'unified-dashboard-rg'),
    'workspace_name': os.getenv('AZURE_ML_WORKSPACE', 'unified-dashboard-ml'),
    'blob_container': os.getenv('AZURE_BLOB_CONTAINER', 'ml-predictions')
}

logger.info(f"🔧 Hybrid Interface initialized (OFFLINE_MODE={OFFLINE_MODE})")


# ============================================================================
# CLIENT FACTORY
# ============================================================================

def _get_ml_client():
    """
    Get ML client (stub or real Azure ML).
    
    Returns:
        AzureMLStubClient or real Azure ML client
    """
    if OFFLINE_MODE:
        return AzureMLStubClient(workspace_name=WORKSPACE_CONFIG['workspace_name'])
    else:
        # TODO: Replace with real Azure ML client when credentials available
        # from azure.ai.ml import MLClient
        # from azure.identity import DefaultAzureCredential
        # 
        # return MLClient(
        #     DefaultAzureCredential(),
        #     subscription_id=WORKSPACE_CONFIG['subscription_id'],
        #     resource_group_name=WORKSPACE_CONFIG['resource_group'],
        #     workspace_name=WORKSPACE_CONFIG['workspace_name']
        # )
        raise NotImplementedError("Real Azure ML client not yet implemented - set OFFLINE_MODE=true")


def _get_blob_client():
    """
    Get Blob Storage client (stub or real Azure Blob).
    
    Returns:
        AzureBlobStubClient or real Azure Blob client
    """
    if OFFLINE_MODE:
        return AzureBlobStubClient(container_name=WORKSPACE_CONFIG['blob_container'])
    else:
        # TODO: Replace with real Azure Blob client
        # from azure.storage.blob import BlobServiceClient
        # 
        # connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        # return BlobServiceClient.from_connection_string(connection_string)
        raise NotImplementedError("Real Azure Blob client not yet implemented - set OFFLINE_MODE=true")


def _get_monitor_client():
    """
    Get Application Insights client (stub or real Azure Monitor).
    
    Returns:
        AzureMonitorStubClient or real Azure Monitor client
    """
    if OFFLINE_MODE:
        return AzureMonitorStubClient()
    else:
        # TODO: Replace with real Azure Monitor client
        # from applicationinsights import TelemetryClient
        # 
        # instrumentation_key = os.getenv('APPINSIGHTS_INSTRUMENTATION_KEY')
        # return TelemetryClient(instrumentation_key)
        raise NotImplementedError("Real Azure Monitor client not yet implemented - set OFFLINE_MODE=true")


# ============================================================================
# ASYNC WRAPPER UTILITIES
# ============================================================================

def sync_wrapper(async_func):
    """
    Decorator to run async functions in sync context.
    
    Allows dashboard callbacks (which are sync) to call async stub clients.
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop is not None:
            # Already in async context
            return async_func(*args, **kwargs)
        else:
            # Create new event loop
            return asyncio.run(async_func(*args, **kwargs))
    
    return wrapper


# ============================================================================
# MAIN ANALYTICS INTERFACE
# ============================================================================

@sync_wrapper
async def run_analytics(
    job_type: Literal['forecast', 'backtest', 'risk', 'optimization', 'shap', 'batch'],
    payload: Dict[str, Any],
    use_cache: bool = True,
    save_to_blob: bool = True
) -> Dict[str, Any]:
    """
    Run ML analytics job (primary interface for dashboard).
    
    This function routes all ML requests through a unified interface,
    allowing seamless switching between local stubs and real Azure ML.
    
    Args:
        job_type: Type of analytics job
            - 'forecast': Generate future predictions
            - 'backtest': Backtest strategy performance
            - 'risk': Calculate risk metrics (VaR, CVaR)
            - 'optimization': Portfolio optimization
            - 'shap': SHAP explainability analysis
            - 'batch': Batch predictions for multiple tickers
        payload: Job payload containing:
            - ticker: Stock symbol (required)
            - features: Dict of feature name -> value (required)
            - date_range: Tuple of (start, end) dates (required)
            - model_type: ML model to use (optional, default: random_forest)
            - forecast_horizon: Time horizon (optional, default: monthly)
            - confidence_level: Confidence level (optional, default: 0.95)
            - explainability: Explainability level (optional, default: basic)
        use_cache: Whether to use cached results if available
        save_to_blob: Whether to save results to blob storage
    
    Returns:
        Dictionary containing:
            - job_uuid: Job identifier
            - ticker: Stock symbol
            - predictions: List of predicted values
            - confidence: Confidence scores
            - explainability_blob: SHAP values and feature importance (if requested)
            - status: Job status
            - latency_ms: Job execution time
            - metadata: Additional job metadata
    
    Example:
        >>> result = run_analytics(
        ...     job_type='forecast',
        ...     payload={
        ...         'ticker': 'AAPL',
        ...         'features': {'momentum_20d': 0.05, 'pe_ratio': 28.5},
        ...         'date_range': ('2025-01-01', '2025-12-31'),
        ...         'forecast_horizon': 'monthly'
        ...     }
        ... )
        >>> print(result['predictions'])
    
    Raises:
        ValueError: If required payload fields missing
        NotImplementedError: If OFFLINE_MODE=false and real Azure client not configured
    """
    # Validate payload
    required_fields = ['ticker', 'features', 'date_range']
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Missing required field in payload: {field}")
    
    # Create input contract
    input_spec = ContractInputSpec(
        ticker=payload['ticker'],
        features=payload['features'],
        date_range=tuple(payload['date_range']),
        mode=job_type,
        model_type=payload.get('model_type', 'random_forest'),
        forecast_horizon=payload.get('forecast_horizon', 'monthly'),
        confidence_level=payload.get('confidence_level', 0.95),
        explainability=payload.get('explainability', 'basic'),
        metadata=payload.get('metadata', {})
    )
    
    # Validate contract
    is_valid, error = input_spec.validate()
    if not is_valid:
        raise ValueError(f"Invalid input contract: {error}")
    
    logger.info(f"🚀 Running {job_type} analytics for {input_spec.ticker} (mode={'OFFLINE' if OFFLINE_MODE else 'ONLINE'})")
    
    # Get clients
    ml_client = _get_ml_client()
    blob_client = _get_blob_client()
    monitor_client = _get_monitor_client()
    
    # Track request start
    import time
    start_time = time.perf_counter()
    
    try:
        # Submit job to ML client
        output_spec = await ml_client.submit_job(input_spec)
        
        # Save to blob storage if requested
        if save_to_blob:
            blob_name = f"results/{job_type}/{input_spec.ticker}_{input_spec.uuid}.json"
            await blob_client.upload_blob(blob_name, output_spec.to_dict())
            logger.debug(f"💾 Saved results to blob: {blob_name}")
        
        # Track success
        duration_ms = (time.perf_counter() - start_time) * 1000
        await monitor_client.track_request(
            name=f"analytics_{job_type}",
            duration_ms=duration_ms,
            success=True,
            properties={
                'ticker': input_spec.ticker,
                'job_uuid': input_spec.uuid,
                'offline_mode': OFFLINE_MODE
            }
        )
        
        logger.info(f"✅ Analytics job completed: {input_spec.ticker} ({duration_ms:.0f}ms)")
        
        # Return as dictionary
        return output_spec.to_dict()
    
    except Exception as e:
        # Track failure
        duration_ms = (time.perf_counter() - start_time) * 1000
        await monitor_client.track_request(
            name=f"analytics_{job_type}",
            duration_ms=duration_ms,
            success=False,
            response_code=500,
            properties={
                'ticker': input_spec.ticker,
                'error': str(e),
                'offline_mode': OFFLINE_MODE
            }
        )
        
        logger.exception(f"❌ Analytics job failed: {e}")
        raise


# ============================================================================
# CONVENIENCE WRAPPERS
# ============================================================================

def run_forecast(
    ticker: str,
    features: Dict[str, float],
    date_range: tuple,
    horizon: str = 'monthly'
) -> Dict[str, Any]:
    """
    Convenience wrapper for forecast analytics.
    
    Args:
        ticker: Stock symbol
        features: Feature dictionary
        date_range: (start, end) date tuple
        horizon: Forecast horizon
    
    Returns:
        Forecast results dictionary
    """
    return run_analytics(
        job_type='forecast',
        payload={
            'ticker': ticker,
            'features': features,
            'date_range': date_range,
            'forecast_horizon': horizon
        }
    )


def run_backtest(
    ticker: str,
    features: Dict[str, float],
    date_range: tuple
) -> Dict[str, Any]:
    """
    Convenience wrapper for backtest analytics.
    
    Args:
        ticker: Stock symbol
        features: Feature dictionary
        date_range: (start, end) date tuple
    
    Returns:
        Backtest results dictionary
    """
    return run_analytics(
        job_type='backtest',
        payload={
            'ticker': ticker,
            'features': features,
            'date_range': date_range
        }
    )


def run_risk_analysis(
    ticker: str,
    features: Dict[str, float],
    date_range: tuple,
    confidence_level: float = 0.95
) -> Dict[str, Any]:
    """
    Convenience wrapper for risk analytics.
    
    Args:
        ticker: Stock symbol
        features: Feature dictionary
        date_range: (start, end) date tuple
        confidence_level: VaR/CVaR confidence level
    
    Returns:
        Risk metrics dictionary
    """
    return run_analytics(
        job_type='risk',
        payload={
            'ticker': ticker,
            'features': features,
            'date_range': date_range,
            'confidence_level': confidence_level
        }
    )


def run_explainability(
    ticker: str,
    features: Dict[str, float],
    date_range: tuple
) -> Dict[str, Any]:
    """
    Convenience wrapper for SHAP explainability.
    
    Args:
        ticker: Stock symbol
        features: Feature dictionary
        date_range: (start, end) date tuple
    
    Returns:
        SHAP explainability dictionary
    """
    return run_analytics(
        job_type='shap',
        payload={
            'ticker': ticker,
            'features': features,
            'date_range': date_range,
            'explainability': 'full'
        }
    )


# ============================================================================
# CONFIGURATION UTILITIES
# ============================================================================

def set_offline_mode(enabled: bool):
    """
    Set offline mode (local stubs vs. real Azure).
    
    Args:
        enabled: True for local stubs, False for real Azure ML
    """
    global OFFLINE_MODE
    OFFLINE_MODE = enabled
    logger.info(f"🔧 Offline mode set to: {enabled}")


def get_workspace_config() -> Dict[str, str]:
    """
    Get current workspace configuration.
    
    Returns:
        Workspace config dictionary
    """
    return WORKSPACE_CONFIG.copy()


def is_offline() -> bool:
    """
    Check if running in offline mode.
    
    Returns:
        True if using local stubs, False if using real Azure
    """
    return OFFLINE_MODE


logger.info("✓ Hybrid Interface loaded (Phase 4 - Hybrid Readiness)")
