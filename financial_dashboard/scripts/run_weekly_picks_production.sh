#!/usr/bin/env bash
# =============================================================================
# Weekly Stock Picks Production Pipeline
# =============================================================================
# This script runs the complete weekly stock picking pipeline:
# 1. Fetch headlines, quotes, and historical data using Finnhub + Alpaca
# 2. Compute technical features using yfinance
# 3. Merge Alpaca prices/market caps into features
# 4. Generate top-K stock picks with trade sizing and risk metrics
#
# Usage:
#   bash scripts/run_weekly_picks_production.sh [TOP_K]
#   
# Example:
#   bash scripts/run_weekly_picks_production.sh 20
#
# Output:
#   models/weekly_run/weeklypicks{MMDD}.csv
#   models/weekly_run/weekly_meta_{YYYYMMDD}.json
# =============================================================================

set -e  # Exit on error

# Configuration
TOP_K=${1:-20}  # Default to top 20 picks
DATE=$(date +%Y%m%d)
UNIVERSE_FILE="Weekly ticker list.csv"
BASE_DIR=$(cd "$(dirname "$0")/.." && pwd)
DATA_DIR="$BASE_DIR/data"
SCRIPTS_DIR="$BASE_DIR/scripts"
OUT_DIR="$BASE_DIR/models/weekly_run"

# Ensure output directory exists
mkdir -p "$OUT_DIR"
mkdir -p "$DATA_DIR"

# Load API keys from keys.env if present
if [ -f "$BASE_DIR/keys.env" ]; then
    echo "Loading API keys from keys.env..."
    set -a
    source "$BASE_DIR/keys.env"
    set +a
else
    echo "Warning: keys.env not found. Some API calls may fail."
fi

echo "======================================================================="
echo "WEEKLY STOCK PICKS PRODUCTION PIPELINE"
echo "======================================================================="
echo "Date: $DATE"
echo "Top K: $TOP_K"
echo "Universe: $UNIVERSE_FILE"
echo "Output: $OUT_DIR/weeklypicks${DATE: -4}.csv"
echo "======================================================================="
echo ""

# =============================================================================
# STEP 1: Fetch Headlines and Market Data (Finnhub + Alpaca)
# =============================================================================
echo "[1/4] Fetching headlines, quotes, and historical data..."
echo "  - Using Finnhub API (2 keys, parallel)"
echo "  - Using Alpaca for historicals (200/min)"
echo ""

python3 "$SCRIPTS_DIR/fetch_headlines_sdk_full.py" \
    --tickers-file "$BASE_DIR/$UNIVERSE_FILE" \
    --out "$DATA_DIR/weekly_headlines_sdk_${DATE}.parquet" \
    --parallel 2 \
    --use-alpaca \
    --sleep 0.3 \
    --days 30

if [ $? -ne 0 ]; then
    echo "ERROR: Headline fetch failed!"
    exit 1
fi

echo ""
echo "  ✓ Headlines and market data fetched successfully"
echo ""

# =============================================================================
# STEP 2: Compute Technical Features (yfinance)
# =============================================================================
echo "[2/4] Computing technical features using yfinance..."
echo "  - Features: returns, volatility, RSI, ATR, moving averages"
echo "  - Note: Some tickers may fail if delisted/no data available"
echo ""

# Run enrichment but don't fail if some tickers error out
python3 "$SCRIPTS_DIR/enrich_weekly_features.py" \
    --tickers-file "$BASE_DIR/$UNIVERSE_FILE" \
    --out "$DATA_DIR/weekly_enriched_${DATE}.parquet" \
    --sleep 0.5 \
    --cache-dir "$DATA_DIR/weekly_enriched_cache" \
    || echo "Warning: Some tickers failed enrichment (this is normal for delisted/OTC stocks)"

