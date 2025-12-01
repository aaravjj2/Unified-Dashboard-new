"""
phase6_full_reports.py - Multi-format report generation for Phase 6 diagnostics
Generates JSON, Markdown, and CSV reports with phase-level metrics.
Author: Agent 1B - Lead Engineer | Date: 2025-10-29
"""

import json
import csv
from typing import Dict, List
from pathlib import Path
from datetime import datetime

class Phase6ReportGenerator:
    """Generate comprehensive reports for Phase 6 diagnostics"""
    
    def __init__(self, config: Dict, output_dir: str = "outputs/phase6_full/reports"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_iteration_json(self, iteration_data: Dict, iteration: int) -> str:
        """Generate JSON report for single iteration"""
        filepath = self.output_dir / f"phase6_iteration_{iteration}.json"
        
        with open(filepath, 'w') as f:
            json.dump(iteration_data, f, indent=2)
        
        return str(filepath)
    
    def generate_summary_markdown(self, all_iterations: List[Dict]) -> str:
        """Generate Markdown summary across all iterations"""
        filepath = self.output_dir / "phase6_summary.md"
        
        md_lines = [
            "# Phase 6 Full Diagnostic Summary",
            f"\n**Generated:** {datetime.now().isoformat()}",
            f"\n**Total Iterations:** {len(all_iterations)}",
            "\n---\n"
        ]
        
        # Aggregate results
        total_tests = sum(it['summary']['total'] for it in all_iterations)
        total_passed = sum(it['summary']['passed'] for it in all_iterations)
        total_failed = sum(it['summary']['failed'] for it in all_iterations)
        avg_success_rate = sum(it['summary']['success_rate'] for it in all_iterations) / len(all_iterations)
        
        md_lines.extend([
            "## Overall Results\n",
            f"- **Total Tests (all iterations):** {total_tests}",
            f"- **Total Passed:** {total_passed} ✅",
            f"- **Total Failed:** {total_failed} ❌",
            f"- **Average Success Rate:** {avg_success_rate:.1f}%\n"
        ])
        
        # Per-iteration summary
        md_lines.append("\n## Per-Iteration Results\n")
        for it_data in all_iterations:
            it_num = it_data['iteration']
            summary = it_data['summary']
            md_lines.extend([
                f"\n### Iteration {it_num}",
                f"- Tests: {summary['total']}",
                f"- Passed: {summary['passed']} ✅",
                f"- Failed: {summary['failed']} ❌",
                f"- Success Rate: {summary['success_rate']:.1f}%",
                f"- Total Time: {summary['total_time_ms']:.2f}ms\n"
            ])
        
        # Phase breakdown (from first iteration)
        if all_iterations:
            phase_summary = all_iterations[0]['summary'].get('phase_summary', {})
            md_lines.append("\n## Phase Breakdown\n")
            for phase, stats in sorted(phase_summary.items()):
                md_lines.extend([
                    f"\n### Phase {phase}",
                    f"- Total: {stats['total']}",
                    f"- Passed: {stats['passed']} ✅",
                    f"- Failed: {stats['failed']} ❌\n"
                ])
        
        # Reproducibility analysis
        if len(all_iterations) >= 2:
            md_lines.extend([
                "\n## Reproducibility Analysis\n",
                self._analyze_reproducibility(all_iterations)
            ])
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(md_lines))
        
        return str(filepath)
    
    def _analyze_reproducibility(self, all_iterations: List[Dict]) -> str:
        """Analyze variation across iterations"""
        success_rates = [it['summary']['success_rate'] for it in all_iterations]
        
        if len(success_rates) < 2:
            return "- Insufficient iterations for reproducibility analysis"
        
        min_rate = min(success_rates)
        max_rate = max(success_rates)
        variation = max_rate - min_rate
        
        max_variation = self.config['reproducibility_validation']['max_variation_percent']
        passes = variation <= max_variation
        
        return f"""- Success rate variation: {variation:.2f}%
- Min: {min_rate:.1f}%, Max: {max_rate:.1f}%
- Threshold: {max_variation}%
- Status: {'✅ PASS' if passes else '❌ FAIL'}"""
    
    def generate_csv_metrics(self, all_iterations: List[Dict]) -> str:
        """Generate CSV with detailed metrics"""
        filepath = self.output_dir / "phase6_metrics.csv"
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Iteration', 'Test Name', 'Phase', 'Category', 'Passed', 'Latency (ms)', 'Error Message'])
            
            for it_data in all_iterations:
                iteration = it_data['iteration']
                for result in it_data['results']:
                    writer.writerow([
                        iteration,
                        result['test_name'],
                        result['phase'],
                        result['category'],
                        result['passed'],
                        f"{result['latency_ms']:.2f}",
                        result.get('error_message', '')
                    ])
        
        return str(filepath)

if __name__ == '__main__':
    print("Phase 6 Report Generator - Use with phase6_full_diagnostic.py")
