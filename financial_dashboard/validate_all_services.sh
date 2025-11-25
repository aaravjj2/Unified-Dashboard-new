#!/bin/bash
# Comprehensive Service Validation Script
# Tests all 11 services to ensure they're functional

echo "============================================"
echo "🔍 COMPREHENSIVE SERVICE VALIDATION"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Testing $name... "
    response=$(curl -s "$url" 2>/dev/null || echo "FAILED")
    
    if echo "$response" | grep -q "$expected"; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((passed++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "  Expected: $expected"
        echo "  Got: $response"
        ((failed++))
    fi
}

echo "1️⃣  Testing Database (PostgreSQL)..."
if docker ps | grep -q "fin_dash_postgres"; then
    echo -e "PostgreSQL: ${GREEN}✓ PASS${NC}"
    ((passed++))
else
    echo -e "PostgreSQL: ${RED}✗ FAIL${NC}"
    ((failed++))
fi

echo ""
echo "2️⃣  Testing Backend Services..."
test_endpoint "Market Trends Health" "http://localhost:8050/health" "healthy"
test_endpoint "Market Forecast Health" "http://localhost:8051/health" "healthy"
test_endpoint "Analysis Hub Health" "http://localhost:8054/health" "healthy"
test_endpoint "Portfolio Health" "http://localhost:8056/health" "healthy"
test_endpoint "Research Lab Health" "http://localhost:8058/health" "healthy"
test_endpoint "Options Service Health" "http://localhost:8060/health" "healthy"
test_endpoint "Chatbot Health" "http://localhost:8062/health" "healthy"
test_endpoint "Backtester Health" "http://localhost:8064/health" "healthy"

echo ""
echo "3️⃣  Testing API Gateway..."
test_endpoint "Gateway Health" "http://localhost:8049/health" "healthy"
test_endpoint "Gateway Market Trends Proxy" "http://localhost:8049/api/market-trends/health" "healthy"
test_endpoint "Gateway Backtester Proxy" "http://localhost:8049/api/backtest/health" "healthy"

echo ""
echo "4️⃣  Testing Dashboard (Frontend)..."
response=$(curl -s http://localhost:8000 2>/dev/null || echo "FAILED")
if echo "$response" | grep -q "Financial Dashboard"; then
    echo -e "Dashboard Loaded: ${GREEN}✓ PASS${NC}"
    ((passed++))
else
    echo -e "Dashboard Loaded: ${RED}✗ FAIL${NC}"
    ((failed++))
fi

if echo "$response" | grep -q "Backtesting Lab"; then
    echo -e "Sprint 8 Tab Present: ${GREEN}✓ PASS${NC}"
    ((passed++))
else
    echo -e "Sprint 8 Tab Present: ${RED}✗ FAIL${NC}"
    ((failed++))
fi

echo ""
echo "============================================"
echo "📊 VALIDATION SUMMARY"
echo "============================================"
echo -e "${GREEN}Passed: $passed${NC}"
echo -e "${RED}Failed: $failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! System is fully operational.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed. Check the output above.${NC}"
    exit 1
fi
