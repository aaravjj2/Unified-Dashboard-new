"""
Azure ML Lab - Diagnostic & Pre-Flight Validation Script

Validates Azure ML Lab setup, module imports, and callback registration.
Run this before E2E testing to ensure all components are ready.

Usage:
    python diagnostics_azure_ml.py

Phase 3 Scaffold - Verifies placeholder functionality only.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# ============================================================================
# DIAGNOSTIC FUNCTIONS
# ============================================================================

def check_module_imports():
    """
    Validate that all Azure ML Lab modules can be imported.
    
    Returns:
        bool: True if all imports successful
    """
    logger.info("=" * 70)
    logger.info("1️⃣ MODULE IMPORT CHECK")
    logger.info("=" * 70)
    
    try:
        # Test main package import
        logger.info("Testing package import...")
        from financial_dashboard.tabs.azure_ml_lab import (
            create_azure_ml_lab_layout,
            register_azure_ml_callbacks,
            preprocess_portfolio_data,
            generate_mock_predictions
        )
        logger.info("✅ Main package imports successful")
        
        # Test individual modules
        logger.info("\nTesting individual modules...")
        
        from financial_dashboard.tabs.azure_ml_lab import layout
        logger.info("✅ layout.py imported")
        
        from financial_dashboard.tabs.azure_ml_lab import callbacks
        logger.info("✅ callbacks.py imported")
        
        from financial_dashboard.tabs.azure_ml_lab import helpers
        logger.info("✅ helpers.py imported")
        
        logger.info("\n✅ ALL MODULE IMPORTS PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"\n❌ MODULE IMPORT FAILED: {e}\n")
        return False


def check_helper_functions():
    """
    Validate that helper functions execute without errors.
    
    Returns:
        bool: True if all functions work
    """
    logger.info("=" * 70)
    logger.info("2️⃣ HELPER FUNCTION CHECK")
    logger.info("=" * 70)
    
    try:
        from financial_dashboard.tabs.azure_ml_lab.helpers import (
            preprocess_portfolio_data,
            generate_mock_predictions,
            generate_mock_historical_data,
            generate_mock_factor_data,
            cache_predictions,
            load_cached_predictions,
            ingest_portfolio_data,
            get_ml_diagnostics
        )
        
        # Test mock data generation
        logger.info("Testing mock data generation...")
        mock_hist = generate_mock_historical_data('AAPL', days=30)
        assert len(mock_hist) == 30, "Mock historical data length mismatch"
        logger.info(f"✅ Mock historical data: {len(mock_hist)} rows")
        
        mock_factors = generate_mock_factor_data(days=30)
        assert len(mock_factors) == 30, "Mock factor data length mismatch"
        logger.info(f"✅ Mock factor data: {len(mock_factors)} rows, {len(mock_factors.columns)} factors")
        
        # Test portfolio ingestion
        logger.info("\nTesting portfolio ingestion...")
        portfolio_data = ingest_portfolio_data()
        logger.info(f"✅ Portfolio data ingested: {portfolio_data.get('total_positions', 0)} positions")
        
        # Test preprocessing
        logger.info("\nTesting data preprocessing...")
        preprocessed = preprocess_portfolio_data(portfolio_data)
        logger.info(f"✅ Preprocessed data: {len(preprocessed)} rows, {len(preprocessed.columns) if len(preprocessed) > 0 else 0} features")
        
        # Test prediction generation
        logger.info("\nTesting mock prediction generation...")
        predictions = generate_mock_predictions(preprocessed, model_type='ensemble', horizon_days=5)
        assert 'predictions' in predictions, "Missing predictions key"
        logger.info(f"✅ Mock predictions: {len(predictions['predictions'])} forecasts generated")
        
        # Test caching
        logger.info("\nTesting prediction caching...")
        cache_success = cache_predictions(predictions, cache_key='diagnostic_test')
        assert cache_success, "Cache write failed"
        logger.info("✅ Predictions cached successfully")
        
        cached = load_cached_predictions(cache_key='diagnostic_test')
        assert cached is not None, "Cache read failed"
        logger.info("✅ Cached predictions loaded successfully")
        
        # Test diagnostics
        logger.info("\nTesting diagnostics...")
        diagnostics = get_ml_diagnostics()
        assert 'status' in diagnostics, "Missing diagnostics status"
        logger.info(f"✅ Diagnostics retrieved: status={diagnostics['status']}")
        
        logger.info("\n✅ ALL HELPER FUNCTIONS PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"\n❌ HELPER FUNCTION CHECK FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def check_layout_generation():
    """
    Validate that layout can be generated without errors.
    
    Returns:
        bool: True if layout generation successful
    """
    logger.info("=" * 70)
    logger.info("3️⃣ LAYOUT GENERATION CHECK")
    logger.info("=" * 70)
    
    try:
        from financial_dashboard.tabs.azure_ml_lab.layout import create_azure_ml_lab_layout
        
        logger.info("Generating Azure ML Lab layout...")
        layout = create_azure_ml_lab_layout()
        
        assert layout is not None, "Layout is None"
        logger.info("✅ Layout generated successfully")
        
        # Check for key components
        logger.info("\nValidating layout structure...")
        layout_str = str(layout)
        
        required_components = [
            'azure-ml-model-type',
            'azure-ml-run-prediction-btn',
            'azure-ml-prediction-results',
            'azure-ml-system-status'
        ]
        
        for component_id in required_components:
            assert component_id in layout_str, f"Missing component: {component_id}"
            logger.info(f"✅ Component found: {component_id}")
        
        logger.info("\n✅ LAYOUT GENERATION PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"\n❌ LAYOUT GENERATION FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def check_callback_registration():
    """
    Validate that callbacks can be registered (mock app).
    
    Returns:
        bool: True if callback registration successful
    """
    logger.info("=" * 70)
    logger.info("4️⃣ CALLBACK REGISTRATION CHECK")
    logger.info("=" * 70)
    
    try:
        from financial_dashboard.tabs.azure_ml_lab.callbacks import register_azure_ml_callbacks
        
        logger.info("Testing callback registration (mock mode)...")
        
        # Create mock app for testing
        class MockApp:
            def callback(self, *args, **kwargs):
                def decorator(func):
                    logger.info(f"  ✅ Callback registered: {func.__name__}")
                    return func
                return decorator
        
        mock_app = MockApp()
        register_azure_ml_callbacks(mock_app)
        
        logger.info("\n✅ CALLBACK REGISTRATION PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"\n❌ CALLBACK REGISTRATION FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def check_docker_environment():
    """
    Validate Docker environment readiness.
    
    Returns:
        bool: True if environment ready
    """
    logger.info("=" * 70)
    logger.info("5️⃣ DOCKER ENVIRONMENT CHECK")
    logger.info("=" * 70)
    
    try:
        import dash
        import dash_bootstrap_components
        import plotly
        import pandas
        import numpy
        
        logger.info(f"✅ Dash version: {dash.__version__}")
        logger.info(f"✅ DBC version: {dash_bootstrap_components.__version__}")
        logger.info(f"✅ Plotly version: {plotly.__version__}")
        logger.info(f"✅ Pandas version: {pandas.__version__}")
        logger.info(f"✅ NumPy version: {numpy.__version__}")
        
        # Check cache directory
        cache_dir = Path(__file__).parent.parent.parent / "cache" / "ml_predictions"
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Cache directory available: {cache_dir}")
        
        logger.info("\n✅ DOCKER ENVIRONMENT PASSED\n")
        return True
    
    except Exception as e:
        logger.error(f"\n❌ DOCKER ENVIRONMENT CHECK FAILED: {e}\n")
        return False


def run_all_diagnostics():
    """
    Run all diagnostic checks and generate report.
    
    Returns:
        bool: True if all checks passed
    """
    logger.info("\n" + "=" * 70)
    logger.info("AZURE ML LAB DIAGNOSTICS - PHASE 3 SCAFFOLD")
    logger.info("=" * 70 + "\n")
    
    results = {
        'Module Imports': check_module_imports(),
        'Helper Functions': check_helper_functions(),
        'Layout Generation': check_layout_generation(),
        'Callback Registration': check_callback_registration(),
        'Docker Environment': check_docker_environment()
    }
    
    # Summary
    logger.info("=" * 70)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 70)
    
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {check_name}")
    
    all_passed = all(results.values())
    
    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("🎉 ALL DIAGNOSTICS PASSED - READY FOR E2E TESTING")
    else:
        logger.info("⚠️  SOME DIAGNOSTICS FAILED - REVIEW ERRORS ABOVE")
    logger.info("=" * 70 + "\n")
    
    return all_passed


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    success = run_all_diagnostics()
    sys.exit(0 if success else 1)
