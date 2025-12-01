#!/bin/bash
# Phase 1 E2E Testing - Docker Runner Script
# Runs dashboard in Docker and executes 3-iteration Playwright tests

set -e

echo "========================================"
echo "Phase 1 Dashboard E2E Testing"
echo "Docker + Playwright + Chromium"
echo "========================================"

# Configuration
DASHBOARD_PORT=8050
CONTAINER_NAME="unified-dashboard-test"
TEST_SCRIPT="tests/phase1_comprehensive_e2e.py"

# Step 1: Ensure Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

echo "✅ Docker found"

# Step 2: Stop any existing container
echo ""
echo "🧹 Cleaning up existing containers..."
docker-compose down 2>/dev/null || true
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Step 3: Build and start dashboard
echo ""
echo "🔨 Building and starting dashboard..."
docker-compose up --build -d dash_app

# Step 4: Wait for dashboard to be ready
echo ""
echo "⏳ Waiting for dashboard to become ready (max 60s)..."
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$DASHBOARD_PORT | grep -q "200"; then
        echo "✅ Dashboard is ready on port $DASHBOARD_PORT!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  Attempt $RETRY_COUNT/$MAX_RETRIES... (waiting 2s)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Dashboard failed to start after 60 seconds"
    echo "Logs:"
    docker-compose logs dash_app | tail -50
    exit 1
fi

# Step 5: Install Playwright if needed
echo ""
echo "📦 Ensuring Playwright is installed..."
pip install playwright pytest-playwright 2>/dev/null || true
python -m playwright install chromium 2>/dev/null || true

# Step 6: Run E2E tests (3 iterations)
echo ""
echo "🚀 Running E2E tests (3 iterations)..."
python $TEST_SCRIPT

# Step 7: Display results summary
echo ""
echo "========================================"
echo "📊 Test Results Summary"
echo "========================================"

if [ -f "outputs/phase1_e2e/reports/aggregate_report.md" ]; then
    cat outputs/phase1_e2e/reports/aggregate_report.md | head -40
    echo ""
    echo "📁 Full reports: outputs/phase1_e2e/reports/"
    echo "📸 Screenshots: outputs/phase1_e2e/screenshots/"
else
    echo "⚠️ Aggregate report not found"
fi

# Step 8: Optional cleanup
read -p "Stop dashboard container? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Stopping dashboard..."
    docker-compose down
    echo "✅ Cleanup complete"
else
    echo "ℹ️ Dashboard still running on port $DASHBOARD_PORT"
    echo "To stop: docker-compose down"
fi

echo ""
echo "🎉 Testing complete!"
