"""
Phase 5 E2E Reports Module

Generates JSON and Markdown reports for E2E test results.
Includes metrics aggregation, reproducibility analysis, and visual summaries.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class E2EReportGenerator:
    """Generates comprehensive test reports."""
    
    def __init__(self, config: Dict):
        """Initialize report generator.
        
        Args:
            config: Test configuration dictionary
        """
        self.config = config
        self.output_config = config.get('output_config', {})
        self.performance_targets = config.get('performance_targets', {})
        self.reproducibility_config = config.get('reproducibility_validation', {})
        
        # Setup output directories
        self.reports_dir = Path(self.output_config.get('reports_directory', './outputs/phase5_e2e/reports'))
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    # ========================================================================
    # ITERATION REPORTS
    # ========================================================================
    
    def generate_iteration_json(self, iteration: int, test_results: List, screenshot_results: List) -> str:
        """Generate JSON report for a single iteration.
        
        Args:
            iteration: Iteration number
            test_results: List of E2ETestResult objects
            screenshot_results: List of screenshot results
            
        Returns:
            Path to JSON file
        """
        report = {
            'metadata': {
                'iteration': iteration,
                'timestamp': datetime.utcnow().isoformat(),
                'suite_name': self.config.get('test_metadata', {}).get('suite_name', 'Phase 5 E2E'),
                'version': self.config.get('test_metadata', {}).get('version', '1.0.0')
            },
            'summary': {
                'total_tests': len(test_results),
                'passed': sum(1 for r in test_results if r.passed),
                'failed': sum(1 for r in test_results if not r.passed),
                'success_rate': (sum(1 for r in test_results if r.passed) / len(test_results) * 100) if test_results else 0,
                'total_latency_ms': sum(r.latency_ms for r in test_results),
                'avg_latency_ms': sum(r.latency_ms for r in test_results) / len(test_results) if test_results else 0
            },
            'tests': [r.to_dict() for r in test_results],
            'screenshots': screenshot_results,
            'performance_analysis': self._analyze_performance(test_results)
        }
        
        # Save to file
        filename = f"phase5_e2e_report_iteration_{iteration}.json"
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"✅ JSON report saved: {filepath}")
        return str(filepath)
        
    def _analyze_performance(self, test_results: List) -> Dict:
        """Analyze performance metrics against targets.
        
        Args:
            test_results: List of test results
            
        Returns:
            Performance analysis dictionary
        """
        analysis = {
            'targets_met': {},
            'targets_missed': {},
            'performance_summary': {}
        }
        
        # Group results by test type
        by_type = {}
        for result in test_results:
            test_type = result.test_type
            if test_type not in by_type:
                by_type[test_type] = []
            by_type[test_type].append(result)
            
        # Analyze each type
        for test_type, results in by_type.items():
            avg_latency = sum(r.latency_ms for r in results) / len(results)
            max_latency = max(r.latency_ms for r in results)
            min_latency = min(r.latency_ms for r in results)
            
            # Get target for this type
            target_key = f"{test_type}_latency_ms"
            target = self.performance_targets.get(target_key, float('inf'))
            
            analysis['performance_summary'][test_type] = {
                'count': len(results),
                'avg_latency_ms': round(avg_latency, 2),
                'min_latency_ms': round(min_latency, 2),
                'max_latency_ms': round(max_latency, 2),
                'target_latency_ms': target,
                'target_met': avg_latency <= target
            }
            
            if avg_latency <= target:
                analysis['targets_met'][test_type] = avg_latency
            else:
                analysis['targets_missed'][test_type] = {
                    'actual': avg_latency,
                    'target': target,
                    'difference_ms': avg_latency - target
                }
                
        return analysis
        
    # ========================================================================
    # SUMMARY REPORT (ACROSS ITERATIONS)
    # ========================================================================
    
    def generate_summary_markdown(self, all_iterations: List[Dict]) -> str:
        """Generate comprehensive Markdown summary report.
        
        Args:
            all_iterations: List of iteration reports
            
        Returns:
            Path to Markdown file
        """
        md_lines = []
        
        # Header
        md_lines.append("# Phase 5 E2E Testing Summary Report")
        md_lines.append("")
        md_lines.append(f"**Generated:** {datetime.utcnow().isoformat()}")
        md_lines.append(f"**Iterations:** {len(all_iterations)}")
        md_lines.append(f"**Suite:** {self.config.get('test_metadata', {}).get('suite_name', 'Phase 5 E2E')}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
        # Overall Summary
        md_lines.append("## Overall Summary")
        md_lines.append("")
        
        total_tests = sum(iter_data['summary']['total_tests'] for iter_data in all_iterations)
        total_passed = sum(iter_data['summary']['passed'] for iter_data in all_iterations)
        total_failed = sum(iter_data['summary']['failed'] for iter_data in all_iterations)
        avg_success_rate = sum(iter_data['summary']['success_rate'] for iter_data in all_iterations) / len(all_iterations)
        
        md_lines.append(f"- **Total Tests:** {total_tests}")
        md_lines.append(f"- **Total Passed:** {total_passed} ✅")
        md_lines.append(f"- **Total Failed:** {total_failed} ❌")
        md_lines.append(f"- **Average Success Rate:** {avg_success_rate:.1f}%")
        md_lines.append("")
        
        # Iteration Breakdown
        md_lines.append("## Iteration Breakdown")
        md_lines.append("")
        md_lines.append("| Iteration | Total | Passed | Failed | Success Rate | Avg Latency (ms) |")
        md_lines.append("|-----------|-------|--------|--------|--------------|------------------|")
        
        for iter_data in all_iterations:
            summary = iter_data['summary']
            md_lines.append(
                f"| {iter_data['metadata']['iteration']} | "
                f"{summary['total_tests']} | "
                f"{summary['passed']} | "
                f"{summary['failed']} | "
                f"{summary['success_rate']:.1f}% | "
                f"{summary['avg_latency_ms']:.1f} |"
            )
            
        md_lines.append("")
        
        # Reproducibility Analysis
        md_lines.append("## Reproducibility Analysis")
        md_lines.append("")
        
        reproducibility = self._analyze_reproducibility(all_iterations)
        
        if reproducibility['consistent']:
            md_lines.append(f"✅ **PASS** - Results are consistent across {len(all_iterations)} iterations")
        else:
            md_lines.append(f"⚠️  **WARNING** - Detected variations across iterations")
            
        md_lines.append("")
        md_lines.append(f"- **Max variation:** {reproducibility['max_variation_percent']:.2f}%")
        md_lines.append(f"- **Threshold:** {self.reproducibility_config.get('max_variation_percent', 5)}%")
        md_lines.append("")
        
        if reproducibility['discrepancies']:
            md_lines.append("### Discrepancies Detected")
            md_lines.append("")
            for disc in reproducibility['discrepancies']:
                md_lines.append(f"- **{disc['test_name']}:** {disc['description']}")
            md_lines.append("")
            
        # Performance Analysis
        md_lines.append("## Performance Analysis")
        md_lines.append("")
        
        # Aggregate performance across iterations
        all_perf = [iter_data['performance_analysis'] for iter_data in all_iterations]
        md_lines.append("### Targets Met")
        md_lines.append("")
        
        # Get unique test types
        all_types = set()
        for perf in all_perf:
            all_types.update(perf['performance_summary'].keys())
            
        md_lines.append("| Test Type | Avg Latency (ms) | Target (ms) | Status |")
        md_lines.append("|-----------|------------------|-------------|--------|")
        
        for test_type in sorted(all_types):
            # Average across iterations
            latencies = [
                perf['performance_summary'].get(test_type, {}).get('avg_latency_ms', 0)
                for perf in all_perf
                if test_type in perf['performance_summary']
            ]
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                target = self.performance_targets.get(f"{test_type}_latency_ms", float('inf'))
                status = "✅ PASS" if avg_latency <= target else "❌ FAIL"
                
                md_lines.append(f"| {test_type} | {avg_latency:.1f} | {target} | {status} |")
                
        md_lines.append("")
        
        # Test Details
        md_lines.append("## Test Details")
        md_lines.append("")
        
        # Get all unique tests
        all_tests = {}
        for iter_data in all_iterations:
            for test in iter_data['tests']:
                test_name = test['test_name']
                if test_name not in all_tests:
                    all_tests[test_name] = []
                all_tests[test_name].append(test)
                
        for test_name, test_runs in all_tests.items():
            passed_count = sum(1 for t in test_runs if t['passed'])
            failed_count = len(test_runs) - passed_count
            avg_latency = sum(t['latency_ms'] for t in test_runs) / len(test_runs)
            
            status = "✅" if all(t['passed'] for t in test_runs) else "❌"
            
            md_lines.append(f"### {status} {test_name}")
            md_lines.append("")
            md_lines.append(f"- **Passed:** {passed_count}/{len(test_runs)}")
            md_lines.append(f"- **Average Latency:** {avg_latency:.1f}ms")
            
            if failed_count > 0:
                md_lines.append("- **Failures:**")
                for test in test_runs:
                    if not test['passed']:
                        md_lines.append(f"  - Iteration {test.get('metadata', {}).get('iteration', '?')}: {test.get('error_message', 'Unknown error')}")
                        
            md_lines.append("")
            
        # Screenshots Summary
        md_lines.append("## Screenshots")
        md_lines.append("")
        
        total_screenshots = sum(len(iter_data['screenshots']) for iter_data in all_iterations)
        successful_screenshots = sum(
            sum(1 for s in iter_data['screenshots'] if s.get('screenshot_success', False))
            for iter_data in all_iterations
        )
        
        md_lines.append(f"- **Total Screenshots:** {total_screenshots}")
        md_lines.append(f"- **Successful:** {successful_screenshots}")
        md_lines.append(f"- **Failed:** {total_screenshots - successful_screenshots}")
        md_lines.append("")
        
        # Recommendations
        md_lines.append("## Recommendations")
        md_lines.append("")
        
        if avg_success_rate >= 95:
            md_lines.append("✅ **System is production-ready** - All tests passing with high reliability")
        elif avg_success_rate >= 80:
            md_lines.append("⚠️  **Minor issues detected** - Review failed tests before deployment")
        else:
            md_lines.append("❌ **Critical issues detected** - System not ready for deployment")
            
        md_lines.append("")
        
        if not reproducibility['consistent']:
            md_lines.append("⚠️  **Reproducibility issues** - Investigate non-deterministic behavior")
            md_lines.append("")
            
        # Save to file
        filename = "phase5_e2e_report_summary.md"
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(md_lines))
            
        logger.info(f"✅ Markdown summary saved: {filepath}")
        return str(filepath)
        
    def _analyze_reproducibility(self, all_iterations: List[Dict]) -> Dict:
        """Analyze reproducibility across iterations.
        
        Args:
            all_iterations: List of iteration reports
            
        Returns:
            Reproducibility analysis
        """
        analysis = {
            'consistent': True,
            'max_variation_percent': 0.0,
            'discrepancies': []
        }
        
        if len(all_iterations) < 2:
            return analysis
            
        # Compare test results across iterations
        test_names = set()
        for iter_data in all_iterations:
            for test in iter_data['tests']:
                test_names.add(test['test_name'])
                
        max_variation_threshold = self.reproducibility_config.get('max_variation_percent', 5)
        
        for test_name in test_names:
            # Get results for this test across all iterations
            results = []
            for iter_data in all_iterations:
                for test in iter_data['tests']:
                    if test['test_name'] == test_name:
                        results.append(test)
                        break
                        
            if len(results) < 2:
                continue
                
            # Check pass/fail consistency
            pass_count = sum(1 for r in results if r['passed'])
            if pass_count not in [0, len(results)]:
                analysis['consistent'] = False
                analysis['discrepancies'].append({
                    'test_name': test_name,
                    'description': f"Inconsistent pass/fail ({pass_count}/{len(results)} passed)"
                })
                
            # Check latency variation
            latencies = [r['latency_ms'] for r in results]
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            
            if avg_latency > 0:
                variation_percent = ((max_latency - min_latency) / avg_latency) * 100
                
                if variation_percent > analysis['max_variation_percent']:
                    analysis['max_variation_percent'] = variation_percent
                    
                if variation_percent > max_variation_threshold:
                    analysis['consistent'] = False
                    analysis['discrepancies'].append({
                        'test_name': test_name,
                        'description': f"High latency variation ({variation_percent:.1f}%, range: {min_latency:.1f}-{max_latency:.1f}ms)"
                    })
                    
        return analysis
        
    # ========================================================================
    # CSV EXPORT
    # ========================================================================
    
    def generate_csv_metrics(self, all_iterations: List[Dict]) -> str:
        """Generate CSV file with detailed metrics.
        
        Args:
            all_iterations: List of iteration reports
            
        Returns:
            Path to CSV file
        """
        import csv
        
        filename = "phase5_e2e_metrics.csv"
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Iteration',
                'Test Name',
                'Test Type',
                'Passed',
                'Latency (ms)',
                'Error Message',
                'Timestamp'
            ])
            
            # Data rows
            for iter_data in all_iterations:
                iteration = iter_data['metadata']['iteration']
                for test in iter_data['tests']:
                    writer.writerow([
                        iteration,
                        test['test_name'],
                        test['test_type'],
                        test['passed'],
                        test['latency_ms'],
                        test.get('error_message', ''),
                        test['timestamp']
                    ])
                    
        logger.info(f"✅ CSV metrics saved: {filepath}")
        return str(filepath)


def generate_reports(config: Dict, all_iterations: List[Dict]) -> Dict[str, str]:
    """Generate all reports.
    
    Args:
        config: Test configuration
        all_iterations: List of iteration reports
        
    Returns:
        Dictionary with paths to generated reports
    """
    generator = E2EReportGenerator(config)
    
    reports = {}
    
    # Generate summary reports
    if config.get('output_config', {}).get('save_markdown_report', True):
        reports['markdown_summary'] = generator.generate_summary_markdown(all_iterations)
        
    if config.get('output_config', {}).get('save_csv_metrics', True):
        reports['csv_metrics'] = generator.generate_csv_metrics(all_iterations)
        
    return reports


# Standalone test
if __name__ == "__main__":
    import json
    from phase5_e2e_tests import E2ETestResult
    
    logging.basicConfig(level=logging.INFO)
    
    # Load config
    with open('phase5_e2e_config.json', 'r') as f:
        config = json.load(f)
        
    # Create mock iteration data
    mock_iterations = []
    for i in range(1, 4):
        mock_tests = [
            E2ETestResult('Test 1', 'tab_rendering'),
            E2ETestResult('Test 2', 'forecast')
        ]
        mock_tests[0].mark_passed({'latency': 100})
        mock_tests[1].mark_passed({'latency': 200})
        
        mock_iterations.append({
            'metadata': {'iteration': i, 'timestamp': datetime.utcnow().isoformat()},
            'summary': {
                'total_tests': 2,
                'passed': 2,
                'failed': 0,
                'success_rate': 100.0,
                'avg_latency_ms': 150.0
            },
            'tests': [t.to_dict() for t in mock_tests],
            'screenshots': [],
            'performance_analysis': {'targets_met': {}, 'targets_missed': {}, 'performance_summary': {}}
        })
        
    # Generate reports
    generator = E2EReportGenerator(config)
    reports = generate_reports(config, mock_iterations)
    
    print("\n✅ Reports generated:")
    for report_type, path in reports.items():
        print(f"  - {report_type}: {path}")
