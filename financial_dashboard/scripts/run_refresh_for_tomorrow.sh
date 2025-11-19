#!/usr/bin/env bash
# Run the refresh_week_start_prices.py script and write output for tomorrow's date
set -euo pipefail
BASE_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$BASE_DIR"

TOMORROW=$(date -d 'tomorrow' +%Y%m%d)
OUT="data/weekly_weekstart_${TOMORROW}.json"

echo "Refreshing week-start prices and writing to $OUT"
python3 scripts/refresh_week_start_prices.py --picks models/weekly_run/weeklypicks_latest.csv --out "$OUT"

echo "Done: $OUT"
