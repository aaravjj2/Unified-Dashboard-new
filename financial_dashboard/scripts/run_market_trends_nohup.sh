#!/bin/bash
# Starts the market trends Dash app in the background using nohup.
# Logs are written to Dash/nohup_market_trends.log
set -e
ROOT_DIR=$(dirname "$(dirname "$0")")
cd "$ROOT_DIR"
mkdir -p Dash
nohup python3 -u Dash/run_market_trends_dash.py > Dash/nohup_market_trends.log 2>&1 &
echo $! > Dash/run_market_trends.pid
echo "Started market trends dash (nohup) with PID $(cat Dash/run_market_trends.pid)"
