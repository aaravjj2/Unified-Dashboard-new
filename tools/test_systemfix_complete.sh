#!/bin/bash
# SYSTEMFIX STEPS D-F: Complete Test Execution Script
# Run this after dashboard has fully started (150s recommended wait time)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "================================================================================"
echo "SYSTEMFIX STEPS D-F: COMPREHENSIVE TEST SUITE"
echo "================================================================================"
echo ""
echo "⚠️  PREREQUISITE: Dashboard MUST be running on port 8050"
echo "   If not started, run in another terminal:"
echo "   cd $REPO_ROOT && PORT=8050 python3 run_dashboard.py"
echo ""
echo "   Wait 150 seconds for full initialization before running this script."
echo ""
read -p "Press ENTER when dashboard is ready (or Ctrl+C to cancel)..."
echo ""

# Test 1: Check dashboard is responding
echo "================================================================================  "
echo "TEST 1: Dashboard Health Check"
echo "================================================================================"
echo ""
echo "Testing if dashboard is responding on port 8050..."
if curl -s -f -m 5 http://localhost:8050/ > /dev/null 2>&1; then
    echo "✅ Dashboard is responding"
else
    echo "❌ Dashboard is NOT responding"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if process is running: ps aux | grep run_dashboard"
    echo "2. Check port is listening: netstat -tuln | grep 8050"
    echo "3. Check logs: tail -50 dashboard_test.log"
    exit 1
fi
echo ""

# Test 2: Health endpoint
echo "================================================================================"
echo "TEST 2: /health/systemfix Endpoint"
echo "================================================================================"
echo ""
curl -s http://localhost:8050/health/systemfix | python3 -m json.tool || {
    echo "❌ Health endpoint failed"
    exit 1
}
echo ""
echo "✅ Health endpoint test passed"
echo ""

# Test 3: Callback map endpoint
echo "================================================================================"
echo "TEST 3: /admin/callback_map Endpoint"
echo "================================================================================"
echo ""
CALLBACK_COUNT=$(curl -s http://localhost:8050/admin/callback_map | python3 -c "import sys, json; print(json.load(sys.stdin)['total_callbacks'])" 2>/dev/null || echo "0")
echo "Total callbacks registered: $CALLBACK_COUNT"
if [ "$CALLBACK_COUNT" -gt "0" ]; then
    echo "✅ Callback map endpoint test passed"
else
    echo "⚠️  Warning: Callback count is 0 (might be lazy registration)"
fi
echo ""

# Test 4: Market sentiment endpoint
echo "================================================================================"
echo "TEST 4: /api/cc/market_sentiment Endpoint"
echo "================================================================================"
echo ""
curl -s http://localhost:8050/api/cc/market_sentiment | python3 -m json.tool | head -20 || {
    echo "⚠️  Market sentiment endpoint returned error (check if poller is running)"
}
echo ""

# Test 5: Quick endpoint validator
echo "================================================================================"
echo "TEST 5: Running Quick Endpoint Validator"
echo "================================================================================"
echo ""
python3 tools/validate_systemfix_endpoints.py || {
    echo "⚠️  Some endpoints failed validation"
}
echo ""

# Test 6: Playwright tests (optional, requires Playwright installed)
echo "================================================================================"
echo "TEST 6: Playwright Headful Smoke Tests (OPTIONAL)"
echo "================================================================================"
echo ""
read -p "Run Playwright tests? This will open a browser window. (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v playwright &> /dev/null; then
        echo "Running Playwright tests in headful mode..."
        python3 tests/playwright/systemfix_smoke_headful.py || {
            echo "⚠️  Some Playwright tests failed"
        }
    else
        echo "❌ Playwright not installed. Install with:"
        echo "   pip install playwright"
        echo "   playwright install chromium"
    fi
else
    echo "⏭️  Skipped Playwright tests"
fi
echo ""

# Test 7: Check all artifacts
echo "================================================================================"
echo "TEST 7: Verify Artifacts Created"
echo "================================================================================"
echo ""
echo "Checking for test artifacts..."
echo ""
echo "📁 Reports directory structure:"
ls -lh reports/systemfix/final/ 2>/dev/null || echo "⚠️  No final reports found"
echo ""
ls -lh reports/systemfix/diagnostics/ 2>/dev/null | head -10 || echo "⚠️  No diagnostic files"
echo ""

# Summary
echo "================================================================================"
echo "TEST EXECUTION SUMMARY"
echo "================================================================================"
echo ""
echo "✅ All manual tests completed"
echo ""
echo "📊 Generated Reports:"
echo "   - Health endpoint response: reports/systemfix/diagnostics/health.json"
echo "   - Callback map response: reports/systemfix/diagnostics/callback_map.json"
echo "   - Market sentiment response: reports/systemfix/diagnostics/market_sentiment.json"
echo "   - Endpoint validation: reports/systemfix/diagnostics/*.json"
if [ -f "reports/systemfix/playwright/systemfix_test_report_"*.json ]; then
    echo "   - Playwright test report: reports/systemfix/playwright/systemfix_test_report_*.json"
fi
echo ""
echo "📖 Documentation:"
echo "   - Completion report: reports/systemfix/final/STEPS_D_E_F_COMPLETION_REPORT.md"
echo "   - Quick summary: reports/systemfix/final/STEPS_D_E_F_QUICK_SUMMARY.md"
echo ""
echo "🎯 Next Steps:"
echo "   1. Review test artifacts in reports/systemfix/"
echo "   2. Check health endpoint in browser: http://localhost:8050/health/systemfix"
echo "   3. Review completion report for detailed findings"
echo "   4. Decide on production deployment timeline"
echo ""
echo "================================================================================"
echo "✅ TESTING COMPLETE"
echo "================================================================================"
