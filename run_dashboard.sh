#!/bin/bash
# ============================================================================
# Dashboard Runner - Starts the unified financial dashboard properly
# ============================================================================

set -e

cd "$(dirname "$0")"

echo "🚀 Starting Financial Dashboard..."
echo "📍 Port: 8051"
echo "📂 Working directory: $(pwd)"

# Run Python as a module to fix import paths
python3 -m financial_dashboard.app > dashboard_runner.log 2>&1 &
PID=$!

echo "✅ Dashboard started with PID: $PID"
echo "📝 Logs: dashboard_runner.log"
echo ""
echo "Waiting 5 seconds for initialization..."
sleep 5

if ps -p $PID > /dev/null; then
    echo "✅ Dashboard is running!"
    echo "🌐 Open: http://localhost:8051"
else
    echo "❌ Dashboard failed to start. Check dashboard_runner.log"
    tail -20 dashboard_runner.log
    exit 1
fi
