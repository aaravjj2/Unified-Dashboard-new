#!/bin/bash
# =============================================================================
# Unified Application Shutdown Script
# =============================================================================
# This script stops the entire Financial Dashboard application stack using
# Docker Compose. All containers are stopped gracefully with proper cleanup.
# =============================================================================

set -e

echo "=========================================="
echo "Financial Dashboard - Unified Shutdown"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed or not in PATH."
    exit 1
fi

echo "🛑 Stopping all Docker Compose services..."
echo ""

# Stop and remove all containers
docker-compose down

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ All services stopped successfully!"
    echo "=========================================="
    echo ""
    echo "📋 Additional Cleanup Options:"
    echo "   • Remove volumes:     docker-compose down -v"
    echo "   • Remove images:      docker-compose down --rmi all"
    echo "   • Full cleanup:       docker-compose down -v --rmi all"
    echo ""
    echo "🔍 Verify shutdown:"
    echo "   • Check containers:   docker-compose ps"
    echo "   • Check processes:    docker ps"
    echo ""
else
    echo ""
    echo "❌ Error: Failed to stop services cleanly."
    echo "   Check running containers with: docker ps"
    exit 1
fi
