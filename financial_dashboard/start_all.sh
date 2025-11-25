#!/bin/bash
# ==============================================================================
# Master Startup Script for Unified Financial Dashboard
# ==============================================================================
# This script stops any running services, generates necessary mock data,
# starts all required dashboard services, and verifies they are running.
#
# Usage:
#   From the project root directory (Dash/), run:
#   ./start_all.sh
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# Default ports (can be overridden by environment)
MONTHLY_PICKS_PORT=${MONTHLY_PICKS_PORT:-8052}
WEEKLY_PICKS_PORT=${WEEKLY_PICKS_PORT:-8053}

# --- Configuration ---
# UPDATED: Sprint 1 - All services now use Application Shell architecture
declare -A SERVICES
SERVICES=(
    ["API Gateway"]="api_gateway.py:8049"
    ["Market Trends Service"]="services/market_trends_service.py:8050"
    ["Market Forecast Service"]="services/market_forecast_service.py:8051"
    ["Analysis Hub Service"]="services/analysis_service.py:8054"
    ["Portfolio Service"]="services/portfolio_service.py:8056"
    ["Research Lab Service"]="services/research_lab_service.py:8058"
    ["Options Trading Service"]="options_service.py:8060"
    ["Integrated Dashboard"]="integrated_dashboard.py:8000"
    ["Monthly Picks Flask"]="monthly_picks_flask.py:${MONTHLY_PICKS_PORT}"
    ["Weekly Picks Flask"]="weekly_picks_flask.py:${WEEKLY_PICKS_PORT}"
)

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}          🚀 Starting Unified Financial Dashboard Services          ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"

# Navigate to the script's directory to ensure correct paths
cd "$(dirname "$0")"

# --- Step 1: Stop Existing Services ---
echo -e "\n${YELLOW}▶ Step 1: Stopping any existing dashboard services...${NC}"
PIDS=$(ps aux | grep -E "(api_gateway.py|market_trends_service.py|analysis_service.py|integrated_dashboard.py|unified_dashboard.py|market_trends_dash.py|analysis_app.py|monthly_picks_flask.py|weekly_picks_flask.py)" | grep -v grep | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "  Killing the following processes: $PIDS"
    kill -9 $PIDS 2>/dev/null || true
    sleep 2
    echo -e "  ${GREEN}✓ Services stopped.${NC}"
else
    echo -e "  ${GREEN}✓ No running services found.${NC}"
fi

# --- Step 2: Load Environment Variables ---
echo -e "\n${YELLOW}▶ Step 2: Loading API keys from keys.env...${NC}"
if [ -f "keys.env" ]; then
    set -a
    source keys.env
    set +a
    echo -e "  ${GREEN}✓ Environment variables loaded.${NC}"
else
    echo -e "  ${YELLOW}⚠ Warning: keys.env not found. API calls may fail.${NC}"
fi

# --- Step 3: Start Dashboard Service ---
echo -e "\n${YELLOW}▶ Step 3: Starting Financial Dashboard in the background...${NC}"

# Ensure a local logs directory exists (project-local instead of /tmp)
mkdir -p logs

for name in "${!SERVICES[@]}"; do
    IFS=':' read -r script port <<< "${SERVICES[$name]}"
    base=$(basename "$script" .py)
    log_file="$(pwd)/logs/${base}.log"

    if [ -f "$script" ]; then
        echo "  • Starting ${name} (port ${port}) -> ${log_file}"
        # Export any detected MONTHLY/WEEKLY picks env vars so scripts can pick them up
        case "$base" in
            monthly_picks_flask)
                MONTHLY_PICKS_PORT=${MONTHLY_PICKS_PORT:-8052} nohup python3 "$script" > "$log_file" 2>&1 &
                ;;
            weekly_picks_flask)
                WEEKLY_PICKS_PORT=${WEEKLY_PICKS_PORT:-8053} nohup python3 "$script" > "$log_file" 2>&1 &
                ;;
            *)
                nohup python3 "$script" > "$log_file" 2>&1 &
                ;;
        esac
    else
        echo -e "  ${RED}✗ Error: Script for ${name} ('${script}') not found. Skipping.${NC}"
    fi
done

echo -e "\n  Waiting for services to initialize..."

# --- Step 4: Verify Services with Health Check Polling (Sprint 2 Enhancement) ---
echo -e "\n${YELLOW}▶ Step 4: Verifying services are responsive (polling health endpoints)...${NC}"
all_ok=true
MAX_RETRIES=30
RETRY_DELAY=2

for name in "${!SERVICES[@]}"; do
    IFS=':' read -r script port <<< "${SERVICES[$name]}"
    
    # Try health check endpoint first, fall back to root
    health_url="http://localhost:${port}/health"
    root_url="http://localhost:${port}"
    
    retry_count=0
    service_up=false
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        # Try health endpoint first
        if curl --output /dev/null --silent --fail "$health_url" 2>/dev/null; then
            echo -e "  ${GREEN}✓ ${name} (port ${port}) is UP (health check passed)${NC}"
            service_up=true
            break
        # Fall back to root endpoint
        elif curl --output /dev/null --silent --head --fail "$root_url" 2>/dev/null; then
            echo -e "  ${GREEN}✓ ${name} (port ${port}) is UP${NC}"
            service_up=true
            break
        fi
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $MAX_RETRIES ]; then
            sleep $RETRY_DELAY
        fi
    done
    
    if [ "$service_up" = false ]; then
        echo -e "  ${RED}✗ ${name} (port ${port}) is DOWN after ${MAX_RETRIES} attempts${NC}"
        all_ok=false
    fi
done

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
if [ "$all_ok" = true ]; then
    echo -e "${GREEN}  🎉 All services started successfully!${NC}"
else
    echo -e "${RED}  🔥 Some services failed to start. Check logs in logs/*.log${NC}"
fi
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${GREEN}Access the dashboards:${NC}"
echo -e "  • API Gateway:         ${YELLOW}http://localhost:8049${NC}"
echo -e "  • API Gateway Health:  ${YELLOW}http://localhost:8049/health${NC}"
echo -e "  • Financial Dashboard: ${YELLOW}http://localhost:8000${NC}"
echo -e "  • Market Trends API:   ${YELLOW}http://localhost:8050${NC}"
echo -e "  • Options Service:     ${YELLOW}http://localhost:8060${NC}"
echo -e "  • Options API Docs:    ${YELLOW}http://localhost:8060/docs${NC}"
echo -e "  • Monthly Picks:       ${YELLOW}http://localhost:${MONTHLY_PICKS_PORT}${NC}"
echo -e "  • Weekly Picks:        ${YELLOW}http://localhost:${WEEKLY_PICKS_PORT}${NC}"

echo -e "\nTo view logs:"
echo "  tail -f logs/*.log"

echo -e "\nTo stop all services:"
echo "  pkill -f 'api_gateway.py|market_trends_service.py|integrated_dashboard.py'"
echo ""