#!/bin/bash

# Financial Dashboard Startup Script
# This script starts the dashboard following the core steps from the documentation

echo "🚀 Starting Financial Dashboard..."

# Step 1: Check Python version
echo "📋 Step 1: Checking Python environment..."
python_version=$(/usr/bin/python3 --version)
echo "✅ Python version: $python_version"

# Step 2: Set environment variables
echo "📋 Step 2: Setting environment variables..."
export DASH_DEBUG=true
export DASH_TEST_SSR=false
export DASH_PORT=8051
export PORT=8051
echo "✅ Environment variables set (Debug: $DASH_DEBUG, Port: $DASH_PORT)"

# Step 3: Check if dependencies are installed
echo "📋 Step 3: Checking dependencies..."
if /usr/bin/python3 -c "import dash, flask, dash_bootstrap_components, psycopg2" 2>/dev/null; then
    echo "✅ All dependencies are installed"
else
    echo "❌ Missing dependencies. Installing..."
    pip3 install -r requirements.txt psycopg2-binary
fi

# Step 4: Start the dashboard server
echo "📋 Step 4: Starting dashboard server..."
echo "🌐 Dashboard will be available at: http://localhost:$DASH_PORT"
echo "🔧 Debug mode: $DASH_DEBUG"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo "=================================================="

# Run the dashboard
/usr/bin/python3 financial_dashboard/app.py