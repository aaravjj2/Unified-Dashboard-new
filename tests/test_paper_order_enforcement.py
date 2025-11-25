"""
Test paper order enforcement

Phase 31 Agent 1A - STEP 4
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__) + '/..')

from financial_dashboard.utils.paper_order_enforcement import enforce_paper_order, save_paper_order

print("=" * 60)
print("TEST 1: Paper order enforcement (LIVE_ORDER_ALLOWED=false)")
print("=" * 60)

os.environ['LIVE_ORDER_ALLOWED'] = 'false'

# Test 1: Paper order should pass through
order1 = {
    'order_id': 'test_001',
    'ticker': 'AAPL',
    'action': 'buy',
    'quantity': 1,
    'paper': True
}

result1 = enforce_paper_order(order1.copy())
assert result1['paper'] == True
print("✅ Paper order allowed")

# Test 2: Live order should be BLOCKED
order2 = {
    'order_id': 'test_002',
    'ticker': 'SPY',
    'action': 'sell',
    'quantity': 5,
    'paper': False  # Request live order
}

try:
    result2 = enforce_paper_order(order2.copy())
    print("❌ FAIL: Live order should have been blocked!")
    sys.exit(1)
except PermissionError as e:
    assert 'LIVE_ORDER_ALLOWED' in str(e)
    print(f"✅ Live order correctly blocked: {e}")

print("\n" + "=" * 60)
print("TEST 2: Save paper order to JSON")
print("=" * 60)

test_order = {
    'order_id': 'test_003',
    'ticker': 'NVDA',
    'option_type': 'call',
    'strike': 500.0,
    'expiration': '2025-12-19',
    'action': 'buy_to_open',
    'quantity': 2,
    'price': 15.50,
    'paper': True,
    'status': 'pending'
}

save_paper_order(test_order, storage_backend='json')

# Verify saved
json_file = 'financial_dashboard/data/options/orders.json'
assert os.path.exists(json_file), f"Orders file not created: {json_file}"

with open(json_file, 'r') as f:
    saved_orders = json.load(f)

assert len(saved_orders) > 0, "No orders saved"
assert any(o['order_id'] == 'test_003' for o in saved_orders), "Test order not found"

print(f"✅ Order saved to JSON ({len(saved_orders)} total orders)")

print("\n" + "=" * 60)
print("TEST 3: Admin audit endpoint readiness")
print("=" * 60)

# Check if JSON file has required fields
last_order = saved_orders[-1]
required_fields = ['order_id', 'ticker', 'paper', 'action', 'quantity']

for field in required_fields:
    assert field in last_order, f"Missing field: {field}"
    print(f"  ✓ {field}: {last_order[field]}")

print("✅ All required fields present for audit")

print("\n" + "=" * 60)
print("✅ ALL PAPER ORDER ENFORCEMENT TESTS PASSED")
print("=" * 60)
print(f"\nOrders file: {json_file}")
print(f"Audit log: reports/options_validation/diagnostics/order_audit.log")
