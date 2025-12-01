"""
Quick validation test for backtest API

Tests backtest endpoint without full app initialization.
"""

import json
import os
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_backtest_fixture_creation():
    """Test deterministic backtest fixture creation"""
    from financial_dashboard.api.options_backtest import create_default_backtest_fixture
    
    fixture = create_default_backtest_fixture()
    
    # Check required fields
    required_fields = ['backtest_id', 'ticker', 'strategy', 'metrics', 'equity_curve', 'trades']
    for field in required_fields:
        assert field in fixture, f"Missing field: {field}"
    
    print(f"✅ Fixture has all required fields")
    
    # Check metrics
    metrics = fixture['metrics']
    required_metrics = ['total_return', 'win_rate', 'total_trades']
    for metric in required_metrics:
        assert metric in metrics, f"Missing metric: {metric}"
    
    print(f"✅ Metrics complete: total_return={metrics['total_return']}%, win_rate={metrics['win_rate']}%")
    
    # Check equity curve
    equity_curve = fixture['equity_curve']
    assert len(equity_curve) >= 5, f"Equity curve too short: {len(equity_curve)}"
    assert all('date' in point and 'equity' in point for point in equity_curve)
    
    print(f"✅ Equity curve valid: {len(equity_curve)} points")
    
    # Check trades
    trades = fixture['trades']
    assert len(trades) > 0, "No trades in fixture"
    assert all('trade_id' in t and 'pnl' in t for t in trades)
    
    print(f"✅ Trades valid: {len(trades)} trades")
    
    # Check deterministic flag
    assert fixture.get('deterministic') == True
    assert fixture.get('seed') == 42
    
    print(f"✅ Deterministic mode confirmed: seed={fixture['seed']}")
    
    return True


def test_backtest_imports():
    """Test backtest module imports"""
    try:
        from financial_dashboard.api.options_backtest import backtest_bp, run_backtest, export_backtest
        print("✅ Backtest API imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_fixture_file_creation():
    """Test fixture file gets created"""
    from financial_dashboard.api.options_backtest import load_deterministic_backtest_fixture
    
    fixture = load_deterministic_backtest_fixture()
    
    assert fixture is not None
    assert 'backtest_id' in fixture
    
    # Check file exists
    fixture_path = Path('tests/fixtures/options/backtest_fixture.json')
    assert fixture_path.exists(), f"Fixture file not created: {fixture_path}"
    
    print(f"✅ Fixture file created: {fixture_path}")
    print(f"   Backtest ID: {fixture['backtest_id']}")
    print(f"   Ticker: {fixture['ticker']}")
    print(f"   Total Return: {fixture['metrics']['total_return']}%")
    
    return True


if __name__ == '__main__':
    print("="*60)
    print("BACKTEST API VALIDATION TEST")
    print("="*60)
    
    # Set deterministic mode
    os.environ['OPTIONS_DETERMINISTIC'] = '1'
    
    tests = [
        ("Backtest API imports", test_backtest_imports),
        ("Backtest fixture creation", test_backtest_fixture_creation),
        ("Fixture file creation", test_fixture_file_creation)
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    if failed == 0:
        print(f"✅ ALL BACKTEST API TESTS PASSED ({passed}/{len(tests)})")
        print("="*60)
        sys.exit(0)
    else:
        print(f"❌ SOME TESTS FAILED: {failed}/{len(tests)} failed, {passed}/{len(tests)} passed")
        print("="*60)
        sys.exit(1)
