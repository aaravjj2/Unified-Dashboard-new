#!/usr/bin/env bash
# Wrapper to place weekly orders with env loaded from scripts/weekly_picks.env
set -euo pipefail
ENV_FILE="$(dirname "${BASH_SOURCE[0]}")/weekly_picks.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file $ENV_FILE not found. Copy weekly_picks.env.template -> weekly_picks.env and edit." >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

PYTHON=/usr/bin/python3
if [[ "$EXECUTE" == "1" ]]; then
  EXEC_FLAG="--execute"
else
  EXEC_FLAG=""
fi
$PYTHON "${DASH_ROOT}/scripts/place_alpaca_orders_for_picks.py" --picks "$OUT_FILE" $EXEC_FLAG --account "$ACCOUNT" >> "$LOG_FILE" 2>&1
