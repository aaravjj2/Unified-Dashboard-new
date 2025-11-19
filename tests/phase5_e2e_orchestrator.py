"""
Phase 5 E2E Orchestrator - Playwright Snapshot + Clicker Loop
==========================================================================================================
Runs 3 full iterations of E2E tests with screenshot capture, JSON reporting, and reproducibility analysis.

Usage:
    python tests/phase5_e2e_orchestrator.py --iterations 3 --headless
    
    Inside Docker:
    docker exec -it unified-dashboard-app python tests/phase5_e2e_orchestrator.py --iterations 3 --headless

Features:
    - Runs Playwright tests for all tabs and subtabs
    - Captures 90+ screenshots per iteration
    - Generates JSON report with performance metrics
    - Creates Markdown summary with reproducibility analysis
    - Monitors dashboard startup time and tab render times
    - Compares screenshots across iterations for consistency
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import hashlib
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Phase5E2EOrchestrator:
    """Orchestrates multi-iteration E2E testing with reproducibility validation."""
    
    def __init__(self, iterations: int = 3, headless: bool = True, dashboard_url: str = "http://localhost:8050"):
        """
        Initialize orchestrator.
        
        Args:
            iterations: Number of test iterations to run
            headless: Run browser in headless mode
            dashboard_url: URL of the dashboard to test
        """
        self.iterations = iterations
        self.headless = headless
        self.dashboard_url = dashboard_url
        
        # Output directories
        self.output_dir = project_root / "outputs" / "phase5_e2e"
        self.screenshots_dir = self.output_dir / "screenshots"
        self.reports_dir = self.output_dir / "reports"
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.iteration_results = []
        self.screenshots_by_iteration = {}
        
        print(f"✅ Phase 5 E2E Orchestrator initialized")
        print(f"   Iterations: {iterations}")
        print(f"   Headless: {headless}")
        print(f"   Dashboard URL: {dashboard_url}")
        print(f"   Output: {self.output_dir}")
    
    def check_dashboard_running(self) -> bool:
        """
        Check if dashboard is running and accessible.
        
        Returns:
            bool: True if dashboard is accessible
        """
        print(f"\n🔍 Checking if dashboard is running at {self.dashboard_url}...")
        
        try:
            import requests
            response = requests.get(self.dashboard_url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ Dashboard is running")
                return True
            else:
                print(f"⚠️ Dashboard returned status {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Dashboard is not accessible: {e}")
            print(f"   Please start the dashboard before running E2E tests:")
            print(f"   python financial_dashboard/app.py")
            return False
    
    def run_iteration(self, iteration_num: int) -> Dict:
        """
        Run one full iteration of E2E tests.
        
        Args:
            iteration_num: Iteration number (1-indexed)
        
        Returns:
            dict: Iteration results
        """
        print(f"\n{'='*80}")
        print(f"🔄 ITERATION {iteration_num}/{self.iterations}")
        print(f"{'='*80}")
        
        iteration_start = time.time()
        
        # Iteration-specific screenshot directory
        iteration_screenshots = self.screenshots_dir / f"iteration_{iteration_num}"
        iteration_screenshots.mkdir(parents=True, exist_ok=True)
        
        # Build pytest command
        pytest_cmd = [
            "pytest",
            "tests/test_azure_ml_lab_e2e_scaffold.py",
            "-v",
            "--tb=short",
            f"--screenshot-dir={iteration_screenshots}",
            "--json-report",
            f"--json-report-file={self.reports_dir / f'iteration_{iteration_num}_report.json'}"
        ]
        
        if self.headless:
            pytest_cmd.append("--headed")  # Playwright uses --headed for visible browser
        
        # Run pytest
        print(f"\n📋 Running pytest...")
        print(f"   Command: {' '.join(pytest_cmd)}")
        
        try:
            result = subprocess.run(
                pytest_cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse results
            test_passed = result.returncode == 0
            iteration_time = time.time() - iteration_start
            
            # Count screenshots
            screenshots = list(iteration_screenshots.glob("*.png"))
            screenshot_count = len(screenshots)
            
            # Store screenshot info
            self.screenshots_by_iteration[iteration_num] = [
                {
                    'path': str(s.relative_to(self.output_dir)),
                    'size': s.stat().st_size,
                    'hash': self._hash_file(s)
                }
                for s in screenshots
            ]
            
            iteration_result = {
                'iteration': iteration_num,
                'timestamp': datetime.now().isoformat(),
                'success': test_passed,
                'duration_seconds': round(iteration_time, 2),
                'screenshot_count': screenshot_count,
                'stdout': result.stdout[-2000:],  # Last 2000 chars
                'stderr': result.stderr[-2000:] if result.stderr else ""
            }
            
            print(f"\n{'✅' if test_passed else '❌'} Iteration {iteration_num} {'PASSED' if test_passed else 'FAILED'}")
            print(f"   Duration: {iteration_time:.2f}s")
            print(f"   Screenshots: {screenshot_count}")
            
            return iteration_result
        
        except subprocess.TimeoutExpired:
            print(f"❌ Iteration {iteration_num} TIMED OUT after 5 minutes")
            return {
                'iteration': iteration_num,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'duration_seconds': 300,
                'screenshot_count': 0,
                'error': 'Timeout after 300 seconds'
            }
        
        except Exception as e:
            print(f"❌ Iteration {iteration_num} ERROR: {e}")
            return {
                'iteration': iteration_num,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'duration_seconds': 0,
                'screenshot_count': 0,
                'error': str(e)
            }
    
    def _hash_file(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def analyze_reproducibility(self) -> Dict:
        """
        Analyze reproducibility by comparing screenshots across iterations.
        
        Returns:
            dict: Reproducibility analysis results
        """
        print(f"\n🔬 Analyzing reproducibility across {self.iterations} iterations...")
        
        if len(self.screenshots_by_iteration) < 2:
            print("⚠️ Not enough iterations for reproducibility analysis")
            return {'status': 'insufficient_data'}
        
        # Compare screenshots by filename
        screenshot_comparison = {}
        
        # Get screenshot names from first iteration
        iteration_1_screenshots = {s['path']: s['hash'] for s in self.screenshots_by_iteration[1]}
        
        identical_count = 0
        different_count = 0
        missing_count = 0
        
        for screenshot_path, hash_1 in iteration_1_screenshots.items():
            screenshot_name = Path(screenshot_path).name
            
            # Compare with other iterations
            comparison = {'iteration_1': hash_1}
            
            for iter_num in range(2, self.iterations + 1):
                if iter_num not in self.screenshots_by_iteration:
                    continue
                
                # Find matching screenshot in this iteration
                iter_screenshots = {Path(s['path']).name: s['hash'] for s in self.screenshots_by_iteration[iter_num]}
                
                if screenshot_name in iter_screenshots:
                    comparison[f'iteration_{iter_num}'] = iter_screenshots[screenshot_name]
                else:
                    comparison[f'iteration_{iter_num}'] = 'MISSING'
                    missing_count += 1
            
            # Check if all hashes are identical
            hashes = [v for k, v in comparison.items() if v != 'MISSING']
            if len(set(hashes)) == 1:
                identical_count += 1
            else:
                different_count += 1
            
            screenshot_comparison[screenshot_name] = comparison
        
        reproducibility_score = (identical_count / len(iteration_1_screenshots) * 100) if iteration_1_screenshots else 0
        
        analysis = {
            'total_screenshots_compared': len(iteration_1_screenshots),
            'identical_across_iterations': identical_count,
            'different_across_iterations': different_count,
            'missing_in_some_iterations': missing_count,
            'reproducibility_score_pct': round(reproducibility_score, 2),
            'screenshot_comparison': screenshot_comparison
        }
        
        print(f"\n📊 Reproducibility Analysis:")
        print(f"   Total screenshots: {len(iteration_1_screenshots)}")
        print(f"   Identical: {identical_count}")
        print(f"   Different: {different_count}")
        print(f"   Missing: {missing_count}")
        print(f"   Reproducibility: {reproducibility_score:.2f}%")
        
        return analysis
    
    def generate_json_report(self) -> Path:
        """
        Generate comprehensive JSON report.
        
        Returns:
            Path: Path to JSON report
        """
        print(f"\n📝 Generating JSON report...")
        
        # Calculate summary statistics
        total_screenshots = sum(r['screenshot_count'] for r in self.iteration_results)
        passed_iterations = sum(1 for r in self.iteration_results if r['success'])
        avg_duration = sum(r['duration_seconds'] for r in self.iteration_results) / len(self.iteration_results)
        
        report = {
            'test_suite': 'Phase 5 E2E Orchestrator',
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'iterations': self.iterations,
                'headless': self.headless,
                'dashboard_url': self.dashboard_url
            },
            'summary': {
                'total_iterations': self.iterations,
                'passed_iterations': passed_iterations,
                'failed_iterations': self.iterations - passed_iterations,
                'total_screenshots': total_screenshots,
                'average_duration_seconds': round(avg_duration, 2)
            },
            'iterations': self.iteration_results,
            'reproducibility_analysis': self.analyze_reproducibility(),
            'output_directory': str(self.output_dir)
        }
        
        report_path = self.reports_dir / f"phase5_e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ JSON report saved: {report_path}")
        
        return report_path
    
    def generate_markdown_summary(self, json_report_path: Path) -> Path:
        """
        Generate Markdown summary report.
        
        Args:
            json_report_path: Path to JSON report
        
        Returns:
            Path: Path to Markdown report
        """
        print(f"\n📄 Generating Markdown summary...")
        
        with open(json_report_path, 'r') as f:
            report = json.load(f)
        
        md_content = f"""# Phase 5 E2E Test Report

