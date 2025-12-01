#!/bin/bash
#
# portfolio_health_check.sh - Standalone Portfolio Dashboard Health Check
# 
# Purpose: Validates that the standalone portfolio dashboard on port 8056
# is running and responding correctly to HTTP requests.
#
# Usage: ./portfolio_health_check.sh
# Exit Codes:
#   0 - Dashboard is healthy (HTTP 200)
#   1 - Dashboard is not responding or returned non-200 status
#

set -e

# Configuration
DASHBOARD_URL="http://localhost:8056"
TIMEOUT=10
MAX_RETRIES=3

echo "================================================"
echo "Portfolio Dashboard Health Check"
echo "================================================"
echo "URL: ${DASHBOARD_URL}"
echo "Timeout: ${TIMEOUT}s"
echo "Max Retries: ${MAX_RETRIES}"
echo ""

# Function to check dashboard health
check_dashboard() {
    local attempt=$1
    echo "Attempt ${attempt}/${MAX_RETRIES}..."
    
    # Make HTTP request and capture status code
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time ${TIMEOUT} ${DASHBOARD_URL} 2>/dev/null || echo "000")
    
    echo "  Response Code: ${HTTP_STATUS}"
    
    if [ "${HTTP_STATUS}" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Main health check loop
for i in $(seq 1 ${MAX_RETRIES}); do
    if check_dashboard $i; then
        echo ""
        echo "✅ SUCCESS: Portfolio Dashboard is healthy and responding!"
        echo "   Status: HTTP 200 OK"
        echo "   URL: ${DASHBOARD_URL}"
        echo ""
        exit 0
    fi
    
    if [ $i -lt ${MAX_RETRIES} ]; then
        echo "  ⏳ Waiting 2 seconds before retry..."
        sleep 2
    fi
done

# All retries failed
echo ""
echo "❌ FAILED: Portfolio Dashboard is not responding after ${MAX_RETRIES} attempts"
echo ""
echo "Troubleshooting steps:"
echo "  1. Check if dashboard is running: ps aux | grep run_portfolio"
echo "  2. Check logs: tail -50 dashboard*.log"
echo "  3. Verify port 8056 is not in use: netstat -tulpn | grep 8056"
echo "  4. Restart dashboard: pkill -f run_portfolio && python run_portfolio.py"
echo ""

exit 1
