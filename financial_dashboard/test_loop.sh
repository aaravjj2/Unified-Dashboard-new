#!/bin/bash
# Test loop - runs tests until all pass or max iterations reached

MAX_ITERATIONS=5
ITERATION=1

echo "=========================================="
echo "TEST LOOP - Running until all tests pass"
echo "Max iterations: $MAX_ITERATIONS"
echo "=========================================="

while [ $ITERATION -le $MAX_ITERATIONS ]; do
    echo ""
    echo "=========================================="
    echo "ITERATION $ITERATION of $MAX_ITERATIONS"
    echo "=========================================="
    
    # Run the comprehensive test
    python3 test_comprehensive_clicker.py
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "✅ ALL TESTS PASSED ON ITERATION $ITERATION"
        echo "=========================================="
        exit 0
    else
        echo ""
        echo "❌ Tests failed on iteration $ITERATION"
        
        if [ $ITERATION -lt $MAX_ITERATIONS ]; then
            echo "Waiting 5 seconds before retry..."
            sleep 5
        fi
    fi
    
    ITERATION=$((ITERATION + 1))
done

echo ""
echo "=========================================="
echo "❌ TESTS FAILED AFTER $MAX_ITERATIONS ITERATIONS"
echo "=========================================="
exit 1