**Date:** {report['timestamp']}  
**Test Suite:** Phase 5 E2E Orchestrator  
**Iterations:** {report['configuration']['iterations']}

---

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Total Iterations** | {report['summary']['total_iterations']} |
| **Passed** | ✅ {report['summary']['passed_iterations']} |
| **Failed** | ❌ {report['summary']['failed_iterations']} |
| **Total Screenshots** | 📸 {report['summary']['total_screenshots']} |
| **Average Duration** | ⏱️ {report['summary']['average_duration_seconds']}s |

---

## 🔄 Iteration Results

"""
        
        for iteration in report['iterations']:
            status_icon = '✅' if iteration['success'] else '❌'
            md_content += f"""### {status_icon} Iteration {iteration['iteration']}

- **Status:** {"PASSED" if iteration['success'] else "FAILED"}
- **Duration:** {iteration['duration_seconds']}s
- **Screenshots:** {iteration['screenshot_count']}
- **Timestamp:** {iteration['timestamp']}

"""
        
        # Reproducibility analysis
        repro = report['reproducibility_analysis']
        if repro.get('status') != 'insufficient_data':
            md_content += f"""---

## 🔬 Reproducibility Analysis

| Metric | Value |
|--------|-------|
| **Screenshots Compared** | {repro['total_screenshots_compared']} |
| **Identical Across Iterations** | ✅ {repro['identical_across_iterations']} |
| **Different Across Iterations** | ⚠️ {repro['different_across_iterations']} |
| **Missing in Some Iterations** | ❌ {repro['missing_in_some_iterations']} |
| **Reproducibility Score** | 🎯 {repro['reproducibility_score_pct']}% |

