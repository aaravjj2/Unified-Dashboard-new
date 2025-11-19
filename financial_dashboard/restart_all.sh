#!/bin/bash
# Quick restart script for unified dashboard
cd /mnt/c/Aarav/fin_env/Dash

echo "🛑 Stopping all services..."
pkill -f market_trends_dash.py
pkill -f market_forecast_app.py
pkill -f monthly_picks_flask.py
pkill -f weekly_picks_flask.py
pkill -f analysis_app.py
pkill -f unified_dashboard.py
sleep 2

echo "🚀 Starting all services..."
./start_all.sh
