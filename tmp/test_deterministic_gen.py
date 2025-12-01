"""
Test generator client deterministic mode for PHASE 1
"""
import os
os.environ['OPTIONS_DETERMINISTIC'] = '1'

from financial_dashboard.services.chat.generator_client import get_generator

def test_deterministic():
    gen = get_generator()
    
    # Test 1: General query
    print("Test 1: General query")
    result1 = gen.complete("What is the volatility for AAPL?", max_tokens=50)
    print(f"Response: {result1.text if hasattr(result1, 'text') else result1}")
    print()
    
    # Test 2: Trade query (should trigger deterministic action response)
    print("Test 2: Trade/order query")
    result2 = gen.complete("I want to trade TSLA", max_tokens=50)
    print(f"Response: {result2.text if hasattr(result2, 'text') else result2}")
    print()
    
    # Test 3: Stock price query
    print("Test 3: Stock price query")
    result3 = gen.complete("What is the price of NVDA?", max_tokens=50)
    print(f"Response: {result3.text if hasattr(result3, 'text') else result3}")
    print()
    
    print("✅ Deterministic mode test complete")

if __name__ == "__main__":
    test_deterministic()
