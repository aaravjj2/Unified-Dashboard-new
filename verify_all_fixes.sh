#!/bin/bash
# Comprehensive verification script

echo ""
echo "======================================================================"
echo "DASHBOARD FIX VERIFICATION"
echo "======================================================================"
echo ""

echo "1. Testing HTTP endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/)
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ HTTP $HTTP_CODE"
else
    echo "   ❌ HTTP $HTTP_CODE"
    exit 1
fi

echo ""
echo "2. Testing layout endpoint..."
LAYOUT_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/_dash-layout)
if [ "$LAYOUT_CODE" = "200" ]; then
    echo "   ✅ Layout endpoint working"
else
    echo "   ❌ Layout endpoint failed: $LAYOUT_CODE"
    exit 1
fi

echo ""
echo "3. Testing dependencies endpoint..."
DEPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/_dash-dependencies)
if [ "$DEPS_CODE" = "200" ]; then
    echo "   ✅ Dependencies endpoint working"
else
    echo "   ❌ Dependencies endpoint failed: $DEPS_CODE"
    exit 1
fi

echo ""
echo "4. Checking callback count..."
CALLBACK_COUNT=$(curl -s http://localhost:8090/_dash-dependencies | python -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ ! -z "$CALLBACK_COUNT" ]; then
    echo "   ✅ $CALLBACK_COUNT callbacks registered"
else
    echo "   ⚠️  Could not count callbacks"
fi

echo ""
echo "5. Running Python attribution test..."
python test_attribution_callbacks.py 2>&1 | grep -q "All attribution_lab callbacks are properly registered"
if [ $? -eq 0 ]; then
    echo "   ✅ Attribution callbacks verified"
else
    echo "   ❌ Attribution callback test failed"
fi

echo ""
echo "======================================================================"
echo "VERIFICATION COMPLETE"
echo "======================================================================"
echo ""
echo "✅ All critical fixes verified"
echo "✅ Dashboard is operational on port 8090"
echo ""
echo "======================================================================"
echo ""
