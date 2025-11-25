#!/bin/bash
# Launcher for all dashboards
# Usage: ./start_all_dashboards.sh

cd "$(dirname "$0")"

echo "🚀 Starting all dashboards..."

# Kill any existing dashboard processes
pkill -f "market_trends_dash.py"
pkill -f "weekly_picks_flask.py"
pkill -f "monthly_picks_flask.py"
sleep 1

# Start Market Trends (Dash) on port 8050
echo "Starting Market Trends Dashboard on port 8050..."
python3 market_trends_dash.py > /tmp/market_trends.log 2>&1 &
TRENDS_PID=$!

# Start Weekly Picks (Flask) on port 8053
echo "Starting Weekly Picks Dashboard on port 8053..."
python3 weekly_picks_flask.py > /tmp/weekly_picks.log 2>&1 &
WEEKLY_PID=$!

# Start Monthly Picks (Flask) on port 8052
echo "Starting Monthly Picks Dashboard on port 8052..."
python3 monthly_picks_flask.py > /tmp/monthly_picks.log 2>&1 &
MONTHLY_PID=$!

sleep 3

echo ""
echo "✅ Dashboards started:"
echo "   Market Trends: http://localhost:8050 (PID: $TRENDS_PID)"
echo "   Weekly Picks:  http://localhost:8053 (PID: $WEEKLY_PID)"
echo "   Monthly Picks: http://localhost:8052 (PID: $MONTHLY_PID)"
echo ""
echo "Checking status..."
ps aux | grep -E "(market_trends_dash|weekly_picks_flask|monthly_picks_flask)" | grep -v grep

echo ""
echo "📊 Dashboard URLs:"
echo "   http://localhost:8050  - Market Trends (interactive analysis)"
echo "   http://localhost:8053  - Weekly Picks (50 stocks)"
echo "   http://localhost:8052  - Monthly Picks (25 stocks)"
