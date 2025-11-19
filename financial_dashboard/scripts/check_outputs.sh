#!/usr/bin/env bash
# Simple check script: prints latest regime_pred JSON path and its sha256
set -e
BASE_DIR="$(dirname "$(dirname "$0")")"
OUT_DIR="$BASE_DIR/output/market_trends"
if [ ! -d "$OUT_DIR" ]; then
  echo "No output dir: $OUT_DIR"
  exit 1
fi
LATEST=$(ls -1 "$OUT_DIR" | grep '^regime_pred_' | tail -n1)
if [ -z "$LATEST" ]; then
  echo "No regime_pred files found in $OUT_DIR"
  exit 1
fi
FULLPATH="$OUT_DIR/$LATEST"
echo "Latest file: $FULLPATH"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$FULLPATH"
else
  sha256 "$FULLPATH" || true
fi
# Optional curl test: print first 10 lines
echo "--- preview ---"
head -n 20 "$FULLPATH"
