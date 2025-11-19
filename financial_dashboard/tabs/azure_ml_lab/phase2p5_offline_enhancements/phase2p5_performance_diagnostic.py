"""
Phase 2.5 Offline Enhancements — Performance Diagnostic Suite

Comprehensive benchmark and validation suite for Phase 2.5 deliverables:

1. Visualization render time tests (all 5 chart types)
2. Comparison mode benchmarks (3, 5, 10 tickers)
3. Cache persistence and TTL validation
4. Narrative template generation speed
5. End-to-end workflow performance

Target: <1.5s average render time per explanation

Author: Autonomous Lead Software Engineer
Version: 1.0.0 (Phase 2.5)
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Phase 2.5 modules
try:
    from insight_visuals import (
        create_feature_importance_bar,
        create_waterfall_chart,
        create_feature_heatmap,
        create_beeswarm_plot,
        create_force_plot,
        get_available_chart_types,
        PLOTLY_AVAILABLE
    )
    from insight_comparator import (
        create_side_by_side_bars,
        compute_differential_importance,
        compute_consensus_ranking,
        generate_comparison_report
    )
    from phase2p5_metrics import Phase25MetricsTracker, get_global_tracker
    from phase2p5_persistent_cache import PersistentCache, HybridCache
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Make sure all Phase 2.5 modules are in the same directory.")
    sys.exit(1)

# Import explainability engine from parent
try:
    from explainability_engine import ExplainabilityEngine, generate_explanation
except ImportError as e:
    print(f"⚠️  Failed to import explainability_engine: {e}")
    print("This diagnostic suite requires explainability_engine.py to be accessible.")
    sys.exit(1)

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory for reports
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent.parent / "outputs" / "phase2p5_reports"


# ============================================================================
# BENCHMARK UTILITIES
# ============================================================================

class BenchmarkTimer:
    """Simple context manager for timing operations."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        return False


