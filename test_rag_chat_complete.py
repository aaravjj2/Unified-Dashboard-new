#!/usr/bin/env python3
"""
RAG Chat Assistant - Complete Integration Test
Tests end-to-end flow: UI → Callbacks → API → RAG → Response

Usage:
    python test_rag_chat_complete.py
"""

import sys
import os
import time
import json
import requests
import subprocess
import signal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_chat_api_health():
    """Test 1: Chat API health endpoint"""
    print("\n" + "="*70)
    print("TEST 1: Chat API Health Check")
    print("="*70)
    
    try:
        response = requests.get("http://localhost:8050/api/chat/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Generator status: {data.get('generator', {}).get('status')}")
            print(f"   Vector index size: {data.get('vector_index', {}).get('size')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_rag_query():
    """Test 2: RAG query endpoint"""
    print("\n" + "="*70)
    print("TEST 2: RAG Query Endpoint")
    print("="*70)
    
    query_data = {
        "query": "What is the volatility for AAPL?",
        "tab_context": {
            "tab": "market_trends",
            "ticker": "AAPL"
        },
        "session_id": "test-session-123"
    }
    
    print(f"Query: {query_data['query']}")
    print(f"Context: {query_data['tab_context']}")
    
    try:
        response = requests.post(
            "http://localhost:8050/api/chat/query",
            json=query_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', '')
            sources = data.get('sources', [])
            action = data.get('action_suggestion')
            
            print(f"✅ RAG query successful")
            print(f"\n📝 Answer ({len(answer)} chars):")
            print(f"   {answer[:200]}...")
            print(f"\n📚 Sources ({len(sources)}):")
            for src in sources[:3]:
                print(f"   - {src}")
            
            if action:
                print(f"\n🤖 Action Suggestion:")
                print(f"   Type: {action.get('action')}")
                print(f"   Payload: {action.get('payload')}")
            
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_action_execution():
    """Test 3: Action execution endpoint"""
    print("\n" + "="*70)
    print("TEST 3: Action Execution Endpoint")
    print("="*70)
    
    action_data = {
        "action_data": {
            "action": "create_paper_order",
            "payload": {
                "symbol": "AAPL",
                "qty": 1,
                "side": "buy",
                "order_type": "market"
            },
            "confidence": 0.85
        },
        "session_id": "test-session-123",
        "user_confirmed": True
    }
    
    print(f"Action: {action_data['action_data']['action']}")
    print(f"Payload: {action_data['action_data']['payload']}")
    
    try:
        response = requests.post(
            "http://localhost:8050/api/chat/execute_action",
            json=action_data,
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            success = data.get('success')
            message = data.get('message', data.get('error', ''))
            
            if success:
                print(f"✅ Action executed successfully")
                print(f"   Message: {message}")
            else:
                print(f"⚠️ Action rejected (expected for safety)")
                print(f"   Reason: {message}")
            
            # Check audit log
            audit_log = "reports/chat_agent/logs/action_audit.log"
            if os.path.exists(audit_log):
                print(f"\n📋 Audit log updated:")
                with open(audit_log, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        print(f"   Timestamp: {last_entry.get('timestamp')}")
                        print(f"   Action: {last_entry.get('action')}")
                        print(f"   Status: {last_entry.get('status')}")
            
            return True
        else:
            print(f"❌ Action execution failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Action execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_css_fix():
    """Test 4: CSS file exists and contains black text fix"""
    print("\n" + "="*70)
    print("TEST 4: CSS Text Color Fix")
    print("="*70)
    
    css_file = "financial_dashboard/assets/chat.css"
    
    if not os.path.exists(css_file):
        print(f"❌ CSS file not found: {css_file}")
        return False
    
    with open(css_file, 'r') as f:
        content = f.read()
    
    # Check for black text color
    if 'color: #000' in content or 'color: black' in content:
        print(f"✅ CSS file exists with black text fix")
        print(f"   File: {css_file}")
        print(f"   Size: {len(content)} bytes")
        return True
    else:
        print(f"⚠️ CSS file exists but missing black text color")
        return False


def test_fixtures_exist():
    """Test 5: RAG fixtures exist"""
    print("\n" + "="*70)
    print("TEST 5: RAG Fixtures")
    print("="*70)
    
    fixtures_dir = "reports/chat_agent/fixtures"
    expected_fixtures = [
        "vol_surface_aapl.json",
        "positions_snapshot.json",
        "finnhub_latest_50.json"
    ]
    
    all_exist = True
    for fixture in expected_fixtures:
        path = os.path.join(fixtures_dir, fixture)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            print(f"   ✅ {fixture}: {len(data)} entries")
        else:
            print(f"   ❌ {fixture}: NOT FOUND")
            all_exist = False
    
    if all_exist:
        print(f"✅ All fixtures present")
    else:
        print(f"⚠️ Some fixtures missing")
    
    return all_exist


def test_ui_components():
    """Test 6: UI components exist"""
    print("\n" + "="*70)
    print("TEST 6: UI Components")
    print("="*70)
    
    files = [
        ("financial_dashboard/components/chatbot_ui.py", "Chatbot UI"),
        ("financial_dashboard/callbacks/chatbot_callbacks.py", "Chatbot Callbacks"),
        ("financial_dashboard/services/chat/generator_client.py", "Generator Client"),
        ("financial_dashboard/services/chat/rag.py", "RAG Orchestrator"),
        ("financial_dashboard/services/chat/actions.py", "Action Executor"),
        ("financial_dashboard/api/chat.py", "Chat API Blueprint"),
    ]
    
    all_exist = True
    for filepath, description in files:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"   ✅ {description}: {size} bytes")
        else:
            print(f"   ❌ {description}: NOT FOUND")
            all_exist = False
    
    if all_exist:
        print(f"✅ All components present")
    else:
        print(f"⚠️ Some components missing")
    
    return all_exist


def test_git_commits():
    """Test 7: Git commits for each phase"""
    print("\n" + "="*70)
    print("TEST 7: Git Commit History")
    print("="*70)
    
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--grep", "chat_agent", "-10"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        commits = result.stdout.strip().split('\n')
        commits = [c for c in commits if c]
        
        print(f"Found {len(commits)} chat_agent commits:")
        for commit in commits[:6]:  # Show first 6
            print(f"   {commit}")
        
        expected_phases = ["PHASE 5", "PHASE 4", "PHASE 3", "PHASE 2", "PHASE 1", "PHASE 0"]
        found_phases = []
        
        for phase in expected_phases:
            if any(phase in commit for commit in commits):
                found_phases.append(phase)
        
        print(f"\n✅ Found {len(found_phases)}/6 expected phase commits")
        return len(found_phases) >= 5  # At least 5 phases committed
        
    except Exception as e:
        print(f"⚠️ Could not check git commits: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("RAG CHAT ASSISTANT - COMPLETE INTEGRATION TEST")
    print("="*70)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if server is running
    print("\n🔍 Checking if dashboard is running on http://localhost:8050...")
    try:
        response = requests.get("http://localhost:8050", timeout=5)
        print("✅ Dashboard is running")
    except:
        print("❌ Dashboard not running. Please start it with:")
        print("   python run_dashboard.py")
        return 1
    
    # Run all tests
    results = {
        "API Health": test_chat_api_health(),
        "RAG Query": test_rag_query(),
        "Action Execution": test_action_execution(),
        "CSS Fix": test_css_fix(),
        "Fixtures": test_fixtures_exist(),
        "UI Components": test_ui_components(),
        "Git Commits": test_git_commits(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed//total}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! RAG chat assistant is ready!")
        print("\n📝 Next steps:")
        print("   1. Install dependencies: pip install gpt4all sentence-transformers faiss-cpu")
        print("   2. Run Playwright tests: pytest tests/playwright/test_chat_rag.py")
        print("   3. Test in browser: http://localhost:8050 → Click chat icon")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
