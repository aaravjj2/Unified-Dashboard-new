#!/bin/bash
################################################################################
# Dashboard Health Check Script
#
# Checks all dashboard endpoints for availability and response time.
# Tests the following services:
#   - Port 8050: Market Trends
#   - Port 8051: Market Forecast
#   - Port 8052: Monthly Picks
#   - Port 8053: Weekly Picks
#   - Port 8054: Analysis Hub
#   - Port 8056: Portfolio
#   - Port 8058: Research Lab
#   - Port 8059: Unified Dashboard
#
# Requirements:
#   - curl command installed
#   - Dashboards must be running (via start)
#
# Usage:
#   ./health_check.sh
#   ./health_check.sh --timeout 5  # Custom timeout in seconds
################################################################################

set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="logs"
LOG_FILE="${LOG_DIR}/health_check_${TIMESTAMP}.log"
TIMEOUT=3  # Default timeout in seconds

mkdir -p "${LOG_DIR}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT=$2
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Dashboard endpoints
# Allow overriding via environment variables; default to legacy ports 8052/8053
MONTHLY_PICKS_PORT=${MONTHLY_PICKS_PORT:-8052}
WEEKLY_PICKS_PORT=${WEEKLY_PICKS_PORT:-8053}

declare -A DASHBOARDS=(
    ["Market Trends"]="http://localhost:8050"
    ["Market Forecast"]="http://localhost:8051"
    ["Monthly Picks"]="http://localhost:${MONTHLY_PICKS_PORT}"
    ["Weekly Picks"]="http://localhost:${WEEKLY_PICKS_PORT}"
    ["Analysis Hub"]="http://localhost:8054"
    ["Portfolio"]="http://localhost:8056"
    ["Research Lab"]="http://localhost:8058"
    ["Unified Dashboard"]="http://localhost:8059"
)

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${LOG_FILE}"
}

check_endpoint() {
    local name=$1
    local url=$2
    local timeout=$3
    
    # Measure response time
    local start_time=$(date +%s%N)
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time ${timeout} "${url}" 2>/dev/null)
    local end_time=$(date +%s%N)
    
    # Calculate response time in milliseconds
    local response_time=$(( (end_time - start_time) / 1000000 ))
    
    # Check HTTP status code
    if [ "${http_code}" = "200" ]; then
        if [ ${response_time} -lt $(( timeout * 1000 )) ]; then
            log_success "${name} (${url}) - ${response_time}ms"
            return 0
        else
            log_warn "${name} (${url}) - ${response_time}ms (slow)"
            return 1
        fi
    elif [ "${http_code}" = "000" ]; then
        log_error "${name} (${url}) - Connection refused or timeout"
        return 1
    else
        log_error "${name} (${url}) - HTTP ${http_code}"
        return 1
    fi
}

################################################################################
# Main Health Check
################################################################################

echo "" | tee -a "${LOG_FILE}"
log_info "🏥 Dashboard Health Check"
log_info "Timestamp: ${TIMESTAMP}"
log_info "Timeout: ${TIMEOUT}s"
log_info "========================================" 
echo "" | tee -a "${LOG_FILE}"

TOTAL=0
PASSED=0
FAILED=0

# Check each dashboard
for name in "${!DASHBOARDS[@]}"; do
    url="${DASHBOARDS[$name]}"
    TOTAL=$((TOTAL + 1))
    
    if check_endpoint "${name}" "${url}" "${TIMEOUT}"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done

# Summary
echo "" | tee -a "${LOG_FILE}"
log_info "========================================" 
log_info "Summary: ${PASSED}/${TOTAL} endpoints healthy"
log_info "========================================" 

if [ ${FAILED} -eq 0 ]; then
    log_success "✅ All dashboards are healthy!"
    echo "" | tee -a "${LOG_FILE}"
    log_info "Log file: ${LOG_FILE}"
    exit 0
else
    log_error "❌ ${FAILED} dashboard(s) failed health check"
    echo "" | tee -a "${LOG_FILE}"
    log_info "Log file: ${LOG_FILE}"
    exit 1
fi
