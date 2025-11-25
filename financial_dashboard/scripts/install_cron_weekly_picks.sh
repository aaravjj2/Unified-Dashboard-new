#!/usr/bin/env bash
# Install cron entries for weekly picks update and order wrappers.
# This registers jobs in the current user's crontab. No sudo required.

set -euo pipefail
REPO_ROOT="/mnt/c/Aarav/fin_env/Dash"
UPDATE_SCRIPT="$REPO_ROOT/scripts/run_weekly_update.sh"
ORDER_SCRIPT="$REPO_ROOT/scripts/run_weekly_order.sh"
LOGFILE="$REPO_ROOT/dashboard.log"

# Cron lines (runs Monday 09:30 and 09:31 America/New_York)
# Cron on many systems does not support TZ per job; we'll wrap with 'TZ=America/New_York' at top of crontab.
CRONJOB="TZ=America/New_York\n30 9 * * 1 $UPDATE_SCRIPT >> $LOGFILE 2>&1\n31 9 * * 1 $ORDER_SCRIPT >> $LOGFILE 2>&1\n"

# Write out existing crontab then add our lines if not present
TMPCRON=$(mktemp)
crontab -l 2>/dev/null || true > "$TMPCRON"
if grep -Fq "$UPDATE_SCRIPT" "$TMPCRON"; then
  echo "Cron already contains update job; skipping"
else
  printf "%s\n" "$CRONJOB" >> "$TMPCRON"
  crontab "$TMPCRON"
  echo "Installed cron jobs. Use 'crontab -l' to verify." 
fi
rm -f "$TMPCRON"
