#!/usr/bin/env python3
"""
Phase Pre-24 Direct Callback Harness
Tests all callbacks programmatically before E2E Playwright validation.
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard')

def log_test(category, test_name, status, details=""):
    """Log test result with timestamp."""
    timestamp = datetime.now().isoformat()
    result = {
        'timestamp': timestamp,
        'category': category,
        'test': test_name,
        'status': status,
        'details': details
    }
    print(f"[{status.upper()}] {category} → {test_name}: {details}")
    return result

def test_imports():
    """Loop 1: Import and lint validation."""
    results = []
    
    print("\n" + "="*80)
    print("LOOP 1: IMPORT & LINT VALIDATION")
    print("="*80)
    
    # Test critical imports
    modules_to_test = [
        ('financial_dashboard.tabs.home', 'Home Tab'),
        ('financial_dashboard.tabs.strategy_lab.callbacks', 'Strategy Lab Callbacks'),
        ('financial_dashboard.tabs.options_lab.callbacks', 'Options Lab Callbacks'),
        ('financial_dashboard.tabs.weekly_picks', 'Weekly Picks'),
        ('financial_dashboard.tabs.monthly_picks', 'Monthly Picks'),
        ('financial_dashboard.tabs.portfolio_tab', 'Portfolio Tab'),
        ('financial_dashboard.tabs.market_forecast', 'Market Forecast'),
        ('observability.sentry_config', 'Sentry Config'),
        ('observability.datadog_config', 'Datadog Config'),
    ]
    
    for module_name, desc in modules_to_test:
        try:
            __import__(module_name, fromlist=[''])
            results.append(log_test('import', desc, 'pass', f'{module_name} imported'))
        except Exception as e:
            results.append(log_test('import', desc, 'fail', f'{module_name}: {str(e)[:100]}'))
    
    return results

def test_home_tab_callbacks():
    """Test Home tab data callbacks."""
    results = []
    
    print("\n" + "="*80)
    print("LOOP 2: HOME TAB CALLBACKS")
    print("="*80)
    
    try:
        # Check if Home tab callbacks exist
        from financial_dashboard.tabs import home
        
        # Test if home module has layout function
        if hasattr(home, 'layout'):
            results.append(log_test('callback', 'Home Tab Layout', 'pass', 
                                   'layout function exists'))
        else:
            results.append(log_test('callback', 'Home Tab Layout', 'fail',
                                   'layout function missing'))
        
        # Check for placeholder patterns
        import inspect
        source = inspect.getsource(home)
        placeholder_count = source.count('placeholder') + source.count('TODO') + source.count('FIXME')
        
        if placeholder_count > 0:
            results.append(log_test('callback', 'Home Tab Placeholders', 'warn',
                                   f'{placeholder_count} placeholders found'))
        else:
            results.append(log_test('callback', 'Home Tab Placeholders', 'pass',
                                   'No obvious placeholders'))
            
    except Exception as e:
        results.append(log_test('callback', 'Home Tab', 'fail', str(e)[:200]))
    
    return results

def test_strategy_lab_sync():
    """Test Strategy Lab backtest and subtab sync."""
    results = []
    
    print("\n" + "="*80)
    print("LOOP 2: STRATEGY LAB SYNC")
    print("="*80)
    
    try:
        from financial_dashboard.tabs.strategy_lab import callbacks as sl_callbacks
        
        # Check for backtest execution callback
        import inspect
        source = inspect.getsource(sl_callbacks)
        
        has_backtest = 'run_backtest' in source or 'execute_backtest' in source
        has_results_update = 'update_results' in source or 'sl-equity-curve' in source
        has_benchmark_update = 'update_benchmark' in source or 'sl-benchmark' in source
        has_risk_update = 'update_risk' in source or 'sl-risk' in source
        
        if has_backtest:
            results.append(log_test('callback', 'Strategy Lab Backtest', 'pass',
                                   'Backtest callback found'))
        else:
            results.append(log_test('callback', 'Strategy Lab Backtest', 'fail',
                                   'Backtest callback not found'))
        
        if has_results_update:
            results.append(log_test('callback', 'Strategy Lab Results Tab', 'pass',
                                   'Results update callback found'))
        else:
            results.append(log_test('callback', 'Strategy Lab Results Tab', 'warn',
                                   'Results update callback questionable'))
        
        if has_benchmark_update:
            results.append(log_test('callback', 'Strategy Lab Benchmark Tab', 'pass',
                                   'Benchmark update callback found'))
        else:
            results.append(log_test('callback', 'Strategy Lab Benchmark Tab', 'fail',
                                   'Benchmark update callback missing'))
        
        if has_risk_update:
            results.append(log_test('callback', 'Strategy Lab Risk Tab', 'pass',
                                   'Risk update callback found'))
        else:
            results.append(log_test('callback', 'Strategy Lab Risk Tab', 'fail',
                                   'Risk update callback missing'))
            
    except Exception as e:
        results.append(log_test('callback', 'Strategy Lab', 'fail', str(e)[:200]))
    
    return results

def test_options_lab_forecast():
    """Test Options Lab generate forecast callback."""
    results = []
    
    print("\n" + "="*80)
    print("LOOP 2: OPTIONS LAB FORECAST")
    print("="*80)
    
    try:
        from financial_dashboard.tabs.options_lab import callbacks as ol_callbacks
        
        import inspect
        source = inspect.getsource(ol_callbacks)
        
        has_forecast = 'generate_forecast' in source or 'options-forecast-btn' in source
        has_forecast_output = 'options-forecast-results' in source
        
        if has_forecast:
            results.append(log_test('callback', 'Options Lab Forecast Callback', 'pass',
                                   'Forecast callback found'))
        else:
            results.append(log_test('callback', 'Options Lab Forecast Callback', 'fail',
                                   'Forecast callback not found'))
        
        if has_forecast_output:
            results.append(log_test('callback', 'Options Lab Forecast Output', 'pass',
                                   'Forecast output binding found'))
        else:
            results.append(log_test('callback', 'Options Lab Forecast Output', 'fail',
                                   'Forecast output binding missing'))
            
    except Exception as e:
        results.append(log_test('callback', 'Options Lab', 'fail', str(e)[:200]))
    
    return results

def test_picks_refresh():
    """Test Weekly/Monthly Picks price refresh."""
    results = []
    
    print("\n" + "="*80)
    print("LOOP 2: PICKS PRICE REFRESH")
    print("="*80)
    
    try:
        from financial_dashboard.tabs import weekly_picks, monthly_picks
        
        import inspect
        
        # Check weekly picks
        wp_source = inspect.getsource(weekly_picks)
        has_wp_refresh = 'refresh' in wp_source.lower() or 'update_price' in wp_source
        
        if has_wp_refresh:
            results.append(log_test('callback', 'Weekly Picks Refresh', 'pass',
                                   'Refresh mechanism found'))
        else:
            results.append(log_test('callback', 'Weekly Picks Refresh', 'warn',
                                   'Refresh mechanism unclear'))
        
        # Check monthly picks
        mp_source = inspect.getsource(monthly_picks)
        has_mp_refresh = 'refresh' in mp_source.lower() or 'update_price' in mp_source
        
        if has_mp_refresh:
            results.append(log_test('callback', 'Monthly Picks Refresh', 'pass',
                                   'Refresh mechanism found'))
        else:
            results.append(log_test('callback', 'Monthly Picks Refresh', 'warn',
                                   'Refresh mechanism unclear'))
            
    except Exception as e:
        results.append(log_test('callback', 'Picks', 'fail', str(e)[:200]))
    
    return results

def test_observability_stubs():
    """Test observability instrumentation and stubs."""
    results = []
    
    print("\n" + "="*80)
    print("OBSERVABILITY VALIDATION")
    print("="*80)
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Test Sentry
    try:
        from observability import sentry_config
        
        sentry_dsn = os.getenv('SENTRY_DSN', '')
        if sentry_dsn:
            results.append(log_test('observability', 'Sentry', 'pass',
                                   'SENTRY_DSN configured'))
        else:
            # Test stub
            stub_path = 'logs/sentry_stub.log'
            if os.path.exists(stub_path) or hasattr(sentry_config, 'capture_exception'):
                results.append(log_test('observability', 'Sentry Stub', 'pass',
                                       'Sentry stub available'))
            else:
                results.append(log_test('observability', 'Sentry Stub', 'warn',
                                       'Sentry not configured, stub recommended'))
    except Exception as e:
        results.append(log_test('observability', 'Sentry', 'fail', str(e)[:100]))
    
    # Test Datadog
    try:
        from observability import datadog_config
        
        dd_enabled = os.getenv('DATADOG_ENABLED', 'false').lower() == 'true'
        if dd_enabled:
            results.append(log_test('observability', 'Datadog', 'pass',
                                   'DATADOG_ENABLED=true'))
        else:
            # Test stub
            if hasattr(datadog_config, 'metric_timing'):
                results.append(log_test('observability', 'Datadog Stub', 'pass',
                                       'Datadog instrumentation available'))
            else:
                results.append(log_test('observability', 'Datadog Stub', 'warn',
                                       'Datadog not configured'))
    except Exception as e:
        results.append(log_test('observability', 'Datadog', 'fail', str(e)[:100]))
    
    return results

def test_css_input_colors():
    """Test CSS for black input text."""
    results = []
    
    print("\n" + "="*80)
    print("CSS INPUT COLOR VALIDATION")
    print("="*80)
    
    css_files = list(Path('financial_dashboard/assets').glob('*.css')) if Path('financial_dashboard/assets').exists() else []
    
    found_black_input = False
    for css_file in css_files:
        try:
            content = css_file.read_text()
            if 'input' in content and 'color' in content and '#000' in content:
                found_black_input = True
                results.append(log_test('css', f'Input Color - {css_file.name}', 'pass',
                                       'Black input color rule found'))
                break
        except:
            pass
    
    if not found_black_input:
        results.append(log_test('css', 'Input Color', 'fail',
                               'Black input color rule not found in CSS'))
    
    return results

def main():
    """Run all tests and generate report."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              🔧 PHASE PRE-24 DIRECT CALLBACK HARNESS 🔧              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    start_time = time.time()
    all_results = []
    
    # Run all test groups
    all_results.extend(test_imports())
    all_results.extend(test_home_tab_callbacks())
    all_results.extend(test_strategy_lab_sync())
    all_results.extend(test_options_lab_forecast())
    all_results.extend(test_picks_refresh())
    all_results.extend(test_observability_stubs())
    all_results.extend(test_css_input_colors())
    
    # Calculate summary
    total = len(all_results)
    passed = len([r for r in all_results if r['status'] == 'pass'])
    failed = len([r for r in all_results if r['status'] == 'fail'])
    warned = len([r for r in all_results if r['status'] == 'warn'])
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warned}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Execution Time: {time.time() - start_time:.2f}s")
    
    # Save results
    os.makedirs('test-artifacts/pre24', exist_ok=True)
    
    output = {
        'timestamp': datetime.now().isoformat(),
        'execution_time_seconds': time.time() - start_time,
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'warnings': warned,
            'success_rate': success_rate
        },
        'results': all_results
    }
    
    with open('test-artifacts/pre24/phase_pre24_callback_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Results saved: test-artifacts/pre24/phase_pre24_callback_results.json")
    
    # Exit with appropriate code
    if failed > 0:
        print("\n❌ HARNESS FAILED - Fixes required")
        sys.exit(1)
    elif warned > 0:
        print("\n⚠️  HARNESS PASSED WITH WARNINGS")
        sys.exit(0)
    else:
        print("\n✅ HARNESS PASSED - All tests successful")
        sys.exit(0)

if __name__ == '__main__':
    main()
