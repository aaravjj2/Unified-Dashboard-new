#!/bin/bash#!/bin/bash

# ==============================================================================# ==============================================================================

# Master Shutdown Script for Unified Financial Dashboard# Master Shutdown Script for Unified Financial Dashboard

# ==============================================================================# ==============================================================================

# This script gracefully stops all dashboard services using PID tracking.# Sprint 2 Enhancement: Uses PID tracking for precise, graceful shutdown.

## ==============================================================================

# Features:

# - PID-based process termination# Colors

# - Graceful shutdown (SIGTERM) with fallback to force kill (SIGKILL)GREEN='\033[0;32m'

# - Verification that all processes have terminatedRED='\033[0;31m'

# - Clean PID file removalYELLOW='\033[1;33m'

#BLUE='\033[0;34m'

# Usage:NC='\033[0m'

#   From the project root directory (Dash/), run:

#   ./stop_all.shecho -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"

# ==============================================================================echo -e "${BLUE}          🛑 Stopping Unified Financial Dashboard Services          ${NC}"

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"

# Exit immediately if a command exits with a non-zero status.

set -ecd "$(dirname "$0")"

mkdir -p pids

# Colors for output

GREEN='\033[0;32m'declare -A SERVICES

RED='\033[0;31m'SERVICES=(

YELLOW='\033[1;33m'    ["API Gateway"]="api_gateway.py"

BLUE='\033[0;34m'    ["Market Trends"]="services/market_trends_service.py"

NC='\033[0;m' # No Color    ["Market Forecast"]="services/market_forecast_service.py"

    ["Analysis Hub"]="services/analysis_service.py"

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"    ["Portfolio"]="services/portfolio_service.py"

echo -e "${BLUE}          🛑 Stopping Unified Financial Dashboard Services          ${NC}"    ["Research Lab"]="services/research_lab_service.py"

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"    ["Options Service"]="options_service.py"

    ["Dashboard"]="integrated_dashboard.py"

# Navigate to the script's directory to ensure correct paths    ["Monthly Picks"]="monthly_picks_flask.py"

cd "$(dirname "$0")"    ["Weekly Picks"]="weekly_picks_flask.py"

)

# PID directory

PID_DIR="pids"echo -e "\n${YELLOW}▶ Stopping services...${NC}"

stopped=0

# Service patterns to match if PID files don't existnot_found=0

SERVICE_PATTERNS=(

    "api_gateway.py"for name in "${!SERVICES[@]}"; do

    "market_trends_service.py"    script="${SERVICES[$name]}"

    "market_forecast_service.py"    pid_file="pids/$(basename "$script" .py).pid"

    "analysis_service.py"    

    "portfolio_service.py"    if [ -f "$pid_file" ]; then

    "research_lab_service.py"        pid=$(cat "$pid_file")

    "options_service.py"        if ps -p "$pid" > /dev/null 2>&1; then

    "integrated_dashboard.py"            kill "$pid" 2>/dev/null

    "unified_dashboard.py"            sleep 2

    "market_trends_dash.py"            if ps -p "$pid" > /dev/null 2>&1; then

    "analysis_app.py"                kill -9 "$pid" 2>/dev/null

    "monthly_picks_flask.py"                echo -e "  ${YELLOW}⚠ ${name} (PID ${pid}) force killed${NC}"

    "weekly_picks_flask.py"            else

)                echo -e "  ${GREEN}✓ ${name} (PID ${pid}) stopped${NC}"

            fi

# --- Step 1: Stop Services Using PID Files ---            stopped=$((stopped + 1))

echo -e "\n${YELLOW}▶ Step 1: Stopping services using PID files...${NC}"        else

            echo -e "  ${YELLOW}⚠ ${name} - PID file exists but process not running${NC}"

stopped_count=0        fi

