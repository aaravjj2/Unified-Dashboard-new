#!/bin/bash
# Phase 4 - One-Command Startup Script
# Starts all Phase 4 services and runs verification

echo "════════════════════════════════════════════════════════════════════════"
echo "  🚀 Phase 4 Market Portfolio Plan - Full Startup"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

cd /mnt/c/Aarav/fin_env/Dash

echo "Starting all services..."
echo ""

# Kill any existing instances
pkill -f "analysis_app.py" 2>/dev/null
pkill -f "portfolio_app.py" 2>/dev/null
pkill -f "event_monitor_app.py" 2>/dev/null
pkill -f "research_lab_app.py" 2>/dev/null
sleep 2

# Start services
echo "  • Starting Analysis Hub (port 8054)..."
python3 analysis_app.py > analysis_app.log 2>&1 &
sleep 2

echo "  • Starting Portfolio Dashboard (port 8056)..."
python3 portfolio_app.py > portfolio_app.log 2>&1 &
sleep 2

echo "  • Starting Event Monitor (port 8057)..."
python3 event_monitor_app.py > event_monitor_app.log 2>&1 &
sleep 2

echo "  • Starting Research Lab (port 8058)..."
python3 research_lab_app.py > research_lab_app.log 2>&1 &
sleep 3

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "  ✅ All Phase 4 Services Started"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Show running processes
echo "Running Services:"
ps aux | grep -E "(analysis_app|portfolio_app|event_monitor_app|research_lab_app)" | grep -v grep | awk '{printf "  • PID %-7s %-25s (CPU: %s%%, MEM: %sMB)\n", $2, $11, $3, int($6/1024)}'

echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo ""
echo "Access URLs:"
echo "  📊 Analysis Hub:       http://localhost:8054"
echo "  💼 Portfolio Dashboard: http://localhost:8056"
echo "  📰 Event Monitor:      http://localhost:8057"
echo "  🧪 Research Lab:       http://localhost:8058"
echo ""
echo "Features:"
echo "  Analysis Hub:"
echo "    • Attribution Analysis (Alpha/Beta breakdown)"
echo "    • Scenario Testing (Macro sensitivity)"
echo "    • Portfolio Optimization (Sharpe, Min Variance, Risk Parity)"
echo "    • Risk Analysis (VaR, CVaR, Drawdown)"
echo "    • Backtesting (Multiple strategies)"
echo "    • Correlation Analysis (Matrix, Rolling, Network)"
echo ""
echo "  Portfolio Dashboard:"
echo "    • Position tracking with P/L"
echo "    • Performance charts & sector attribution"
echo "    • Transaction upload & reconciliation"
echo "    • Real-time alerts"
echo ""
echo "  Event Monitor:"
echo "    • Real-time event feed"
echo "    • Severity-based alerts"
echo "    • Portfolio exposure tracking"
echo ""
echo "  Research Lab:"
echo "    • Experiment sandbox"
echo "    • Feature ablation testing"
echo "    • Model comparison"
echo "    • Artifact tracking & promotion"
echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo ""
echo "Quick Commands:"
echo "  • Verify services:  ./verify_phase4.sh"
echo "  • Run tests:        python3 test_phase4_comprehensive.py"
echo "  • Stop services:    pkill -f '_app.py'"
echo ""
echo "Logs:"
echo "  • Analysis Hub:     tail -f analysis_app.log"
echo "  • Portfolio:        tail -f portfolio_app.log"
echo "  • Event Monitor:    tail -f event_monitor_app.log"
echo "  • Research Lab:     tail -f research_lab_app.log"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "  🎉 Phase 4 Implementation Complete & Operational!"
echo "════════════════════════════════════════════════════════════════════════"
