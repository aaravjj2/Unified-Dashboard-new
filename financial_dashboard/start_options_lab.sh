#!/bin/bash

# Quick Start Script for Options Lab Standalone
# Starts the Options Lab on port 8060

echo "═══════════════════════════════════════════════════════════════"
echo "    Options Lab - Standalone Application"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if port 8060 is already in use
if lsof -Pi :8060 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8060 is already in use. Stopping existing service..."
    pkill -f options_lab_standalone
    sleep 2
fi

# Start the application
echo "🚀 Starting Options Lab Standalone..."
cd "$(dirname "$0")"

# Run in background
nohup python3 options_lab_standalone.py > /tmp/options_lab.log 2>&1 &
PID=$!

# Wait for startup
echo "⏳ Waiting for service to start..."
sleep 4

# Check if it's running
if ps -p $PID > /dev/null; then
    echo ""
    echo "✅ Options Lab is running!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  📊 Web UI:        http://localhost:8060"
    echo "  📖 API Docs:      http://localhost:8060/docs"
    echo "  🏥 Health Check:  http://localhost:8060/health"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Mode: PAPER TRADING (No real money)"
    echo "  PID: $PID"
    echo "  Log: /tmp/options_lab.log"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "To stop: pkill -f options_lab_standalone"
    echo "To view logs: tail -f /tmp/options_lab.log"
    echo ""
else
    echo ""
    echo "❌ Failed to start Options Lab"
    echo "Check logs: tail -50 /tmp/options_lab.log"
    exit 1
fi
