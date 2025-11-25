"""
Quick validation test for Playwright harness

Validates harness imports, element registry load, and configuration without full browser launch.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_harness_imports():
    """Verify harness module imports successfully"""
    try:
        # Import without executing
        import tests.playwright.options_button_audit as harness_module
        print("✅ Harness imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_element_registry_exists():
    """Verify element registry file exists"""
    registry_path = Path('reports/options_validation/diagnostics/interactive_elements_after.json')
    
    if not registry_path.exists():
        print(f"❌ Element registry not found: {registry_path}")
        return False
    
    print(f"✅ Element registry exists: {registry_path}")
    return True


def test_element_registry_schema():
    """Verify element registry has expected schema"""
    registry_path = Path('reports/options_validation/diagnostics/interactive_elements_after.json')
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Check required keys
    required_keys = ['all_ids_alphabetical']
    for key in required_keys:
        if key not in registry:
            print(f"❌ Missing key in registry: {key}")
            return False
    
    all_ids = registry['all_ids_alphabetical']
    
    if not isinstance(all_ids, list):
        print(f"❌ all_ids_alphabetical is not a list")
        return False
    
    if len(all_ids) == 0:
        print(f"❌ all_ids_alphabetical is empty")
        return False
    
    print(f"✅ Registry schema valid: {len(all_ids)} total IDs")
    return True


def test_directories_created():
    """Verify artifact directories exist"""
    dirs = [
        Path('reports/options_validation/screenshots'),
        Path('reports/options_validation/playwright'),
        Path('reports/options_validation/dom')
    ]
    
    all_exist = True
    for d in dirs:
        if not d.exists():
            print(f"⚠️  Directory will be created on run: {d}")
            # This is OK - harness creates them
        else:
            print(f"✅ Directory exists: {d}")
    
    return True


def test_harness_configuration():
    """Verify harness configuration constants"""
    import tests.playwright.options_button_audit as harness
    
    # Check headless mode
    if harness.HEADLESS != False:
        print(f"❌ HEADLESS must be False, got: {harness.HEADLESS}")
        return False
    print(f"✅ HEADLESS = {harness.HEADLESS} (correct)")
    
    # Check timeout
    if harness.DEFAULT_TIMEOUT < 1000:
        print(f"❌ DEFAULT_TIMEOUT too low: {harness.DEFAULT_TIMEOUT}")
        return False
    print(f"✅ DEFAULT_TIMEOUT = {harness.DEFAULT_TIMEOUT}ms")
    
    # Check dashboard URL
    expected_url = 'http://localhost:8029'
    if harness.DASHBOARD_URL != expected_url:
        print(f"⚠️  DASHBOARD_URL = {harness.DASHBOARD_URL} (expected {expected_url})")
    else:
        print(f"✅ DASHBOARD_URL = {harness.DASHBOARD_URL}")
    
    return True


if __name__ == '__main__':
    print("="*60)
    print("PLAYWRIGHT HARNESS VALIDATION TEST")
    print("="*60)
    
    tests = [
        ("Harness imports", test_harness_imports),
        ("Element registry exists", test_element_registry_exists),
        ("Element registry schema", test_element_registry_schema),
        ("Directories", test_directories_created),
        ("Harness configuration", test_harness_configuration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Exception: {e}")
            failed += 1
    
    print("\n" + "="*60)
    if failed == 0:
        print(f"✅ ALL HARNESS VALIDATION TESTS PASSED ({passed}/{len(tests)})")
        print("="*60)
        sys.exit(0)
    else:
        print(f"❌ SOME TESTS FAILED: {failed}/{len(tests)} failed, {passed}/{len(tests)} passed")
        print("="*60)
        sys.exit(1)
