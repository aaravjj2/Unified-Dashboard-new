#!/bin/bash
# Safe prune system script for the Unified Financial Dashboard
# This script performs an aggressive cleanup but requires interactive confirmation
# or a --yes flag to proceed. It must be executed from the `financial_dashboard` directory.

set -euo pipefail

SCRIPT_NAME=$(basename "$0")
USAGE="Usage: $SCRIPT_NAME [--yes]\n\n--yes    Run without interactive confirmation (use with care)."

if [[ "${1-}" == "--help" || "${1-}" == "-h" ]]; then
  echo -e "$USAGE"
  exit 0
fi

FORCE=false
if [[ "${1-}" == "--yes" || "${1-}" == "-y" ]]; then
  FORCE=true
fi

echo "--- PRUNE SYSTEM SCRIPT ---"
echo "Warning: this script will remove containers defined in the project compose files, delete test artifacts, and run 'docker system prune -af' which can remove images used by other projects on this host."
echo "Make sure you understand the consequences before proceeding."

if ! $FORCE; then
  read -p "Do you want to continue? (yes/NO): " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted by user. No changes made."
    exit 1
  fi
fi

echo "--- Stopping and removing project containers (compose files are explicit) ..."
# Stop and remove compose stacks. We explicitly reference files to avoid ambiguity.
if [[ -f ../platform-stack/docker-compose.yml ]]; then
  docker-compose --file ../platform-stack/docker-compose.yml down -v --remove-orphans || true
else
  echo "Note: ../platform-stack/docker-compose.yml not found, skipping."
fi

if [[ -f ./docker-compose.yml ]]; then
  docker-compose --file ./docker-compose.yml down -v --remove-orphans || true
else
  echo "Note: ./docker-compose.yml not found, skipping."
fi

echo "--- Pruning unused Docker images, networks, and build cache (aggressive) ..."
echo "This runs: docker system prune -af"
docker system prune -af || true

echo "--- Deleting old Playwright test results and snapshots (if present) ..."
rm -rf ./tests/test-results/ || true
rm -rf ./playwright-report/ || true

echo "--- System Prune Complete. Ready for a clean build and test run. ---"
