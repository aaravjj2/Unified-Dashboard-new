#!/bin/bash

# Test script to check if tabs load properly via curl

echo "Testing Dashboard Tabs..."
echo "========================"

# Test main page
echo -e "\n1. Testing main page..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
if [ "$RESPONSE" = "200" ]; then
    echo "✓ Main page: OK ($RESPONSE)"
else
    echo "✗ Main page: FAILED ($RESPONSE)"
fi

# Test if Analysis Hub content exists in main page
echo -e "\n2. Checking Analysis Hub content..."
ANALYSIS_CHECK=$(curl -s http://localhost:8000/ | grep -o "Analysis Hub" | head -1)
if [ ! -z "$ANALYSIS_CHECK" ]; then
    echo "✓ Analysis Hub: Content found"
else
    echo "✗ Analysis Hub: Content NOT found"
fi

# Test if Portfolio content exists
echo -e "\n3. Checking Portfolio content..."
PORTFOLIO_CHECK=$(curl -s http://localhost:8000/ | grep -o "Portfolio Tracker" | head -1)
if [ ! -z "$PORTFOLIO_CHECK" ]; then
    echo "✓ Portfolio: Content found"
else
    echo "✗ Portfolio: Content NOT found"
fi

# Test if Research Lab content exists
echo -e "\n4. Checking Research Lab content..."
RESEARCH_CHECK=$(curl -s http://localhost:8000/ | grep -o "Scenario Analysis" | head -1)
if [ ! -z "$RESEARCH_CHECK" ]; then
    echo "✓ Research Lab: Content found"
else
    echo "✗ Research Lab: Content NOT found"
fi

# Check for JavaScript errors in HTML
echo -e "\n5. Checking for error markers in HTML..."
ERROR_CHECK=$(curl -s http://localhost:8000/ | grep -i "error\|500\|internal server")
if [ -z "$ERROR_CHECK" ]; then
    echo "✓ No error markers found in HTML"
else
    echo "✗ Error markers found:"
    echo "$ERROR_CHECK" | head -5
fi

echo -e "\n========================"
echo "Test complete!"
