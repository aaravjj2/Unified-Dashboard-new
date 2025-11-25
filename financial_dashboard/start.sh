#!/bin/bash
# =============================================================================
# Unified Application Startup Script
# =============================================================================
# This script starts the entire Financial Dashboard application stack using
# Docker Compose as the single source of truth. All services are orchestrated
# through docker-compose.yml with proper dependency management and health checks.
# =============================================================================

set -e

echo "=========================================="
echo "Financial Dashboard - Unified Startup"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed or not in PATH."
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Using default values."
    echo "   Create a .env file with your API keys for full functionality."
    echo ""
fi

# Display services that will be started
echo "📦 Services to be started:"
echo "   • PostgreSQL Database (port 5432)"
echo "   • Market Trends Service (port 8050)"
echo "   • Market Forecast Service (port 8051)"
echo "   • Analysis Hub Service (port 8054)"
echo "   • Portfolio Service (port 8056)"
echo "   • Research Lab Service (port 8058)"
echo "   • Options Trading Service (port 8060)"
echo "   • API Gateway (port 8049)"
echo "   • Main Dashboard (port 8000)"
echo ""

# Ask for confirmation
read -p "Continue with startup? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Startup cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting all services with Docker Compose..."
echo ""

# Build and start all services in detached mode
docker-compose up -d --build

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ All services started successfully!"
    echo "=========================================="
    echo ""
    echo "🌐 Access Points:"
    echo "   • Main Dashboard:    http://localhost:8000"
    echo "   • API Gateway:       http://localhost:8049"
    echo "   • Market Trends:     http://localhost:8050/health"
    echo "   • Market Forecast:   http://localhost:8051/health"
    echo "   • Analysis Hub:      http://localhost:8054/health"
    echo "   • Portfolio:         http://localhost:8056/health"
    echo "   • Research Lab:      http://localhost:8058/health"
    echo "   • Options Trading:   http://localhost:8060/health"
    echo ""
    echo "📊 Useful Commands:"
    echo "   • View logs:         docker-compose logs -f"
    echo "   • View status:       docker-compose ps"
    echo "   • Stop services:     ./stop.sh (or docker-compose down)"
    echo "   • Restart service:   docker-compose restart <service-name>"
    echo ""
    echo "⏳ Note: Services may take 30-60 seconds to become fully healthy."
    echo "   Use 'docker-compose logs -f' to monitor startup progress."
    echo ""
else
    echo ""
    echo "❌ Error: Failed to start services."
    echo "   Check logs with: docker-compose logs"
    exit 1
fi
