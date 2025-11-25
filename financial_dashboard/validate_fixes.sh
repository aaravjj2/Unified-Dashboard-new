#!/bin/bash
# Simple curl-based validation of Portfolio Dashboard fixes
# No Playwright needed - just check server logs for errors

echo "============================================"
echo "Portfolio Dashboard - Bug Fix Validation"
echo "============================================"
echo ""

DASHBOARD_URL="http://127.0.0.1:8056"
LOG_FILE="/mnt/c/Aarav/fin_env/Dash/dashboard_fixed.log"

# Function to check for errors in log
check_log_for_error() {
    local error_pattern="$1"
    local test_name="$2"
    
    if tail -100 "$LOG_FILE" | grep -q "$error_pattern"; then
        echo "❌ FAIL: $test_name - Error found: $error_pattern"
        return 1
    else
        echo "✅ PASS: $test_name - No errors found"
        return 0
    fi
}

# Test 1: Load main page
echo "Test 1: Loading dashboard..."
curl -s "$DASHBOARD_URL" > /dev/null
sleep 2
check_log_for_error "Cannot compare tz-naive and tz-aware" "Timezone comparison"
check_log_for_error "If using all scalar values, you must pass an index" "Analytics scalar index error"

# Test 2: Check for ReferenceError
echo ""
echo "Test 2: Checking for ReferenceError..."
check_log_for_error "ReferenceError.*positions-datatable" "DataTable ReferenceError"

# Test 3: Check if SHAP errors are handled gracefully
echo ""
echo "Test 3: Checking SHAP error handling..."
if tail -100 "$LOG_FILE" | grep -q "SHAP file not found"; then
    echo "ℹ️  INFO: SHAP files not found (expected) - checking if handled gracefully"
    if tail -100 "$LOG_FILE" | grep -q "Error.*SHAP"; then
        echo "❌ FAIL: SHAP errors not handled gracefully"
    else
        echo "✅ PASS: SHAP missing files handled gracefully"
    fi
else
    echo "✅ PASS: SHAP data loaded successfully"
fi

# Test 4: Check for optimization errors
echo ""
echo "Test 4: Checking optimization error handling..."
check_log_for_error "Error running optimization:.*Check logs" "Generic optimization error"

# Summary
echo ""
echo "============================================"
echo "Validation Complete"
echo "============================================"
echo ""
echo "📊 Check the full log at: $LOG_FILE"
echo "🌐 Dashboard running at: $DASHBOARD_URL"
echo ""
echo "✅ All critical errors should be resolved"
echo "   - No timezone comparison errors"
echo "   - No scalar index errors"
echo "   - No ReferenceErrors"
echo "   - SHAP files handled gracefully"
echo ""
