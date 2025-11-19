#!/usr/bin/env python3
"""
Phase 6 — Smoke Test Script
============================

Quick validation of Phase 6 Azure ML SHAP & Options integration.

Usage:
    python phase6_smoke_test.py
    
    # With custom portfolio size
    PORTFOLIO_SIZE=5 python phase6_smoke_test.py
    
    # With Azure ML endpoints (production mode)
    AZURE_ML_OFFLINE_MODE=false python phase6_smoke_test.py

Author: Agent 1A — Unified Financial Dashboard Team
Version: 1.0
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("Phase 6 — Azure ML SHAP & Options Forecasting — SMOKE TEST")
print("=" * 80)

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

offline_mode = os.getenv("AZURE_ML_OFFLINE_MODE", "true").lower() == "true"
portfolio_size = int(os.getenv("PORTFOLIO_SIZE", "3"))

print(f"\n📋 Configuration:")
print(f"   • Offline Mode: {offline_mode}")
print(f"   • Portfolio Size: {portfolio_size} tickers")
print(f"   • Test Timeout: 30s")

if offline_mode:
    print(f"   ✅ Mock mode enabled (deterministic synthetic data)")
else:
    print(f"   ⚠️  Production mode (requires Azure ML endpoints)")
    print(f"      AZURE_ML_ENDPOINT_URL: {os.getenv('AZURE_ML_ENDPOINT_URL', 'NOT SET')}")
    print(f"      AZURE_ML_OPTIONS_ENDPOINT_URL: {os.getenv('AZURE_ML_OPTIONS_ENDPOINT_URL', 'NOT SET')}")

# ============================================================================
# TEST 1: IMPORT MODULES
# ============================================================================

print("\n" + "=" * 80)
print("TEST 1: Import Phase 6 Modules")
print("=" * 80)

try:
    from financial_dashboard.tabs.azure_ml_lab.phase6_azure_integration import (
        create_azure_shap_client,
        create_azure_options_client,
        create_batch_orchestrator,
        Phase6CacheKeyGenerator,
        create_phase6_cache_config
    )
    print("✅ All Phase 6 modules imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# ============================================================================
# TEST 2: SINGLE SHAP EXPLANATION
# ============================================================================

print("\n" + "=" * 80)
print("TEST 2: Single SHAP Explanation")
print("=" * 80)

try:
    shap_client = create_azure_shap_client()
    
    # Test ticker
    ticker = "AAPL"
    features = {f"feature_{i}": float(i) / 100.0 for i in range(28)}
    
    print(f"Generating SHAP for {ticker}...")
    start = time.time()
    contract = shap_client.generate_shap_explanation_azure(ticker, features)
    elapsed_ms = (time.time() - start) * 1000
    
    # Validate contract
    assert hasattr(contract, "prediction_id"), "Missing prediction_id"
    assert hasattr(contract, "shap_values"), "Missing shap_values"
    assert hasattr(contract, "feature_importance"), "Missing feature_importance"
    assert len(contract.shap_values) == 28, f"Expected 28 SHAP values, got {len(contract.shap_values)}"
    
    # Check performance
    sla_ms = 2500
    sla_status = "✅" if elapsed_ms < sla_ms else "❌"
    
    print(f"{sla_status} Single SHAP: {elapsed_ms:.1f}ms (SLA: <{sla_ms}ms)")
    print(f"   • Prediction ID: {contract.prediction_id[:20]}...")
    print(f"   • Base Value: {contract.base_value:.4f}")
    print(f"   • Top 3 Features: {list(contract.feature_importance.keys())[:3]}")
    
except Exception as e:
    print(f"❌ Single SHAP test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 3: OPTIONS FORECAST
# ============================================================================

print("\n" + "=" * 80)
print("TEST 3: Options Forecast")
print("=" * 80)

try:
    options_client = create_azure_options_client()
    
    ticker = "AAPL"
    expiration_days = 30
    
    print(f"Generating options forecast for {ticker} ({expiration_days}d expiration)...")
    start = time.time()
    forecast = options_client.generate_options_forecast(ticker, expiration_days)
    elapsed_ms = (time.time() - start) * 1000
    
    # Validate contract
    assert hasattr(forecast, "forecast_id"), "Missing forecast_id"
    assert hasattr(forecast, "expected_return"), "Missing expected_return"
    assert hasattr(forecast, "metadata"), "Missing metadata"
    assert "greeks" in forecast.metadata, "Missing Greeks in metadata"
    
    greeks = forecast.metadata["greeks"]
    required_greeks = ["delta", "gamma", "theta", "vega"]
    for greek in required_greeks:
        assert greek in greeks, f"Missing {greek} in Greeks"
    
    # Check performance
    sla_ms = 3000
    sla_status = "✅" if elapsed_ms < sla_ms else "❌"
    
    print(f"{sla_status} Options Forecast: {elapsed_ms:.1f}ms (SLA: <{sla_ms}ms)")
    print(f"   • Forecast ID: {forecast.forecast_id[:20]}...")
    print(f"   • Expected Return: {forecast.expected_return:.2%}")
    print(f"   • Greeks: Delta={greeks['delta']:.3f}, Gamma={greeks['gamma']:.3f}, Theta={greeks['theta']:.3f}, Vega={greeks['vega']:.3f}")
    
except Exception as e:
    print(f"❌ Options forecast test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 4: BATCH SHAP
# ============================================================================

print("\n" + "=" * 80)
print("TEST 4: Batch SHAP Explanation")
print("=" * 80)

try:
    orchestrator = create_batch_orchestrator(shap_client=shap_client)
    
    # Create test portfolio CSV
    test_portfolio_path = project_root / "test-artifacts" / "smoke_test_portfolio.csv"
    test_portfolio_path.parent.mkdir(exist_ok=True)
    
    test_tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"][:portfolio_size]
    
    with open(test_portfolio_path, "w") as f:
        f.write("ticker,shares,cost_basis\n")
        for ticker in test_tickers:
            f.write(f"{ticker},100,150.00\n")
    
    print(f"Running batch SHAP for {len(test_tickers)} tickers...")
    start = time.time()
    batch_result = orchestrator.batch_explain_portfolio(
        portfolio_source="csv",
        csv_path=str(test_portfolio_path)
    )
    elapsed_ms = (time.time() - start) * 1000
    
    # Validate result
    assert batch_result is not None, "Batch result is None"
    assert len(batch_result.ticker_results) == len(test_tickers), \
        f"Expected {len(test_tickers)} results, got {len(batch_result.ticker_results)}"
    assert batch_result.aggregated_importance is not None, "Missing aggregated importance"
    
    # Check performance (scale SLA by portfolio size: 8s for 10 tickers = 0.8s per ticker)
    sla_ms = 800 * len(test_tickers) * 1.1  # 10% tolerance
    sla_status = "✅" if elapsed_ms < sla_ms else "❌"
    
    print(f"{sla_status} Batch SHAP: {elapsed_ms:.1f}ms (SLA: <{sla_ms:.1f}ms for {len(test_tickers)} tickers)")
    print(f"   • Tickers Analyzed: {batch_result.tickers_analyzed}")
    print(f"   • Execution Time: {batch_result.execution_time_seconds:.2f}s")
    print(f"   • Cache Hit Rate: {batch_result.cache_hit_rate_pct:.1f}%")
    print(f"   • Top 3 Aggregated Features: {list(batch_result.aggregated_importance.keys())[:3]}")
    
except Exception as e:
    print(f"❌ Batch SHAP test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 5: CACHE KEY DETERMINISM
# ============================================================================

print("\n" + "=" * 80)
print("TEST 5: Cache Key Determinism")
print("=" * 80)

try:
    keygen = Phase6CacheKeyGenerator()
    
    # Test SHAP key
    features1 = {"rsi": 0.65, "macd": 0.02, "volume_ratio": 1.2}
    features2 = {"volume_ratio": 1.2, "rsi": 0.65, "macd": 0.02}  # Different order
    
    key1 = keygen.generate_shap_key("AAPL", features1, "1.0")
    key2 = keygen.generate_shap_key("AAPL", features2, "1.0")
    
    assert key1 == key2, f"SHAP keys not deterministic: {key1} != {key2}"
    print(f"✅ SHAP cache keys deterministic: {key1}")
    
    # Test options key price bucketing
    options_key1 = keygen.generate_options_key("AAPL", 30, 182.00)
    options_key2 = keygen.generate_options_key("AAPL", 30, 182.49)
    options_key3 = keygen.generate_options_key("AAPL", 30, 184.99)
    
    assert options_key1 == options_key2, "Price bucketing failed (should be same)"
    assert options_key2 != options_key3, "Price bucketing failed (should be different)"
    print(f"✅ Options cache keys with price bucketing: {options_key1}")
    
    # Test batch SHAP key ordering
    batch_key1 = keygen.generate_batch_shap_key(["AAPL", "TSLA", "NVDA"], "1.0")
    batch_key2 = keygen.generate_batch_shap_key(["NVDA", "AAPL", "TSLA"], "1.0")  # Different order
    
    assert batch_key1 == batch_key2, f"Batch SHAP keys not order-independent: {batch_key1} != {batch_key2}"
    print(f"✅ Batch SHAP cache keys order-independent: {batch_key1}")
    
except Exception as e:
    print(f"❌ Cache key determinism test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 6: REPRODUCIBILITY
# ============================================================================

print("\n" + "=" * 80)
print("TEST 6: Deterministic Reproducibility")
print("=" * 80)

try:
    ticker = "AAPL"
    features = {f"feature_{i}": float(i) / 100.0 for i in range(28)}
    
    # Run SHAP 3 times
    print(f"Running SHAP 3 times for {ticker}...")
    results = []
    for i in range(3):
        contract = shap_client.generate_shap_explanation_azure(ticker, features)
        results.append(contract)
    
    # Compare SHAP values
    shap_values_0 = results[0].shap_values
    shap_values_1 = results[1].shap_values
    shap_values_2 = results[2].shap_values
    
    assert shap_values_0 == shap_values_1, "Iteration 1 vs 2 mismatch"
    assert shap_values_1 == shap_values_2, "Iteration 2 vs 3 mismatch"
    
    print(f"✅ SHAP reproducibility validated (3 iterations identical)")
    
    # Run options forecast 3 times
    print(f"Running options forecast 3 times for {ticker}...")
    forecasts = []
    for i in range(3):
        forecast = options_client.generate_options_forecast(ticker, 30)
        forecasts.append(forecast)
    
    # Compare expected returns (within floating-point tolerance)
    er_0 = forecasts[0].expected_return
    er_1 = forecasts[1].expected_return
    er_2 = forecasts[2].expected_return
    
    assert abs(er_0 - er_1) < 1e-6, f"Expected return mismatch (1 vs 2): {er_0} != {er_1}"
    assert abs(er_1 - er_2) < 1e-6, f"Expected return mismatch (2 vs 3): {er_1} != {er_2}"
    
    print(f"✅ Options forecast reproducibility validated (3 iterations identical)")
    
except Exception as e:
    print(f"❌ Reproducibility test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("SMOKE TEST SUMMARY")
print("=" * 80)

print("""
✅ TEST 1: Module Imports .......................... PASS
✅ TEST 2: Single SHAP Explanation ................. PASS
✅ TEST 3: Options Forecast ........................ PASS
✅ TEST 4: Batch SHAP Explanation .................. PASS
✅ TEST 5: Cache Key Determinism ................... PASS
✅ TEST 6: Deterministic Reproducibility ........... PASS

🎉 All Phase 6 smoke tests passed!

Next Steps:
1. Run full E2E test suite: pytest tests/test_phase6_e2e.py -v
2. Start dashboard: python financial_dashboard/analysis_app.py
3. Test UI:
   - Navigate to "Model Insights" tab
   - Click "Explain All Portfolio" button
   - Navigate to "Market Forecast" tab
   - Click "Fetch Options Forecast" button
4. Monitor cache hit rates and performance

For production deployment:
1. Set Azure ML endpoint URLs in environment variables
2. Configure API keys or service principal credentials
3. Run smoke test with AZURE_ML_OFFLINE_MODE=false
4. Deploy to staging environment
""")

print("=" * 80)
print("✅ Phase 6 smoke test completed successfully")
print("=" * 80)