if [ -d "$PID_DIR" ] && [ "$(ls -A $PID_DIR 2>/dev/null)" ]; then        rm -f "$pid_file"

    for pid_file in "$PID_DIR"/*.pid; do    else

        if [ -f "$pid_file" ]; then        if pkill -f "$script" 2>/dev/null; then

            service_name=$(basename "$pid_file" .pid)            echo -e "  ${GREEN}✓ ${name} stopped (pkill fallback)${NC}"

            pid=$(cat "$pid_file")            stopped=$((stopped + 1))

                    else

            # Check if process is still running            echo -e "  ${YELLOW}○ ${name} not running${NC}"

            if ps -p "$pid" > /dev/null 2>&1; then            not_found=$((not_found + 1))

                echo "  • Stopping $service_name (PID: $pid)..."        fi

                    fi

                # Try graceful shutdown first (SIGTERM)done

                kill -TERM "$pid" 2>/dev/null || true

                echo -e "\n${GREEN}Stopped: ${stopped} | Not running: ${not_found}${NC}"

                # Wait up to 5 seconds for graceful shutdownecho -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}\n"

                for i in {1..5}; do
                    if ! ps -p "$pid" > /dev/null 2>&1; then
                        echo -e "    ${GREEN}✓ $service_name stopped gracefully${NC}"
                        stopped_count=$((stopped_count + 1))
                        rm -f "$pid_file"
                        break
                    fi
                    sleep 1
                done
                
                # Force kill if still running
                if ps -p "$pid" > /dev/null 2>&1; then
                    echo "    ⚠ Force killing $service_name..."
                    kill -9 "$pid" 2>/dev/null || true
                    sleep 1
                    if ! ps -p "$pid" > /dev/null 2>&1; then
                        echo -e "    ${GREEN}✓ $service_name force killed${NC}"
                        stopped_count=$((stopped_count + 1))
                    else
                        echo -e "    ${RED}✗ Failed to kill $service_name${NC}"
                    fi
                    rm -f "$pid_file"
                fi
            else
                echo "  • $service_name (PID: $pid) not running, removing stale PID file"
                rm -f "$pid_file"
            fi
        fi
    done
else
    echo -e "  ${YELLOW}ℹ No PID files found in $PID_DIR${NC}"
fi

# --- Step 2: Fallback - Find and Stop by Process Pattern ---
echo -e "\n${YELLOW}▶ Step 2: Checking for any remaining dashboard processes...${NC}"

# Build grep pattern
pattern=$(IFS='|'; echo "${SERVICE_PATTERNS[*]}")

PIDS=$(ps aux | grep -E "($pattern)" | grep -v grep | awk '{print $2}')

if [ -n "$PIDS" ]; then
    echo "  Found additional processes: $PIDS"
    
    for pid in $PIDS; do
        process_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
        echo "  • Stopping $process_name (PID: $pid)..."
        
        # Try graceful shutdown first
        kill -TERM "$pid" 2>/dev/null || true
        sleep 1
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null || true
            echo -e "    ${GREEN}✓ Process $pid force killed${NC}"
        else
            echo -e "    ${GREEN}✓ Process $pid stopped${NC}"
        fi
        stopped_count=$((stopped_count + 1))
    done
else
    echo -e "  ${GREEN}✓ No additional dashboard processes found${NC}"
fi

# --- Step 3: Clean Up PID Directory ---
echo -e "\n${YELLOW}▶ Step 3: Cleaning up PID directory...${NC}"

if [ -d "$PID_DIR" ]; then
    rm -rf "$PID_DIR"/*.pid 2>/dev/null || true
    echo -e "  ${GREEN}✓ PID files cleaned${NC}"
fi

# --- Step 4: Verify All Services Stopped ---
echo -e "\n${YELLOW}▶ Step 4: Verifying all services stopped...${NC}"

remaining_pids=$(ps aux | grep -E "($pattern)" | grep -v grep | awk '{print $2}')

if [ -z "$remaining_pids" ]; then
    echo -e "  ${GREEN}✓ All dashboard services successfully stopped${NC}"
else
    echo -e "  ${RED}✗ Warning: Some processes may still be running:${NC}"
    ps aux | grep -E "($pattern)" | grep -v grep
fi

# --- Summary ---
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
if [ -z "$remaining_pids" ]; then
    echo -e "${GREEN}  🎉 Shutdown complete! Stopped $stopped_count service(s).${NC}"
else
    echo -e "${YELLOW}  ⚠ Shutdown mostly complete. $stopped_count service(s) stopped.${NC}"
    echo -e "${YELLOW}    Check remaining processes manually if needed.${NC}"
fi
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
echo ""
