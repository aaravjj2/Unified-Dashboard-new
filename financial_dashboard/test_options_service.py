#!/usr/bin/env python3
"""
Quick test script for Options Trading Service
Tests basic functionality without requiring API keys
"""

import sys
import yaml
from pathlib import Path

def test_config():
    """Test configuration loading."""
    print("Testing configuration loading...")
    config_path = Path('options_config.yaml')
    if not config_path.exists():
        print("  ✗ options_config.yaml not found")
        return False
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    required_sections = ['api', 'strategies', 'risk', 'alerts', 'service']
    for section in required_sections:
        if section not in config:
            print(f"  ✗ Missing section: {section}")
            return False
    
    print("  ✓ Configuration loaded successfully")
    return True

def test_imports():
    """Test all module imports."""
    print("\nTesting module imports...")
    
    try:
        from utils.finnhub_client import FinnhubClient
        print("  ✓ FinnhubClient imported")
    except Exception as e:
        print(f"  ✗ FinnhubClient import failed: {e}")
        return False
    
    try:
        from utils.alpaca_trader import AlpacaTrader
        print("  ✓ AlpacaTrader imported")
    except Exception as e:
        print(f"  ✗ AlpacaTrader import failed: {e}")
        return False
    
    try:
        from utils.risk_manager import RiskManager
        print("  ✓ RiskManager imported")
    except Exception as e:
        print(f"  ✗ RiskManager import failed: {e}")
        return False
    
    try:
        from utils.alerter import Alerter, AlertSeverity, AlertCategory
        print("  ✓ Alerter imported")
    except Exception as e:
        print(f"  ✗ Alerter import failed: {e}")
        return False
    
    try:
        from strategies.base_strategy import BaseStrategy
        print("  ✓ BaseStrategy imported")
    except Exception as e:
        print(f"  ✗ BaseStrategy import failed: {e}")
        return False
    
    try:
        from strategies.covered_call_screener import CoveredCallScreener
        print("  ✓ CoveredCallScreener imported")
    except Exception as e:
        print(f"  ✗ CoveredCallScreener import failed: {e}")
        return False
    
    return True

def test_risk_manager():
    """Test risk manager instantiation and basic functions."""
    print("\nTesting Risk Manager...")
    
    try:
        from utils.risk_manager import RiskManager
        
        config = {
            'max_position_size_per_ticker': 1000.0,
            'max_total_exposure': 10000.0,
            'max_daily_loss': 500.0
        }
        
        rm = RiskManager(config=config)
        print("  ✓ RiskManager instantiated")
        
        # Test risk check
        trade = {
            'symbol': 'TEST',
            'quantity': 1,
            'side': 'buy',
            'estimated_cost': 100.0
        }
        
        positions = []
        account = {'buying_power': 10000.0, 'portfolio_value': 50000.0}
        
        approved, reason = rm.check_trade_risk(trade, positions, account)
        if approved:
            print(f"  ✓ Risk check passed: {reason}")
        else:
            print(f"  ✗ Risk check failed unexpectedly: {reason}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ RiskManager test failed: {e}")
        return False

def test_alerter():
    """Test alerter instantiation and basic functions."""
    print("\nTesting Alerter...")
    
    try:
        from utils.alerter import Alerter, AlertSeverity, AlertCategory
        
        config = {
            'log_to_file': False  # Don't create log file during test
        }
        
        alerter = Alerter(config=config)
        print("  ✓ Alerter instantiated")
        
        # Send test alert
        alerter.send_alert(
            "Test alert message",
            AlertSeverity.INFO,
            AlertCategory.SYSTEM
        )
        print("  ✓ Alert sent successfully")
        
        # Get recent alerts
        alerts = alerter.get_recent_alerts(limit=10)
        if len(alerts) > 0:
            print(f"  ✓ Retrieved {len(alerts)} alert(s)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Alerter test failed: {e}")
        return False

def test_strategy():
    """Test strategy instantiation."""
    print("\nTesting Strategy System...")
    
    try:
        from strategies.covered_call_screener import CoveredCallScreener
        
        config = {
            'enabled': True,
            'target_delta': 0.30,
            'min_premium': 0.50
        }
        
        strategy = CoveredCallScreener(config=config)
        print("  ✓ CoveredCallScreener instantiated")
        
        status = strategy.get_status()
        print(f"  ✓ Strategy status: {status['name']}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Strategy test failed: {e}")
        return False

def test_fastapi_import():
    """Test FastAPI import."""
    print("\nTesting FastAPI...")
    
    try:
        from fastapi import FastAPI
        print("  ✓ FastAPI imported")
        
        app = FastAPI(title="Test App")
        print("  ✓ FastAPI app instantiated")
        
        return True
        
    except Exception as e:
        print(f"  ✗ FastAPI test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("Options Trading Service - Quick Test")
    print("=" * 70)
    
    tests = [
        ("Configuration", test_config),
        ("Imports", test_imports),
        ("Risk Manager", test_risk_manager),
        ("Alerter", test_alerter),
        ("Strategy", test_strategy),
        ("FastAPI", test_fastapi_import),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print("-" * 70)
    print(f"  {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 All tests passed! Service is ready to start.")
        print("\nNext steps:")
        print("  1. Add API keys to keys.env (FINNHUB_API_KEY, ALPACA_API_KEY, ALPACA_API_SECRET)")
        print("  2. Run: python3 options_service.py")
        print("  3. Visit: http://localhost:8060/docs")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix before starting service.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
