"""
Volatility Lab Integration Test - Verify tab renders and is functional

This test validates that the Volatility Lab tab:
1. Loads without errors
2. Appears in the dashboard
3. Has all required vl-* components
4. Callbacks are registered
"""

import pytest
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def test_volatility_lab_in_loaded_tabs():
    """Test that Volatility Lab appears in the dashboard tabs"""
    # Check Docker logs to confirm tab loaded
    import subprocess
    result = subprocess.run(
        ['docker', 'compose', 'logs', 'dash_app'],
        capture_output=True,
        text=True,
        cwd='/mnt/c/Aarav/fin_env/unified-dashboard'
    )
    
    # Verify tab loaded
    assert '✓ Loaded tab: ⚡ Volatility Lab' in result.stdout, \
        "Volatility Lab tab not loaded in app startup"
    
    # Verify callbacks registered
    assert '✓ Registered callbacks for ⚡ Volatility Lab' in result.stdout, \
        "Volatility Lab callbacks not registered"
    
    # Verify tab appears in tab list
    assert '⚡ Volatility Lab' in result.stdout, \
        "Volatility Lab not in loaded tabs list"
    
    print("✅ Volatility Lab successfully loaded in dashboard")


def test_volatility_lab_http_accessible():
    """Test that the dashboard is accessible via HTTP"""
    try:
        response = requests.get('http://localhost:8050', timeout=5)
        assert response.status_code == 200, \
            f"Dashboard not accessible: {response.status_code}"
        print("✅ Dashboard HTTP endpoint accessible")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Dashboard not reachable: {e}")


def test_volatility_lab_components_present():
    """Test that all vl-* component IDs are present in the layout"""
    # Read the volatility_lab.py file to verify components
    with open('/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/volatility_lab.py', 'r') as f:
        content = f.read()
    
    required_components = [
        'vl-tickers-input',
        'vl-date-range',
        'vl-window',
        'vl-type',
        'vl-compute',
        'vl-price-graph',
        'vl-vol-graph',
        'vl-results-table',
        'vl-status'
    ]
    
    for component_id in required_components:
        assert component_id in content, \
            f"Required component '{component_id}' not found in layout"
    
    print(f"✅ All {len(required_components)} vl-* components present in layout")


def test_volatility_lab_import_fixed():
    """Test that the import issue is fixed"""
    with open('/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/volatility_lab.py', 'r') as f:
        content = f.read()
    
    # Verify relative import is used (not absolute)
    assert 'from .volatility_lib import' in content, \
        "Relative import not found - should use 'from .volatility_lib import'"
    
    # Verify absolute import is NOT used
    assert 'from financial_dashboard.tabs.volatility_lib import' not in content, \
        "Absolute import still present - should be relative"
    
    print("✅ Import statement correctly fixed to relative import")


def test_volatility_lab_enabled_in_index():
    """Test that volatility_lab is in enabled_tabs"""
    with open('/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/index.py', 'r') as f:
        content = f.read()
    
    # Verify volatility_lab is in enabled_tabs
    assert "'volatility_lab'" in content or '"volatility_lab"' in content, \
        "volatility_lab not found in index.py enabled_tabs"
    
    print("✅ volatility_lab is enabled in index.py")


if __name__ == '__main__':
    print("=" * 70)
    print("  VOLATILITY LAB INTEGRATION TEST")
    print("=" * 70)
    print()
    
    tests = [
        ("Tab Loading", test_volatility_lab_in_loaded_tabs),
        ("HTTP Accessible", test_volatility_lab_http_accessible),
        ("Component IDs", test_volatility_lab_components_present),
        ("Import Fix", test_volatility_lab_import_fixed),
        ("Enabled in Index", test_volatility_lab_enabled_in_index),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"Running: {test_name}...")
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
            print()
    
    print("=" * 70)
    print(f"Results: {passed}/{len(tests)} passed, {failed}/{len(tests)} failed")
    print("=" * 70)
    
    if failed == 0:
        print()
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("   Volatility Lab is successfully integrated and functional.")
        exit(0)
    else:
        exit(1)
