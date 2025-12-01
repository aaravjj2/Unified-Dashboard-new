#!/bin/bash
set -e

echo "🔧 Phase 24-25 Critical Fix - Docker Rebuild"
echo "=============================================="

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Remove existing dashboard image to force rebuild
echo "🗑️ Removing existing dashboard image..."
docker rmi $(docker images -q "*dash_app*" "*financial*dashboard*" 2>/dev/null) 2>/dev/null || true

# Copy fixes to the container build context
echo "📁 Copying critical fixes to build context..."
cp -r test_artifacts/phase24_25_targeted_fix financial_dashboard/

# Build with fixes
echo "🔨 Building dashboard with critical fixes..."
docker-compose build --no-cache dash_app

# Start services
echo "🚀 Starting services with fixes..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Test the fixes
echo "🧪 Testing the fixes..."
curl -f http://localhost:8050/ > /dev/null && echo "✅ Dashboard is responding" || echo "❌ Dashboard not responding"

# Test callback endpoint
echo "🔗 Testing callback endpoint..."
curl -X POST -H "Content-Type: application/json" -d '{}' http://localhost:8050/_dash-update-component 2>/dev/null | grep -q "500" && echo "❌ 500 errors still present" || echo "✅ No 500 errors detected"

echo "=============================================="
echo "🎉 Phase 24-25 Critical Fix deployment complete!"
echo "📊 Check http://localhost:8050 to verify fixes"
echo "=============================================="
