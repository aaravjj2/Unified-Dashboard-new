#!/bin/bash
# Sprint 1 Test Runner - Unit & Utility Testing

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  SPRINT 1: UNIT & UTILITY TESTING"
echo "════════════════════════════════════════════════════════════════"
echo ""

cd /mnt/c/Aarav/fin_env/Dash

# Install pytest if needed
pip install pytest pytest-cov pytest-mock -q 2>/dev/null || true

echo "Running unit tests..."
echo ""

# Run tests with detailed output
pytest tests/ \
    --verbose \
    --tb=short \
    --color=yes \
    --durations=10 \
    -v

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  SPRINT 1 COMPLETE"
echo "════════════════════════════════════════════════════════════════"
