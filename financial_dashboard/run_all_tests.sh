#!/bin/bash
##########################################################################
# Comprehensive Test Runner for Financial Dashboard
# Runs all tests across all sprints with health checks and reporting
##########################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="tests"
REPORT_DIR="test_reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="${REPORT_DIR}/test_results_${TIMESTAMP}.txt"

# Service URLs
# Note: the integrated dashboard in this workspace runs on port 8000 by default
# Allow overriding via env var, but default to the integrated dashboard port
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8000}"
API_GATEWAY_URL="http://localhost:8049"
OPTIONS_SERVICE_URL="http://localhost:8060"

# Create report directory
mkdir -p "$REPORT_DIR"

##########################################################################
# Helper Functions
##########################################################################

log_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_service() {
    local name=$1
    local url=$2
    local max_retries=5
    local retry=0
    
    echo -n "Checking $name... "
    
    while [ $retry -lt $max_retries ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "$name is accessible"
            return 0
        fi
        retry=$((retry + 1))
        sleep 2
    done
    
    log_warning "$name is not accessible at $url"
    return 1
}

run_test_suite() {
    local name=$1
    local path=$2
    local required=${3:-true}
    
    log_section "Running $name"
    
    echo "Test path: $path"
    echo "Required: $required"
    echo ""
    
    if python3 -m pytest "$path" -v --tb=short 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "$name: PASSED"
        return 0
    else
        if [ "$required" = "true" ]; then
            log_error "$name: FAILED (REQUIRED)"
            return 1
        else
            log_warning "$name: FAILED (OPTIONAL)"
            return 0
        fi
    fi
}

##########################################################################
# Main Execution
##########################################################################

log_section "Financial Dashboard - Comprehensive Test Suite"
echo "Timestamp: $(date)"
echo "Report file: $REPORT_FILE"
echo ""

# Initialize report
{
    echo "=========================================="
    echo "Financial Dashboard - Test Report"
    echo "Timestamp: $(date)"
    echo "=========================================="
    echo ""
} > "$REPORT_FILE"

##########################################################################
# Phase 1: Health Checks
##########################################################################

log_section "Phase 1: Service Health Checks"

SERVICES_OK=true

# Check dashboard
if ! check_service "Dashboard" "$DASHBOARD_URL"; then
    log_warning "Dashboard not running - some E2E tests will be skipped"
    SERVICES_OK=false
fi

# Check API Gateway (optional)
check_service "API Gateway" "$API_GATEWAY_URL/health" || true

# Check Options Service (optional)
check_service "Options Service" "$OPTIONS_SERVICE_URL/health" || true

echo ""

##########################################################################
# Phase 2: Unit Tests
##########################################################################

log_section "Phase 2: Unit Tests"

UNIT_TESTS_PASSED=true

# Sprint 2 Tests (Database & Services - if available)
if [ -f "${TEST_DIR}/test_sprint_2.py" ]; then
    if ! run_test_suite "Sprint 2 Tests (Database & Services)" "${TEST_DIR}/test_sprint_2.py" false; then
        log_warning "Sprint 2 tests failed (optional)"
    fi
fi

# Sprint 3 Tests (Options Engine)
if [ -f "${TEST_DIR}/test_sprint_3_unit.py" ]; then
    if ! run_test_suite "Sprint 3 Unit Tests (Options Engine)" "${TEST_DIR}/test_sprint_3_unit.py" true; then
        UNIT_TESTS_PASSED=false
    fi
fi

# Sprint 4 Tests (Risk & Live Execution)
if [ -f "${TEST_DIR}/test_sprint_4_unit.py" ]; then
    if ! run_test_suite "Sprint 4 Unit Tests (Risk & Live Execution)" "${TEST_DIR}/test_sprint_4_unit.py" true; then
        UNIT_TESTS_PASSED=false
    fi
fi

# Sprint 5 Tests (Broker Abstraction & Production) - NEW
if [ -f "${TEST_DIR}/test_sprint_5_unit.py" ]; then
    if ! run_test_suite "Sprint 5 Unit Tests (Production Readiness)" "${TEST_DIR}/test_sprint_5_unit.py" true; then
        UNIT_TESTS_PASSED=false
    fi
fi

##########################################################################
# Phase 3: Integration Tests
##########################################################################

log_section "Phase 3: Integration Tests"

INTEGRATION_TESTS_PASSED=true

# Sprint 2 Tests (Database & Services)
if [ -f "${TEST_DIR}/test_sprint_2.py" ]; then
    run_test_suite "Sprint 2 Tests (Database & Services)" "${TEST_DIR}/test_sprint_2.py" false || true
fi

# Long-running tests (short version only)
if [ -f "${TEST_DIR}/test_long_running.py" ]; then
    log_section "Long-Running Stability Tests (5-minute validation)"
    if ! run_test_suite "Long-Running Tests (Short)" "${TEST_DIR}/test_long_running.py::TestLongRunningExecution::test_short_duration_run" false; then
        log_warning "Long-running tests failed (optional)"
    fi
fi

##########################################################################
# Phase 4: End-to-End Tests
##########################################################################

log_section "Phase 4: End-to-End Tests"

E2E_TESTS_PASSED=true

if [ "$SERVICES_OK" = "true" ]; then
    # Sprint 0 Validation Tests (Playwright)
    if [ -f "${TEST_DIR}/test_sprint_0_validation.py" ]; then
        run_test_suite "Sprint 0 Validation (E2E)" "${TEST_DIR}/test_sprint_0_validation.py" false || true
    fi
    
    # Sprint 3 E2E Tests
    if [ -f "${TEST_DIR}/test_sprint_3_e2e.py" ]; then
        if ! run_test_suite "Sprint 3 E2E Tests" "${TEST_DIR}/test_sprint_3_e2e.py" false; then
            E2E_TESTS_PASSED=false
        fi
    fi
    
    # Sprint 4 E2E Tests
    if [ -f "${TEST_DIR}/test_sprint_4_e2e.py" ]; then
        if ! run_test_suite "Sprint 4 E2E Tests" "${TEST_DIR}/test_sprint_4_e2e.py" false; then
            E2E_TESTS_PASSED=false
        fi
    fi
    
    # Sprint 5 Master E2E Tests (Comprehensive UI Validation) - NEW
    if [ -f "${TEST_DIR}/test_sprint_5_e2e.py" ]; then
        if ! run_test_suite "Sprint 5 Master E2E Tests (Full UI Validation)" "${TEST_DIR}/test_sprint_5_e2e.py" false; then
            E2E_TESTS_PASSED=false
        fi
    fi
    
    # Complete E2E Tests (Legacy)
    if [ -f "${TEST_DIR}/test_e2e_complete.py" ]; then
        if ! run_test_suite "Complete E2E Tests" "${TEST_DIR}/test_e2e_complete.py" false; then
            E2E_TESTS_PASSED=false
        fi
    fi
else
    log_warning "Skipping E2E tests - services not available"
    echo "To run E2E tests, start all services first:" | tee -a "$REPORT_FILE"
    echo "  python3 unified_dashboard.py &" | tee -a "$REPORT_FILE"
    echo "  python3 api_gateway.py &" | tee -a "$REPORT_FILE"
    echo "  python3 options_service.py &" | tee -a "$REPORT_FILE"
fi

##########################################################################
# Phase 5: Docker Tests (if Docker available)
##########################################################################

log_section "Phase 5: Docker Container Tests"

if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    log_success "Docker available - running container tests"
    
    # Test docker-compose configuration
    echo "Validating docker-compose.yml..."
    if docker-compose config > /dev/null 2>&1; then
        log_success "docker-compose.yml is valid"
    else
        log_error "docker-compose.yml has errors"
    fi
    
    # Test building images (optional - takes time)
    if [ "${BUILD_DOCKER:-false}" = "true" ]; then
        log_section "Building Docker images (this may take a while)..."
        if docker-compose build 2>&1 | tee -a "$REPORT_FILE"; then
            log_success "Docker images built successfully"
        else
            log_error "Docker build failed"
        fi
    else
        log_warning "Skipping Docker build (set BUILD_DOCKER=true to enable)"
    fi
else
    log_warning "Docker not available - skipping container tests"
fi

##########################################################################
# Final Report
##########################################################################

log_section "Test Summary"

# Count results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Parse pytest results from report
if [ -f "$REPORT_FILE" ]; then
    # Extract test counts (this is a simplified version)
    PASSED_COUNT=$(grep -c "PASSED" "$REPORT_FILE" || echo "0")
    FAILED_COUNT=$(grep -c "FAILED" "$REPORT_FILE" || echo "0")
    
    echo "Passed: $PASSED_COUNT"
    echo "Failed: $FAILED_COUNT"
fi

# Determine overall status
OVERALL_STATUS="UNKNOWN"
EXIT_CODE=0

if [ "$UNIT_TESTS_PASSED" = "true" ]; then
    log_success "Core unit tests: PASSED"
else
    log_error "Core unit tests: FAILED"
    OVERALL_STATUS="FAILED"
    EXIT_CODE=1
fi

if [ "$SERVICES_OK" = "true" ]; then
    log_success "Service health checks: PASSED"
else
    log_warning "Service health checks: SOME SERVICES DOWN"
fi

if [ "$E2E_TESTS_PASSED" = "true" ]; then
    log_success "E2E tests: PASSED"
elif [ "$SERVICES_OK" = "false" ]; then
    log_warning "E2E tests: SKIPPED (services not running)"
else
    log_warning "E2E tests: FAILED (non-critical)"
fi

# Final status
echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    log_success "OVERALL STATUS: ALL CRITICAL TESTS PASSED ✓"
else
    log_error "OVERALL STATUS: SOME CRITICAL TESTS FAILED ✗"
fi
echo "=========================================="

echo ""
echo "Full report saved to: $REPORT_FILE"
echo ""

# Additional information
log_section "Next Steps"
echo "1. Review the full report: cat $REPORT_FILE"
echo "2. Run specific test suite: python3 -m pytest tests/test_sprint_X.py -v"
echo "3. Run E2E tests: python3 -m pytest tests/test_e2e_complete.py -v -s"
echo "4. Run 24-hour stability test: python3 -m pytest tests/test_long_running.py -m slow -v -s"
echo "5. Start services: ./start_all.sh"
echo "6. Build Docker containers: BUILD_DOCKER=true ./run_all_tests.sh"
echo ""

exit $EXIT_CODE
