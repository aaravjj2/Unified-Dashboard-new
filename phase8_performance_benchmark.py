#!/usr/bin/env python3
"""
Phase 8 Performance Benchmark
Measures actual speedup vs Phase 7 baseline
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from phase7_batch_orchestrator import run_batch_simulation


class Phase8PerformanceBenchmark:
    """
    Performance testing harness for Phase 8 optimizations
    """
    
    def __init__(self, output_dir: str = "outputs/phase8_optimization"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
    
    def benchmark_batch_simulation(
        self,
        test_name: str,
        tickers: List[str],
        num_monte_carlo: int = 3,
        max_workers: int = 4,
        num_runs: int = 3
    ) -> Dict[str, Any]:
        """
        Benchmark batch simulation with multiple runs
        
        Args:
            test_name: Name of test
            tickers: Ticker list
            num_monte_carlo: Number of Monte Carlo scenarios
            max_workers: Number of worker threads
            num_runs: Number of benchmark runs
        
        Returns:
            Benchmark results
        """
        print(f"\n{'='*80}")
        print(f"BENCHMARK: {test_name}")
        print(f"{'='*80}")
        print(f"Tickers: {len(tickers)} ({', '.join(tickers[:3])}{'...' if len(tickers) > 3 else ''})")
        print(f"Monte Carlo Scenarios: {num_monte_carlo}")
        print(f"Max Workers: {max_workers}")
        print(f"Runs: {num_runs}")
        print()
        
        execution_times = []
        throughputs = []
        
        for run in range(num_runs):
            print(f"Run {run+1}/{num_runs}...", end=" ", flush=True)
            
            start_time = time.perf_counter()
            
            try:
                result = run_batch_simulation(
                    tickers=tickers,
                    num_monte_carlo=num_monte_carlo,
                    max_workers=max_workers
                )
                
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                
                execution_times.append(execution_time)
                
                # Calculate throughput
                total_scenarios = len(tickers) * num_monte_carlo
                throughput = total_scenarios / execution_time
                throughputs.append(throughput)
                
                print(f"✅ {execution_time:.2f}s ({throughput:.1f} scenarios/sec)")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                execution_times.append(None)
                throughputs.append(None)
        
        # Calculate statistics
        valid_times = [t for t in execution_times if t is not None]
        valid_throughputs = [tp for tp in throughputs if tp is not None]
        
        if valid_times:
            avg_time = sum(valid_times) / len(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
            avg_throughput = sum(valid_throughputs) / len(valid_throughputs)
        else:
            avg_time = min_time = max_time = avg_throughput = None
        
        benchmark_result = {
            "test_name": test_name,
            "num_tickers": len(tickers),
            "num_monte_carlo": num_monte_carlo,
            "max_workers": max_workers,
            "num_runs": num_runs,
            "execution_times": execution_times,
            "avg_execution_time": avg_time,
            "min_execution_time": min_time,
            "max_execution_time": max_time,
            "avg_throughput": avg_throughput,
            "timestamp": datetime.now().isoformat()
        }
        
        print()
        print(f"Results:")
        if avg_time:
            print(f"  Avg Time: {avg_time:.2f}s")
            print(f"  Min Time: {min_time:.2f}s")
            print(f"  Max Time: {max_time:.2f}s")
            print(f"  Avg Throughput: {avg_throughput:.1f} scenarios/sec")
        else:
            print(f"  ❌ All runs failed")
        print(f"{'='*80}\n")
        
        self.results.append(benchmark_result)
        
        return benchmark_result
    
    def compare_with_baseline(self, baseline_path: Path) -> Dict[str, Any]:
        """
        Compare current results with Phase 7 baseline
        
        Args:
            baseline_path: Path to Phase 7 baseline JSON
        
        Returns:
            Comparison results
        """
        if not baseline_path.exists():
            print(f"⚠️ Baseline file not found: {baseline_path}")
            return {"status": "no_baseline"}
        
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)
        
        print(f"\n{'='*80}")
        print(f"PHASE 7 vs PHASE 8 COMPARISON")
        print(f"{'='*80}")
        print()
        
        comparisons = []
        
        for current in self.results:
            # Find matching baseline test
            matching_baseline = next(
                (b for b in baseline.get('results', [])
                 if b.get('num_tickers') == current['num_tickers']),
                None
            )
            
            if not matching_baseline:
                continue
            
            baseline_time = matching_baseline.get('avg_execution_time')
            current_time = current.get('avg_execution_time')
            
            if baseline_time and current_time:
                speedup = ((baseline_time - current_time) / baseline_time) * 100
                
                comparison = {
                    "test_name": current['test_name'],
                    "num_tickers": current['num_tickers'],
                    "baseline_time": baseline_time,
                    "current_time": current_time,
                    "speedup_percent": speedup,
                    "speedup_factor": baseline_time / current_time
                }
                
                comparisons.append(comparison)
                
                status = "✅ FASTER" if speedup > 0 else "⚠️ SLOWER"
                print(f"{current['test_name']}:")
                print(f"  Phase 7 Baseline: {baseline_time:.2f}s")
                print(f"  Phase 8 Current:  {current_time:.2f}s")
                print(f"  Speedup: {speedup:+.1f}% {status}")
                print()
        
        # Calculate overall speedup
        if comparisons:
            avg_speedup = sum(c['speedup_percent'] for c in comparisons) / len(comparisons)
        else:
            avg_speedup = None
        
        comparison_result = {
            "timestamp": datetime.now().isoformat(),
            "comparisons": comparisons,
            "avg_speedup_percent": avg_speedup,
            "phase8_target": 25.0,
            "target_met": avg_speedup >= 25.0 if avg_speedup else False
        }
        
        if avg_speedup is not None:
            print(f"{'='*80}")
            print(f"OVERALL SPEEDUP: {avg_speedup:+.1f}%")
            if comparison_result['target_met']:
                print(f"✅ TARGET MET (≥25%)")
            else:
                print(f"⚠️ TARGET MISSED (target: ≥25%, actual: {avg_speedup:.1f}%)")
            print(f"{'='*80}\n")
        
        # Save comparison
        comparison_path = self.output_dir / "phase8_vs_phase7_comparison.json"
        with open(comparison_path, 'w') as f:
            json.dump(comparison_result, f, indent=2)
        
        print(f"💾 Comparison saved: {comparison_path}\n")
        
        return comparison_result
    
    def save_results(self):
        """Save benchmark results to JSON"""
        results_path = self.output_dir / "phase8_performance_results.json"
        
        output = {
            "timestamp": datetime.now().isoformat(),
            "num_tests": len(self.results),
            "results": self.results
        }
        
        with open(results_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"💾 Performance results saved: {results_path}")


def main():
    """Run Phase 8 performance benchmarks"""
    print("=" * 80)
    print("PHASE 8: PERFORMANCE BENCHMARKING")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    benchmark = Phase8PerformanceBenchmark()
    
    # Test 1: 10-ticker benchmark (matches Phase 7 validation)
    benchmark.benchmark_batch_simulation(
        test_name="10-Ticker Batch",
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "JPM", "V"],
        num_monte_carlo=3,
        max_workers=4,
        num_runs=3
    )
    
    # Test 2: 5-ticker quick test
    benchmark.benchmark_batch_simulation(
        test_name="5-Ticker Quick",
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        num_monte_carlo=3,
        max_workers=4,
        num_runs=3
    )
    
    # Save results
    benchmark.save_results()
    
    # Compare with Phase 7 baseline if available
    baseline_path = Path("outputs/phase7_e2e_validation/phase7_performance_baseline.json")
    if baseline_path.exists():
        benchmark.compare_with_baseline(baseline_path)
    else:
        print(f"\n⚠️ No Phase 7 baseline found at {baseline_path}")
        print("Skipping comparison (this IS the new baseline)")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 8 PERFORMANCE BENCHMARKING COMPLETE")
    print("=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
