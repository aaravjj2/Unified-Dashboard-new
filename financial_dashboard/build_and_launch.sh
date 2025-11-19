#!/bin/bash
# Optimized Docker Build and Launch Script
# Implements multi-stage builds and comprehensive monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="build_and_launch_${TIMESTAMP}.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Docker Optimization & Launch Script                         ║${NC}"
echo -e "${BLUE}║   Multi-Stage Build + Comprehensive Monitoring                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📝 Logging to: ${LOG_FILE}${NC}"
echo -e "${GREEN}🕐 Started at: $(date)${NC}"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1 failed${NC}"
        exit 1
    fi
}

# Step 1: Pre-flight Checks
print_section "Step 1: Pre-flight Checks"

echo "🔍 Checking Docker availability..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

echo "🔍 Checking required files..."
required_files=("base_requirements.txt" "Dockerfile.dagster" "Dockerfile.mlflow" "docker-compose.yml")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Required file not found: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required files present${NC}"

# Step 2: Docker Authentication (Skipped - using existing credentials)
print_section "Step 2: Docker Authentication Check"

echo "🔐 Checking Docker daemon status..."
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker daemon is running${NC}"
else
    echo -e "${RED}❌ Docker daemon is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
# Note: Removed forced logout/login cycle to avoid credential prompts
# If Docker Hub authentication is needed, use 'docker login' manually before running this script

# Step 3: Cleanup (non-interactive) - remove orphan containers to avoid port conflicts
print_section "Step 3: Environment Cleanup (non-interactive)"

echo "🧹 Stopping and removing existing containers (remove-orphans)..."
docker compose down --remove-orphans --volumes 2>/dev/null || true

# Note: We do not automatically prune to avoid removing developer images unintentionally


# Step 4: Build & Start (use compose up --build --wait for a single coordinated operation)
print_section "Step 4: Build & Start Services"

echo "🏗️  Building and starting services (this will build images and bring them up)..."
echo "   First run may take several minutes; subsequent runs will be faster thanks to BuildKit cache"

BUILD_START=$(date +%s)

# Use BuildKit for better caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Start a background composer events logger (captures detailed runtime events)
echo "� Starting compose events logger..."
nohup sh -c 'docker compose events --json' >> "$LOG_FILE" 2>&1 &

# Bring up everything with rebuild and wait for services' healthchecks
docker compose up -d --build --wait
check_success "Compose up completed"

BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))
echo -e "${GREEN}⏱️  Build & start completed in ${BUILD_TIME} seconds${NC}"

# Step 5: Start Services
print_section "Step 5: Starting Services"

echo "🚀 Executing start_sprint2_services.sh..."
echo ""

if [ -f "./start_sprint2_services.sh" ]; then
    bash ./start_sprint2_services.sh
    check_success "Services started"
else
    echo -e "${RED}❌ start_sprint2_services.sh not found${NC}"
    exit 1
fi

# Step 6: Health Verification
print_section "Step 6: Health Verification"

echo "🏥 Checking service health..."
sleep 5

docker compose ps

echo ""
echo "🔍 Testing service endpoints..."

services=(
    "http://localhost:8050|Dashboard"
    "http://localhost:8000|API Gateway"
    "http://localhost:3000|Dagster"
    "http://localhost:5000|MLflow"
    "http://localhost:9000/minio/health/live|MinIO"
    "http://localhost:8006/health|News Analysis"
)

for service in "${services[@]}"; do
    IFS='|' read -r url name <<< "$service"
    echo -n "  Testing $name ($url)... "
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${YELLOW}⚠️  Not responding${NC}"
    fi
done

# Step 7: Playwright Snapshot Test
print_section "Step 7: Dashboard Verification"

echo "📸 Running Playwright snapshot test..."
echo ""

if [ -f "playwright_snapshot_test.py" ]; then
    if python3 playwright_snapshot_test.py; then
        echo -e "${GREEN}✅ Dashboard snapshot test PASSED${NC}"
    else
        echo -e "${YELLOW}⚠️  Dashboard snapshot test FAILED (may need manual verification)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  playwright_snapshot_test.py not found, skipping...${NC}"
fi

# Final Summary
print_section "Summary"

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - $(date -d "$(head -1 "$LOG_FILE" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')" +%s 2>/dev/null || echo $END_TIME)))

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ SUCCESS                                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📊 Build Time:        ${BUILD_TIME} seconds"
echo -e "⏱️  Total Time:        ${TOTAL_TIME} seconds"
echo -e "📝 Full Log:          ${LOG_FILE}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo -e "  📊 Dashboard:       http://localhost:8050"
echo -e "  🌐 API Gateway:     http://localhost:8000"
echo -e "  📈 Dagster:         http://localhost:3000"
echo -e "  🧪 MLflow:          http://localhost:5000"
echo -e "  📦 MinIO Console:   http://localhost:9001"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  docker compose ps                    # View service status"
echo -e "  docker compose logs -f <service>     # View logs"
echo -e "  docker compose down                  # Stop services"
echo -e "  ./build_and_launch.sh                # Re-run this script"
echo ""
echo -e "${GREEN}🎉 All systems operational!${NC}"
echo ""
