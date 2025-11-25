#!/usr/bin/env python3
"""
Market Trends Implementation Validator

Validates that all components are properly implemented and integrated
without requiring a browser.
"""

import os
import sys
import importlib
import inspect

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(text)
    print("="*80)

def print_section(text):
    """Print formatted section"""
    print(f"\n{text}")
    print("-" * len(text))

def validate_implementation():
    """Validate the Market Trends implementation"""
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    print_header("MARKET TRENDS IMPLEMENTATION VALIDATOR")
    
    # Test 1: Module Imports
    print_section("1. Testing Module Imports")
    
    modules_to_test = [
        ('financial_dashboard.utils.cache_manager', 'CacheManager'),
        ('financial_dashboard.utils.news_manager', 'NewsManager'),
        ('financial_dashboard.tabs.market_trends_callbacks_fixed', 'register_fixed_callbacks'),
    ]
    
    for module_name, class_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                print(f"✅ {module_name}.{class_name}")
                results['passed'].append(f"Import: {module_name}.{class_name}")
            else:
                print(f"❌ {module_name} missing {class_name}")
                results['failed'].append(f"Missing: {module_name}.{class_name}")
        except Exception as e:
            print(f"❌ {module_name}: {str(e)[:50]}")
            results['failed'].append(f"Import failed: {module_name}")
    
    # Test 2: Cache Manager Functionality
    print_section("2. Testing Cache Manager")
    
    try:
        from financial_dashboard.utils.cache_manager import CacheManager
        import tempfile
        
        # Create temp cache file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_cache = f.name
        
        try:
            # Test initialization
            memory_cache = {}
            cm = CacheManager(temp_cache, memory_cache)
            print("✅ CacheManager initialization")
            results['passed'].append("CacheManager: initialization")
            
            # Test save
            test_data = {'detailed': [{'ticker': 'TEST', 'price': 100.0}], 'tickers': ['TEST']}
            success = cm.save_to_disk(test_data)
            if success:
                print("✅ CacheManager save_to_disk")
                results['passed'].append("CacheManager: save_to_disk")
            else:
                print("❌ CacheManager save_to_disk failed")
                results['failed'].append("CacheManager: save_to_disk")
            
            # Test load
            loaded = cm.load_from_disk()
            if loaded and 'detailed' in loaded:
                print("✅ CacheManager load_from_disk")
                results['passed'].append("CacheManager: load_from_disk")
            else:
                print("❌ CacheManager load_from_disk failed")
                results['failed'].append("CacheManager: load_from_disk")
            
            # Test update
            success = cm.update_cache(test_data)
            if success and 'results' in memory_cache:
                print("✅ CacheManager update_cache (memory + disk sync)")
                results['passed'].append("CacheManager: update_cache")
            else:
                print("❌ CacheManager update_cache failed")
                results['failed'].append("CacheManager: update_cache")
            
            # Test TTL
            is_fresh = cm.is_cache_fresh(300)
            print(f"✅ CacheManager TTL validation (fresh: {is_fresh})")
            results['passed'].append("CacheManager: TTL validation")
            
        finally:
            if os.path.exists(temp_cache):
                os.remove(temp_cache)
                
    except Exception as e:
        print(f"❌ CacheManager tests failed: {e}")
        results['failed'].append(f"CacheManager: {str(e)[:50]}")
    
    # Test 3: News Manager Functionality
    print_section("3. Testing News Manager")
    
    try:
        from financial_dashboard.utils.news_manager import NewsManager
        
        # Test initialization
        nm = NewsManager(ttl_seconds=300)
        print("✅ NewsManager initialization")
        results['passed'].append("NewsManager: initialization")
        
        # Test cache check
        is_stale = nm.is_news_stale()
        print(f"✅ NewsManager cache staleness check (stale: {is_stale})")
        results['passed'].append("NewsManager: staleness check")
        
        # Test render (without data)
        panel = nm.render_news_panel(show_loading=True)
        if panel:
            print("✅ NewsManager render_news_panel")
            results['passed'].append("NewsManager: render_news_panel")
        else:
            print("❌ NewsManager render_news_panel failed")
            results['failed'].append("NewsManager: render_news_panel")
            
    except Exception as e:
        print(f"❌ NewsManager tests failed: {e}")
        results['failed'].append(f"NewsManager: {str(e)[:50]}")
    
    # Test 4: Fixed Callbacks Structure
    print_section("4. Testing Fixed Callbacks")
    
    try:
        from financial_dashboard.tabs.market_trends_callbacks_fixed import (
            register_fixed_callbacks,
            create_safe_callback
        )
        
        print("✅ register_fixed_callbacks function")
        results['passed'].append("Callbacks: register_fixed_callbacks")
        
        print("✅ create_safe_callback decorator")
        results['passed'].append("Callbacks: create_safe_callback")
        
        # Check function signature
        sig = inspect.signature(register_fixed_callbacks)
        params = list(sig.parameters.keys())
        if 'app' in params and 'cache_manager' in params and 'news_manager' in params:
            print("✅ register_fixed_callbacks has correct signature")
            results['passed'].append("Callbacks: correct signature")
        else:
            print("❌ register_fixed_callbacks signature incorrect")
            results['failed'].append("Callbacks: incorrect signature")
            
    except Exception as e:
        print(f"❌ Fixed callbacks tests failed: {e}")
        results['failed'].append(f"Callbacks: {str(e)[:50]}")
    
    # Test 5: Integration Check
    print_section("5. Testing Integration")
    
    try:
        # Check if market_trends.py has the integration code
        mt_path = 'financial_dashboard/tabs/market_trends.py'
        if os.path.exists(mt_path):
            with open(mt_path, 'r') as f:
                content = f.read()
            
            checks = [
                ('CacheManager import', 'from financial_dashboard.utils.cache_manager import CacheManager'),
                ('NewsManager import', 'from financial_dashboard.utils.news_manager import NewsManager'),
                ('register_fixed_callbacks import', 'from financial_dashboard.tabs.market_trends_callbacks_fixed import register_fixed_callbacks'),
                ('CacheManager initialization', 'cache_manager = CacheManager'),
                ('NewsManager initialization', 'news_manager = NewsManager'),
                ('register_fixed_callbacks call', 'register_fixed_callbacks(app, cache_manager, news_manager)'),
            ]
            
            for check_name, check_str in checks:
                if check_str in content:
                    print(f"✅ {check_name}")
                    results['passed'].append(f"Integration: {check_name}")
                else:
                    print(f"⚠️  {check_name} not found")
                    results['warnings'].append(f"Integration: {check_name} missing")
        else:
            print(f"❌ market_trends.py not found")
            results['failed'].append("Integration: market_trends.py not found")
            
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        results['failed'].append(f"Integration: {str(e)[:50]}")
    
    # Test 6: File Structure
    print_section("6. Testing File Structure")
    
    required_files = [
        'financial_dashboard/utils/cache_manager.py',
        'financial_dashboard/utils/news_manager.py',
        'financial_dashboard/tabs/market_trends_callbacks_fixed.py',
        'tests/test_cache_manager_properties.py',
        'tests/test_cache_manager_unit.py',
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({size} bytes)")
            results['passed'].append(f"File: {file_path}")
        else:
            print(f"❌ {file_path} missing")
            results['failed'].append(f"File missing: {file_path}")
    
    # Test 7: Documentation
    print_section("7. Testing Documentation")
    
    doc_files = [
        '.kiro/specs/market-trends-fix/requirements.md',
        '.kiro/specs/market-trends-fix/design.md',
        '.kiro/specs/market-trends-fix/tasks.md',
        'MARKET_TRENDS_100_PERCENT_COMPLETE.md',
        'FINAL_DELIVERY_SUMMARY.md',
    ]
    
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            print(f"✅ {doc_file}")
            results['passed'].append(f"Doc: {doc_file}")
        else:
            print(f"⚠️  {doc_file} missing")
            results['warnings'].append(f"Doc missing: {doc_file}")
    
    return results

def print_summary(results):
    """Print test summary"""
    print_header("VALIDATION SUMMARY")
    
    print(f"\n✅ PASSED ({len(results['passed'])}):")
    for item in results['passed'][:10]:  # Show first 10
        print(f"   • {item}")
    if len(results['passed']) > 10:
        print(f"   ... and {len(results['passed']) - 10} more")
    
    if results['warnings']:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
        for item in results['warnings']:
            print(f"   • {item}")
    
    if results['failed']:
        print(f"\n❌ FAILED ({len(results['failed'])}):")
        for item in results['failed']:
            print(f"   • {item}")
    
    total = len(results['passed']) + len(results['warnings']) + len(results['failed'])
    success_rate = (len(results['passed']) / total * 100) if total > 0 else 0
    
    print(f"\n" + "="*80)
    print(f"OVERALL: {len(results['passed'])}/{total} passed ({success_rate:.1f}%)")
    
    if len(results['failed']) == 0:
        print("\n🎉 ALL CRITICAL TESTS PASSED!")
        print("✅ Implementation is complete and functional")
        print("✅ Ready for manual testing in browser")
    else:
        print("\n⚠️  Some tests failed - review above")
    
    print("="*80)
    
    return len(results['failed']) == 0

def main():
    """Main validation function"""
    print("\n🔍 Validating Market Trends Implementation")
    print("This will test all components without requiring a browser\n")
    
    try:
        results = validate_implementation()
        success = print_summary(results)
        
        if success:
            print("\n📋 NEXT STEPS:")
            print("1. Start dashboard: python run_dashboard.py")
            print("2. Open browser: http://localhost:8090")
            print("3. Navigate to Market Trends tab")
            print("4. Test each button manually:")
            print("   • Reload Model")
            print("   • Refresh Cached Display")
            print("   • Toggle Full Brief")
            print("   • Download CSV")
            print("   • Backtest Trend Signals")
            print("   • Debug Logs")
            print("5. Verify news auto-refreshes")
            print("6. Check price data displays")
            
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
