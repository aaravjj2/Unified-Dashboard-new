#!/usr/bin/env python3
"""
Complete Options Lab End-to-End Validation Suite
Executes all validation steps with detailed logging and artifact capture.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, '.')

# Load environment
from dotenv import load_dotenv
load_dotenv('keys.env')

def ensure_directories():
    """Create required directories for artifacts."""
    dirs = [
        'test-results/options_lab',
        'test-artifacts/options_lab/screenshots',
        'test-artifacts/options_lab/logs',
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

def test_live_data_comprehensive():
    """Step 1: Comprehensive live data verification."""
    print("\n" + "="*70)
    print("STEP 1: LIVE DATA VERIFICATION")
    print("="*70)
    
    from financial_dashboard.tabs.options_lab.data_loader import fetch_options_chain
    
    tickers = ['SPY', 'AAPL', 'QQQ']
    results = {
        'timestamp': datetime.now().isoformat(),
        'tickers': {},
        'summary': {
            'total_tickers': len(tickers),
            'successful': 0,
            'failed': 0,
            'total_expirations': 0,
            'total_contracts': 0,
        }
    }
    
    for ticker in tickers:
        print(f"\n📊 Testing {ticker}...")
        try:
            start_time = time.time()
            chain_data = fetch_options_chain(ticker, use_alpaca=True, use_mock=False)
            load_time = time.time() - start_time
            
            if chain_data.get('error'):
                print(f"   ❌ Error: {chain_data['error']}")
                results['tickers'][ticker] = {'error': chain_data['error']}
                results['summary']['failed'] += 1
                continue
            
            import pandas as pd
            calls = chain_data.get('calls', [])
            puts = chain_data.get('puts', [])
            
            calls_count = len(calls) if isinstance(calls, pd.DataFrame) else 0
            puts_count = len(puts) if isinstance(puts, pd.DataFrame) else 0
            
            # Extract IV range
            iv_range = {'min': 0, 'max': 0, 'avg': 0}
            if isinstance(calls, pd.DataFrame) and not calls.empty and 'impliedVolatility' in calls.columns:
                iv_values = calls['impliedVolatility'].dropna()
                if len(iv_values) > 0:
                    iv_range = {
                        'min': float(iv_values.min()),
                        'max': float(iv_values.max()),
                        'avg': float(iv_values.mean())
                    }
            
            ticker_result = {
                'source': chain_data.get('source', 'unknown'),
                'spot_price': chain_data.get('spot_price', 0),
                'expirations': chain_data.get('expirations', []),
                'expirations_count': len(chain_data.get('expirations', [])),
                'calls_count': calls_count,
                'puts_count': puts_count,
                'total_contracts': calls_count + puts_count,
                'load_time_seconds': round(load_time, 2),
                'iv_range': iv_range,
                'quality_checks': {
                    'has_expirations': len(chain_data.get('expirations', [])) > 0,
                    'min_20_expirations': len(chain_data.get('expirations', [])) >= 20,
                    'has_calls': calls_count > 0,
                    'has_puts': puts_count > 0,
                    'valid_spot': chain_data.get('spot_price', 0) > 0,
                    'load_time_ok': load_time < 3.0,
                }
            }
            
            results['tickers'][ticker] = ticker_result
            results['summary']['successful'] += 1
            results['summary']['total_expirations'] += ticker_result['expirations_count']
            results['summary']['total_contracts'] += ticker_result['total_contracts']
            
            # Display results
            source_badge = {'alpaca': '🟢', 'yfinance': '🟡', 'mock': '🔵'}.get(ticker_result['source'], '⚪')
            print(f"   {source_badge} Source: {ticker_result['source'].upper()}")
            print(f"   💵 Spot: ${ticker_result['spot_price']:.2f}")
            print(f"   📅 Expirations: {ticker_result['expirations_count']}")
            print(f"   📞 Calls: {ticker_result['calls_count']}")
            print(f"   📍 Puts: {ticker_result['puts_count']}")
            print(f"   ⏱️  Load Time: {ticker_result['load_time_seconds']}s")
            print(f"   📊 IV Range: {iv_range['min']:.1%} - {iv_range['max']:.1%} (avg: {iv_range['avg']:.1%})")
            
            # Quality checks
            all_pass = all(ticker_result['quality_checks'].values())
            status = "✅" if all_pass else "⚠️"
            print(f"   {status} Quality: {'All checks pass' if all_pass else 'Some checks failed'}")
            
            for check, passed in ticker_result['quality_checks'].items():
                if not passed:
                    print(f"      ❌ {check}")
            
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            results['tickers'][ticker] = {'error': str(e)}
            results['summary']['failed'] += 1
    
    # Save results
    output_file = Path('test-results/options_lab/step1_live_data.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✅ Successful: {results['summary']['successful']}/{results['summary']['total_tickers']}")
    print(f"📅 Total Expirations: {results['summary']['total_expirations']}")
    print(f"📋 Total Contracts: {results['summary']['total_contracts']}")
    print(f"💾 Results saved: {output_file}")
    print(f"{'='*70}")
    
    return results

def test_callbacks_functional():
    """Verify all callbacks can be registered without errors."""
    print("\n" + "="*70)
    print("STEP 2: CALLBACK VALIDATION")
    print("="*70)
    
    try:
        from financial_dashboard.tabs.options_lab import callbacks
        print("✅ Callbacks module imported")
        print(f"✅ register_callbacks available: {callable(callbacks.register_callbacks)}")
        
        # Test mock Dash app
        from dash import Dash
        import dash_bootstrap_components as dbc
        
        app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        callbacks.register_callbacks(app)
        
        print("✅ Callbacks registered successfully")
        
        # Count registered callbacks
        callback_count = len(app.callback_map)
        print(f"✅ Total callbacks registered: {callback_count}")
        
        return {'success': True, 'callback_count': callback_count}
        
    except Exception as e:
        print(f"❌ Callback validation failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def generate_performance_report(results: Dict[str, Any]):
    """Generate performance metrics report."""
    print("\n" + "="*70)
    print("PERFORMANCE REPORT")
    print("="*70)
    
    if 'tickers' not in results:
        print("⚠️  No performance data available")
        return
    
    print("\n📊 Load Time Performance:")
    for ticker, data in results['tickers'].items():
        if 'load_time_seconds' in data:
            load_time = data['load_time_seconds']
            status = "✅" if load_time < 3.0 else "⚠️"
            print(f"   {status} {ticker}: {load_time}s {'(PASS)' if load_time < 3.0 else '(SLOW)'}")
    
    print("\n📊 Data Volume:")
    for ticker, data in results['tickers'].items():
        if 'total_contracts' in data:
            contracts = data['total_contracts']
            expirations = data.get('expirations_count', 0)
            print(f"   • {ticker}: {contracts} contracts across {expirations} expirations")

def main():
    """Execute complete validation suite."""
    print("="*70)
    print("🎯 OPTIONS LAB COMPLETE VALIDATION SUITE")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    
    # Setup
    ensure_directories()
    
    # Execute validation steps
    test_results = {
        'start_time': datetime.now().isoformat(),
        'steps': {}
    }
    
    # Step 1: Live Data
    step1_results = test_live_data_comprehensive()
    test_results['steps']['live_data'] = step1_results
    
    # Step 2: Callbacks
    step2_results = test_callbacks_functional()
    test_results['steps']['callbacks'] = step2_results
    
    # Performance Report
    generate_performance_report(step1_results)
    
    # Final Summary
    test_results['end_time'] = datetime.now().isoformat()
    test_results['overall_status'] = 'PASS' if step1_results['summary']['successful'] > 0 else 'FAIL'
    
    # Save comprehensive results
    output_file = Path('test-results/options_lab/complete_validation.json')
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"🏁 VALIDATION COMPLETE")
    print(f"{'='*70}")
    print(f"Overall Status: {test_results['overall_status']}")
    print(f"Results saved: {output_file}")
    print(f"{'='*70}\n")
    
    return 0 if test_results['overall_status'] == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
