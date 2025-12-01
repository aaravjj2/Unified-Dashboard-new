#!/usr/bin/env python3
"""
Test generator client in deterministic mode
PHASE 1 validation
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/home/aarav/unified-dashboard')

os.environ['OPTIONS_DETERMINISTIC'] = '1'

from financial_dashboard.services.chat.generator_client import GeneratorClient

def test_deterministic():
    """Test deterministic mode responses"""
    client = GeneratorClient(deterministic=True)
    
    print("Testing deterministic generator responses...")
    print("=" * 60)
    
    # Test 1: Volatility query
    print("\n1. Volatility query")
    response = client.complete("What is the volatility for AAPL?")
    print(f"Response: {response.text[:200]}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.total_tokens}")
    
    # Test 2: Summary query
    print("\n2. Summary query")
    response = client.complete("Summarize the latest positions")
    print(f"Response: {response.text[:200]}")
    print(f"Model: {response.model}")
    
    # Test 3: Trade action query
    print("\n3. Trade action query")
    response = client.complete("Suggest a paper order for AAPL")
    print(f"Response: {response.text[:200]}")
    print(f"Model: {response.model}")
    
    # Test 4: Generic query
    print("\n4. Generic query")
    response = client.complete("Hello, how can you help?")
    print(f"Response: {response.text[:200]}")
    print(f"Model: {response.model}")
    
    print("\n" + "=" * 60)
    print("✓ Deterministic mode tests complete")

if __name__ == '__main__':
    test_deterministic()
