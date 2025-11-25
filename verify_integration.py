#!/usr/bin/env python3
"""
Verify Market Trends Integration

Quick check that everything is properly integrated.
"""

print("Checking Market Trends integration...")
print()

# Check 1: Imports
print("1. Checking imports...")
try:
    from financial_dashboard.utils.cache_manager import CacheManager
    print("   ✅ CacheManager")
except Exception as e:
    print(f"   ❌ CacheManager: {e}")
    exit(1)

try:
    from financial_dashboard.utils.news_manager import NewsManager
    print("   ✅ NewsManager")
except Exception as e:
    print(f"   ❌ NewsManager: {e}")
    exit(1)

try:
    from financial_dashboard.tabs.market_trends_callbacks_fixed import register_fixed_callbacks
    print("   ✅ register_fixed_callbacks")
except Exception as e:
    print(f"   ❌ register_fixed_callbacks: {e}")
    exit(1)

# Check 2: Integration in market_trends.py
print()
print("2. Checking integration in market_trends.py...")
import os
mt_path = 'financial_dashboard/tabs/market_trends.py'
with open(mt_path, 'r') as f:
    content = f.read()

checks = [
    'from financial_dashboard.utils.cache_manager import CacheManager',
    'from financial_dashboard.utils.news_manager import NewsManager',
    'from financial_dashboard.tabs.market_trends_callbacks_fixed import register_fixed_callbacks',
    'cache_manager = CacheManager',
    'news_manager = NewsManager',
    'register_fixed_callbacks(app, cache_manager, news_manager)',
]

all_good = True
for check in checks:
    if check in content:
        print(f"   ✅ {check[:60]}...")
    else:
        print(f"   ❌ Missing: {check[:60]}...")
        all_good = False

if not all_good:
    print()
    print("❌ Integration incomplete!")
    exit(1)

print()
print("="*70)
print("✅ ALL CHECKS PASSED!")
print("="*70)
print()
print("The integration is complete. To see the changes:")
print()
print("1. STOP the dashboard if it's running (Ctrl+C)")
print("2. START the dashboard: python run_dashboard.py")
print("3. Open browser: http://localhost:8090")
print("4. Navigate to Market Trends tab")
print("5. Test the buttons!")
print()
print("The buttons should now work:")
print("  • Reload Model")
print("  • Refresh Cached Display")
print("  • Toggle Full Brief")
print("  • Download CSV")
print("  • Backtest Trend Signals")
print("  • Debug Logs")
print()
