#!/usr/bin/env python3
"""
Phase 8 Performance Profiler
Identifies bottlenecks in batch simulation and reporting
"""

import cProfile
import pstats
import io
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
from datetime import datetime

# Import Phase 7 modules
from phase7_batch_orchestrator import BatchSimulationOrchestrator
from batch_options_analysis import BatchOptionsAnalyzer
from simulation_report_builder import BatchReportBuilder
from options_risk_simulator import OptionContract
from scenario_engine import ScenarioEngine


class Phase8Profiler:
    """
    Comprehensive performance profiler for Phase 7 simulation framework
    Identifies top bottlenecks and generates optimization recommendations
    """
    
    def __init__(self, output_dir: str = "outputs/phase8_profiling"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profiling_results: List[Dict[str, Any]] = []
    
    def profile_batch_simulation(
        self,
        num_tickers: int = 10,
        num_scenarios: int = 8
    ) -> Dict[str, Any]:
        """
        Profile batch simulation with cProfile
        """
        print(f"\n{'='*80}")
        print(f"PROFILING: Batch Simulation ({num_tickers} tickers, {num_scenarios} scenarios)")
        print(f"{'='*80}")
        
        profiler = cProfile.Profile()
        
        # Import and setup
        from phase7_batch_orchestrator import run_batch_simulation
        tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"][:num_tickers]
        
        # Profile execution
        start_time = time.time()
        profiler.enable()
        
        result = run_batch_simulation(
            tickers=tickers,
            num_monte_carlo=3,
            max_workers=4
        )
        
        profiler.disable()
        execution_time = time.time() - start_time
        
        # Analyze results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(30)  # Top 30 functions
        
        profile_output = s.getvalue()
        
        # Save detailed profile
        profile_path = self.output_dir / f"batch_sim_{num_tickers}t_profile.txt"
        with open(profile_path, 'w') as f:
            f.write(profile_output)
        
        # Extract top bottlenecks
        bottlenecks = self._extract_bottlenecks(profile_output)
        
        result_data = {
            "test_name": f"batch_simulation_{num_tickers}_tickers",
            "num_tickers": num_tickers,
            "num_scenarios": num_scenarios,
            "execution_time_seconds": execution_time,
            "scenarios_per_second": num_scenarios / execution_time,
            "top_bottlenecks": bottlenecks,
            "profile_file": str(profile_path)
        }
        
        self.profiling_results.append(result_data)
        
        print(f"\n✅ Profiling complete: {execution_time:.2f}s")
        print(f"   Throughput: {num_scenarios/execution_time:.2f} scenarios/sec")
        print(f"\n📊 Top 5 Bottlenecks:")
        for i, bottleneck in enumerate(bottlenecks[:5], 1):
            print(f"   {i}. {bottleneck['function']}: {bottleneck['cumulative_time']:.3f}s ({bottleneck['percent']:.1f}%)")
        
        return result_data
    
    def profile_options_analysis(self) -> Dict[str, Any]:
        """
        Profile options portfolio analysis
        """
        print(f"\n{'='*80}")
        print(f"PROFILING: Options Portfolio Analysis")
        print(f"{'='*80}")
        
        profiler = cProfile.Profile()
        
        # Setup
        analyzer = BatchOptionsAnalyzer()
        engine = ScenarioEngine()
        
        scenario = engine.generate_monte_carlo(
            tickers=["SPY", "QQQ", "IWM"],
            num_days=60,
            random_seed=42
        )
        
        contracts = [
            OptionContract("SPY", 450.0, 60, "call", "long", 10, 5.50),
            OptionContract("SPY", 440.0, 60, "put", "short", 10, 4.25),
            OptionContract("QQQ", 385.0, 60, "call", "long", 5, 8.75),
            OptionContract("IWM", 220.0, 60, "call", "short", 5, 3.25),
        ]
        
        # Profile execution
        start_time = time.time()
        profiler.enable()
        
        result = analyzer.analyze(
            contracts=contracts,
            scenario=scenario,
            portfolio_id="test_portfolio"
        )
        
        profiler.disable()
        execution_time = time.time() - start_time
        
        # Analyze results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(30)
        
        profile_output = s.getvalue()
        
        # Save profile
        profile_path = self.output_dir / "options_analysis_profile.txt"
        with open(profile_path, 'w') as f:
            f.write(profile_output)
        
        bottlenecks = self._extract_bottlenecks(profile_output)
        
        result_data = {
            "test_name": "options_portfolio_analysis",
            "num_contracts": len(contracts),
            "execution_time_seconds": execution_time,
            "top_bottlenecks": bottlenecks,
            "profile_file": str(profile_path)
        }
        
        self.profiling_results.append(result_data)
        
        print(f"\n✅ Profiling complete: {execution_time:.2f}s")
        print(f"\n📊 Top 5 Bottlenecks:")
        for i, bottleneck in enumerate(bottlenecks[:5], 1):
            print(f"   {i}. {bottleneck['function']}: {bottleneck['cumulative_time']:.3f}s ({bottleneck['percent']:.1f}%)")
        
        return result_data
    
    def profile_report_generation(self) -> Dict[str, Any]:
        """
        Profile report generation (JSON, CSV, HTML)
        """
        print(f"\n{'='*80}")
        print(f"PROFILING: Report Generation")
        print(f"{'='*80}")
        
        # Generate sample data
        orchestrator = BatchSimulationOrchestrator()
        result = orchestrator.run_batch(
            tickers=["SPY", "QQQ"],
            num_monte_carlo=2,
            num_stress=3,
            num_events=0,
            num_days=60,
            workers=2
        )
        
        builder = BatchReportBuilder()
        
        # Profile JSON generation
        profiler = cProfile.Profile()
        start_time = time.time()
        profiler.enable()
        
        builder.generate_batch_summary_json(
            batch_id="profile_test",
            results=result.simulations,
            execution_time=result.execution_time,
            cache_hit_rate=result.cache_hit_rate
        )
        
        profiler.disable()
        json_time = time.time() - start_time
        
        # Profile HTML generation
        profiler2 = cProfile.Profile()
        start_time = time.time()
        profiler2.enable()
        
        builder.generate_html_report(
            batch_id="profile_test",
            results=result.simulations
        )
        
        profiler2.disable()
        html_time = time.time() - start_time
        
        # Analyze JSON profile
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)
        json_profile = s.getvalue()
        
        # Analyze HTML profile
        s2 = io.StringIO()
        ps2 = pstats.Stats(profiler2, stream=s2).sort_stats('cumulative')
        ps2.print_stats(20)
        html_profile = s2.getvalue()
        
        # Save profiles
        json_path = self.output_dir / "json_generation_profile.txt"
        html_path = self.output_dir / "html_generation_profile.txt"
        
        with open(json_path, 'w') as f:
            f.write(json_profile)
        with open(html_path, 'w') as f:
            f.write(html_profile)
        
        json_bottlenecks = self._extract_bottlenecks(json_profile)
        html_bottlenecks = self._extract_bottlenecks(html_profile)
        
        result_data = {
            "test_name": "report_generation",
            "json_time_seconds": json_time,
            "html_time_seconds": html_time,
            "json_bottlenecks": json_bottlenecks[:5],
            "html_bottlenecks": html_bottlenecks[:5],
            "json_profile_file": str(json_path),
            "html_profile_file": str(html_path)
        }
        
        self.profiling_results.append(result_data)
        
        print(f"\n✅ Profiling complete:")
        print(f"   JSON generation: {json_time:.3f}s")
        print(f"   HTML generation: {html_time:.3f}s")
        
        return result_data
    
    def _extract_bottlenecks(self, profile_output: str) -> List[Dict[str, Any]]:
        """
        Extract top bottlenecks from cProfile output
        """
        bottlenecks = []
        lines = profile_output.split('\n')
        
        # Find the stats table
        parsing_stats = False
        for line in lines:
            if 'ncalls' in line and 'tottime' in line:
                parsing_stats = True
                continue
            
            if parsing_stats and line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        ncalls = parts[0]
                        tottime = float(parts[1])
                        cumtime = float(parts[3])
                        function = ' '.join(parts[5:])
                        
                        bottlenecks.append({
                            "function": function,
                            "ncalls": ncalls,
                            "total_time": tottime,
                            "cumulative_time": cumtime,
                            "percent": 0.0  # Will calculate later
                        })
                    except (ValueError, IndexError):
                        continue
        
        # Calculate percentages
        if bottlenecks:
            total_time = sum(b['cumulative_time'] for b in bottlenecks)
            for b in bottlenecks:
                b['percent'] = (b['cumulative_time'] / total_time * 100) if total_time > 0 else 0
        
        # Sort by cumulative time
        bottlenecks.sort(key=lambda x: x['cumulative_time'], reverse=True)
        
        return bottlenecks
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive profiling summary
        """
        print(f"\n{'='*80}")
        print(f"GENERATING PROFILING SUMMARY")
        print(f"{'='*80}")
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.profiling_results),
            "profiling_results": self.profiling_results,
            "top_overall_bottlenecks": self._aggregate_bottlenecks(),
            "optimization_recommendations": self._generate_recommendations()
        }
        
        # Save summary JSON
        summary_path = self.output_dir / "phase8_profiling_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, indent=2, fp=f)
        
        print(f"\n📊 Profiling Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Output Directory: {self.output_dir}")
        print(f"   Summary File: {summary_path}")
        
        print(f"\n🔍 Top Overall Bottlenecks:")
        for i, bottleneck in enumerate(summary['top_overall_bottlenecks'][:5], 1):
            print(f"   {i}. {bottleneck['category']}: {bottleneck['avg_time']:.3f}s avg ({bottleneck['occurrences']} occurrences)")
        
        print(f"\n💡 Optimization Recommendations:")
        for i, rec in enumerate(summary['optimization_recommendations'][:5], 1):
            print(f"   {i}. {rec['recommendation']} (Expected speedup: {rec['expected_speedup']})")
        
        return summary
    
    def _aggregate_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Aggregate bottlenecks across all tests
        """
        bottleneck_map = {}
        
        for result in self.profiling_results:
            if 'top_bottlenecks' in result:
                for bottleneck in result['top_bottlenecks'][:10]:
                    func = bottleneck['function']
                    category = self._categorize_bottleneck(func)
                    
                    if category not in bottleneck_map:
                        bottleneck_map[category] = {
                            "category": category,
                            "total_time": 0,
                            "occurrences": 0,
                            "functions": []
                        }
                    
                    bottleneck_map[category]['total_time'] += bottleneck['cumulative_time']
                    bottleneck_map[category]['occurrences'] += 1
                    bottleneck_map[category]['functions'].append(func)
        
        # Calculate averages
        aggregated = []
        for category, data in bottleneck_map.items():
            aggregated.append({
                "category": category,
                "total_time": data['total_time'],
                "avg_time": data['total_time'] / data['occurrences'],
                "occurrences": data['occurrences'],
                "sample_functions": data['functions'][:3]
            })
        
        # Sort by total time
        aggregated.sort(key=lambda x: x['total_time'], reverse=True)
        
        return aggregated
    
    def _categorize_bottleneck(self, function_name: str) -> str:
        """
        Categorize bottleneck by function name pattern
        """
        if 'monte_carlo' in function_name.lower() or '_generate_gbm' in function_name:
            return "Monte Carlo Generation"
        elif 'black_scholes' in function_name.lower() or 'greeks' in function_name.lower():
            return "Options Pricing"
        elif 'json' in function_name.lower() or 'dumps' in function_name:
            return "JSON Serialization"
        elif 'html' in function_name.lower() or '_build_html' in function_name:
            return "HTML Generation"
        elif 'numpy' in function_name or 'ndarray' in function_name:
            return "NumPy Operations"
        elif 'pandas' in function_name or 'DataFrame' in function_name:
            return "Pandas Operations"
        elif 'scenario' in function_name.lower():
            return "Scenario Generation"
        elif 'portfolio' in function_name.lower() or 'simulate' in function_name:
            return "Portfolio Simulation"
        elif 'thread' in function_name.lower() or 'executor' in function_name:
            return "Thread Pool Execution"
        else:
            return "Other"
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate optimization recommendations based on profiling results
        """
        recommendations = []
        
        # Analyze bottlenecks
        aggregated = self._aggregate_bottlenecks()
        
        for bottleneck in aggregated[:5]:
            category = bottleneck['category']
            
            if category == "Monte Carlo Generation":
                recommendations.append({
                    "recommendation": "Reduce Monte Carlo paths (1000 → 500) or vectorize GBM calculation",
                    "expected_speedup": "30-50%",
                    "category": category,
                    "priority": "High"
                })
            elif category == "JSON Serialization":
                recommendations.append({
                    "recommendation": "Use orjson or ujson instead of stdlib json",
                    "expected_speedup": "20-40%",
                    "category": category,
                    "priority": "Medium"
                })
            elif category == "HTML Generation":
                recommendations.append({
                    "recommendation": "Cache HTML templates and use string formatting instead of concatenation",
                    "expected_speedup": "15-25%",
                    "category": category,
                    "priority": "Medium"
                })
            elif category == "Pandas Operations":
                recommendations.append({
                    "recommendation": "Convert DataFrame operations to NumPy for intermediate calculations",
                    "expected_speedup": "10-20%",
                    "category": category,
                    "priority": "Low"
                })
            elif category == "Thread Pool Execution":
                recommendations.append({
                    "recommendation": "Increase worker count or use ProcessPoolExecutor for CPU-bound tasks",
                    "expected_speedup": "20-40%",
                    "category": category,
                    "priority": "High"
                })
        
        return recommendations


def main():
    """
    Run comprehensive profiling suite
    """
    print("=" * 80)
    print("PHASE 8: PERFORMANCE PROFILING")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    profiler = Phase8Profiler()
    
    # Profile batch simulations
    profiler.profile_batch_simulation(num_tickers=10, num_scenarios=8)
    
    # Profile options analysis
    profiler.profile_options_analysis()
    
    # Profile report generation
    profiler.profile_report_generation()
    
    # Generate summary
    summary = profiler.generate_summary_report()
    
    print("\n" + "=" * 80)
    print("✅ PROFILING COMPLETE")
    print("=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output Directory: {profiler.output_dir}")
    print()


if __name__ == "__main__":
    main()
