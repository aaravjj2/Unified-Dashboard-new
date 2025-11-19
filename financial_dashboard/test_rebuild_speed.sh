#!/bin/bash
# Test rebuild speed to verify caching is working
# Makes a trivial code change and measures rebuild time

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Docker Rebuild Speed Test                                   ║${NC}"
echo -e "${BLUE}║   Validating Cache Optimization                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Find a Python file to modify
TEST_FILE="analysis_app.py"

if [ ! -f "$TEST_FILE" ]; then
    echo -e "${YELLOW}⚠️  $TEST_FILE not found, using a different file...${NC}"
    TEST_FILE=$(find . -maxdepth 1 -name "*.py" | head -1)
fi

echo -e "${BLUE}📝 Making trivial change to: $TEST_FILE${NC}"

# Add a comment
echo "# Test comment added at $(date)" >> "$TEST_FILE"

echo -e "${GREEN}✅ Change applied${NC}"
echo ""
echo -e "${BLUE}🏗️  Rebuilding Dagster image with cached dependencies...${NC}"
echo ""

export DOCKER_BUILDKIT=1

BUILD_START=$(date +%s)
docker compose build dagster
BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Rebuild Test Results                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "⏱️  Rebuild Time: ${BUILD_TIME} seconds"
echo ""

if [ $BUILD_TIME -lt 90 ]; then
    echo -e "${GREEN}✅ EXCELLENT: Cache optimization is working!${NC}"
    echo -e "   (Build time < 90 seconds indicates dependencies were cached)"
elif [ $BUILD_TIME -lt 180 ]; then
    echo -e "${YELLOW}⚠️  GOOD: Partial caching detected${NC}"
    echo -e "   (Build time between 90-180 seconds)"
else
    echo -e "${YELLOW}⚠️  Cache may not be optimal${NC}"
    echo -e "   (Build time > 180 seconds - dependencies may have been reinstalled)"
fi

echo ""
echo -e "${BLUE}💡 For comparison:${NC}"
echo -e "   • First build (no cache): ~230-300 seconds"
echo -e "   • Rebuild with cache:     <60 seconds"
echo -e "   • Your rebuild:           ${BUILD_TIME} seconds"
echo ""

# Cleanup test comment
git checkout "$TEST_FILE" 2>/dev/null || sed -i '$ d' "$TEST_FILE"
echo -e "${GREEN}✅ Test change reverted${NC}"
