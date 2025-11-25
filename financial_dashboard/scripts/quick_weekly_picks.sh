#!/usr/bin/env bash
# =============================================================================
# Quick Weekly Picks Generator (uses existing data)
# =============================================================================
# This script generates picks from already-fetched data.
# Use this when you've already run the full pipeline and just want to
# regenerate picks with different parameters.
#
# Usage:
#   bash scripts/quick_weekly_picks.sh [TOP_K]
#   
# Example:
#   bash scripts/quick_weekly_picks.sh 30
#
# For a full data refresh, use: scripts/run_weekly_picks_production.sh
# =============================================================================

set -e

TOP_K=${1:-20}
DATE=$(date +%Y%m%d)
BASE_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "==================================================================="
echo "Quick Weekly Picks Generator"
echo "==================================================================="
echo "Top K: $TOP_K"
echo "Using latest enriched features file"
echo ""

# Find most recent enriched features with Alpaca prices
FEATURES_FILE=$(ls -t "$BASE_DIR/data"/weekly_enriched_with_alpaca_prices*.parquet 2>/dev/null | head -1)

if [ -z "$FEATURES_FILE" ]; then
    echo "ERROR: No enriched features file found!"
    echo "Please run the full pipeline first:"
    echo "  bash scripts/run_weekly_picks_production.sh"
    exit 1
fi

echo "Using features: $(basename $FEATURES_FILE)"
echo ""

python3 "$BASE_DIR/scripts/train_or_update_weekly.py" \
    --top-k "$TOP_K" \
    --features "$FEATURES_FILE" \
    --date "$DATE"

echo ""
echo "==================================================================="
echo "✅ Picks generated successfully"
echo "==================================================================="
echo ""
echo "Output: models/weekly_run/weeklypicks${DATE: -4}.csv"
echo ""
echo "Preview:"
python3 - << 'PY'
import pandas as pd
import sys
df = pd.read_csv('models/weekly_run/weeklypicks' + sys.argv[1][-4:] + '.csv')
print(df[['ticker','last_price','market_cap','pred_mean','liquidity_flag']].head(10).to_string(index=False))
PY

echo ""
