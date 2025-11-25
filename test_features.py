#!/usr/bin/env python3
"""
Manual test script for IV Surface and Market Forecast features
"""

import sys
import os

# Add project to path
sys.path.insert(0, '/home/aarav/unified-dashboard')

def test_iv_surface():
    """Test IV Surface computation"""
    print("\n" + "="*60)
    print("TESTING IV SURFACE")
    print("="*60)
    
    try:
        from financial_dashboard.services.iv_surface_service import compute_iv_surface
        
        print("✓ IV Surface service imported successfully")
        
        # Test with AAPL
        print("\nComputing IV Surface for AAPL...")
        result = compute_iv_surface(
            ticker="AAPL",
            days_to_expiry=30,
            strike_range=0.15
        )
        
        if result and 'surface_data' in result:
            print(f"✅ IV Surface computed successfully!")
            print(f"   - Surface data points: {len(result.get('surface_data', []))}")
            print(f"   - Has figure: {'figure' in result}")
            return True
        else:
            print(f"❌ IV Surface computation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ IV Surface test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_market_forecast():
    """Test Market Forecast"""
    print("\n" + "="*60)
    print("TESTING MARKET FORECAST")
    print("="*60)
    
    try:
        from financial_dashboard.services.forecast_service import generate_forecast
        
        print("✓ Forecast service imported successfully")
        
        # Test with AAPL
        print("\nGenerating forecast for AAPL...")
        result = generate_forecast(
            ticker="AAPL",
            days_ahead=30
        )
        
        if result and 'forecast' in result:
            print(f"✅ Forecast generated successfully!")
            print(f"   - Forecast points: {len(result.get('forecast', []))}")
            print(f"   - Has figure: {'figure' in result}")
            print(f"   - Metrics: {list(result.get('metrics', {}).keys())}")
            return True
        else:
            print(f"❌ Forecast generation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Forecast test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_signals():
    """Test Signals scanning"""
    print("\n" + "="*60)
    print("TESTING SIGNALS SCANNER")
    print("="*60)
    
    try:
        from financial_dashboard.services.signals_service import scan_signals
        
        print("✓ Signals service imported successfully")
        
        # Test signal scanning
        print("\nScanning for signals...")
        result = scan_signals(
            tickers=["AAPL", "MSFT", "GOOGL"],
            min_iv_rank=50
        )
        
        if result and 'signals' in result:
            print(f"✅ Signals scanned successfully!")
            print(f"   - Signals found: {len(result.get('signals', []))}")
            return True
        else:
            print(f"❌ Signal scanning failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Signals test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 DASHBOARD FEATURE TESTING")
    print("="*60)
    
    results = {
        "IV Surface": test_iv_surface(),
        "Market Forecast": test_market_forecast(),
        "Signals Scanner": test_signals()
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for feature, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {feature}")
    
    print("\n")
    sys.exit(0 if all(results.values()) else 1)
