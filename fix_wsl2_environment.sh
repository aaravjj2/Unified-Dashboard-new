#!/bin/bash
#
# Fix WSL2 Environment - Reinstall packages in native filesystem
# Run with: bash fix_wsl2_environment.sh
#

set -e  # Exit on error

echo "================================"
echo "WSL2 Environment Fix Script"
echo "================================"
echo ""

# Check if we're in WSL2
if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be WSL2"
    echo "This script is designed for WSL2 environments"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📍 Current location: $(pwd)"
echo "🐍 Current Python: $(which python3)"
echo ""

# Navigate to project root
cd ~/unified-dashboard || {
    echo "❌ ERROR: ~/unified-dashboard not found"
    echo "Please navigate to your project directory first"
    exit 1
}

echo "✓ Found project directory: $(pwd)"
echo ""

# Check if .venv_wsl2 already exists
if [ -d ".venv_wsl2" ]; then
    echo "⚠️  .venv_wsl2 already exists"
    read -p "Delete and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing old .venv_wsl2..."
        rm -rf .venv_wsl2
    else
        echo "ℹ️  Using existing .venv_wsl2"
        source .venv_wsl2/bin/activate
        echo "✓ Activated existing environment"
        echo "🐍 Python: $(which python3)"
        exit 0
    fi
fi

echo "📦 Creating new WSL2-native virtual environment..."
python3 -m venv .venv_wsl2

echo "🔄 Activating environment..."
source .venv_wsl2/bin/activate

echo "📈 Upgrading pip..."
pip install --upgrade pip --quiet

echo "📚 Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✓ Requirements installed"
else
    echo "⚠️  requirements.txt not found, installing core packages..."
    pip install dash dash-bootstrap-components pandas numpy plotly flask
fi

echo ""
echo "================================"
echo "🧪 Running Validation Tests"
echo "================================"
echo ""

# Test pandas
echo "Testing pandas import..."
if python3 -c "import pandas as pd; print('✓ Pandas OK')" 2>&1; then
    echo "✅ Pandas works!"
else
    echo "❌ Pandas still failing"
    exit 1
fi

# Test dash
echo "Testing dash import..."
if timeout 5 python3 -c "from dash import Dash; print('✓ Dash OK')" 2>&1; then
    echo "✅ Dash works!"
else
    echo "❌ Dash still failing"
    exit 1
fi

# Test dashboard imports
echo "Testing dashboard imports..."
if timeout 10 python3 -c "
import sys
sys.path.insert(0, 'financial_dashboard')
from layout_placeholders import get_all_placeholders
print('✓ Dashboard imports OK')
" 2>&1; then
    echo "✅ Dashboard imports work!"
else
    echo "❌ Dashboard imports failing"
    exit 1
fi

echo ""
echo "================================"
echo "✅ Environment Fix Complete!"
echo "================================"
echo ""
echo "Your new Python environment:"
echo "  Location: $(pwd)/.venv_wsl2"
echo "  Python: $(which python3)"
echo "  Version: $(python3 --version)"
echo ""
echo "To use this environment in the future:"
echo "  $ source ~/.bashrc"
echo "  $ cd ~/unified-dashboard"
echo "  $ source .venv_wsl2/bin/activate"
echo ""
echo "To start the dashboard:"
echo "  $ python3 -u financial_dashboard/index.py"
echo ""
echo "The dashboard will be available at:"
echo "  http://localhost:8050"
echo ""
