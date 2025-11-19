#!/usr/bin/env bash
# doppler_run.sh
# Wrapper to run a command with Doppler secrets loaded into the environment.
# Usage:
#   ./doppler_run.sh --project my-project --config dev -- /path/to/python script.py --arg
# If no project/config provided, will try to use DOPPLER_PROJECT / DOPPLER_CONFIG env vars.

set -euo pipefail

show_help() {
  cat <<EOF
Usage: $0 [--project <project>] [--config <config>] -- <command...>

Runs the provided command with secrets injected from Doppler using 'doppler run'.
Requires 'doppler' CLI installed and authenticated.

Examples:
  ./doppler_run.sh --project my-project --config dev -- /usr/bin/python3 scripts/fetch_and_trade_weekly.py --target-count 20 --dry-run
  doppler_run.sh -- /usr/bin/python3 -m pip install requests
EOF
}

PROJECT="${DOPPLER_PROJECT:-}"
CONFIG="${DOPPLER_CONFIG:-}"

# Parse args until '--'
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT="$2"; shift 2;;
    --config)
      CONFIG="$2"; shift 2;;
    --)
      shift; break;;
    -h|--help)
      show_help; exit 0;;
    *)
      echo "Unknown option: $1" >&2; show_help; exit 2;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "No command provided. Use -- to separate options and command." >&2
  show_help
  exit 2
fi

CMD=("$@")

# Check doppler exists
if ! command -v doppler >/dev/null 2>&1; then
  echo "doppler CLI not found in PATH. Install it from https://www.doppler.com/docs/install" >&2
  exit 3
fi

# Build doppler run command
DOPPLER_CMD=(doppler run --)
if [[ -n "$PROJECT" ]]; then
  DOPPLER_CMD+=(--project "$PROJECT")
fi
if [[ -n "$CONFIG" ]]; then
  DOPPLER_CMD+=(--config "$CONFIG")
fi

# If running under WSL, ensure paths are in Linux form when calling Linux binaries.
# Execute via doppler run -- <cmd>
exec doppler run ${PROJECT:+--project "$PROJECT"} ${CONFIG:+--config "$CONFIG"} -- "${CMD[@]}"

