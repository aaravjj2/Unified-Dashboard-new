#!/usr/bin/env python3
"""
Phase 8B Profiler - Production Performance Analysis
Identifies bottlenecks in Phase 7/8 simulation pipeline using cProfile
"""

import cProfile
import pstats
import io
import json
import time
import psutil
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from phase7_batch_orchestrator import run_batch_simulation


class Phase8BProfiler:
    """
    Advanced profiler for Phase 7/8 simulation pipeline
    Uses cProfile for CPU profiling and psutil for resource monitoring
    """
    
    def __init__(self, output_dir: str = "outputs/phase8b_profiling"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profile_results = []
        
    def profile_batch_simulation(
        self,
        tickers: List[str],
        num_monte_carlo: int = 3,
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """
        Profile batch simulation with cProfile
        
        Args:
            tickers: List of ticker symbols
            num_monte_carlo: Number of Monte Carlo scenarios
            max_workers: Number of worker threads
        
        Returns:
            Profiling results with bottlenecks
        """
        print(f"\n{'='*80}")
        print(f"PROFILING: Batch Simulation ({len(tickers)} tickers)")
        print(f"{'='*80}")
        print(f"Tickers: {', '.join(tickers)}")
        print(f"Monte Carlo Scenarios: {num_monte_carlo}")
        print(f"Max Workers: {max_workers}")
        print()
        
        # Setup profiler
        profiler = cProfile.Profile()
        
        # Monitor resources before
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent_before = psutil.cpu_percent(interval=0.1)
        
        # Profile execution
        print("Starting profiling...")
        start_time = time.perf_counter()
        
        profiler.enable()
        try:
            result = run_batch_simulation(
                tickers=tickers,
                num_monte_carlo=num_monte_carlo,
                max_workers=max_workers
            )
            success = True
        except Exception as e:
            print(f"❌ Error during simulation: {e}")
            success = False
            result = None
        finally:
            profiler.disable()
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # Monitor resources after
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent_after = psutil.cpu_percent(interval=0.1)
        
        print(f"✅ Profiling complete: {execution_time:.2f}s")
        print()
        
        # Extract statistics
        stats_stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stats_stream)
        stats.sort_stats('cumulative')
        stats.print_stats(50)  # Top 50 functions
        
        profile_output = stats_stream.getvalue()
        
        # Parse bottlenecks
        bottlenecks = self._extract_bottlenecks(profile_output)
        
        # Categorize bottlenecks
        categorized = self._categorize_bottlenecks(bottlenecks)
        
        profile_result = {
            "test_name": f"{len(tickers)}-ticker batch simulation",
            "num_tickers": len(tickers),
            "num_monte_carlo": num_monte_carlo,
            "max_workers": max_workers,
            "execution_time": execution_time,
            "success": success,
            "memory_before_mb": mem_before,
            "memory_after_mb": mem_after,
            "memory_delta_mb": mem_after - mem_before,
            "cpu_percent_before": cpu_percent_before,
            "cpu_percent_after": cpu_percent_after,
            "total_scenarios": len(tickers) * num_monte_carlo if success else 0,
            "throughput": (len(tickers) * num_monte_carlo / execution_time) if success else 0,
            "top_bottlenecks": bottlenecks[:10],
            "bottleneck_categories": categorized,
            "profile_text": profile_output[:5000],  # First 5000 chars
            "timestamp": datetime.now().isoformat()
        }
        
        self.profile_results.append(profile_result)
        
        # Display top bottlenecks
        print(f"{'='*80}")
        print(f"TOP 10 BOTTLENECKS")
        print(f"{'='*80}")
        for i, bottleneck in enumerate(bottlenecks[:10], 1):
            print(f"{i}. {bottleneck['function']}")
            print(f"   Cumulative Time: {bottleneck['cumtime']:.3f}s ({bottleneck['cumtime_pct']:.1f}%)")
            print(f"   Total Time: {bottleneck['tottime']:.3f}s")
            print(f"   Calls: {bottleneck['ncalls']}")
            print()
        
        # Display resource usage
        print(f"{'='*80}")
        print(f"RESOURCE USAGE")
        print(f"{'='*80}")
        print(f"Memory Before: {mem_before:.1f} MB")
        print(f"Memory After: {mem_after:.1f} MB")
        print(f"Memory Delta: {mem_after - mem_before:+.1f} MB")
        print(f"CPU Utilization: {cpu_percent_after:.1f}%")
        print(f"{'='*80}\n")
        
        return profile_result
    
    def _extract_bottlenecks(self, profile_output: str) -> List[Dict[str, Any]]:
        """
        Parse cProfile output to extract bottleneck data
        
        Args:
            profile_output: String output from pstats
        
        Returns:
            List of bottleneck dictionaries
        """
        bottlenecks = []
        
        # Parse profile output lines
        lines = profile_output.split('\n')
        
        # Find data section (after headers)
        data_start = False
        total_time = 0.0
        
        for line in lines:
            # Detect total time
            if 'function calls' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'seconds' and i > 0:
                        try:
                            total_time = float(parts[i-1])
                        except:
                            pass
            
            # Detect data start
            if 'ncalls' in line and 'tottime' in line:
                data_start = True
                continue
            
            if not data_start:
                continue
            
            # Parse data line
            parts = line.split()
            if len(parts) >= 6:
                try:
                    ncalls = parts[0]
                    tottime = float(parts[1])
                    percall_tot = float(parts[2]) if parts[2] != '0.000' else 0.0
                    cumtime = float(parts[3])
                    percall_cum = float(parts[4]) if parts[4] != '0.000' else 0.0
                    function = ' '.join(parts[5:])
                    
                    # Calculate percentage
                    cumtime_pct = (cumtime / total_time * 100) if total_time > 0 else 0.0
                    
                    bottlenecks.append({
                        'ncalls': ncalls,
                        'tottime': tottime,
                        'percall_tot': percall_tot,
                        'cumtime': cumtime,
                        'percall_cum': percall_cum,
                        'cumtime_pct': cumtime_pct,
                        'function': function
                    })
                except (ValueError, IndexError):
                    continue
        
        # Sort by cumulative time (descending)
        bottlenecks.sort(key=lambda x: x['cumtime'], reverse=True)
        
        return bottlenecks
    
    def _categorize_bottlenecks(self, bottlenecks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Categorize bottlenecks by type
        
        Args:
            bottlenecks: List of bottleneck dictionaries
        
        Returns:
            Categorized bottleneck summary
        """
        categories = {
            "monte_carlo_generation": [],
            "portfolio_simulation": [],
            "json_serialization": [],
            "file_io": [],
            "numpy_operations": [],
            "threading": [],
            "other": []
        }
        
        category_patterns = {
            "monte_carlo_generation": ["monte_carlo", "scenario", "generate"],
            "portfolio_simulation": ["portfolio", "simulate", "apply_scenario"],
            "json_serialization": ["json", "dumps", "dump", "serialize"],
            "file_io": ["write", "read", "open", "save"],
            "numpy_operations": ["numpy", "np.", "ndarray", "array"],
            "threading": ["thread", "pool", "executor", "worker"]
        }
        
        for bottleneck in bottlenecks:
            func = bottleneck['function'].lower()
            categorized = False
            
            for category, patterns in category_patterns.items():
                if any(pattern in func for pattern in patterns):
                    categories[category].append(bottleneck)
                    categorized = True
                    break
            
            if not categorized:
                categories["other"].append(bottleneck)
        
        # Calculate totals per category
        category_summary = {}
        for category, items in categories.items():
            if items:
                total_cumtime = sum(item['cumtime'] for item in items)
                category_summary[category] = {
                    "count": len(items),
                    "total_cumtime": total_cumtime,
                    "top_function": items[0]['function'] if items else None
                }
        
        return category_summary
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive summary report
        
        Returns:
            Summary report dictionary
        """
        if not self.profile_results:
            print("⚠️ No profiling results to summarize")
            return {}
        
        print(f"\n{'='*80}")
        print(f"PROFILING SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {len(self.profile_results)}")
        print()
        
        # Aggregate bottlenecks across all tests
        all_bottlenecks = []
        for result in self.profile_results:
            all_bottlenecks.extend(result['top_bottlenecks'])
        
        # Get unique top bottlenecks (by function name)
        unique_bottlenecks = {}
        for bottleneck in all_bottlenecks:
            func = bottleneck['function']
            if func not in unique_bottlenecks:
                unique_bottlenecks[func] = bottleneck
            else:
                # Accumulate times
                unique_bottlenecks[func]['cumtime'] += bottleneck['cumtime']
                unique_bottlenecks[func]['tottime'] += bottleneck['tottime']
        
        # Sort by cumulative time
        top_bottlenecks = sorted(
            unique_bottlenecks.values(),
            key=lambda x: x['cumtime'],
            reverse=True
        )[:10]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(top_bottlenecks)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.profile_results),
            "top_bottlenecks_global": top_bottlenecks,
            "recommendations": recommendations,
            "test_results": self.profile_results
        }
        
        # Display recommendations
        print(f"{'='*80}")
        print(f"OPTIMIZATION RECOMMENDATIONS")
        print(f"{'='*80}")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec['bottleneck']}")
            print(f"   Category: {rec['category']}")
            print(f"   Optimization: {rec['optimization']}")
            print(f"   Expected Speedup: {rec['expected_speedup']}")
            print()
        
        print(f"{'='*80}\n")
        
        # Save summary
        summary_path = self.output_dir / "profile_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"💾 Summary saved: {summary_path}")
        
        # Save hotspot rankings CSV
        self._save_hotspot_rankings(top_bottlenecks)
        
        return summary
    
    def _generate_recommendations(
        self,
        bottlenecks: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Generate optimization recommendations based on bottlenecks
        
        Args:
            bottlenecks: List of top bottlenecks
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        for bottleneck in bottlenecks[:5]:  # Top 5
            func = bottleneck['function'].lower()
            
            if 'monte_carlo' in func or 'scenario' in func:
                recommendations.append({
                    'bottleneck': bottleneck['function'],
                    'category': 'Monte Carlo Generation',
                    'optimization': 'Reduce paths from 1000 to 500, or vectorize GBM calculation',
                    'expected_speedup': '30-50%'
                })
            elif 'json' in func or 'dump' in func:
                recommendations.append({
                    'bottleneck': bottleneck['function'],
                    'category': 'JSON Serialization',
                    'optimization': 'Switch to orjson or ujson for faster serialization',
                    'expected_speedup': '20-30%'
                })
            elif 'portfolio' in func or 'simulate' in func:
                recommendations.append({
                    'bottleneck': bottleneck['function'],
                    'category': 'Portfolio Simulation',
                    'optimization': 'Vectorize portfolio calculations using NumPy',
                    'expected_speedup': '15-25%'
                })
            elif 'write' in func or 'save' in func:
                recommendations.append({
                    'bottleneck': bottleneck['function'],
                    'category': 'File I/O',
                    'optimization': 'Buffer writes in memory, flush only at end',
                    'expected_speedup': '10-15%'
                })
            elif 'thread' in func or 'pool' in func:
                recommendations.append({
                    'bottleneck': bottleneck['function'],
                    'category': 'Threading',
                    'optimization': 'Increase worker pool from 4 to 8, or use ProcessPoolExecutor',
                    'expected_speedup': '15-20%'
                })
            else:
                recommendations.append({
                    'bottleneck': bottleneck['function'],
                    'category': 'Other',
                    'optimization': 'Review function implementation for inefficiencies',
                    'expected_speedup': '5-10%'
                })
        
        return recommendations
    
    def _save_hotspot_rankings(self, bottlenecks: List[Dict[str, Any]]):
        """Save hotspot rankings to CSV"""
        csv_path = self.output_dir / "hotspot_rankings.csv"
        
        with open(csv_path, 'w') as f:
            f.write("Rank,Function,Cumulative Time (s),Total Time (s),Calls,Cum %\n")
            for i, bottleneck in enumerate(bottlenecks, 1):
                f.write(f"{i},{bottleneck['function']},{bottleneck['cumtime']:.3f},"
                       f"{bottleneck['tottime']:.3f},{bottleneck['ncalls']},"
                       f"{bottleneck.get('cumtime_pct', 0):.1f}%\n")
        
        print(f"💾 Hotspot rankings saved: {csv_path}")


def main():
    """Run Phase 8B profiling"""
    print("=" * 80)
    print("PHASE 8B: PERFORMANCE PROFILING")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    profiler = Phase8BProfiler()
    
    # Profile Test 1: 5-ticker quick test
    profiler.profile_batch_simulation(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        num_monte_carlo=3,
        max_workers=4
    )
    
    # Profile Test 2: 10-ticker benchmark
    profiler.profile_batch_simulation(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "JPM", "V"],
        num_monte_carlo=3,
        max_workers=4
    )
    
    # Generate summary
    profiler.generate_summary_report()
    
    print("\n" + "=" * 80)
    print("✅ PHASE 8B PROFILING COMPLETE")
    print("=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
