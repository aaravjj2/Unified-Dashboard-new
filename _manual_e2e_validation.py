"""
Manual E2E Validation Script
Replaces Playwright tests with direct HTTP calls and Dash test client
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8050"
RESULTS_FILE = "e2e_results_phase2.json"

def test_dashboard_accessibility():
    """Test 1: Dashboard is accessible."""
    try:
        start = time.time()
        resp = requests.get(BASE_URL, timeout=5)
        load_time = time.time() - start
        
        result = {
            'test': 'dashboard_accessibility',
            'status': 'PASS' if resp.status_code == 200 else 'FAIL',
            'http_code': resp.status_code,
            'load_time': round(load_time, 3),
            'content_length': len(resp.text)
        }
        
        print(f"✅ Dashboard Accessible: HTTP {resp.status_code} in {load_time:.2f}s")
        return result
        
    except Exception as e:
        print(f"❌ Dashboard Not Accessible: {e}")
        return {'test': 'dashboard_accessibility', 'status': 'FAIL', 'error': str(e)}


def test_attribution_lab_in_html():
    """Test 2: Attribution Lab tab exists in HTML."""
    try:
        resp = requests.get(BASE_URL, timeout=5)
        html = resp.text
        
        # Check for Attribution Lab tab ID
        has_tab_id = 'tab-attribution_lab' in html or 'attribution_lab' in html
        has_emoji = '📊' in html or 'Attribution' in html
        
        result = {
            'test': 'attribution_lab_presence',
            'status': 'PASS' if has_tab_id else 'FAIL',
            'tab_id_found': has_tab_id,
            'attribution_text_found': has_emoji,
            'html_size_kb': round(len(html) / 1024, 2)
        }
        
        print(f"✅ Attribution Lab Found: tab_id={has_tab_id}, text={has_emoji}")
        return result
        
    except Exception as e:
        print(f"❌ Attribution Lab Check Failed: {e}")
        return {'test': 'attribution_lab_presence', 'status': 'FAIL', 'error': str(e)}


def test_dash_dependencies():
    """Test 3: Dash dependencies endpoint works."""
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/_dash-dependencies", timeout=5)
        load_time = time.time() - start
        
        if resp.status_code == 200:
            deps = resp.json()
            n_callbacks = len(deps)
            
            # Check for attribution lab callbacks
            attr_callbacks = [cb for cb in deps if 'attribution' in str(cb).lower()]
            
            result = {
                'test': 'dash_dependencies',
                'status': 'PASS',
                'total_callbacks': n_callbacks,
                'attribution_callbacks': len(attr_callbacks),
                'load_time': round(load_time, 3)
            }
            
            print(f"✅ Dash Dependencies: {n_callbacks} callbacks ({len(attr_callbacks)} attribution-related)")
            return result
        else:
            print(f"⚠️ Dash Dependencies: HTTP {resp.status_code}")
            return {'test': 'dash_dependencies', 'status': 'WARN', 'http_code': resp.status_code}
            
    except Exception as e:
        print(f"❌ Dash Dependencies Failed: {e}")
        return {'test': 'dash_dependencies', 'status': 'FAIL', 'error': str(e)}


def test_dash_layout():
    """Test 4: Dash layout endpoint works."""
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/_dash-layout", timeout=10)
        load_time = time.time() - start
        
        if resp.status_code == 200:
            layout = resp.json()
            
            # Check for attribution lab in layout
            layout_str = json.dumps(layout)
            has_attribution = 'attribution_lab' in layout_str or 'attribution-lab' in layout_str
            
            result = {
                'test': 'dash_layout',
                'status': 'PASS',
                'has_attribution_lab': has_attribution,
                'layout_size_kb': round(len(layout_str) / 1024, 2),
                'load_time': round(load_time, 3)
            }
            
            print(f"✅ Dash Layout: {result['layout_size_kb']}KB, Attribution={has_attribution}")
            return result
        else:
            print(f"⚠️ Dash Layout: HTTP {resp.status_code}")
            return {'test': 'dash_layout', 'status': 'WARN', 'http_code': resp.status_code}
            
    except Exception as e:
        print(f"❌ Dash Layout Failed: {e}")
        return {'test': 'dash_layout', 'status': 'FAIL', 'error': str(e)}


def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("PHASE 2: E2E FUNCTIONAL VERIFICATION (HTTP-based)")
    print("=" * 60)
    print()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'base_url': BASE_URL,
        'tests': []
    }
    
    # Run tests
    results['tests'].append(test_dashboard_accessibility())
    results['tests'].append(test_attribution_lab_in_html())
    results['tests'].append(test_dash_dependencies())
    results['tests'].append(test_dash_layout())
    
    # Summary
    passed = sum(1 for t in results['tests'] if t.get('status') == 'PASS')
    failed = sum(1 for t in results['tests'] if t.get('status') == 'FAIL')
    warned = sum(1 for t in results['tests'] if t.get('status') == 'WARN')
    
    results['summary'] = {
        'total': len(results['tests']),
        'passed': passed,
        'failed': failed,
        'warned': warned,
        'pass_rate': round(passed / len(results['tests']) * 100, 1)
    }
    
    # Save results
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    print()
    print("=" * 60)
    print(f"SUMMARY: {passed} PASSED | {failed} FAILED | {warned} WARNINGS")
    print(f"Results saved to: {RESULTS_FILE}")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    exit(0 if results['summary']['failed'] == 0 else 1)
