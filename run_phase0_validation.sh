#!/bin/bash
# 🧪 Phase 0 Validation Runner Script
# Orchestrates the full validation loop in Docker environment

set -e

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  🧪 PHASE 0 VALIDATION - DOCKERIZED EXECUTION"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Configuration
COMPOSE_FILE="docker-compose.yml"
DASHBOARD_SERVICE="dash_app"
VALIDATION_SCRIPT="tests/phase0_validation_orchestrator.py"

# Step 1: Check Docker Compose exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ docker-compose.yml not found!"
    exit 1
fi

echo "✅ Found docker-compose.yml"
echo ""

# Step 2: Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true
echo ""

# Step 3: Build and start dashboard service
echo "🏗️  Building and starting dashboard service..."
docker-compose -f "$COMPOSE_FILE" up --build -d "$DASHBOARD_SERVICE"
echo ""

# Step 4: Wait for dashboard to be ready
echo "⏳ Waiting for dashboard to be ready..."
sleep 10

MAX_WAIT=60
ELAPSED=0
DASHBOARD_READY=false

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8050 > /dev/null 2>&1; then
        DASHBOARD_READY=true
        echo "✅ Dashboard is ready!"
        break
    fi
    
    echo "   Still waiting... (${ELAPSED}s / ${MAX_WAIT}s)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ "$DASHBOARD_READY" = false ]; then
    echo "❌ Dashboard failed to start within ${MAX_WAIT}s"
    echo "📋 Last 50 lines of dashboard logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=50 "$DASHBOARD_SERVICE"
    exit 1
fi

echo ""

# Step 5: Install Playwright in container (if needed)
echo "🎭 Checking Playwright installation..."
docker exec "$DASHBOARD_SERVICE" bash -c "
    pip install playwright pytest-playwright > /dev/null 2>&1 || true
    python -m playwright install chromium --with-deps > /dev/null 2>&1 || true
" || echo "⚠️  Playwright installation skipped (may already be installed)"

echo "✅ Playwright ready"
echo ""

# Step 6: Run Phase 0 validation inside container
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  🚀 LAUNCHING VALIDATION ORCHESTRATOR"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

docker exec -it "$DASHBOARD_SERVICE" python -m tests.phase0_validation_orchestrator

VALIDATION_EXIT_CODE=$?

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"

if [ $VALIDATION_EXIT_CODE -eq 0 ]; then
    echo "  ✅ VALIDATION PASSED"
else
    echo "  ❌ VALIDATION FAILED (Exit code: $VALIDATION_EXIT_CODE)"
fi

echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Step 7: Copy validation reports to host
echo "📁 Copying validation reports to host..."
docker cp "$DASHBOARD_SERVICE:/app/outputs/phase0_validation" ./outputs/ 2>/dev/null || \
    echo "⚠️  Could not copy reports (they may not exist yet)"

echo ""
echo "📊 Validation reports location: ./outputs/phase0_validation/reports/"
echo ""

exit $VALIDATION_EXIT_CODE
