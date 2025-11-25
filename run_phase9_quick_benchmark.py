"""Quick Phase 9 benchmark runner with proper JSON serialization"""

import json
import time
import numpy as np
from pathlib import Path
from phase9_performance_benchmark import Phase9Benchmark

# Convert numpy types to Python types
def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

# Run benchmarks
print("=" * 80)
print("PHASE 9 — QUICK PERFORMANCE BENCHMARK (5 + 10-ticker)")
print("=" * 80)

benchmark = Phase9Benchmark()
benchmark.configs = benchmark.configs[:2]  # Only 5 and 10-ticker

# Run tier 1: 5-ticker
result_5 = benchmark.run_single_tier(benchmark.configs[0])
benchmark.results.append(result_5)

# Run tier 2: 10-ticker  
result_10 = benchmark.run_single_tier(benchmark.configs[1])
benchmark.results.append(result_10)

# Generate report
report = benchmark._generate_report()

# Convert numpy types
report_dict = convert_numpy_types(report.to_dict())

# Save JSON
output_file = Path("outputs/phase9_benchmarks/phase9_performance_benchmarks.json")
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(report_dict, f, indent=2)

print(f"\n✅ Saved: {output_file}")

# Print summary
print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print(f"5-ticker: Cold {result_5.cold_run_time_s:.2f}s → Warm {result_5.avg_warm_run_time_s:.4f}s ({result_5.speedup_factor:.0f}x speedup)")
print(f"10-ticker: Cold {result_10.cold_run_time_s:.2f}s → Warm {result_10.avg_warm_run_time_s:.4f}s ({result_10.speedup_factor:.0f}x speedup)")
print(f"Cache hit rate: {report.summary_statistics['avg_cache_hit_rate']:.1f}%")
print(f"SLA pass rate: {report.summary_statistics['sla_pass_rate']:.0f}%")
print("=" * 80)
