#!/bin/bash
# Test runner for comprehensive system validation

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==============================================="
echo "COMPREHENSIVE SYSTEM TEST REPORT"
echo "==============================================="
echo ""

# Create test data directory
echo "[1/6] Creating test data..."
python3 tests/data/create_mock_features.py
echo "✓ Test data created"
echo ""

# Run unit tests
echo "[2/6] Running unit tests..."
echo ""

# Test 1: Locks
echo "  Running test_locks.py..."
python3 -m pytest tests/test_locks.py -v --tb=short
LOCKS_STATUS=$?
echo ""

# Test 2: Price Fetch
echo "  Running test_price_fetch.py..."
python3 -m pytest tests/test_price_fetch.py -v --tb=short
PRICE_STATUS=$?
echo ""

# Test 3: Weekly Pipeline Smoke Test
echo "  Running test_weekly_pipeline_smoke.py..."
python3 -m pytest tests/test_weekly_pipeline_smoke.py -v --tb=short
PIPELINE_STATUS=$?
echo ""

# Verify start_all.sh configuration
echo "[3/6] Verifying start_all.sh configuration..."
SERVICES_COUNT=$(grep -c '"]=".*\.py:' start_all.sh || true)
echo "  Services configured: $SERVICES_COUNT"
if [ "$SERVICES_COUNT" -ge 8 ]; then
    echo "  ✓ All 8 services configured"
    START_STATUS=0
else
    echo "  ✗ Expected 8 services, found $SERVICES_COUNT"
    START_STATUS=1
fi
echo ""

# Verify LightGBM model is used
echo "[4/6] Verifying ML model implementation..."
if grep -q "from lightgbm import LGBMRegressor" scripts/train_or_update_weekly.py; then
    echo "  ✓ LightGBM model imported"
    if grep -q "model.fit(X_train, y_train)" scripts/train_or_update_weekly.py; then
        echo "  ✓ Model training code found"
        MODEL_STATUS=0
    else
        echo "  ✗ No model.fit() call found"
        MODEL_STATUS=1
    fi
else
    echo "  ✗ LightGBM not imported"
    MODEL_STATUS=1
fi
echo ""

# Verify trade enrichment
echo "[5/6] Verifying trade enrichment..."
if grep -q "from utils import trade_utils" run_monthly_picks.py; then
    echo "  ✓ trade_utils imported in monthly picks"
    ENRICH_STATUS=0
else
    echo "  ✗ trade_utils not imported"
    ENRICH_STATUS=1
fi
if grep -q "compute_position_size" scripts/train_or_update_weekly.py; then
    echo "  ✓ Position sizing in weekly picks"
else
    echo "  ⚠ No position sizing in weekly picks"
fi
echo ""

# Check if Playwright script exists
echo "[6/6] Verifying Playwright script..."
if [ -f "capture_initial_state.py" ]; then
    echo "  ✓ capture_initial_state.py exists"
    PLAYWRIGHT_STATUS=0
else
    echo "  ✗ capture_initial_state.py not found"
    PLAYWRIGHT_STATUS=1
fi
echo ""

# Final summary
echo "==============================================="
echo "TEST RESULTS SUMMARY"
echo "==============================================="
echo ""
echo "Unit Tests:"
echo "  test_locks.py:                 $([ $LOCKS_STATUS -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "  test_price_fetch.py:           $([ $PRICE_STATUS -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "  test_weekly_pipeline_smoke.py: $([ $PIPELINE_STATUS -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo ""
echo "Code Quality:"
echo "  start_all.sh services:         $([ $START_STATUS -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "  LightGBM model:                $([ $MODEL_STATUS -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "  Trade enrichment:              $([ $ENRICH_STATUS -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "  Playwright script:             $([ $PLAYWRIGHT_STATUS -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo ""

TOTAL_STATUS=$((LOCKS_STATUS + PRICE_STATUS + PIPELINE_STATUS + START_STATUS + MODEL_STATUS + ENRICH_STATUS + PLAYWRIGHT_STATUS))

if [ $TOTAL_STATUS -eq 0 ]; then
    echo "==============================================="
    echo "ALL TESTS PASSED ✓"
    echo "==============================================="
    exit 0
else
    echo "==============================================="
    echo "SOME TESTS FAILED ✗"
    echo "==============================================="
    exit 1
fi
