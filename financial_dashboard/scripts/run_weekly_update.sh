#!/usr/bin/env bash
# Wrapper to run weekly update with env loaded from scripts/weekly_picks.env
set -euo pipefail
ENV_FILE="$(dirname "${BASH_SOURCE[0]}")/weekly_picks.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file $ENV_FILE not found. Copy weekly_picks.env.template -> weekly_picks.env and edit." >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

PYTHON=/usr/bin/python3
$PYTHON "${DASH_ROOT}/scripts/update_week_start_price_and_refresh_picks.py" --picks "$PICKS_FILE" --features "$FEATURES_FILE" --out "$OUT_FILE" >> "$LOG_FILE" 2>&1
