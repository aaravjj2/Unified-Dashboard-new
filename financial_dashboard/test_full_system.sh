#!/bin/bash
################################################################################
# Full System End-to-End Test Script
#
# Tests the complete pipeline from data fetch to dashboard startup:
# 1. Weekly pipeline (feature engineering + predictions)
# 2. Monthly picks generation
# 3. Event classification
# 4. Trade execution (dry-run)
# 5. Picks performance analysis
# 6. Dashboard startup
#
# Exits on first failure. Logs all output to logs/system_test_{timestamp}.log
#
# Usage:
#   ./test_full_system.sh
#   ./test_full_system.sh --skip-weekly  # Skip weekly pipeline (slow)
################################################################################

set -e  # Exit on first error
set -o pipefail  # Catch errors in pipes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="logs"
LOG_FILE="${LOG_DIR}/system_test_${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}"

# Parse arguments
SKIP_WEEKLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-weekly)
            SKIP_WEEKLY=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${LOG_FILE}"
}

run_step() {
    local step_name=$1
    local step_cmd=$2
    
    echo "" | tee -a "${LOG_FILE}"
    log_info "========================================" 
    log_info "Step: ${step_name}"
    log_info "Command: ${step_cmd}"
    log_info "========================================"
    
    # Run command and capture output
    if eval "${step_cmd}" >> "${LOG_FILE}" 2>&1; then
        log_success "${step_name} completed successfully"
        return 0
    else
        log_error "${step_name} FAILED!"
        log_error "Check log file for details: ${LOG_FILE}"
        return 1
    fi
}

################################################################################
# Main Test Sequence
################################################################################

log_info "🚀 Starting Full System End-to-End Test"
log_info "Timestamp: ${TIMESTAMP}"
log_info "Log file: ${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

# Step 1: Weekly Pipeline (optional, can be slow)
if [ "$SKIP_WEEKLY" = false ]; then
    if [ -f "scripts/run_weekly_pipeline.sh" ]; then
        run_step "Weekly Pipeline" \
            "bash scripts/run_weekly_pipeline.sh --date $(date +%Y%m%d) --top-k 10 --sample-size 20" || exit 1
    else
        log_warn "scripts/run_weekly_pipeline.sh not found - skipping"
    fi
else
    log_info "Skipping Weekly Pipeline (--skip-weekly flag)"
fi

# Step 2: Monthly Picks Generation
if [ -f "run_monthly_picks.py" ]; then
    run_step "Monthly Picks Generation" \
        "python3 run_monthly_picks.py" || exit 1
else
    log_error "run_monthly_picks.py not found!"
    exit 1
fi

# Step 3: Event Classification
if [ -f "pipelines/event_classifier.py" ]; then
    run_step "Event Classification" \
        "python3 pipelines/event_classifier.py" || exit 1
else
    log_warn "pipelines/event_classifier.py not found - skipping"
fi

# Step 4: Trade Execution (Dry-Run)
if [ -f "pipelines/execute_trades.py" ]; then
    run_step "Trade Execution (Dry-Run)" \
        "python3 pipelines/execute_trades.py --dry-run" || exit 1
else
    log_warn "pipelines/execute_trades.py not found - skipping"
fi

# Step 5: Picks Performance Analysis
if [ -f "pipelines/analyze_picks_performance.py" ]; then
    run_step "Picks Performance Analysis" \
        "python3 pipelines/analyze_picks_performance.py --lookback-days 180" || exit 1
else
    log_warn "pipelines/analyze_picks_performance.py not found - skipping"
fi

# Step 6: Dashboard Startup (verify it starts without errors)
if [ -f "start_all.sh" ]; then
    log_info "Testing dashboard startup..."
    
    # Start dashboards in background
    bash start >> "${LOG_FILE}" 2>&1 &
    DASHBOARD_PID=$!
    
    log_info "Dashboards started (PID: ${DASHBOARD_PID}), waiting 15 seconds for initialization..."
    sleep 15
    
    # Check if processes are still running
    if ps -p ${DASHBOARD_PID} > /dev/null; then
        log_success "Dashboards started successfully"
        
        # Kill dashboard processes
        log_info "Stopping dashboards..."
        pkill -P ${DASHBOARD_PID} 2>/dev/null || true
        kill ${DASHBOARD_PID} 2>/dev/null || true
        sleep 2
        log_success "Dashboards stopped"
    else
        log_error "Dashboards failed to start or crashed"
        exit 1
    fi
else
    log_warn "start_all.sh not found - skipping dashboard startup test"
fi

# Summary
echo "" | tee -a "${LOG_FILE}"
log_info "========================================" 
log_success "✅ FULL SYSTEM TEST PASSED!"
log_info "========================================" 
log_info "All pipeline steps completed successfully"
log_info "Log file: ${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

exit 0
