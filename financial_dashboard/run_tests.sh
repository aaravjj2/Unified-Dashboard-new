#!/bin/bash
##########################################################################
# Unified Test Runner for Financial Dashboard
# Runs all tests with Docker Compose orchestration
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

##########################################################################
# Main Execution
##########################################################################

log_section "Financial Dashboard - Unified Test Suite"
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
# Phase 1: Start Services with Docker Compose
##########################################################################

log_section "Phase 1: Starting Services with Docker Compose"

echo "🚀 Starting all services..."
if ! docker-compose up -d --build 2>&1 | tee -a "$REPORT_FILE"; then
    log_error "Failed to start services with Docker Compose"
    exit 1
fi

log_success "Services started"

echo ""
echo "⏳ Waiting 60 seconds for all services to become healthy..."
sleep 60

# Check service health
echo ""
echo "📊 Service Health Status:"
docker-compose ps | tee -a "$REPORT_FILE"

##########################################################################
# Phase 2: Run Test Suite
##########################################################################

log_section "Phase 2: Running Test Suite"

# Activate virtual environment if it exists
if [ -d ".venv_local" ]; then
    source .venv_local/bin/activate
fi

TESTS_PASSED=true

# Run all Sprint tests in order
for sprint in 2 3 4 5 6; do
    unit_test="${TEST_DIR}/test_sprint_${sprint}_unit.py"
    e2e_test="${TEST_DIR}/test_sprint_${sprint}_e2e.py"
    
    # Run unit tests
    if [ -f "$unit_test" ]; then
        log_section "Sprint $sprint Unit Tests"
        if python3 -m pytest "$unit_test" -v --tb=short 2>&1 | tee -a "$REPORT_FILE"; then
            log_success "Sprint $sprint Unit Tests: PASSED"
        else
            log_error "Sprint $sprint Unit Tests: FAILED"
            TESTS_PASSED=false
        fi
    fi
    
    # Run E2E tests
    if [ -f "$e2e_test" ]; then
        log_section "Sprint $sprint E2E Tests"
        if python3 -m pytest "$e2e_test" -v --tb=short 2>&1 | tee -a "$REPORT_FILE"; then
            log_success "Sprint $sprint E2E Tests: PASSED"
        else
            log_error "Sprint $sprint E2E Tests: FAILED"
            TESTS_PASSED=false
        fi
    fi
done

##########################################################################
# Phase 3: Cleanup
##########################################################################

log_section "Phase 3: Cleanup"

echo "🛑 Stopping services..."
docker-compose down 2>&1 | tee -a "$REPORT_FILE"

log_success "Services stopped"

##########################################################################
# Phase 4: Final Report
##########################################################################

log_section "Test Results Summary"

{
    echo ""
    echo "=========================================="
    echo "Final Results"
    echo "=========================================="
    echo ""
} >> "$REPORT_FILE"

if [ "$TESTS_PASSED" = true ]; then
    log_success "ALL TESTS PASSED ✓"
    echo "Status: ALL TESTS PASSED ✓" >> "$REPORT_FILE"
    exit 0
else
    log_error "SOME TESTS FAILED ✗"
    echo "Status: SOME TESTS FAILED ✗" >> "$REPORT_FILE"
    exit 1
fi
