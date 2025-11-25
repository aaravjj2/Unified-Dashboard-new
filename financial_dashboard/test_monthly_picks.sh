#!/bin/bash
# Test Monthly Picks Generation with Enhanced Data
# This script runs the monthly picks analysis and validates the output

echo "=================================================="
echo "Monthly Picks Generator - Enhanced Version"
echo "=================================================="
echo ""

cd /mnt/c/Aarav/fin_env/Dash

echo "Starting analysis at $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Run the monthly picks generator
python3 run_monthly_picks.py

echo ""
echo "=================================================="
echo "Validating Output"
echo "=================================================="

# Find the latest CSV
LATEST_CSV=$(ls -t models/full_run/picks_*.csv 2>/dev/null | head -1)

if [ -z "$LATEST_CSV" ]; then
    echo "❌ ERROR: No output CSV found!"
    exit 1
fi

echo "✅ Found output: $LATEST_CSV"
echo ""

# Check CSV content
echo "📊 CSV Statistics:"
echo "-------------------"
LINES=$(wc -l < "$LATEST_CSV")
echo "  Total lines: $LINES"

# Show header
echo ""
echo "📋 Columns:"
echo "-------------------"
head -1 "$LATEST_CSV" | tr ',' '\n' | nl

# Show top 5 picks
echo ""
echo "🏆 Top 5 Picks Preview:"
echo "-------------------"
head -6 "$LATEST_CSV" | column -t -s','

# Validate key columns exist
echo ""
echo "✅ Column Validation:"
echo "-------------------"
HEADER=$(head -1 "$LATEST_CSV")

check_column() {
    if echo "$HEADER" | grep -q "$1"; then
        echo "  ✅ $1"
        return 0
    else
        echo "  ❌ MISSING: $1"
        return 1
    fi
}

ERRORS=0
check_column "rank" || ERRORS=$((ERRORS + 1))
check_column "ticker" || ERRORS=$((ERRORS + 1))
check_column "composite" || ERRORS=$((ERRORS + 1))
check_column "price" || ERRORS=$((ERRORS + 1))
check_column "rsi" || ERRORS=$((ERRORS + 1))
check_column "beta" || ERRORS=$((ERRORS + 1))
check_column "vol_surge" || ERRORS=$((ERRORS + 1))

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All required columns present!"
    echo ""
    echo "🎉 Monthly picks generation SUCCESSFUL!"
    echo ""
    echo "View picks at: http://localhost:8052"
else
    echo "⚠️  Warning: $ERRORS required columns missing"
    exit 1
fi

echo ""
echo "=================================================="
