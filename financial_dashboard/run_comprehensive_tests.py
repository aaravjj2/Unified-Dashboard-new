#!/usr/bin/env python3
"""
Comprehensive Test Runner for All Services
Runs curl, playwright, clicker, and pytest tests
"""

import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

# Test configuration
SERVICES = {
    'Integrated Dashboard': {'port': 8000, 'name': 'integrated_dashboard'},
    'Market Trends': {'port': 8050, 'name': 'market_trends'},
    'Market Forecast': {'port': 8051, 'name': 'market_forecast'},
    'Monthly Picks': {'port': 8052, 'name': 'monthly_picks'},
    'Weekly Picks': {'port': 8053, 'name': 'weekly_picks'},
    'Analysis Hub': {'port': 8054, 'name': 'analysis_hub'},
    'Portfolio Tracker': {'port': 8056, 'name': 'portfolio'},
    'Research Lab': {'port': 8058, 'name': 'research_lab'}
}

results = {
    'timestamp': datetime.now().isoformat(),
    'curl_tests': {},
    'playwright_tests': {},
    'clicker_tests': {},
    'pytest_tests': {},
    'summary': {}
}

def run_command(cmd, timeout=60):
    """Run a command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': 'Timeout expired',
            'success': False
        }
    except Exception as e:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'success': False
        }

print("=" * 80)
print("🧪 COMPREHENSIVE TEST SUITE")
print("=" * 80)
print()

# 1. CURL TESTS - Check all service endpoints
print("📡 Running CURL tests for all services...")
print("-" * 80)
for service_name, config in SERVICES.items():
    port = config['port']
    url = f"http://localhost:{port}"
    
    print(f"  Testing {service_name} ({url})...", end=" ")
    result = run_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url}", timeout=10)
    
    status_code = result['stdout'].strip().strip("'")
    success = status_code == '200'
    
    results['curl_tests'][service_name] = {
        'port': port,
        'status_code': status_code,
        'success': success
    }
    
    if success:
        print(f"✅ HTTP {status_code}")
    else:
        print(f"❌ HTTP {status_code}")

print()

# 2. PLAYWRIGHT TESTS
print("🎭 Running Playwright tests...")
print("-" * 80)

playwright_tests = [
    'test_comprehensive_playwright.py',
    'test_phase4_playwright.py',
    'test_analysis_hub_e2e.py'
]

for test_file in playwright_tests:
    test_path = Path(test_file)
    if test_path.exists():
        print(f"  Running {test_file}...", end=" ")
        result = run_command(f"python3 {test_file}", timeout=120)
        results['playwright_tests'][test_file] = {
            'success': result['success'],
            'output': result['stdout'][:500]  # First 500 chars
        }
        if result['success']:
            print("✅")
        else:
            print("❌")
    else:
        print(f"  ⚠️  {test_file} not found, skipping")

print()

# 3. CLICKER TESTS
print("🖱️  Running Clicker tests...")
print("-" * 80)

clicker_tests = [
    'clicker_portfolio.py',
    'clicker_portfolio_detailed.py',
    'clicker_test.py'
]

for test_file in clicker_tests:
    test_path = Path(test_file)
    if test_path.exists():
        print(f"  Running {test_file}...", end=" ")
        result = run_command(f"python3 {test_file}", timeout=90)
        results['clicker_tests'][test_file] = {
            'success': result['success'],
            'output': result['stdout'][:500]
        }
        if result['success']:
            print("✅")
        else:
            print("❌")
    else:
        print(f"  ⚠️  {test_file} not found, skipping")

print()

# 4. PYTEST UNIT TESTS
print("🧬 Running pytest unit tests...")
print("-" * 80)

pytest_result = run_command("python3 -m pytest tests/ -v --tb=short", timeout=180)
results['pytest_tests']['unit_tests'] = {
    'success': pytest_result['success'],
    'output': pytest_result['stdout']
}

if pytest_result['success']:
    print("  ✅ Unit tests passed")
else:
    print("  ❌ Unit tests failed")

print()

# 5. COMPREHENSIVE FEATURE TESTS
print("🔬 Running comprehensive feature tests...")
print("-" * 80)

feature_tests = [
    'test_all_dashboards.py',
    'test_portfolio_comprehensive.py',
    'test_market_trends_buttons.py',
    'test_market_forecast_buttons.py'
]

for test_file in feature_tests:
    test_path = Path(test_file)
    if test_path.exists():
        print(f"  Running {test_file}...", end=" ")
        result = run_command(f"python3 {test_file}", timeout=90)
        
        key = f"feature_{test_file}"
        results['pytest_tests'][key] = {
            'success': result['success'],
            'output': result['stdout'][:500]
        }
        
        if result['success']:
            print("✅")
        else:
            print("❌")
    else:
        print(f"  ⚠️  {test_file} not found, skipping")

print()

# Generate summary
print("=" * 80)
print("📊 TEST SUMMARY")
print("=" * 80)

# Count successes
curl_passed = sum(1 for r in results['curl_tests'].values() if r['success'])
curl_total = len(results['curl_tests'])

playwright_passed = sum(1 for r in results['playwright_tests'].values() if r['success'])
playwright_total = len(results['playwright_tests'])

clicker_passed = sum(1 for r in results['clicker_tests'].values() if r['success'])
clicker_total = len(results['clicker_tests'])

pytest_passed = sum(1 for r in results['pytest_tests'].values() if r['success'])
pytest_total = len(results['pytest_tests'])

results['summary'] = {
    'curl': {'passed': curl_passed, 'total': curl_total},
    'playwright': {'passed': playwright_passed, 'total': playwright_total},
    'clicker': {'passed': clicker_passed, 'total': clicker_total},
    'pytest': {'passed': pytest_passed, 'total': pytest_total}
}

print(f"\n  CURL Tests:       {curl_passed}/{curl_total} passed")
print(f"  Playwright Tests: {playwright_passed}/{playwright_total} passed")
print(f"  Clicker Tests:    {clicker_passed}/{clicker_total} passed")
print(f"  Pytest Tests:     {pytest_passed}/{pytest_total} passed")

total_passed = curl_passed + playwright_passed + clicker_passed + pytest_passed
total_tests = curl_total + playwright_total + clicker_total + pytest_total

print(f"\n  OVERALL:          {total_passed}/{total_tests} tests passed")

# Save results to JSON
results_file = f"test_results_comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n  Results saved to: {results_file}")
print()

if total_passed == total_tests:
    print("🎉 ALL TESTS PASSED!")
else:
    print(f"⚠️  {total_tests - total_passed} test(s) failed")

print("=" * 80)
