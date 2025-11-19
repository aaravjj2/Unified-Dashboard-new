#!/bin/bash
# Run local end-to-end tests inside the dash_app container
# OPTIMIZED: Uses pytest-xdist for parallel test execution

set -e

echo "======================================"
echo "Running Local E2E Test Suite (Parallel)"
echo "======================================"

# Copy updated test file into container
docker cp tests/test_e2e_full_suite.py dash_app:/app/tests/test_e2e_full_suite.py

# Execute tests inside container with parallel execution (-n auto)
# pytest-xdist will automatically detect CPU cores and run tests in parallel
docker-compose exec -T dash_app pytest tests/test_e2e_full_suite.py -n auto --browser chromium -v --tb=short

echo "======================================"
echo "Local Test Suite Complete"
echo "======================================"
