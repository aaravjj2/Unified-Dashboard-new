#!/bin/bash
# React Error Fix Startup Script

echo "🔧 Applying React error fixes..."

# Set environment variables
export DASH_TEST_SSR=false
export DASH_DEBUG=true
export REACT_APP_DISABLE_SSR=true
export DASH_SUPPRESS_CALLBACK_EXCEPTIONS=true

echo "✅ Environment variables set"

# Start dashboard with fixes applied
echo "🚀 Starting dashboard with React error fixes..."
python3 financial_dashboard/index.py
