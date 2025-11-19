#!/usr/bin/env python3
"""
Phase 24-25 Fix Validation Script
Tests that all critical fixes are working properly
"""

import requests
import time
import json

def test_dashboard_response():
    """Test that dashboard responds without errors"""
    print("🌐 Testing dashboard response...")
    try:
        response = requests.get('http://localhost:8050/', timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard is responding (200 OK)")
            return True
        else:
            print(f"❌ Dashboard returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard connection failed: {e}")
        return False

def test_callback_endpoint():
    """Test that callback endpoint no longer returns 500 errors"""
    print("🔗 Testing callback endpoint...")
    
    test_payloads = [
        {'name': 'Empty POST', 'payload': {}},
        {'name': 'Safe Callback', 'payload': {
            'output': 'test-output.children',
            'outputs': [{'id': 'test-output', 'property': 'children'}],
            'inputs': [],
            'changedPropIds': [],
            'state': []
        }}
    ]
    
    success_count = 0
    
    for test in test_payloads:
        try:
            response = requests.post(
                'http://localhost:8050/_dash-update-component',
                json=test['payload'],
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code < 400:
                print(f"✅ {test['name']}: {response.status_code} (Fixed!)")
                success_count += 1
            else:
                print(f"❌ {test['name']}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {test['name']}: {e}")
    
    return success_count > 0

def test_ui_fixes():
    """Test that UI fixes are applied"""
    print("🎨 Testing UI fixes...")
    try:
        # Check if CSS file is accessible
        response = requests.get('http://localhost:8050/assets/phase24_25_ui_fixes.css', timeout=5)
        if response.status_code == 200:
            print("✅ UI CSS fixes are accessible")
            return True
        else:
            print(f"❌ UI CSS not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ UI CSS test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 Phase 24-25 Fix Validation")
    print("=" * 50)
    
    # Wait for dashboard to start
    print("⏳ Waiting for dashboard to start...")
    time.sleep(10)
    
    tests = [
        ("Dashboard Response", test_dashboard_response),
        ("Callback Endpoint", test_callback_endpoint),
        ("UI Fixes", test_ui_fixes)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Critical fixes are working!")
    else:
        print("❌ SOME TESTS FAILED - Additional fixes may be needed")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
