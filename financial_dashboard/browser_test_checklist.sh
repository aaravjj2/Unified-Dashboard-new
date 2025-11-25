#!/bin/bash
# Quick browser test checklist
# Run this to see current status and what to test

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           📋 Browser Testing Checklist                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🔍 Step 1: Check Service Status"
echo "─────────────────────────────────────────────────────────────"

for port in 8000 8050 8051 8052 8053 8054 8056 8057 8058; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        STATUS="✅ ONLINE"
    else
        STATUS="❌ OFFLINE"
    fi
    
    case $port in
        8000) NAME="Unified Dashboard    " ;;
        8050) NAME="Market Trends        " ;;
        8051) NAME="Market Forecast      " ;;
        8052) NAME="Monthly Picks        " ;;
        8053) NAME="Weekly Picks         " ;;
        8054) NAME="Analysis Hub         " ;;
        8056) NAME="Portfolio Dashboard  " ;;
        8057) NAME="Event Monitor        " ;;
        8058) NAME="Research Lab         " ;;
    esac
    
    echo "  $STATUS  Port $port: $NAME http://localhost:$port"
done

echo ""
echo "🌐 Step 2: Browser Tests"
echo "─────────────────────────────────────────────────────────────"
echo ""
echo "  TEST 1: Unified Dashboard"
echo "  └─ URL: http://localhost:8000"
echo "  └─ Expected: All 8 tabs visible and clickable"
echo "  └─ Test: Press Ctrl+1, Ctrl+2, etc. to switch tabs"
echo ""
echo "  TEST 2: Analysis Hub - Tab Visibility Fix"
echo "  └─ URL: http://localhost:8054"
echo "  └─ Action: Press Ctrl+Shift+R for hard refresh"
echo "  └─ Expected: 3 tabs visible: Attribution | Scenario | Portfolio"
echo "  └─ Check: Click each tab and verify content loads"
echo ""
echo "  TEST 3: Portfolio Dashboard - Initial Load"
echo "  └─ URL: http://localhost:8056"
echo "  └─ Expected: Positions table, P/L chart, transactions visible"
echo "  └─ NOT Expected: Blank page"
echo ""
echo "  TEST 4: Event Monitor"
echo "  └─ URL: http://localhost:8057"
echo "  └─ Expected: Event timeline, filters, event cards"
echo "  └─ Test: Filter by severity/type"
echo ""
echo "  TEST 5: Research Lab - Outcomes Display"
echo "  └─ URL: http://localhost:8058"
echo "  └─ Expected: Experiment list, run history, outcomes"
echo "  └─ Test: View experiment details"
echo ""
echo "🐛 Step 3: Debugging (If Tabs Still Hidden)"
echo "─────────────────────────────────────────────────────────────"
echo ""
echo "  1. Open DevTools (F12)"
echo "  2. Go to Console tab"
echo "  3. Look for: [TabsFix] messages"
echo "  4. Should see: 'Tabs visibility forced!'"
echo ""
echo "  If tabs still hidden, run in Console:"
echo "  ────────────────────────────────────────────────────────────"
echo "  document.querySelectorAll('.nav-tabs, [role=\"tablist\"]').forEach(el => {"
echo "      el.style.display = 'flex';"
echo "      el.style.visibility = 'visible';"
echo "      el.style.opacity = '1';"
echo "  });"
echo "  ────────────────────────────────────────────────────────────"
echo ""
echo "📊 Step 4: Verify Content Generation"
echo "─────────────────────────────────────────────────────────────"
echo ""

# Run test script if available
if [ -f "test_visual_render.py" ]; then
    echo "  Running automated content verification..."
    python3 test_visual_render.py 2>&1 | grep -E "(Testing|✓|✗)" | sed 's/^/  /'
else
    echo "  ⚠ test_visual_render.py not found - skipping automated test"
fi

echo ""
echo "📝 Step 5: Logs (If Issues)"
echo "─────────────────────────────────────────────────────────────"
echo ""
echo "  View recent logs:"
echo "  $ tail -n 50 /tmp/*_app.log"
echo ""
echo "  View specific service:"
echo "  $ tail -f /tmp/analysis_app.log"
echo ""
echo "🛑 Stop All Services"
echo "─────────────────────────────────────────────────────────────"
echo ""
echo "  $ pkill -f 'dash.py|_app.py|flask.py|unified_dashboard'"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "✅ NEXT ACTION:"
echo "   Open your browser and test: http://localhost:8000"
echo "   Then test Analysis Hub:    http://localhost:8054"
echo ""
echo "═══════════════════════════════════════════════════════════════"
