#!/usr/bin/env python3
"""Test action detection and execution flow for PHASE 4"""
import requests
import json
import time

DASHBOARD_URL = "http://localhost:8050"

def test_action_detection():
    """Test that action patterns are detected from queries"""
    
    test_cases = [
        {
            "query": "Buy 100 shares of AAPL",
            "expected_action": "create_paper_order",
            "description": "Paper order creation"
        },
        {
            "query": "Show me the volatility surface tab",
            "expected_action": "open_tab",
            "description": "Tab navigation"
        },
        {
            "query": "Run a backtest for momentum strategy",
            "expected_action": "run_backtest",
            "description": "Backtest execution"
        }
    ]
    
    print("=" * 80)
    print("PHASE 4 - Action Detection Test")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        print(f"\n📤 Query: {case['query']}")
        print(f"   Expected: {case['expected_action']} ({case['description']})")
        
        response = requests.post(
            f"{DASHBOARD_URL}/api/chat/query",
            json={"query": case['query'], "use_rag": True, "top_k": 3},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"   ❌ HTTP {response.status_code}")
            failed += 1
            continue
        
        data = response.json()
        action_suggestion = data.get('action_suggestion')
        
        if not action_suggestion:
            print(f"   ❌ No action detected")
            failed += 1
            continue
        
        detected_action = action_suggestion.get('action')
        confidence = action_suggestion.get('confidence', 0)
        payload = action_suggestion.get('payload', {})
        
        if detected_action == case['expected_action']:
            print(f"   ✅ PASS - {detected_action} detected (confidence: {confidence})")
            print(f"      Payload: {json.dumps(payload, indent=2)[:100]}...")
            passed += 1
        else:
            print(f"   ❌ FAIL - Expected {case['expected_action']}, got {detected_action}")
            failed += 1
    
    print(f"\n{'=' * 80}")
    print(f"Action Detection: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")
    
    return passed, failed


def test_action_execution():
    """Test action execution with audit logging"""
    
    print("=" * 80)
    print("PHASE 4 - Action Execution Test")
    print("=" * 80)
    
    # Test 1: Execute paper order
    print("\n📤 Test 1: Execute paper order (AAPL buy)")
    
    action_id = f"test_action_{int(time.time() * 1000)}"
    
    exec_response = requests.post(
        f"{DASHBOARD_URL}/api/chat/execute_action",
        json={
            "action_id": action_id,
            "action_type": "create_paper_order",
            "payload": {
                "symbol": "AAPL",
                "qty": 10,
                "side": "buy",
                "type": "market",
                "paper": True
            },
            "confirmed": True,
            "user_id": "test_user"
        },
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   Response: HTTP {exec_response.status_code}")
    if exec_response.status_code == 200:
        result = exec_response.json()
        print(f"   ✅ Success: {result.get('success')}")
        print(f"   Action ID: {result.get('action_id')}")
        print(f"   Result: {json.dumps(result.get('result', {}), indent=2)[:200]}...")
    else:
        print(f"   ❌ Error: {exec_response.text}")
    
    # Test 2: Reject unconfirmed action
    print("\n📤 Test 2: Reject unconfirmed action")
    
    reject_response = requests.post(
        f"{DASHBOARD_URL}/api/chat/execute_action",
        json={
            "action_id": f"reject_{int(time.time() * 1000)}",
            "action_type": "create_paper_order",
            "payload": {
                "symbol": "MSFT",
                "qty": 5,
                "side": "sell",
                "type": "market",
                "paper": True
            },
            "confirmed": False
        },
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   Response: HTTP {reject_response.status_code}")
    if reject_response.status_code == 403:
        print(f"   ✅ Correctly rejected unconfirmed action")
    else:
        print(f"   ❌ Expected 403, got {reject_response.status_code}")
        print(f"   Response: {reject_response.text}")
    
    # Test 3: Block live trading
    print("\n📤 Test 3: Block live trading attempt")
    
    live_response = requests.post(
        f"{DASHBOARD_URL}/api/chat/execute_action",
        json={
            "action_id": f"live_{int(time.time() * 1000)}",
            "action_type": "create_paper_order",
            "payload": {
                "symbol": "TSLA",
                "qty": 1,
                "side": "buy",
                "type": "market",
                "paper": False  # Try to make it live
            },
            "confirmed": True
        },
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   Response: HTTP {live_response.status_code}")
    result = live_response.json()
    if not result.get('success') and 'BLOCKED' in result.get('error', '').upper():
        print(f"   ✅ Live trading correctly blocked")
        print(f"   Error: {result.get('error')}")
    else:
        print(f"   ❌ Live trading was not blocked!")
        print(f"   Response: {json.dumps(result, indent=2)}")
    
    print(f"\n{'=' * 80}")
    print("Action Execution Test Complete")
    print(f"{'=' * 80}\n")


def check_audit_log():
    """Check if audit log was created"""
    import os
    
    print("=" * 80)
    print("PHASE 4 - Audit Log Verification")
    print("=" * 80)
    
    audit_path = "/home/aarav/unified-dashboard/reports/chat_agent/logs/action_audit.log"
    
    if os.path.exists(audit_path):
        print(f"\n✅ Audit log exists: {audit_path}")
        with open(audit_path, 'r') as f:
            lines = f.readlines()
            print(f"   Total entries: {len(lines)}")
            print(f"   Last 3 entries:")
            for line in lines[-3:]:
                print(f"      {line.strip()}")
    else:
        print(f"\n⚠️  Audit log not found: {audit_path}")
    
    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    # Run all tests
    passed, failed = test_action_detection()
    test_action_execution()
    check_audit_log()
    
    print("\n" + "=" * 80)
    print("PHASE 4 COMPLETE")
    print("=" * 80)
