#!/bin/bash
# Start or restart the Portfolio Dashboard (portfolio_app.py)
# Behavior:
#  - Kill any existing portfolio_app processes
#  - Prefer gunicorn (if available) -> waitress-serve -> fallback to python3
#  - Write logs to logs/portfolio_app.log
#  - Verify HTTP health on port 8056

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/portfolio_app.log"

PORT=8056
APP_MODULE="portfolio_app:server" # gunicorn expects module:object if the app exposes `server`
APP_PY="$ROOT_DIR/portfolio_app.py"

echo "Stopping any existing portfolio processes..."
pkill -f "portfolio_app.py" || true
sleep 1

start_with_gunicorn() {
    if command -v gunicorn >/dev/null 2>&1; then
        echo "Starting with gunicorn..."
        # Use 2 workers by default; bind to 0.0.0.0:PORT
        gunicorn --workers 2 --bind 0.0.0.0:${PORT} "${APP_MODULE}" --log-file "${LOG_FILE}" --capture-output --log-level info &
        return 0
    fi
    return 1
}

start_with_waitress() {
    if python3 -c "import waitress" >/dev/null 2>&1; then
        echo "Starting with waitress..."
        nohup python3 - <<PY >/dev/null 2>&1 &
import waitress
from portfolio_app import server
waitress.serve(server, host='0.0.0.0', port=${PORT})
PY
        # Note: waitress writes to stdout/stderr; redirect via nohup wrapper above
        return 0
    fi
    return 1
}

start_with_dev() {
    echo "Starting with development server (python3)..."
    nohup python3 "$APP_PY" > "$LOG_FILE" 2>&1 &
}

echo "Choosing start method..."
if start_with_gunicorn; then
    echo "Launched via gunicorn (see ${LOG_FILE})"
elif start_with_waitress; then
    echo "Launched via waitress (logs may be in ${LOG_FILE})"
else
    start_with_dev
    echo "Launched via python dev server (see ${LOG_FILE})"
fi

echo "Waiting for service to respond on http://localhost:${PORT}..."
for i in {1..15}; do
    if curl --silent --fail "http://localhost:${PORT}" >/dev/null 2>&1; then
        echo "Service responded (attempt ${i})."
        exit 0
    else
        sleep 1
    fi
done

echo "Service did not respond after timeout. Check ${LOG_FILE} for details."
exit 2
