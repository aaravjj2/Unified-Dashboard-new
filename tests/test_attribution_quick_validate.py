"""
Quick Attribution Lab Validation Script

Tests attribution_lab module functionality without E2E browser testing.
Validates:
- Module imports
- Data loading functions
- Layout generation
- Callback registration
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all attribution_lab modules import successfully."""
    print("\n=== Testing Imports ===")
    try:
        from financial_dashboard.tabs.attribution_lab import layout, register_callbacks
        from financial_dashboard.tabs.attribution_lab import data_loader
        print("✅ All modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_loading():
    """Test data loading functions."""
    print("\n=== Testing Data Loading ===")
    try:
        from financial_dashboard.tabs.attribution_lab.data_loader import (
            load_portfolio_holdings,
            load_benchmark_data,
            load_factor_data
        )
        
        # Test portfolio loading
        print("Testing load_portfolio_holdings('weekly')...")
        portfolio = load_portfolio_holdings('weekly')
        print(f"  ✅ Loaded {len(portfolio)} holdings")
        print(f"  Columns: {list(portfolio.columns)}")
        print(f"  Sample tickers: {portfolio['ticker'].head(3).tolist()}")
        
        # Test benchmark loading
        print("\nTesting load_benchmark_data('SPY')...")
        benchmark = load_benchmark_data('SPY', days=30)
        print(f"  ✅ Loaded {len(benchmark)} days of data")
        print(f"  Columns: {list(benchmark.columns)}")
        
        # Test factor loading
        print("\nTesting load_factor_data()...")
        factors = load_factor_data(days=30)
        print(f"  ✅ Loaded {len(factors)} days of factor data")
        print(f"  Factors: {list(factors.columns)}")
        
        return True
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_layout_generation():
    """Test layout function."""
    print("\n=== Testing Layout Generation ===")
    try:
        from financial_dashboard.tabs.attribution_lab import layout
        
        # Layout doesn't need app parameter
        print("Calling layout()...")
        layout_component = layout()
        print(f"  ✅ Layout generated: {type(layout_component)}")
        print(f"  Has children: {hasattr(layout_component, 'children')}")
        
        return True
    except Exception as e:
        print(f"❌ Layout generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_portfolio_csv_integration():
    """Test real CSV file loading from outputs directory."""
    print("\n=== Testing Portfolio CSV Integration ===")
    try:
        from pathlib import Path
        import pandas as pd
        
        # Find latest weekly picks CSV
        project_root = Path(__file__).parent.parent
        portfolio_dir = project_root / 'outputs'
        
        weekly_csvs = list(portfolio_dir.glob('top20_weekly_picks_*.csv'))
        print(f"Found {len(weekly_csvs)} weekly picks CSV files")
        
        if weekly_csvs:
            latest = max(weekly_csvs, key=lambda p: p.stat().st_mtime)
            print(f"Latest file: {latest.name}")
            
            df = pd.read_csv(latest)
            print(f"  ✅ Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
            print(f"  Columns: {list(df.columns)[:5]}...")
            print(f"  Sample tickers: {df['ticker'].head(5).tolist()}")
            
            return True
        else:
            print("  ⚠️ No weekly picks CSV files found")
            return False
            
    except Exception as e:
        print(f"❌ CSV integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("="*60)
    print("Attribution Lab Quick Validation")
    print("="*60)
    
    results = {
        'Imports': test_imports(),
        'Data Loading': test_data_loading(),
        'Layout Generation': test_layout_generation(),
        'CSV Integration': test_portfolio_csv_integration()
    }
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(results.values())
    print("="*60)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - Attribution Lab is functional")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
