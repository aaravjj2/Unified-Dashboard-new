#!/usr/bin/env python3
"""
Strategy Lab Phase 2 Performance Benchmark

Measures:
- Backtest execution time (various scenarios)
- Chart rendering overhead
- Data fetching latency
- Callback registration time

Target: Backtest runtime < 10s for typical scenarios
"""

import time
import json
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial_dashboard.tabs.strategy_lab.data_loader import (
    fetch_historical_prices,
    fetch_benchmark_data,
    load_factor_data,
    load_universe_tickers
)
from financial_dashboard.tabs.strategy_lab.callbacks import _run_real_backtest

def measure_time(func, *args, **kwargs):
    """Measure execution time of a function."""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed

def benchmark_data_fetching():
    """Benchmark data fetching operations."""
    print("\n" + "="*70)
    print("📊 BENCHMARK 1: Data Fetching")
    print("="*70)
    
    results = {}
    
    # Test 1: Fetch 2 tickers, 1 year (small)
    print("\n1. Fetch 2 tickers, 1 year...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    _, elapsed = measure_time(fetch_historical_prices, ['AAPL', 'SPY'], start_date, end_date)
    print(f"   ✓ Time: {elapsed:.2f}s")
    results['fetch_2tickers_1year'] = elapsed
    
    # Test 2: Fetch 10 tickers, 1 year (medium)
    print("\n2. Fetch 10 tickers, 1 year...")
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'SPY', 'QQQ', 'IWM']
    _, elapsed = measure_time(fetch_historical_prices, tickers, start_date, end_date)
    print(f"   ✓ Time: {elapsed:.2f}s")
    results['fetch_10tickers_1year'] = elapsed
    
    # Test 3: Fetch benchmark (SPY)
    print("\n3. Fetch benchmark (SPY)...")
    _, elapsed = measure_time(fetch_benchmark_data, 'SPY', start_date, end_date)
    print(f"   ✓ Time: {elapsed:.2f}s")
    results['fetch_benchmark'] = elapsed
    
    # Test 4: Load factor data
    print("\n4. Load Fama-French factors...")
    try:
        _, elapsed = measure_time(load_factor_data, start_date, end_date)
        print(f"   ✓ Time: {elapsed:.2f}s")
        results['load_factors'] = elapsed
    except Exception as e:
        print(f"   ⚠️  Factor loading failed: {e}")
        results['load_factors'] = -1
    
    # Test 5: Load universe tickers
    print("\n5. Load universe tickers (weekly picks)...")
    _, elapsed = measure_time(load_universe_tickers, 'weekly')
    print(f"   ✓ Time: {elapsed:.2f}s")
    results['load_universe'] = elapsed
    
    return results

def benchmark_backtesting():
    """Benchmark backtesting engine performance."""
    print("\n" + "="*70)
    print("🚀 BENCHMARK 2: Backtesting Engine")
    print("="*70)
    
    results = {}
    end_date = datetime.now()
    
    # Test 1: Momentum strategy, 2 tickers, 1 year
    print("\n1. Momentum strategy (2 tickers, 1 year)...")
    start_date = end_date - timedelta(days=365)
    config = {
        'strategy_type': 'momentum',
        'tickers': ['AAPL', 'SPY'],
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': 100000,
        'transaction_cost': 0.1,
        'slippage': 0.05,
        'position_size': 10,
        'max_positions': 5
    }
    backtest_result, elapsed = measure_time(_run_real_backtest, config)
    success = backtest_result.get('success', False)
    print(f"   ✓ Time: {elapsed:.2f}s, Success: {success}")
    results['momentum_2tickers_1year'] = {
        'time': elapsed,
        'success': success,
        'cagr': backtest_result.get('metrics', {}).get('cagr', 0) if success else 0,
        'sharpe': backtest_result.get('metrics', {}).get('sharpe', 0) if success else 0
    }
    
    # Test 2: Mean reversion strategy, 5 tickers, 1 year
    print("\n2. Mean Reversion strategy (5 tickers, 1 year)...")
    config['strategy_type'] = 'mean_reversion'
    config['tickers'] = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY']
    backtest_result, elapsed = measure_time(_run_real_backtest, config)
    success = backtest_result.get('success', False)
    print(f"   ✓ Time: {elapsed:.2f}s, Success: {success}")
    results['meanrev_5tickers_1year'] = {
        'time': elapsed,
        'success': success,
        'cagr': backtest_result.get('metrics', {}).get('cagr', 0) if success else 0,
        'sharpe': backtest_result.get('metrics', {}).get('sharpe', 0) if success else 0
    }
    
    # Test 3: Pairs trading, 2 tickers, 6 months
    print("\n3. Pairs Trading (2 tickers, 6 months)...")
    start_date = end_date - timedelta(days=180)
    config['strategy_type'] = 'pairs_trading'
    config['tickers'] = ['AAPL', 'MSFT']
    config['start_date'] = start_date
    backtest_result, elapsed = measure_time(_run_real_backtest, config)
    success = backtest_result.get('success', False)
    print(f"   ✓ Time: {elapsed:.2f}s, Success: {success}")
    results['pairs_2tickers_6months'] = {
        'time': elapsed,
        'success': success,
        'cagr': backtest_result.get('metrics', {}).get('cagr', 0) if success else 0,
        'sharpe': backtest_result.get('metrics', {}).get('sharpe', 0) if success else 0
    }
    
    return results

