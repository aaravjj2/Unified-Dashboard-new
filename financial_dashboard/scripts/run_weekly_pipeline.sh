#!/bin/bash

# ==============================================================================
# Weekly Stock Picking Pipeline Runner
# ==============================================================================
# This script executes the consolidated weekly pipeline script.
#
# Usage:
#   From the project root directory (Dash/), run:
#   bash scripts/run_weekly_pipeline.sh
#
# All configuration is handled via arguments to the Python script.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
UNIVERSE_FILE="Weekly ticker list.csv"
TOP_K=50

# --- Pipeline Steps ---

echo "--- Executing Consolidated Weekly Pipeline ---"
python3 scripts/train_or_update_weekly.py \
  --universe-file "$UNIVERSE_FILE" \
  --no-mock-data \
  --train-model \
  --top-k "$TOP_K"

echo "--- ✅ Weekly pipeline completed successfully! ---"