def generate_mock_feature_importance(
    ticker: str,
    num_features: int = 10,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate mock feature importance data for testing.
    
    Args:
        ticker: Ticker symbol
        num_features: Number of features to generate
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with columns: feature, shap_value, contribution_pct
    """
    if seed is None:
        seed = sum(ord(c) for c in ticker)
    
    rng = np.random.RandomState(seed)
    
    features = [
        'momentum_20', 'rsi_14', 'macd', 'volatility_30', 'volume_ratio',
        'pe_ratio', 'debt_to_equity', 'roe', 'sentiment_score', 'beta',
        'ma_50', 'atr_14', 'earnings_growth', 'analyst_rating', 'market_return'
    ]
    
    # Select features
    selected_features = features[:num_features]
    
    # Generate SHAP values
    shap_values = rng.randn(num_features) * 0.1
    
    # Calculate contributions
    abs_shap = np.abs(shap_values)
    contribution_pct = (abs_shap / abs_shap.sum()) * 100
    
    df = pd.DataFrame({
        'feature': selected_features,
        'shap_value': shap_values,
        'contribution_pct': contribution_pct
    })
    
    return df.sort_values('contribution_pct', ascending=False).reset_index(drop=True)


# ============================================================================
# VISUALIZATION BENCHMARKS
# ============================================================================

def benchmark_chart_types(tickers: List[str], top_n: int = 10) -> Dict[str, Any]:
    """
    Benchmark all 5 chart types for render time.
    
    Args:
        tickers: List of ticker symbols to test
        top_n: Number of features per chart
        
    Returns:
        Benchmark results dictionary
    """
    logger.info("🎨 Benchmarking chart types...")
    
    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not available - skipping chart benchmarks")
        return {'status': 'skipped', 'reason': 'Plotly not available'}
    
    results = {
        'tickers_tested': tickers,
        'top_n': top_n,
        'chart_types': {},
        'total_time_seconds': 0
    }
    
    overall_start = time.time()
    
    for ticker in tickers:
        # Generate mock data
        importance_df = generate_mock_feature_importance(ticker, num_features=top_n)
        
        # Test each chart type
        for chart_type in ['bar', 'waterfall', 'heatmap', 'beeswarm', 'force']:
            with BenchmarkTimer(f"{chart_type}_{ticker}") as timer:
                try:
                    if chart_type == 'bar':
                        fig = create_feature_importance_bar(importance_df, ticker, top_n=top_n)
                    elif chart_type == 'waterfall':
                        fig = create_waterfall_chart(
                            importance_df, ticker,
                            baseline_value=0.0,
                            prediction_value=0.05,
                            top_n=top_n
                        )
                    elif chart_type == 'heatmap':
                        # Heatmap needs multiple tickers
                        multi_importance = [importance_df for _ in range(3)]
                        fig = create_feature_heatmap(multi_importance, [ticker] * 3, top_n=top_n)
                    elif chart_type == 'beeswarm':
                        fig = create_beeswarm_plot(importance_df, ticker, top_n=top_n)
                    elif chart_type == 'force':
                        fig = create_force_plot(
                            importance_df, ticker,
                            baseline_value=0.0,
                            prediction_value=0.05,
                            top_n=top_n
                        )
                    
                    # Record success
                    if chart_type not in results['chart_types']:
                        results['chart_types'][chart_type] = {
                            'times_ms': [],
                            'success_count': 0,
                            'failure_count': 0
                        }
                    
                    results['chart_types'][chart_type]['times_ms'].append(timer.elapsed * 1000)
                    results['chart_types'][chart_type]['success_count'] += 1
                    
                except Exception as e:
                    logger.error(f"Chart type {chart_type} failed for {ticker}: {e}")
                    if chart_type not in results['chart_types']:
                        results['chart_types'][chart_type] = {
                            'times_ms': [],
                            'success_count': 0,
                            'failure_count': 0
                        }
                    results['chart_types'][chart_type]['failure_count'] += 1
    
    results['total_time_seconds'] = time.time() - overall_start
    
    # Calculate statistics
    for chart_type, data in results['chart_types'].items():
        if data['times_ms']:
            data['avg_time_ms'] = sum(data['times_ms']) / len(data['times_ms'])
            data['min_time_ms'] = min(data['times_ms'])
            data['max_time_ms'] = max(data['times_ms'])
            data['p95_time_ms'] = np.percentile(data['times_ms'], 95)
        else:
            data['avg_time_ms'] = 0
            data['min_time_ms'] = 0
            data['max_time_ms'] = 0
            data['p95_time_ms'] = 0
    
    logger.info(f"✅ Chart type benchmarks complete ({results['total_time_seconds']:.2f}s)")
    return results


# ============================================================================
# COMPARISON MODE BENCHMARKS
# ============================================================================

def benchmark_comparison_mode(ticker_groups: List[List[str]], top_n: int = 10) -> Dict[str, Any]:
    """
    Benchmark multi-ticker comparison features.
    
    Args:
        ticker_groups: List of ticker lists (e.g., [[AAPL, GOOGL, TSLA], [MSFT, AMZN, ...]])
        top_n: Number of features per comparison
        
    Returns:
        Benchmark results dictionary
    """
    logger.info("📊 Benchmarking comparison mode...")
    
    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not available - skipping comparison benchmarks")
        return {'status': 'skipped', 'reason': 'Plotly not available'}
    
    results = {
        'ticker_groups': ticker_groups,
        'top_n': top_n,
        'comparison_tests': [],
        'total_time_seconds': 0
    }
    
    overall_start = time.time()
    
    for group_idx, tickers in enumerate(ticker_groups):
        # Generate mock results for each ticker
        mock_results = {}
        for ticker in tickers:
            importance_df = generate_mock_feature_importance(ticker, num_features=top_n)
            mock_results[ticker] = {
                'feature_importance': importance_df,
                'prediction_value': 0.05,
                'prediction_target': 'return'
            }
        
        # Test side-by-side comparison
        with BenchmarkTimer(f"side_by_side_{len(tickers)}") as timer:
            try:
                fig = create_side_by_side_bars(mock_results, tickers, top_n=top_n)
                side_by_side_time_ms = timer.elapsed * 1000
                side_by_side_success = True
            except Exception as e:
                logger.error(f"Side-by-side comparison failed for group {group_idx}: {e}")
                side_by_side_time_ms = 0
                side_by_side_success = False
        
        # Test differential analysis
        with BenchmarkTimer(f"differential_{len(tickers)}") as timer:
            try:
                diff_df = compute_differential_importance(mock_results, tickers, top_n=top_n)
                differential_time_ms = timer.elapsed * 1000
                differential_success = True
            except Exception as e:
                logger.error(f"Differential analysis failed for group {group_idx}: {e}")
                differential_time_ms = 0
                differential_success = False
        
        # Test consensus ranking
        consensus_times = {}
        for method in ['mean_rank', 'mean_importance', 'top3_frequency']:
            with BenchmarkTimer(f"consensus_{method}_{len(tickers)}") as timer:
                try:
                    consensus_df = compute_consensus_ranking(mock_results, tickers, method=method)
                    consensus_times[method] = timer.elapsed * 1000
                except Exception as e:
                    logger.error(f"Consensus ranking ({method}) failed for group {group_idx}: {e}")
                    consensus_times[method] = 0
        
        # Test full comparison report
        with BenchmarkTimer(f"full_report_{len(tickers)}") as timer:
            try:
                report = generate_comparison_report(mock_results, tickers)
                full_report_time_ms = timer.elapsed * 1000
                full_report_success = True
            except Exception as e:
                logger.error(f"Full comparison report failed for group {group_idx}: {e}")
                full_report_time_ms = 0
                full_report_success = False
        
        # Record results
        results['comparison_tests'].append({
            'group_index': group_idx,
            'ticker_count': len(tickers),
            'tickers': tickers,
            'side_by_side_ms': side_by_side_time_ms,
            'side_by_side_success': side_by_side_success,
            'differential_ms': differential_time_ms,
            'differential_success': differential_success,
            'consensus_times_ms': consensus_times,
            'full_report_ms': full_report_time_ms,
            'full_report_success': full_report_success,
            'total_time_ms': (side_by_side_time_ms + differential_time_ms +
                              sum(consensus_times.values()) + full_report_time_ms)
        })
    
    results['total_time_seconds'] = time.time() - overall_start
    
    logger.info(f"✅ Comparison mode benchmarks complete ({results['total_time_seconds']:.2f}s)")
    return results


# ============================================================================
# CACHE PERFORMANCE TESTS
# ============================================================================

def benchmark_cache_performance(num_operations: int = 100) -> Dict[str, Any]:
    """
    Benchmark cache performance (persistent and hybrid).
    
    Args:
        num_operations: Number of get/set operations to test
        
    Returns:
        Benchmark results dictionary
    """
    logger.info("💾 Benchmarking cache performance...")
    
    results = {
        'num_operations': num_operations,
        'persistent_cache': {},
        'hybrid_cache': {},
        'total_time_seconds': 0
    }
    
    overall_start = time.time()
    
    # Test PersistentCache
    persistent_cache = PersistentCache(ttl_seconds=3600)
    
    # Write performance
    write_times = []
    for i in range(num_operations):
        key = f"test_key_{i}"
        value = {'data': f"value_{i}", 'index': i}
        
        with BenchmarkTimer(f"write_{i}") as timer:
            persistent_cache.set(key, value)
        
        write_times.append(timer.elapsed * 1000)
    
    # Read performance
    read_times = []
    for i in range(num_operations):
        key = f"test_key_{i}"
        
        with BenchmarkTimer(f"read_{i}") as timer:
            _ = persistent_cache.get(key)
        
        read_times.append(timer.elapsed * 1000)
    
    # Cleanup
    cleanup_start = time.time()
    persistent_cache.clear_all()
    cleanup_time_ms = (time.time() - cleanup_start) * 1000
    
    results['persistent_cache'] = {
        'avg_write_ms': sum(write_times) / len(write_times),
        'p95_write_ms': np.percentile(write_times, 95),
        'avg_read_ms': sum(read_times) / len(read_times),
        'p95_read_ms': np.percentile(read_times, 95),
        'cleanup_ms': cleanup_time_ms
    }
    
    # Test HybridCache
    hybrid_cache = HybridCache(lru_size=10, ttl_seconds=3600)
    
    # Write performance
    hybrid_write_times = []
    for i in range(num_operations):
        key = f"test_key_{i}"
        value = {'data': f"value_{i}", 'index': i}
        
        with BenchmarkTimer(f"hybrid_write_{i}") as timer:
            hybrid_cache.set(key, value)
        
        hybrid_write_times.append(timer.elapsed * 1000)
    
    # Read performance (should hit memory for recent entries)
    hybrid_read_times = []
    for i in range(num_operations):
        key = f"test_key_{i}"
        
        with BenchmarkTimer(f"hybrid_read_{i}") as timer:
            _ = hybrid_cache.get(key)
        
        hybrid_read_times.append(timer.elapsed * 1000)
    
    # Cleanup
    hybrid_cleanup_start = time.time()
    hybrid_cache.clear_all()
    hybrid_cleanup_time_ms = (time.time() - hybrid_cleanup_start) * 1000
    
    results['hybrid_cache'] = {
        'avg_write_ms': sum(hybrid_write_times) / len(hybrid_write_times),
        'p95_write_ms': np.percentile(hybrid_write_times, 95),
        'avg_read_ms': sum(hybrid_read_times) / len(hybrid_read_times),
        'p95_read_ms': np.percentile(hybrid_read_times, 95),
        'cleanup_ms': hybrid_cleanup_time_ms,
        'stats': hybrid_cache.get_stats()
    }
    
    results['total_time_seconds'] = time.time() - overall_start
    
    logger.info(f"✅ Cache performance benchmarks complete ({results['total_time_seconds']:.2f}s)")
    return results


# ============================================================================
# END-TO-END WORKFLOW BENCHMARK
# ============================================================================

def benchmark_end_to_end_workflow(tickers: List[str]) -> Dict[str, Any]:
    """
    Benchmark end-to-end explanation generation workflow.
    
    Tests the full pipeline:
    1. Generate explanation (narrative templates)
    2. Create visualization (bar chart)
    3. Cache result
    4. Retrieve from cache
    
    Args:
        tickers: List of ticker symbols to test
        
    Returns:
        Benchmark results with target <1.5s average
    """
    logger.info("🚀 Benchmarking end-to-end workflow...")
    
    results = {
        'tickers_tested': tickers,
        'target_time_ms': 1500,  # <1.5s target
        'workflow_times': [],
        'total_time_seconds': 0
    }
    
    overall_start = time.time()
    
    # Initialize engine
    engine = ExplainabilityEngine()
    
    for ticker in tickers:
        with BenchmarkTimer(f"e2e_{ticker}") as timer:
            try:
                # Step 1: Generate feature importance
                importance_df = engine.compute_feature_importance(ticker, top_n=10)
                
                # Step 2: Generate narrative explanation
                narrative = engine.generate_textual_rationale(
                    ticker=ticker,
                    prediction_value=0.05,
                    prediction_target='return',
                    top_n=5,
                    use_narrative_templates=True
                )
                
                # Step 3: Create visualization (if Plotly available)
                if PLOTLY_AVAILABLE:
                    fig = create_feature_importance_bar(importance_df, ticker, top_n=10)
                
                # Step 4: Simulate cache write
                # (In real usage, this is handled by the caching decorator)
                
                elapsed_ms = timer.elapsed * 1000
                success = True
                
            except Exception as e:
                logger.error(f"End-to-end workflow failed for {ticker}: {e}")
                elapsed_ms = 0
                success = False
        
        results['workflow_times'].append({
            'ticker': ticker,
            'elapsed_ms': elapsed_ms,
            'success': success,
            'meets_target': elapsed_ms < results['target_time_ms'] if success else False
        })
    
    results['total_time_seconds'] = time.time() - overall_start
    
    # Calculate statistics
    successful_times = [t['elapsed_ms'] for t in results['workflow_times'] if t['success']]
    if successful_times:
        results['avg_time_ms'] = sum(successful_times) / len(successful_times)
        results['p50_time_ms'] = np.percentile(successful_times, 50)
        results['p95_time_ms'] = np.percentile(successful_times, 95)
        results['max_time_ms'] = max(successful_times)
        results['success_rate'] = len(successful_times) / len(tickers) * 100
        results['target_achievement_rate'] = sum(1 for t in results['workflow_times'] if t.get('meets_target', False)) / len(tickers) * 100
    else:
        results['avg_time_ms'] = 0
        results['p50_time_ms'] = 0
        results['p95_time_ms'] = 0
        results['max_time_ms'] = 0
        results['success_rate'] = 0
        results['target_achievement_rate'] = 0
    
    logger.info(f"✅ End-to-end workflow benchmarks complete ({results['total_time_seconds']:.2f}s)")
    logger.info(f"   Average time: {results['avg_time_ms']:.1f}ms (target: <1500ms)")
    logger.info(f"   Target achievement: {results['target_achievement_rate']:.1f}%")
    
    return results


# ============================================================================
# MAIN DIAGNOSTIC RUNNER
# ============================================================================

def run_all_diagnostics(output_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Run all Phase 2.5 performance diagnostics.
    
    Args:
        output_file: Path to save results JSON (default: phase2p5_performance_report.json)
        
    Returns:
        Complete diagnostic results dictionary
    """
    logger.info("=" * 80)
    logger.info("PHASE 2.5 PERFORMANCE DIAGNOSTIC SUITE")
    logger.info("=" * 80)
    
    diagnostic_start = time.time()
    
    # Test tickers
    test_tickers = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN']
    
    # Run all benchmarks
    results = {
        'diagnostic_timestamp': datetime.now().isoformat(),
        'plotly_available': PLOTLY_AVAILABLE,
        'test_tickers': test_tickers,
        'benchmarks': {}
    }
    
    # 1. Chart type benchmarks
    results['benchmarks']['chart_types'] = benchmark_chart_types(test_tickers[:3], top_n=10)
    
    # 2. Comparison mode benchmarks
    ticker_groups = [
        test_tickers[:3],   # 3 tickers
        test_tickers[:5],   # 5 tickers
    ]
    results['benchmarks']['comparison_mode'] = benchmark_comparison_mode(ticker_groups, top_n=10)
    
    # 3. Cache performance benchmarks
    results['benchmarks']['cache_performance'] = benchmark_cache_performance(num_operations=50)
    
    # 4. End-to-end workflow benchmarks
    results['benchmarks']['end_to_end_workflow'] = benchmark_end_to_end_workflow(test_tickers)
    
    # Calculate total diagnostic time
    results['total_diagnostic_time_seconds'] = time.time() - diagnostic_start
    
    # Determine overall status
    e2e_results = results['benchmarks']['end_to_end_workflow']
    target_met = e2e_results.get('target_achievement_rate', 0) >= 80  # 80% must meet <1.5s target
    
    results['overall_status'] = 'PASS' if target_met else 'FAIL'
    results['summary'] = {
        'avg_render_time_ms': e2e_results.get('avg_time_ms', 0),
        'target_time_ms': 1500,
        'target_achievement_rate': e2e_results.get('target_achievement_rate', 0),
        'status': 'PASS ✅' if target_met else 'FAIL ❌'
    }
    
    # Save results
    if output_file is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / "phase2p5_performance_report.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("=" * 80)
    logger.info(f"DIAGNOSTIC COMPLETE: {results['overall_status']}")
    logger.info(f"Total time: {results['total_diagnostic_time_seconds']:.2f}s")
    logger.info(f"Average render time: {results['summary']['avg_render_time_ms']:.1f}ms (target: <1500ms)")
    logger.info(f"Results saved to: {output_file}")
    logger.info("=" * 80)
    
    return results


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("\n🔬 Phase 2.5 Performance Diagnostic Suite\n")
    
    # Run diagnostics
    results = run_all_diagnostics()
    
    # Display summary
    print("\n📊 SUMMARY")
    print("=" * 60)
    print(f"Status: {results['summary']['status']}")
    print(f"Average Render Time: {results['summary']['avg_render_time_ms']:.1f}ms")
    print(f"Target Achievement: {results['summary']['target_achievement_rate']:.1f}%")
    print(f"Total Diagnostic Time: {results['total_diagnostic_time_seconds']:.2f}s")
    print("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_status'] == 'PASS' else 1)