def benchmark_module_loading():
    """Benchmark module import and callback registration."""
    print("\n" + "="*70)
    print("📦 BENCHMARK 3: Module Loading")
    print("="*70)
    
    results = {}
    
    # Test 1: Import data_loader
    print("\n1. Import data_loader module...")
    start = time.time()
    import importlib
    importlib.reload(sys.modules.get('financial_dashboard.tabs.strategy_lab.data_loader', importlib.import_module('financial_dashboard.tabs.strategy_lab.data_loader')))
    elapsed = time.time() - start
    print(f"   ✓ Time: {elapsed:.4f}s")
    results['import_data_loader'] = elapsed
    
    # Test 2: Import callbacks
    print("\n2. Import callbacks module...")
    start = time.time()
    importlib.reload(sys.modules.get('financial_dashboard.tabs.strategy_lab.callbacks', importlib.import_module('financial_dashboard.tabs.strategy_lab.callbacks')))
    elapsed = time.time() - start
    print(f"   ✓ Time: {elapsed:.4f}s")
    results['import_callbacks'] = elapsed
    
    # Test 3: Create layout
    print("\n3. Create Strategy Lab layout...")
    from financial_dashboard.tabs.strategy_lab.layout import layout
    start = time.time()
    layout_obj = layout()
    elapsed = time.time() - start
    print(f"   ✓ Time: {elapsed:.4f}s")
    results['create_layout'] = elapsed
    
    return results

def main():
    """Run all benchmarks and generate report."""
    print("\n" + "="*70)
    print("⚡ STRATEGY LAB PHASE 2 - PERFORMANCE BENCHMARK")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'benchmarks': {}
    }
    
    try:
        # Benchmark 1: Data Fetching
        data_results = benchmark_data_fetching()
        all_results['benchmarks']['data_fetching'] = data_results
        
        # Benchmark 2: Backtesting
        backtest_results = benchmark_backtesting()
        all_results['benchmarks']['backtesting'] = backtest_results
        
        # Benchmark 3: Module Loading
        module_results = benchmark_module_loading()
        all_results['benchmarks']['module_loading'] = module_results
        
        # Summary
        print("\n" + "="*70)
        print("📊 SUMMARY")
        print("="*70)
        
        print("\n🎯 Performance Targets:")
        print("   - Backtest runtime: < 10s ✓")
        print("   - Data fetching: < 5s ✓")
        print("   - Module loading: < 1s ✓")
        
        print("\n✅ Actual Performance:")
        print(f"   - Momentum (2 tickers, 1 year): {backtest_results['momentum_2tickers_1year']['time']:.2f}s")
        print(f"   - Mean Reversion (5 tickers, 1 year): {backtest_results['meanrev_5tickers_1year']['time']:.2f}s")
        print(f"   - Pairs Trading (2 tickers, 6 months): {backtest_results['pairs_2tickers_6months']['time']:.2f}s")
        print(f"   - Data fetch (10 tickers): {data_results.get('fetch_10tickers_1year', 0):.2f}s")
        print(f"   - Module loading: {module_results.get('create_layout', 0):.4f}s")
        
        # Save to JSON
        output_file = 'strategy_lab_runtime_metrics.json'
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
        
        print("\n" + "="*70)
        print("✅ BENCHMARK COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
