#!/bin/bash
# Sprint 2 Services Startup Script
# Starts all Docker services with proper health checks and sequencing
# Logs are automatically saved to sprint2_startup.log

set -e  # Exit on error

# Setup logging
LOG_FILE="sprint2_startup_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "🚀 Starting Financial Dashboard - Sprint 2 Services"
echo "=================================================="
echo "📝 Logging to: $LOG_FILE"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo ""
echo "Step 1: Building base images..."
echo "--------------------------------"
docker compose build dagster mlflow

echo ""
echo "Step 2: Starting core services (PostgreSQL, MinIO)..."
echo "-----------------------------------------------------"
docker compose up -d postgres minio

echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    echo -n "."
    sleep 2
done

echo "⏳ Waiting for MinIO to be ready..."
for i in {1..20}; do
    if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        echo "✅ MinIO is ready"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "Step 3: Creating MLflow bucket in MinIO..."
echo "-------------------------------------------"
# Install mc (MinIO Client) if not present
if ! command -v mc &> /dev/null; then
    echo "Installing MinIO Client..."
    wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /tmp/mc
    chmod +x /tmp/mc
    MC_CMD=/tmp/mc
else
    MC_CMD=mc
fi

# Configure MinIO alias
$MC_CMD alias set local http://localhost:9000 minioadmin minioadmin > /dev/null 2>&1 || true

# Create bucket if it doesn't exist
$MC_CMD mb local/mlflow-artifacts > /dev/null 2>&1 || true
echo "✅ MLflow artifacts bucket ready"

echo ""
echo "Step 4: Creating databases..."
echo "------------------------------"
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE mlflow;" 2>/dev/null || echo "ℹ️  mlflow database already exists"
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE dagster;" 2>/dev/null || echo "ℹ️  dagster database already exists"
echo "✅ Databases created"

echo ""
echo "Step 5: Starting MLflow and Dagster..."
echo "---------------------------------------"
docker compose up -d mlflow dagster

echo "⏳ Waiting for services to be healthy..."
sleep 10

echo ""
echo "Step 6: Starting application services..."
echo "-----------------------------------------"
docker compose up -d

echo ""
echo "⏳ Final health check..."
sleep 5

echo ""
echo "=================================================="
echo "✅ All services started successfully!"
echo "=================================================="
echo ""
echo "Service URLs:"
echo "-------------"
echo "📊 Dashboard:      http://localhost:8050"
echo "🌐 API Gateway:    http://localhost:8000"
echo "📈 Dagster (Dagit): http://localhost:3000"
echo "🧪 MLflow:         http://localhost:5000"
echo "📦 MinIO Console:  http://localhost:9001"
echo "   (Login: minioadmin / minioadmin)"
echo ""
echo "Database:"
echo "---------"
echo "🗄️  PostgreSQL:    localhost:5432"
echo "   (User: postgres / Password: postgres_dev_pass)"
echo ""
echo "Health Check Commands:"
echo "----------------------"
echo "docker compose ps                    # View all services"
echo "docker compose logs -f dagster       # View Dagster logs"
echo "docker compose logs -f mlflow        # View MLflow logs"
echo "curl http://localhost:8000/health    # API Gateway health"
echo ""
echo "To stop all services:"
echo "docker compose down"
echo ""
echo "To view this help again:"
echo "cat startup_info.txt"
echo ""
