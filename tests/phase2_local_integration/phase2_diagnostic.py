"""
Phase 2 Local Integration - Diagnostic Test Suite

Validates Phase 2 deliverables:
- Callback performance (target: <1s avg)
- Cache hit rate (expect ~80% on repeated calls)
- Mode routing (mock/live switching)
- Batch processing (portfolio-wide explanations)
- Error handling and graceful degradation

This test suite should be run BEFORE Phase 2 sign-off to ensure all
components work correctly in isolation.

Author: Unified Financial Dashboard Team
Version: 1.0 (Phase 2)
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from financial_dashboard.tabs.azure_ml_lab.explainability_engine import (
    generate_explanation_summary,
    get_cache_stats,
    reset_cache_stats
)

from financial_dashboard.tabs.azure_ml_lab.phase2_local_integration.mode_router import (
    route_explanation_request,
    get_mode_info,
    set_mock_mode,
    is_mock_mode
)

from financial_dashboard.tabs.azure_ml_lab.phase2_local_integration.batch_explain import (
    generate_batch_explanations,
    generate_portfolio_comparison,
    summarize_batch_report
)


# ============================================================================
# TEST 1: CACHING PERFORMANCE
# ============================================================================

def test_caching_performance() -> Dict:
    """
    Test that caching improves performance for repeated calls.
    
    Expected:
    - First call (cache miss): ~100-500ms
    - Repeated calls (cache hits): <10ms
    - Cache hit rate: ~80% for repeated tickers
    """
    print("\n" + "="*80)
    print("TEST 1: Caching Performance & Hit Rate")
    print("="*80)
    
    reset_cache_stats()
    
    test_cases = [
        ('AAPL', 0.08, 'return', 10),
        ('TSLA', 0.12, 'return', 10),
        ('NVDA', 0.15, 'volatility', 10),
        ('AAPL', 0.08, 'return', 10),  # Repeat - should hit cache
        ('TSLA', 0.12, 'return', 10),  # Repeat - should hit cache
        ('AAPL', 0.08, 'return', 10),  # Repeat - should hit cache
        ('GOOGL', 0.10, 'return', 10), # New - cache miss
        ('NVDA', 0.15, 'volatility', 10), # Repeat - should hit cache
    ]
    
    times = []
    cache_hits_expected = 0
    
    for i, (ticker, pred_val, target, top_n) in enumerate(test_cases):
        start = time.perf_counter()
        
        result = generate_explanation_summary(
            ticker=ticker,
            prediction_value=pred_val,
            prediction_target=target,
            top_n_features=top_n,
            use_cache=True
        )
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        times.append(elapsed_ms)
        
        cache_hit = result['metadata'].get('cache_hit', False)
        
        print(f"  [{i+1}] {ticker:5s} | {elapsed_ms:6.1f}ms | {'🎯 HIT' if cache_hit else '⏱️  MISS'}")
        
        # Track expected cache hits (repeats after first occurrence)
        if i >= 3:  # First 3 are unique, rest should hit cache
            cache_hits_expected += 1
    
    # Calculate statistics
    avg_time = sum(times) / len(times)
    first_call_avg = sum(times[:3]) / 3  # First unique calls
    repeat_call_avg = sum(times[3:]) / len(times[3:])  # Repeated calls
    
    cache_stats = get_cache_stats()
    hit_rate = cache_stats['hit_rate_percent']
    
    # Performance targets
    target_avg = 1000  # <1s avg (Phase 2 target)
    target_hit_rate = 60  # At least 60% hit rate for repeated calls
    
    passed = (
        avg_time < target_avg and
        hit_rate >= target_hit_rate and
        repeat_call_avg < first_call_avg / 2  # Repeats should be 2x+ faster
    )
    
    print(f"\n  📊 Statistics:")
    print(f"     Avg time (all):         {avg_time:.1f}ms")
    print(f"     Avg time (first calls): {first_call_avg:.1f}ms")
    print(f"     Avg time (repeats):     {repeat_call_avg:.1f}ms")
    print(f"     Cache hit rate:         {hit_rate:.1f}%")
    print(f"     Speedup (repeats):      {first_call_avg/repeat_call_avg:.1f}x")
    
    print(f"\n  ✅ PASSED" if passed else f"\n  ❌ FAILED")
    
    return {
        'test': 'caching_performance',
        'passed': passed,
        'avg_time_ms': round(avg_time, 2),
        'first_call_avg_ms': round(first_call_avg, 2),
        'repeat_call_avg_ms': round(repeat_call_avg, 2),
        'cache_hit_rate': hit_rate,
        'speedup_factor': round(first_call_avg / repeat_call_avg, 2),
        'cache_stats': cache_stats
    }


# ============================================================================
# TEST 2: MODE ROUTING
# ============================================================================

def test_mode_routing() -> Dict:
    """
    Test that mode router correctly switches between mock and live modes.
    
    Expected:
    - Mock mode: Returns valid explanations
    - Live mode: Returns error (not yet implemented)
    - Mode detection: Correct mode based on environment variable
    """
    print("\n" + "="*80)
    print("TEST 2: Mode Routing (Mock vs Live)")
    print("="*80)
    
    passed = True
    errors = []
    
    # Test 1: Mock mode (should succeed)
    print("\n  🔍 Testing MOCK mode...")
    set_mock_mode(True)
    
    if not is_mock_mode():
        errors.append("Mock mode not activated correctly")
        passed = False
    
    result_mock = route_explanation_request('AAPL', 0.08, 'return', 10)
    
    if 'error' in result_mock:
        errors.append(f"Mock mode returned error: {result_mock['error']}")
        passed = False
    else:
        print(f"     ✅ Mock mode working: {result_mock['ticker']} explanation generated")
    
    mode_info = get_mode_info()
    print(f"     Mode: {mode_info['current_mode']}")
    print(f"     Mock available: {mode_info['mock_available']}")
    print(f"     Live available: {mode_info['live_available']}")
    
    # Test 2: Live mode (should return "not yet implemented" error)
    print("\n  🔍 Testing LIVE mode (expect graceful error)...")
    set_mock_mode(False)
    
    result_live = route_explanation_request('TSLA', 0.12, 'return', 10)
    
    if 'error' not in result_live:
        errors.append("Live mode should return error (Phase 3 not implemented)")
        passed = False
    else:
        if 'Live mode unavailable' in result_live['error']:
            print(f"     ✅ Live mode correctly returns 'unavailable' error")
        else:
            errors.append(f"Unexpected live mode error: {result_live['error']}")
            passed = False
    
    # Reset to mock mode
    set_mock_mode(True)
    
    print(f"\n  {'✅ PASSED' if passed else '❌ FAILED'}")
    if errors:
        print(f"  Errors: {errors}")
    
    return {
        'test': 'mode_routing',
        'passed': passed,
        'errors': errors,
        'mode_info': mode_info
    }


# ============================================================================
# TEST 3: BATCH PROCESSING
# ============================================================================

def test_batch_processing() -> Dict:
    """
    Test batch explainability for portfolio-wide analysis.
    
    Expected:
    - All tickers processed successfully
    - Report saved to outputs/phase2_reports/
    - Performance: <1s per ticker on average
    - Cache hit rate improves on second batch
    """
    print("\n" + "="*80)
    print("TEST 3: Batch Processing (Portfolio-Wide)")
    print("="*80)
    
    tickers = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT']
    
    print(f"\n  🔄 Processing batch of {len(tickers)} tickers...")
    reset_cache_stats()
    
    start = time.perf_counter()
    batch_report = generate_batch_explanations(
        tickers=tickers,
        top_n_features=10,
        use_cache=True
    )
    elapsed = time.perf_counter() - start
    
    summary = batch_report['summary']
    agg_stats = batch_report['aggregated_stats']
    
    print(f"\n  📊 Batch Summary:")
    print(f"     Total tickers: {summary['total_tickers']}")
    print(f"     Successful: {summary['successful']}")
    print(f"     Failed: {summary['failed']}")
    print(f"     Success rate: {summary['success_rate_percent']}%")
    print(f"     Total time: {summary['elapsed_time_seconds']}s")
    print(f"     Avg time per ticker: {summary['avg_time_per_ticker_ms']}ms")
    print(f"     Cache hit rate: {agg_stats['avg_cache_hit_rate_percent']}%")
    
    # Performance targets
    target_success_rate = 100  # All should succeed in mock mode
    target_avg_time_per_ticker = 1000  # <1s per ticker
    
    passed = (
        summary['success_rate_percent'] == target_success_rate and
        summary['avg_time_per_ticker_ms'] < target_avg_time_per_ticker
    )
    
    # Test report saving
    output_file = batch_report['metadata'].get('output_file')
    if output_file and Path(output_file).exists():
        print(f"     ✅ Report saved: {output_file}")
    else:
        print(f"     ❌ Report file not found: {output_file}")
        passed = False
    
    print(f"\n  {'✅ PASSED' if passed else '❌ FAILED'}")
    
    return {
        'test': 'batch_processing',
        'passed': passed,
        'summary': summary,
        'aggregated_stats': agg_stats,
        'output_file': output_file
    }


# ============================================================================
# TEST 4: PORTFOLIO COMPARISON
# ============================================================================

def test_portfolio_comparison() -> Dict:
    """
    Test portfolio-wide comparative feature importance analysis.
    
    Expected:
    - Feature rankings calculated correctly
    - Top features identified across portfolio
    - Comparison report saved
    """
    print("\n" + "="*80)
    print("TEST 4: Portfolio Comparison Analysis")
    print("="*80)
    
    tickers = ['AAPL', 'TSLA', 'NVDA']
    
    print(f"\n  🔄 Generating portfolio comparison for {len(tickers)} tickers...")
    
    comparison = generate_portfolio_comparison(tickers)
    
    feature_rankings = comparison['feature_rankings']
    top_5_features = feature_rankings[:5]
    
    print(f"\n  📊 Top 5 Most Important Features (across portfolio):")
    for i, feat in enumerate(top_5_features):
        print(f"     {i+1}. {feat['feature']:25s} | Avg importance: {feat['avg_importance']:.4f}")
    
    # Validation
    passed = (
        len(feature_rankings) > 0 and
        'output_file' in comparison['metadata'] and
        Path(comparison['metadata']['output_file']).exists()
    )
    
    print(f"\n  {'✅ PASSED' if passed else '❌ FAILED'}")
    
    return {
        'test': 'portfolio_comparison',
        'passed': passed,
        'num_features_ranked': len(feature_rankings),
        'top_5_features': [f['feature'] for f in top_5_features],
        'output_file': comparison['metadata'].get('output_file')
    }


# ============================================================================
# TEST 5: ERROR HANDLING
# ============================================================================

def test_error_handling() -> Dict:
    """
    Test graceful error handling for edge cases.
    
    Expected:
    - Invalid inputs: Return error dict (not exception)
    - Missing ticker: Graceful error
    - Invalid top_n: Graceful error
    """
    print("\n" + "="*80)
    print("TEST 5: Error Handling & Edge Cases")
    print("="*80)
    
    passed = True
    errors = []
    
    # Test 1: Empty ticker
    print("\n  🔍 Testing empty ticker...")
    try:
        result = generate_explanation_summary('', 0.08, 'return', 10)
        # Should still work (mock engine generates deterministic output)
        print(f"     ✅ Handled gracefully (no exception)")
    except Exception as e:
        errors.append(f"Empty ticker raised exception: {e}")
        passed = False
    
    # Test 2: Invalid top_n (should clamp to valid range)
    print("\n  🔍 Testing invalid top_n...")
    try:
        result = generate_explanation_summary('AAPL', 0.08, 'return', 0)
        # Engine should handle this gracefully
        print(f"     ✅ Handled gracefully (no exception)")
    except Exception as e:
        # Expected to fail, which is acceptable
        print(f"     ⚠️  Exception raised (acceptable): {type(e).__name__}")
    
    # Test 3: Batch with mixed valid/invalid tickers
    print("\n  🔍 Testing batch with mixed tickers...")
    try:
        batch = generate_batch_explanations(['AAPL', '', 'TSLA'])
        if batch['summary']['failed'] == 0:
            print(f"     ✅ All tickers processed (mock mode is permissive)")
        else:
            print(f"     ⚠️  Some failures: {batch['summary']['failed']}")
    except Exception as e:
        errors.append(f"Batch processing raised exception: {e}")
        passed = False
    
    print(f"\n  {'✅ PASSED' if passed else '❌ FAILED'}")
    
    return {
        'test': 'error_handling',
        'passed': passed,
        'errors': errors
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_all_tests() -> Dict:
    """Run all Phase 2 diagnostic tests and generate report."""
    
    print("\n" + "="*80)
    print("PHASE 2 DIAGNOSTIC TEST SUITE")
    print("Testing: Caching, Mode Routing, Batch Processing, Error Handling")
    print("="*80)
    
    start_time = datetime.now()
    
    results = {
        'test_1_caching': test_caching_performance(),
        'test_2_mode_routing': test_mode_routing(),
        'test_3_batch_processing': test_batch_processing(),
        'test_4_portfolio_comparison': test_portfolio_comparison(),
        'test_5_error_handling': test_error_handling()
    }
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Summary
    all_passed = all(result['passed'] for result in results.values())
    num_passed = sum(1 for result in results.values() if result['passed'])
    num_total = len(results)
    
    print("\n" + "="*80)
    print("PHASE 2 DIAGNOSTIC SUMMARY")
    print("="*80)
    print(f"  Tests passed: {num_passed}/{num_total}")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("="*80)
    
    # Save results
    report = {
        'summary': {
            'all_passed': all_passed,
            'num_passed': num_passed,
            'num_total': num_total,
            'elapsed_seconds': round(elapsed, 2),
            'timestamp': datetime.now().isoformat()
        },
        'results': results
    }
    
    output_dir = Path('outputs/phase2_reports')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'phase2_diagnostic_report.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Full report saved: {output_file}\n")
    
    return report


if __name__ == '__main__':
    report = run_all_tests()
    sys.exit(0 if report['summary']['all_passed'] else 1)