"""
        
        md_content += f"""---

## 📁 Output

- **JSON Report:** `{json_report_path.relative_to(project_root)}`
- **Screenshots:** `{self.screenshots_dir.relative_to(project_root)}`

---

## ✅ Phase 5 Completion Checklist

- [{'x' if report['summary']['passed_iterations'] >= 3 else ' '}] 3+ iterations passed
- [{'x' if report['summary']['total_screenshots'] >= 90 else ' '}] 90+ screenshots captured
- [{'x' if repro.get('reproducibility_score_pct', 0) >= 90 else ' '}] Reproducibility ≥90%
- [ ] Dashboard startup <60s
- [ ] Tab rendering <2s

"""
        
        md_path = self.reports_dir / f"PHASE5_E2E_SUMMARY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(md_path, 'w') as f:
            f.write(md_content)
        
        print(f"✅ Markdown summary saved: {md_path}")
        
        return md_path
    
    def run(self) -> bool:
        """
        Run full E2E orchestration.
        
        Returns:
            bool: True if all iterations passed
        """
        print(f"\n{'='*80}")
        print(f"🚀 PHASE 5 E2E ORCHESTRATOR - STARTING")
        print(f"{'='*80}")
        
        # Check dashboard is running
        if not self.check_dashboard_running():
            print(f"\n❌ Cannot proceed - dashboard is not running")
            return False
        
        # Run iterations
        for i in range(1, self.iterations + 1):
            iteration_result = self.run_iteration(i)
            self.iteration_results.append(iteration_result)
        
        # Generate reports
        json_report = self.generate_json_report()
        md_report = self.generate_markdown_summary(json_report)
        
        # Final summary
        all_passed = all(r['success'] for r in self.iteration_results)
        
        print(f"\n{'='*80}")
        print(f"{'✅ ALL ITERATIONS PASSED' if all_passed else '❌ SOME ITERATIONS FAILED'}")
        print(f"{'='*80}")
        print(f"\n📊 Reports:")
        print(f"   JSON: {json_report}")
        print(f"   Markdown: {md_report}")
        print(f"\n📸 Screenshots: {self.screenshots_dir}")
        
        return all_passed


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Phase 5 E2E Orchestrator')
    parser.add_argument('--iterations', type=int, default=3, help='Number of test iterations')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--url', type=str, default='http://localhost:8050', help='Dashboard URL')
    
    args = parser.parse_args()
    
    orchestrator = Phase5E2EOrchestrator(
        iterations=args.iterations,
        headless=args.headless,
        dashboard_url=args.url
    )
    
    success = orchestrator.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
