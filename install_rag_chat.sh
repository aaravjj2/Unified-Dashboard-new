#!/bin/bash
# RAG Chat Assistant - Installation & Validation Script
# 
# This script:
# 1. Installs required dependencies
# 2. Validates backend components
# 3. Runs integration tests
# 4. Generates final report

set -e  # Exit on error

echo "=================================================================="
echo "RAG CHAT ASSISTANT - INSTALLATION & VALIDATION"
echo "=================================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Install Python dependencies
echo -e "${YELLOW}Step 1: Installing Python dependencies...${NC}"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Not in a virtual environment. Consider activating one first.${NC}"
fi

# Install RAG dependencies
pip install --upgrade pip
pip install gpt4all sentence-transformers faiss-cpu requests

echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Step 2: Validate file structure
echo -e "${YELLOW}Step 2: Validating file structure...${NC}"
echo ""

required_files=(
    "financial_dashboard/services/chat/generator_client.py"
    "financial_dashboard/services/chat/faiss_index.py"
    "financial_dashboard/services/chat/rag.py"
    "financial_dashboard/services/chat/actions.py"
    "financial_dashboard/api/chat.py"
    "financial_dashboard/callbacks/chatbot_callbacks.py"
    "financial_dashboard/components/chatbot_ui.py"
    "financial_dashboard/assets/chat.css"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing ${#missing_files[@]} required files${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required files present${NC}"
echo ""

# Step 3: Check git commits
echo -e "${YELLOW}Step 3: Checking git commit history...${NC}"
echo ""

git log --oneline --grep="chat_agent" -6 || echo "No chat_agent commits found"
echo ""

# Step 4: Create required directories
echo -e "${YELLOW}Step 4: Creating required directories...${NC}"
echo ""

mkdir -p reports/chat_agent/fixtures
mkdir -p reports/chat_agent/logs
mkdir -p reports/chat_agent/screenshots
mkdir -p reports/chat_agent/videos
mkdir -p data/faiss_index

echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Step 5: Check fixtures
echo -e "${YELLOW}Step 5: Checking RAG fixtures...${NC}"
echo ""

fixtures=(
    "reports/chat_agent/fixtures/vol_surface_aapl.json"
    "reports/chat_agent/fixtures/positions_snapshot.json"
    "reports/chat_agent/fixtures/finnhub_latest_50.json"
)

fixture_count=0
for fixture in "${fixtures[@]}"; do
    if [ -f "$fixture" ]; then
        size=$(stat -f%z "$fixture" 2>/dev/null || stat -c%s "$fixture" 2>/dev/null)
        echo -e "${GREEN}✅${NC} $fixture ($size bytes)"
        ((fixture_count++))
    else
        echo -e "${YELLOW}⚠️${NC} $fixture (not found)"
    fi
done

if [ $fixture_count -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  No fixtures found. Backend will work but retrieval may be limited.${NC}"
    echo "   To create fixtures, run: POST /api/chat/ingest"
fi
echo ""

# Step 6: Run Python validation tests
echo -e "${YELLOW}Step 6: Running backend validation...${NC}"
echo ""

# Check if dashboard is running
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8050 | grep -q "200"; then
    echo -e "${GREEN}✅ Dashboard is running on http://localhost:8050${NC}"
    
    # Run integration tests
    echo ""
    echo -e "${YELLOW}Running integration tests...${NC}"
    python test_rag_chat_complete.py
    test_result=$?
    
    if [ $test_result -eq 0 ]; then
        echo -e "${GREEN}✅ All integration tests passed${NC}"
    else
        echo -e "${RED}❌ Some integration tests failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Dashboard not running. Skipping integration tests.${NC}"
    echo "   To start: python run_dashboard.py"
fi
echo ""

# Step 7: Summary
echo "=================================================================="
echo "VALIDATION SUMMARY"
echo "=================================================================="
echo ""
echo "✅ Dependencies installed"
echo "✅ File structure validated"
echo "✅ Directories created"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Start dashboard (if not running):"
echo "   python run_dashboard.py"
echo ""
echo "2. Test chat in browser:"
echo "   http://localhost:8050 → Click chat icon (bottom right)"
echo ""
echo "3. Run Playwright E2E tests:"
echo "   pytest tests/playwright/test_chat_rag.py -v --headed"
echo ""
echo "4. Review implementation:"
echo "   cat reports/chat_agent/final/FINAL_REPORT.md"
echo ""
echo "=================================================================="