# Check if enrichment produced output
if [ ! -f "$DATA_DIR/weekly_enriched_${DATE}.parquet" ]; then
    # If fresh enrichment failed, try to use most recent enriched file
    echo "  ⚠ Fresh enrichment incomplete, using most recent enriched file..."
    LATEST_ENRICHED=$(ls -t "$DATA_DIR"/weekly_enriched*.parquet 2>/dev/null | head -1)
    if [ -n "$LATEST_ENRICHED" ]; then
        cp "$LATEST_ENRICHED" "$DATA_DIR/weekly_enriched_${DATE}.parquet"
        echo "  ✓ Using: $LATEST_ENRICHED"
    else
        echo "ERROR: No enriched features file available!"
        exit 1
    fi
fi

echo ""
echo "  ✓ Technical features computed"
echo ""

# =============================================================================
# STEP 3: Merge Alpaca Prices and Market Caps
# =============================================================================
echo "[3/4] Merging Alpaca prices and market caps into features..."
echo ""

python3 - "$DATE" << 'PY_MERGE'
import pandas as pd
from pathlib import Path
import sys

base = Path('.')
date = sys.argv[1] if len(sys.argv) > 1 else ''

# Load enriched features
feat_file = base / 'data' / f'weekly_enriched_{date}.parquet'
if not feat_file.exists():
    print(f"ERROR: Features file not found: {feat_file}")
    sys.exit(1)

feat = pd.read_parquet(feat_file)
print(f"Loaded {len(feat)} enriched features")

# Load Alpaca headlines
head_file = base / 'data' / f'weekly_headlines_sdk_{date}.parquet'
if not head_file.exists():
    print(f"ERROR: Headlines file not found: {head_file}")
    sys.exit(1)

head = pd.read_parquet(head_file)
print(f"Loaded {len(head)} headlines with prices/caps")

# Normalize tickers
feat['ticker'] = feat['ticker'].astype(str).str.strip()
head['ticker'] = head['ticker'].astype(str).str.strip()

# Merge prices and market caps
for col in ['last_price', 'market_cap']:
    if col in head.columns:
        map_series = head.set_index('ticker')[col]
        if col not in feat.columns:
            feat[col] = feat['ticker'].map(map_series)
            print(f"Created column: {col}")
        else:
            # Update with Alpaca values where available
            feat[col] = feat['ticker'].map(map_series).fillna(feat[col])
            print(f"Updated column: {col}")

# Write merged features
out_file = base / 'data' / f'weekly_enriched_with_alpaca_prices_{date}.parquet'
feat.to_parquet(out_file, index=False)
print(f"✓ Wrote merged features: {out_file} ({len(feat)} rows)")
PY_MERGE

if [ $? -ne 0 ]; then
    echo "ERROR: Merge failed!"
    exit 1
fi

echo ""
echo "  ✓ Alpaca prices and market caps merged"
echo ""

# =============================================================================
# STEP 4: Generate Stock Picks
# =============================================================================
echo "[4/4] Generating top $TOP_K stock picks..."
echo ""

python3 "$SCRIPTS_DIR/train_or_update_weekly.py" \
    --top-k "$TOP_K" \
    --features "$DATA_DIR/weekly_enriched_with_alpaca_prices_${DATE}.parquet" \
    --date "$DATE"

if [ $? -ne 0 ]; then
    echo "ERROR: Pick generation failed!"
    exit 1
fi

echo ""
echo "======================================================================="
echo "✅ PIPELINE COMPLETED SUCCESSFULLY"
echo "======================================================================="
echo ""
echo "Output files:"
echo "  - Picks: $OUT_DIR/weeklypicks${DATE: -4}.csv"
echo "  - Meta:  $OUT_DIR/weekly_meta_${DATE}.json"
echo ""
echo "Preview of top 10 picks:"
echo "-----------------------------------------------------------------------"
python3 - << 'PY_PREVIEW'
import pandas as pd
df = pd.read_csv('models/weekly_run/weeklypicks' + __import__('sys').argv[1][-4:] + '.csv')
print(df[['ticker','last_price','market_cap','avg_dollar_vol_3mo','pred_mean','liquidity_flag']].head(10).to_string(index=False))
PY_PREVIEW

echo "======================================================================="
echo ""
echo "To view full results:"
echo "  cat $OUT_DIR/weeklypicks${DATE: -4}.csv"
echo ""
