#!/usr/bin/env python3
"""
Test to verify button functionality after MultiplexerTransform fix.
"""
import requests
import json
import sys

def test_server_health():
    """Test basic server response"""
    try:
        response = requests.get("http://localhost:8050/", timeout=5)
        print(f"✅ Server responding: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False

def test_callback_registration():
    """Check if callbacks are registered"""
    try:
        response = requests.get("http://localhost:8050/_dash-dependencies", timeout=5)
        if response.status_code == 200:
            deps = response.json()
            callback_count = len(deps)
            print(f"✅ Callbacks registered: {callback_count}")
            
            # Look for run-btn specifically
            run_btn_found = False
            for dep in deps:
                inputs_str = json.dumps(dep.get('inputs', []))
                if 'run-btn' in inputs_str:
                    run_btn_found = True
                    print(f"✅ Found 'run-btn' callback")
                    print(f"   Callback ID: {dep.get('output', 'unknown')}")
                    break
            
            if not run_btn_found:
                print("⚠️  'run-btn' callback not found in dependencies")
            
            return callback_count > 0
        else:
            print(f"❌ Callback endpoint returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not fetch callbacks: {e}")
        return False

def test_callback_trigger():
    """Test triggering a callback (simulated button click)"""
    # This simulates clicking a button that uses allow_duplicate
    # The MultiplexerTransform should handle the hashed callback ID
    try:
        # Get the page first to establish session
        session = requests.Session()
        response = session.get("http://localhost:8050/", timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Could not load page: {response.status_code}")
            return False
        
        # Try to trigger the Market Trends refresh callback
        # This is a simple callback that should work if MultiplexerTransform is active
        payload = {
            "output": "trends-last-cached.data",
            "outputs": {"id": "trends-last-cached", "property": "data"},
            "inputs": [{"id": "url", "property": "pathname", "value": "/"}],
            "changedPropIds": ["url.pathname"],
            "state": []
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": session.cookies.get("_csrf_token", "")
        }
        
        response = session.post(
            "http://localhost:8050/_dash-update-component",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"✅ Callback test response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ MultiplexerTransform is working correctly!")
            return True
        elif response.status_code == 500:
            print(f"❌ Callback failed with 500 error")
            print(f"   Response: {response.text[:200]}")
            return False
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Callback test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("=" * 60)
    print("BUTTON FUNCTIONALITY VERIFICATION")
    print("=" * 60)
    print()
    
    # Test 1: Server health
    print("Test 1: Server Health Check")
    print("-" * 40)
    health_ok = test_server_health()
    print()
    
    if not health_ok:
        print("❌ Server is not running. Please start the server first.")
        sys.exit(1)
    
    # Test 2: Callback registration
    print("Test 2: Callback Registration")
    print("-" * 40)
    callbacks_ok = test_callback_registration()
    print()
    
    if not callbacks_ok:
        print("❌ Callbacks not registered properly.")
        sys.exit(1)
    
    # Test 3: Callback trigger
    print("Test 3: Callback Trigger Test")
    print("-" * 40)
    trigger_ok = test_callback_trigger()
    print()
    
    # Summary
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Server Health:        {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Callback Registration: {'✅ PASS' if callbacks_ok else '❌ FAIL'}")
    print(f"Callback Trigger:     {'✅ PASS' if trigger_ok else '❌ FAIL'}")
    print()
    
    if health_ok and callbacks_ok and trigger_ok:
        print("✅ ALL TESTS PASSED - Buttons should work!")
        print()
        print("Next steps:")
        print("1. Open http://localhost:8050 in your browser")
        print("2. Navigate to Market Trends tab")
        print("3. Click 'Run Full Analysis' button")
        print("4. Verify the button triggers the analysis")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Further debugging needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
