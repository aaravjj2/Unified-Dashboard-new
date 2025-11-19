#!/usr/bin/env python
"""
Quick validation script for Attribution Lab integration.

Tests:
1. Module imports successfully
2. Layout function returns valid Dash component
3. Callbacks can be registered without errors
4. Data loader functions are callable
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("ATTRIBUTION LAB VALIDATION SCRIPT")
print("=" * 70)

# Test 1: Module Import
print("\n[1/5] Testing module import...")
try:
    from financial_dashboard.tabs.attribution_lab import layout, register_callbacks
    print("✅ Module imports successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Layout Function
print("\n[2/5] Testing layout function...")
try:
    layout_component = layout()
    print(f"✅ Layout function returns: {type(layout_component).__name__}")
except Exception as e:
    print(f"❌ Layout function failed: {e}")
    sys.exit(1)

# Test 3: Data Loader Import
print("\n[3/5] Testing data loader functions...")
try:
    from financial_dashboard.tabs.attribution_lab.data_loader import (
        get_available_portfolios,
        get_available_benchmarks,
        get_available_factors,
        load_portfolio_holdings,
        get_sector_mapping
    )
    
    portfolios = get_available_portfolios()
    benchmarks = get_available_benchmarks()
    factors = get_available_factors()
    
    print(f"✅ Data loader functions loaded")
    print(f"   - Portfolios: {portfolios}")
    print(f"   - Benchmarks: {benchmarks}")
    print(f"   - Factors: {factors}")
except Exception as e:
    print(f"❌ Data loader import failed: {e}")
    sys.exit(1)

# Test 4: Mock Data Generation
print("\n[4/5] Testing mock data generation...")
try:
    holdings = load_portfolio_holdings('current')
    sector_map = get_sector_mapping()
    
    print(f"✅ Mock data generation works")
    print(f"   - Holdings shape: {holdings.shape}")
    print(f"   - Sectors: {len(sector_map)} tickers mapped")
except Exception as e:
    print(f"❌ Mock data generation failed: {e}")
    sys.exit(1)

# Test 5: Callback Registration (dry run)
print("\n[5/5] Testing callback registration...")
try:
    from dash import Dash
    import dash_bootstrap_components as dbc
    
    # Create minimal Dash app
    test_app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
    test_app.layout = layout()
    
    # Register callbacks
    register_callbacks(test_app)
    
    print(f"✅ Callbacks registered successfully")
    print(f"   - Total callbacks: {len(test_app.callback_map)}")
except Exception as e:
    print(f"❌ Callback registration failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL VALIDATION TESTS PASSED")
print("=" * 70)
print("\nNext steps:")
print("1. Start dashboard: python financial_dashboard/index.py")
print("2. Navigate to: http://localhost:8050")
print("3. Click '📊 Attribution Lab' tab")
print("4. Run E2E tests: pytest tests/test_attribution_lab_e2e.py -v -s")
print("=" * 70)
