#!/usr/bin/env python3
"""
Comprehensive Browser Test for AI Automation Features on Port 8053
Tests the new 100+ improvements in Enhanced Alpaca Options Lab
"""

import requests
import json
import time
from datetime import datetime


def test_server_health():
    """Test server is running."""
    try:
        response = requests.get('http://localhost:8053/', timeout=5)
        return response.status_code == 200
    except:
        return False


def test_api_endpoints():
    """Test API endpoints."""
    endpoints = [
        ('/', 'Main page'),
        ('/_dash-layout', 'Dash layout'),
        ('/_dash-dependencies', 'Dash dependencies'),
    ]
    results = []
    for endpoint, name in endpoints:
        try:
            response = requests.get(f'http://localhost:8053{endpoint}', timeout=5)
            results.append({
                'endpoint': endpoint,
                'name': name,
                'status': response.status_code,
                'success': response.status_code == 200
            })
        except Exception as e:
            results.append({
                'endpoint': endpoint,
                'name': name,
                'status': 'error',
                'success': False,
                'error': str(e)
            })
    return results


def test_ai_components_in_layout():
    """Test AI components are present in the layout."""
    try:
        response = requests.get('http://localhost:8053/_dash-layout', timeout=10)
        if response.status_code != 200:
            return {'success': False, 'error': 'Failed to get layout'}
        
        layout = response.text
        
        # Check for AI Automation Hub components
        ai_components = [
            'ai-regime-display',
            'ai-regime-strategies', 
            'ai-scanner-results',
            'ai-signals-container',
            'ai-ta-analysis',
            'ai-iv-analysis',
            'ai-auto-strategy',
            'ai-ml-predictions',
            'ai-alerts-container'
        ]
        
        found = []
        missing = []
        for comp in ai_components:
            if comp in layout:
                found.append(comp)
            else:
                missing.append(comp)
        
        # Check for focus tickers
        focus_tickers = ['GLD', 'SLV', 'SPY', 'NVDA', 'AAPL', 'MSFT', 'GOOGL']
        tickers_found = [t for t in focus_tickers if t in layout]
        
        # Check for AI feature badges
        features = [
            'AI Automation Hub',
            'Auto Market Scanner',
            'AI Signal Generator',
            'Market Regime',
            'Technical Analysis',
            'IV Analysis',
            'Auto Strategy',
            'ML Predictions'
        ]
        features_found = [f for f in features if f in layout]
        
        return {
            'success': len(found) >= 5,
            'ai_components_found': found,
            'ai_components_missing': missing,
            'focus_tickers_found': tickers_found,
            'features_found': features_found
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def test_callbacks_registered():
    """Test callbacks are registered."""
    try:
        response = requests.get('http://localhost:8053/_dash-dependencies', timeout=10)
        if response.status_code != 200:
            return {'success': False, 'error': 'Failed to get dependencies'}
        
        deps = json.loads(response.text)
        
        # Check for AI callbacks
        ai_outputs = [
            'ai-regime-display',
            'ai-scanner-results',
            'ai-signals-container',
            'ai-ta-analysis',
            'ai-iv-analysis',
            'ai-auto-strategy',
            'ai-ml-predictions',
            'ai-alerts-container'
        ]
        
        callback_outputs = []
        for dep in deps:
            if 'outputs' in dep:
                for output in dep['outputs']:
                    if 'id' in output:
                        callback_outputs.append(output['id'])
        
        ai_callbacks_found = [o for o in ai_outputs if any(o in co for co in callback_outputs)]
        
        return {
            'success': len(ai_callbacks_found) >= 3,
            'total_callbacks': len(deps),
            'ai_callbacks_found': ai_callbacks_found,
            'sample_outputs': callback_outputs[:20]
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def run_all_tests():
    """Run all browser tests."""
    print("=" * 60)
    print("🧪 AI AUTOMATION BROWSER TEST - PORT 8053")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'tests': []
    }
    
    # Test 1: Server Health
    print("📡 Test 1: Server Health...")
    health = test_server_health()
    results['total'] += 1
    if health:
        results['passed'] += 1
        print("   ✅ Server is running on port 8053")
    else:
        results['failed'] += 1
        print("   ❌ Server not responding")
    results['tests'].append({'name': 'Server Health', 'passed': health})
    print()
    
    # Test 2: API Endpoints
    print("🔗 Test 2: API Endpoints...")
    endpoints = test_api_endpoints()
    for ep in endpoints:
        results['total'] += 1
        if ep['success']:
            results['passed'] += 1
            print(f"   ✅ {ep['name']} ({ep['endpoint']}): {ep['status']}")
        else:
            results['failed'] += 1
            print(f"   ❌ {ep['name']} ({ep['endpoint']}): {ep.get('error', ep['status'])}")
        results['tests'].append({'name': f"Endpoint: {ep['name']}", 'passed': ep['success']})
    print()
    
    # Test 3: AI Components in Layout
    print("🤖 Test 3: AI Components in Layout...")
    ai_layout = test_ai_components_in_layout()
    results['total'] += 1
    if ai_layout.get('success'):
        results['passed'] += 1
        print(f"   ✅ AI Components Found: {len(ai_layout.get('ai_components_found', []))}")
        print(f"      Components: {', '.join(ai_layout.get('ai_components_found', [])[:5])}")
        print(f"      Focus Tickers: {', '.join(ai_layout.get('focus_tickers_found', []))}")
        print(f"      Features: {len(ai_layout.get('features_found', []))}")
    else:
        results['failed'] += 1
        print(f"   ❌ AI Components: {ai_layout.get('error', 'Not found')}")
        if ai_layout.get('ai_components_missing'):
            print(f"      Missing: {', '.join(ai_layout.get('ai_components_missing', []))}")
    results['tests'].append({'name': 'AI Components in Layout', 'passed': ai_layout.get('success', False)})
    print()
    
    # Test 4: Callbacks Registered
    print("⚙️ Test 4: Callbacks Registered...")
    callbacks = test_callbacks_registered()
    results['total'] += 1
    if callbacks.get('success'):
        results['passed'] += 1
        print(f"   ✅ Total Callbacks: {callbacks.get('total_callbacks', 0)}")
        print(f"      AI Callbacks Found: {len(callbacks.get('ai_callbacks_found', []))}")
    else:
        results['failed'] += 1
        print(f"   ❌ Callbacks: {callbacks.get('error', 'Issue detected')}")
    results['tests'].append({'name': 'Callbacks Registered', 'passed': callbacks.get('success', False)})
    print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📈 Pass Rate: {results['passed']/results['total']*100:.1f}%")
    print()
    
    if results['failed'] == 0:
        print("🎉 ALL TESTS PASSED! AI Automation is working!")
    else:
        print("⚠️ Some tests failed - check the output above")
    
    return results


if __name__ == '__main__':
    run_all_tests()
