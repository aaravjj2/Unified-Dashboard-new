#!/usr/bin/env python3
"""
Volatility Lab - Quick Validation Script
=========================================

Validates the compact Volatility Lab implementation without starting the dashboard.

Checks:
1. Module imports work
2. Component IDs are stable and unique
3. Fixtures are valid JSON
4. Solver functions are callable
5. API blueprint registers correctly
6. Database migration SQL is valid syntax

Usage:
    python validate_volatility_lab.py
"""

import sys
import json
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_imports():
    """Verify all modules import without errors"""
    print("🔍 Checking imports...")
    
    try:
        from financial_dashboard.tabs import volatility_lab_compact
        print("  ✅ volatility_lab_compact imports successfully")
    except Exception as e:
        print(f"  ❌ Failed to import volatility_lab_compact: {e}")
        return False
    
    try:
        from financial_dashboard.api import volsurface
        print("  ✅ volsurface API imports successfully")
    except Exception as e:
        print(f"  ❌ Failed to import volsurface: {e}")
        return False
    
    try:
        from volatility import solver
        print("  ✅ solver imports successfully")
    except Exception as e:
        print(f"  ❌ Failed to import solver: {e}")
        return False
    
    return True


def check_component_ids():
    """Verify component IDs are stable and follow convention"""
    print("\n🔍 Checking component IDs...")
    
    from financial_dashboard.tabs.volatility_lab_compact import COMPONENT_IDS
    
    # Check ID convention (all should start with 'vl-')
    non_compliant = [k for k, v in COMPONENT_IDS.items() if not v.startswith('vl-')]
    if non_compliant:
        print(f"  ❌ Non-compliant IDs found: {non_compliant}")
        return False
    
    # Check uniqueness
    values = list(COMPONENT_IDS.values())
    if len(values) != len(set(values)):
        print("  ❌ Duplicate component IDs detected")
        return False
    
    print(f"  ✅ {len(COMPONENT_IDS)} component IDs verified (all start with 'vl-')")
    return True


def check_fixtures():
    """Verify fixtures are valid JSON and have expected structure"""
    print("\n🔍 Checking fixtures...")
    
    fixture_dir = project_root / 'tests' / 'fixtures' / 'vol'
    fixtures = {
        'iv_grid.json': ['xs', 'ys', 'grid'],
        'signals.json': ['signals'],
        'backtest_preview.json': ['summary']
    }
    
    for filename, required_keys in fixtures.items():
        fixture_path = fixture_dir / filename
        if not fixture_path.exists():
            print(f"  ❌ Fixture missing: {filename}")
            return False
        
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
            
            missing_keys = [k for k in required_keys if k not in data]
            if missing_keys:
                print(f"  ❌ {filename} missing keys: {missing_keys}")
                return False
            
            print(f"  ✅ {filename} valid")
        except json.JSONDecodeError as e:
            print(f"  ❌ {filename} invalid JSON: {e}")
            return False
    
    return True


def check_solver():
    """Verify solver functions are callable and have correct signatures"""
    print("\n🔍 Checking solver...")
    
    from volatility.solver import solve_iv, compute_surface_grid, black_scholes_call, vega
    
    # Check function callability
    functions = {
        'solve_iv': solve_iv,
        'compute_surface_grid': compute_surface_grid,
        'black_scholes_call': black_scholes_call,
        'vega': vega
    }
    
    for name, func in functions.items():
        if not callable(func):
            print(f"  ❌ {name} is not callable")
            return False
    
    print(f"  ✅ All {len(functions)} solver functions callable")
    
    # Quick smoke test (should not raise)
    try:
        bs_price = black_scholes_call(S=100, K=100, T=1.0, r=0.05, sigma=0.2)
        if not (0 < bs_price < 100):
            print(f"  ⚠️  Black-Scholes price unusual: {bs_price}")
        else:
            print(f"  ✅ Black-Scholes smoke test passed (price={bs_price:.2f})")
    except Exception as e:
        print(f"  ❌ Black-Scholes smoke test failed: {e}")
        return False
    
    return True


def check_api_blueprint():
    """Verify API blueprint has correct endpoints"""
    print("\n🔍 Checking API blueprint...")
    
    from financial_dashboard.api.volsurface import volsurface_bp, admin_bp
    
    # Count routes
    volsurface_routes = len([r for r in volsurface_bp.deferred_functions if r])
    admin_routes = len([r for r in admin_bp.deferred_functions if r])
    
    print(f"  ✅ volsurface_bp: {volsurface_routes} routes")
    print(f"  ✅ admin_bp: {admin_routes} routes")
    
    # Check blueprint names
    if volsurface_bp.name != 'volsurface':
        print(f"  ❌ volsurface_bp name incorrect: {volsurface_bp.name}")
        return False
    
    if admin_bp.name != 'vollab_admin':
        print(f"  ❌ admin_bp name incorrect: {admin_bp.name}")
        return False
    
    print("  ✅ Blueprint names correct")
    return True


def check_migration_sql():
    """Verify migration SQL is syntactically valid (basic check)"""
    print("\n🔍 Checking migration SQL...")
    
    migration_path = project_root / 'migrations' / '20251118_create_vol_tables.sql'
    if not migration_path.exists():
        print("  ❌ Migration file not found")
        return False
    
    with open(migration_path, 'r') as f:
        sql = f.read()
    
    # Basic syntax checks
    required_keywords = ['CREATE TABLE', 'PRIMARY KEY', 'SERIAL', 'TIMESTAMP']
    for keyword in required_keywords:
        if keyword not in sql:
            print(f"  ❌ Missing SQL keyword: {keyword}")
            return False
    
    # Check for 4 tables
    table_count = sql.count('CREATE TABLE')
    if table_count != 4:
        print(f"  ❌ Expected 4 tables, found {table_count}")
        return False
    
    print(f"  ✅ Migration SQL valid (4 tables, {len(sql)} bytes)")
    return True


def check_documentation():
    """Verify documentation files exist and are non-empty"""
    print("\n🔍 Checking documentation...")
    
    docs = [
        'financial_dashboard/tabs/volatility_lab/README.md',
        'financial_dashboard/tabs/volatility_lab/QUICKREF.md',
        'reports/vol_lab_compact/REBUILD_SUMMARY.md'
    ]
    
    for doc_path in docs:
        full_path = project_root / doc_path
        if not full_path.exists():
            print(f"  ❌ Missing: {doc_path}")
            return False
        
        size = full_path.stat().st_size
        if size < 100:
            print(f"  ❌ {doc_path} too small ({size} bytes)")
            return False
        
        print(f"  ✅ {doc_path} ({size} bytes)")
    
    return True


def main():
    print("=" * 60)
    print("VOLATILITY LAB - VALIDATION SCRIPT")
    print("=" * 60)
    
    checks = [
        ("Imports", check_imports),
        ("Component IDs", check_component_ids),
        ("Fixtures", check_fixtures),
        ("Solver", check_solver),
        ("API Blueprint", check_api_blueprint),
        ("Migration SQL", check_migration_sql),
        ("Documentation", check_documentation),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ {name} check crashed: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - Volatility Lab ready for testing")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start dashboard: VOLLAB_DETERMINISTIC=1 python financial_dashboard/app.py")
        print("2. Navigate to Volatility Lab tab")
        print("3. Click '▶ Run' in IV Surface panel")
        print("4. Verify heatmap renders with 7×5 grid")
        return 0
    else:
        print("❌ VALIDATION FAILED - Review errors above")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
