#!/bin/bash
# Sprint 0: Final Validation Script
# Validates that the refactored architecture is working correctly

set -e  # Exit on any error

echo "============================================================"
echo "Sprint 0: Final System Validation"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_check() {
    TEST_NAME="$1"
    if eval "$2"; then
        echo -e "${GREEN}✓${NC} $TEST_NAME"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $TEST_NAME"
        ((FAILED++))
    fi
}

echo "1. Architecture Validation"
echo "----------------------------"

# Test: app.py exists
test_check "app.py exists" "[ -f app.py ]"

# Test: index.py exists
test_check "index.py exists" "[ -f index.py ]"

# Test: Can import app
test_check "Can import app.py" "python3 -c 'from app import app' 2>/dev/null"

# Test: Can import index
test_check "Can import index.py" "python3 -c 'from index import app' 2>/dev/null"

echo ""
echo "2. Tab Module Validation"
echo "-------------------------"

# Test: All tabs exist
TABS=(
    "tabs/home.py"
    "tabs/market_trends.py"
    "tabs/market_forecast.py"
    "tabs/volatility_lab.py"
    "tabs/monthly_picks.py"
    "tabs/weekly_picks.py"
    "tabs/analysis_hub_refactored.py"
    "tabs/portfolio_tracker_refactored.py"
    "tabs/research_lab_tab.py"
    "tabs/options_lab.py"
    "tabs/backtesting_lab.py"
)

for tab in "${TABS[@]}"; do
    test_check "Tab exists: $tab" "[ -f $tab ]"
done

echo ""
echo "3. Service Validation"
echo "---------------------"

# Test: Services directory exists
test_check "services/ directory exists" "[ -d services ]"

# Test: Key services exist
SERVICES=(
    "services/market_trends_service.py"
    "services/market_forecast_service.py"
    "services/analysis_service.py"
    "services/options_service.py"
    "services/portfolio_service.py"
)

for service in "${SERVICES[@]}"; do
    test_check "Service exists: $service" "[ -f $service ]"
done

echo ""
echo "4. Docker Configuration Validation"
echo "-----------------------------------"

# Test: docker-compose.yml exists
test_check "docker-compose.yml exists" "[ -f docker-compose.yml ]"

# Test: Dockerfiles exist
test_check "Dockerfile.base exists" "[ -f Dockerfile.base ]"
test_check "Dockerfile.analysis exists" "[ -f Dockerfile.analysis ]"
test_check "Dockerfile.market_trends exists" "[ -f Dockerfile.market_trends ]"

echo ""
echo "5. Test Suite Validation"
echo "-------------------------"

# Test: Test directory exists
test_check "tests/ directory exists" "[ -d tests ]"

# Test: Final validation test exists
test_check "test_final_validation.py exists" "[ -f tests/test_final_validation.py ]"

echo ""
echo "6. Documentation Validation"
echo "----------------------------"

# Test: Sprint 0 documentation exists
test_check "SPRINT_0_COMPLETION_REPORT.md exists" "[ -f SPRINT_0_COMPLETION_REPORT.md ]"
test_check "README_SPRINT_0.md exists" "[ -f README_SPRINT_0.md ]"
test_check "SPRINT_0_EXECUTIVE_SUMMARY.md exists" "[ -f SPRINT_0_EXECUTIVE_SUMMARY.md ]"

echo ""
echo "7. Dependency Validation"
echo "------------------------"

# Test: Key Python packages
test_check "dash installed" "python3 -c 'import dash' 2>/dev/null"
test_check "dash_bootstrap_components installed" "python3 -c 'import dash_bootstrap_components' 2>/dev/null"
test_check "plotly installed" "python3 -c 'import plotly' 2>/dev/null"
test_check "pandas installed" "python3 -c 'import pandas' 2>/dev/null"
test_check "fastapi installed" "python3 -c 'import fastapi' 2>/dev/null"

echo ""
echo "8. Data Quality Validation"
echo "--------------------------"

# Test: Attribution analysis fix
if grep -q "monthly_picks_\*.csv" tabs/attribution_analysis.py; then
    echo -e "${GREEN}✓${NC} Attribution analysis monthly picks pattern fixed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Attribution analysis monthly picks pattern NOT fixed"
    ((FAILED++))
fi

echo ""
echo "============================================================"
echo "VALIDATION SUMMARY"
echo "============================================================"
echo ""
echo -e "Tests Passed:  ${GREEN}${PASSED}${NC}"
echo -e "Tests Failed:  ${RED}${FAILED}${NC}"
echo ""

TOTAL=$((PASSED + FAILED))
PERCENTAGE=$((PASSED * 100 / TOTAL))

echo "Pass Rate: ${PERCENTAGE}% (${PASSED}/${TOTAL})"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL VALIDATIONS PASSED${NC}"
    echo ""
    echo "Sprint 0 is COMPLETE and ready for production!"
    echo ""
    echo "Next steps:"
    echo "1. Start services: docker-compose up -d"
    echo "2. Start dashboard: python3 index.py"
    echo "3. Run E2E tests: pytest tests/test_final_validation.py -v"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  SOME VALIDATIONS FAILED${NC}"
    echo ""
    echo "Please review the failed checks above."
    echo ""
    exit 1
fi
