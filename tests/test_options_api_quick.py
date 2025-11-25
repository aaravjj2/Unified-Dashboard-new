"""
Quick API test for options forecast endpoint (no full app init)

Agent 1A Phase 31 STEP 3
"""

import json
import os
import sys

# Test 1: Load fixture directly
print("=" * 60)
print("TEST 1: Load deterministic fixture")
print("=" * 60)

fixture_path = 'tests/fixtures/options/forecast_fixture.json'

if not os.path.exists(fixture_path):
    print(f"❌ Fixture not found: {fixture_path}")
    sys.exit(1)

with open(fixture_path, 'r') as f:
    fixture = json.load(f)

print(f"✅ Fixture loaded: {len(fixture)} keys")
print(f"   - error: {fixture.get('error')}")
print(f"   - ticker: {fixture.get('result', {}).get('ticker')}")
print(f"   - forecast_series: {len(fixture.get('result', {}).get('forecast_series', []))} entries")
print(f"   - surface_grid rows: {len(fixture.get('result', {}).get('surface_grid', {}).get('iv_matrix', []))}")

# Validate schema
result = fixture['result']
assert 'forecast_series' in result
assert 'term_structure' in result
assert 'surface_grid' in result
assert 'metrics' in result
assert 'explanation' in result

assert len(result['forecast_series']) >= 5
assert len(result['term_structure']) >= 5
assert len(result['surface_grid']['iv_matrix']) >= 5

print("✅ Schema validation passed")

# Test 2: Validate IV ranges
print("\n" + "=" * 60)
print("TEST 2: Validate IV ranges")
print("=" * 60)

for entry in result['forecast_series']:
    iv = entry['predicted_iv']
    assert 0.01 <= iv <= 3.0, f"IV out of range: {iv}"

for term in result['term_structure']:
    iv = term['atm_iv']
    assert 0.01 <= iv <= 3.0, f"ATM IV out of range: {iv}"

for row in result['surface_grid']['iv_matrix']:
    for iv in row:
        assert 0.01 <= iv <= 3.0, f"Surface IV out of range: {iv}"

print("✅ All IV values within [0.01, 3.0] range")

# Test 3: Import API module
print("\n" + "=" * 60)
print("TEST 3: Import API module")
print("=" * 60)

try:
    sys.path.insert(0, os.path.dirname(__file__) + '/..')
    from financial_dashboard.api.options_forecast import options_forecast_api, load_deterministic_fixture
    
    print("✅ API module imported successfully")
    print(f"   - Blueprint name: {options_forecast_api.name}")
    print(f"   - URL prefix: {options_forecast_api.url_prefix}")
    
    # Test fixture loader
    loaded_fixture = load_deterministic_fixture()
    assert loaded_fixture is not None
    assert loaded_fixture['error'] == False
    
    print("✅ Fixture loader function works")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL QUICK TESTS PASSED")
print("=" * 60)
print("\nNext: Full integration test via curl to running server")
