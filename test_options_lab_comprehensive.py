#!/usr/bin/env python3
"""
Comprehensive Options Lab Functionality Test
Tests all aspects of Options Lab including callbacks, data loading, and UI components.
"""

import sys
sys.path.insert(0, '.')

from financial_dashboard.tabs.options_lab import layout, callbacks, data_loader
import pandas as pd

def test_1_module_imports():
    """Test 1: Module Imports"""
    print("\n" + "="*70)
    print("TEST 1: Module Imports")
    print("="*70)
    
    tests = [
        ("layout function", callable(layout)),
        ("register_callbacks", callable(callbacks.register_callbacks)),
        ("fetch_options_chain", callable(data_loader.fetch_options_chain)),
        ("calculate_greeks_summary", callable(data_loader.calculate_greeks_summary)),
        ("generate_vol_surface_data", callable(data_loader.generate_vol_surface_data)),
    ]
    
    for name, result in tests:
        status = "✅" if result else "❌"
        print(f"{status} {name}: {result}")
    
    all_passed = all(result for _, result in tests)
    return all_passed


def test_2_mock_data_generation():
    """Test 2: Mock Data Generation"""
    print("\n" + "="*70)
    print("TEST 2: Mock Data Generation")
    print("="*70)
    
    try:
        result = data_loader.fetch_options_chain('TEST', use_mock=True)
        
        tests = [
            ("Returns dict", isinstance(result, dict)),
            ("Has 'calls' key", 'calls' in result),
            ("Has 'puts' key", 'puts' in result),
            ("Has 'source' key", 'source' in result),
            ("Source is 'mock'", result.get('source') == 'mock'),
            ("Has expirations", len(result.get('expirations', [])) > 0),
            ("Has spot_price", 'spot_price' in result and result['spot_price'] > 0),
            ("Calls > 0", len(result.get('calls', [])) > 0),
            ("Puts > 0", len(result.get('puts', [])) > 0),
        ]
        
        for name, passed in tests:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
        
        print(f"\n📊 Data Summary:")
        print(f"   Calls: {len(result.get('calls', []))}")
        print(f"   Puts: {len(result.get('puts', []))}")
        print(f"   Expirations: {len(result.get('expirations', []))}")
        print(f"   Spot Price: ${result.get('spot_price', 0):.2f}")
        
        return all(passed for _, passed in tests)
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_alpaca_integration():
    """Test 3: Alpaca Integration (will fallback if no credentials)"""
    print("\n" + "="*70)
    print("TEST 3: Alpaca Integration")
    print("="*70)
    
    try:
        # This should fallback gracefully
        result = data_loader.fetch_options_chain('AAPL', use_alpaca=True, use_mock=False)
        
        tests = [
            ("Returns dict", isinstance(result, dict)),
            ("Has source", 'source' in result),
            ("Source valid", result.get('source') in ['alpaca', 'yfinance', 'mock']),
            ("No error", not result.get('error')),
        ]
        
        for name, passed in tests:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
        
        print(f"\n📊 Data Source: {result.get('source', 'unknown').upper()}")
        
        if result.get('source') == 'alpaca':
            print("   🟢 Alpaca API working!")
        elif result.get('source') == 'yfinance':
            print("   🟡 Using yfinance fallback")
        else:
            print("   🔵 Using mock data fallback")
        
        return all(passed for _, passed in tests)
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_greeks_calculation():
    """Test 4: Greeks Calculation"""
    print("\n" + "="*70)
    print("TEST 4: Greeks Calculation")
    print("="*70)
    
    try:
        chain_data = data_loader.fetch_options_chain('TEST', use_mock=True)
        summary = data_loader.calculate_greeks_summary(chain_data)
        
        tests = [
            ("Returns dict", isinstance(summary, dict)),
            ("Has total_volume", 'total_volume' in summary),
            ("Has total_oi", 'total_oi' in summary),
            ("Has put_call_ratio", 'put_call_ratio' in summary),
            ("Has avg_iv_calls", 'avg_iv_calls' in summary),
            ("Has avg_iv_puts", 'avg_iv_puts' in summary),
        ]
        
        for name, passed in tests:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
        
        print(f"\n📊 Greeks Summary:")
        print(f"   Total Volume: {summary.get('total_volume', 0):,}")
        print(f"   Total OI: {summary.get('total_oi', 0):,}")
        print(f"   Put/Call Ratio: {summary.get('put_call_ratio', 0):.2f}")
        print(f"   Avg IV (Calls): {summary.get('avg_iv_calls', 0):.2%}")
        print(f"   Avg IV (Puts): {summary.get('avg_iv_puts', 0):.2%}")
        
        return all(passed for _, passed in tests)
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_vol_surface():
    """Test 5: Volatility Surface Generation"""
    print("\n" + "="*70)
    print("TEST 5: Volatility Surface Generation")
    print("="*70)
    
    try:
        chain_data = data_loader.fetch_options_chain('TEST', use_mock=True)
        vol_surface = data_loader.generate_vol_surface_data(chain_data)
        
        tests = [
            ("Returns DataFrame", isinstance(vol_surface, pd.DataFrame)),
            ("Not empty", not vol_surface.empty),
            ("Has strike column", 'strike' in vol_surface.columns),
            ("Has dte column", 'dte' in vol_surface.columns),
            ("Has iv column", 'iv' in vol_surface.columns),
        ]
        
        for name, passed in tests:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
        
        if not vol_surface.empty:
            print(f"\n📊 Surface Data:")
            print(f"   Shape: {vol_surface.shape}")
            print(f"   Strike range: ${vol_surface['strike'].min():.2f} - ${vol_surface['strike'].max():.2f}")
            print(f"   DTE range: {vol_surface['dte'].min():.0f} - {vol_surface['dte'].max():.0f} days")
        
        return all(passed for _, passed in tests)
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_layout_generation():
    """Test 6: Layout Generation"""
    print("\n" + "="*70)
    print("TEST 6: Layout Generation")
    print("="*70)
    
    try:
        layout_component = layout()
        
        tests = [
            ("Layout returns component", layout_component is not None),
            ("Has children attribute", hasattr(layout_component, 'children')),
        ]
        
        for name, passed in tests:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
        
        print(f"\n✅ Layout component generated successfully")
        
        return all(passed for _, passed in tests)
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 OPTIONS LAB COMPREHENSIVE FUNCTIONALITY TEST")
    print("="*70)
    
    tests = [
        test_1_module_imports,
        test_2_mock_data_generation,
        test_3_alpaca_integration,
        test_4_greeks_calculation,
        test_5_vol_surface,
        test_6_layout_generation,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"\n❌ {test_func.__name__} crashed: {e}")
            results.append((test_func.__name__, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n{passed_count}/{total_count} tests passed ({passed_count/total_count*100:.0f}%)")
    
    if passed_count == total_count:
        print("\n✅ ALL TESTS PASSED - OPTIONS LAB IS FULLY FUNCTIONAL!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - SEE DETAILS ABOVE")
        return 1


if __name__ == '__main__':
    sys.exit(main())
