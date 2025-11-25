"""
Phase 5 E2E Loop - Main Orchestrator

Runs N-iteration E2E testing loop with reproducibility validation.
Orchestrates tests, screenshots, and report generation.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import E2E modules
from phase5_e2e_tests import run_tests_for_iteration, E2ETestResult
from phase5_e2e_screenshots import capture_screenshots_for_iteration, PLAYWRIGHT_AVAILABLE
from phase5_e2e_reports import E2EReportGenerator, generate_reports

logger = logging.getLogger(__name__)


class E2EOrchestrator:
    """Main orchestrator for E2E testing loop."""
    
    def __init__(self, config_path: str = 'phase5_e2e_config.json'):
        """Initialize orchestrator.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Configuration sections
        self.test_execution = self.config.get('test_execution', {})
        self.dashboard_config = self.config.get('dashboard_config', {})
        self.azure_mock_config = self.config.get('azure_mock_config', {})
        self.output_config = self.config.get('output_config', {})
        
        # Setup output directories
        self.output_dir = Path(self.output_config.get('output_directory', './outputs/phase5_e2e'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.screenshots_dir = Path(self.output_config.get('screenshots_directory', './outputs/phase5_e2e/screenshots'))
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        self.reports_dir = Path(self.output_config.get('reports_directory', './outputs/phase5_e2e/reports'))
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.logs_dir = Path(self.output_config.get('logs_directory', './outputs/phase5_e2e/logs'))
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Iteration tracking
        self.iteration_results = []
        
    def _load_config(self) -> Dict:
        """Load configuration from JSON file.
        
        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"✅ Configuration loaded: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            raise
            
    def _setup_environment(self):
        """Setup environment variables for mock Azure mode."""
        logger.info("Setting up mock Azure environment...")
        
        for key, value in self.azure_mock_config.items():
            os.environ[key] = str(value)
            logger.debug(f"  {key} = {value}")
            
        logger.info("✅ Mock Azure environment configured")
        
    def _start_dashboard(self) -> bool:
        """Start dashboard in background (optional).
        
        Returns:
            True if dashboard started successfully, False otherwise
        """
        # This would start the dashboard process
        # For now, assume dashboard is already running
        logger.info("⚠️  Assuming dashboard is already running")
        logger.info(f"  Dashboard URL: {self.dashboard_config.get('base_url')}")
        return True
        
    def _wait_for_dashboard(self) -> bool:
        """Wait for dashboard to be ready.
        
        Returns:
            True if dashboard is ready, False if timeout
        """
        import requests
        
        base_url = self.dashboard_config.get('base_url')
        timeout = self.dashboard_config.get('startup_timeout_seconds', 30)
        
        logger.info(f"Waiting for dashboard at {base_url}...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(base_url, timeout=2)
                if response.status_code == 200:
                    logger.info("✅ Dashboard is ready")
                    return True
            except:
                pass
                
            time.sleep(1)
            
        logger.error("❌ Dashboard startup timeout")
        return False
        
    def run_single_iteration(self, iteration: int) -> Dict:
        """Run a single test iteration.
        
        Args:
            iteration: Iteration number
            
        Returns:
            Iteration results dictionary
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"ITERATION {iteration}/{self.test_execution.get('iterations', 3)}")
        logger.info(f"{'='*70}\n")
        
        iteration_start = time.time()
        
        # Run tests
        logger.info("Running test suite...")
        test_results = run_tests_for_iteration(self.config, iteration)
        
        # Capture screenshots
        screenshot_results = []
        if self.test_execution.get('capture_screenshots', True):
            logger.info("Capturing screenshots...")
            if PLAYWRIGHT_AVAILABLE:
                try:
                    screenshot_results = capture_screenshots_for_iteration(self.config, iteration)
                    logger.info(f"✅ Captured {len(screenshot_results)} screenshots")
                except Exception as e:
                    logger.error(f"❌ Screenshot capture failed: {e}")
            else:
                logger.warning("⚠️  Playwright not available - skipping screenshots")
        else:
            logger.info("Screenshot capture disabled")
            
        # Generate iteration report
        report_generator = E2EReportGenerator(self.config)
        json_report_path = report_generator.generate_iteration_json(
            iteration,
            test_results,
            screenshot_results
        )
        
        iteration_duration = time.time() - iteration_start
        
        # Print iteration summary
        passed = sum(1 for r in test_results if r.passed)
        failed = len(test_results) - passed
        success_rate = (passed / len(test_results) * 100) if test_results else 0
        
        logger.info(f"\n{'='*70}")
        logger.info(f"ITERATION {iteration} COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Tests: {len(test_results)} total, {passed} passed, {failed} failed")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Duration: {iteration_duration:.1f}s")
        logger.info(f"Report: {json_report_path}")
        logger.info(f"{'='*70}\n")
        
        # Load and return JSON report
        with open(json_report_path, 'r') as f:
            return json.load(f)
            
    def run_all_iterations(self) -> List[Dict]:
        """Run all configured iterations.
        
        Returns:
            List of iteration results
        """
        iterations = self.test_execution.get('iterations', 3)
        delay_between = self.test_execution.get('delay_between_iterations_seconds', 5)
        
        logger.info(f"\n{'#'*70}")
        logger.info(f"STARTING E2E TEST LOOP - {iterations} ITERATIONS")
        logger.info(f"{'#'*70}\n")
        
        for i in range(1, iterations + 1):
            iteration_result = self.run_single_iteration(i)
            self.iteration_results.append(iteration_result)
            
            # Delay before next iteration
            if i < iterations:
                logger.info(f"Waiting {delay_between}s before next iteration...\n")
                time.sleep(delay_between)
                
        return self.iteration_results
        
    def generate_final_reports(self) -> Dict[str, str]:
        """Generate final summary reports.
        
        Returns:
            Dictionary with paths to generated reports
        """
        logger.info(f"\n{'='*70}")
        logger.info("GENERATING FINAL REPORTS")
        logger.info(f"{'='*70}\n")
        
        reports = generate_reports(self.config, self.iteration_results)
        
        for report_type, path in reports.items():
            logger.info(f"✅ {report_type}: {path}")
            
        return reports
        
    def print_final_summary(self):
        """Print final summary to console."""
        if not self.iteration_results:
            logger.warning("No iteration results to summarize")
            return
            
        logger.info(f"\n{'#'*70}")
        logger.info("FINAL SUMMARY")
        logger.info(f"{'#'*70}\n")
        
        # Overall stats
        total_iterations = len(self.iteration_results)
        total_tests = sum(iter_data['summary']['total_tests'] for iter_data in self.iteration_results)
        total_passed = sum(iter_data['summary']['passed'] for iter_data in self.iteration_results)
        total_failed = sum(iter_data['summary']['failed'] for iter_data in self.iteration_results)
        avg_success_rate = sum(iter_data['summary']['success_rate'] for iter_data in self.iteration_results) / total_iterations
        
        logger.info(f"Iterations: {total_iterations}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Total Passed: {total_passed} ✅")
        logger.info(f"Total Failed: {total_failed} ❌")
        logger.info(f"Average Success Rate: {avg_success_rate:.1f}%")
        logger.info("")
        
        # Reproducibility check
        if total_iterations >= 2:
            success_rates = [iter_data['summary']['success_rate'] for iter_data in self.iteration_results]
            max_variation = max(success_rates) - min(success_rates)
            
            threshold = self.config.get('reproducibility_validation', {}).get('max_variation_percent', 5)
            
            if max_variation <= threshold:
                logger.info(f"✅ REPRODUCIBILITY: PASS (variation: {max_variation:.1f}%, threshold: {threshold}%)")
            else:
                logger.info(f"⚠️  REPRODUCIBILITY: WARNING (variation: {max_variation:.1f}%, threshold: {threshold}%)")
        else:
            logger.info("⚠️  REPRODUCIBILITY: Insufficient iterations for validation")
            
        logger.info("")
        
        # Recommendation
        if avg_success_rate >= 95:
            logger.info("✅ VERDICT: System is production-ready")
        elif avg_success_rate >= 80:
            logger.info("⚠️  VERDICT: Minor issues detected - review before deployment")
        else:
            logger.info("❌ VERDICT: Critical issues detected - not ready for deployment")
            
        logger.info(f"\n{'#'*70}\n")
        
    def run(self):
        """Main entry point - run full E2E test loop."""
        overall_start = time.time()
        
        try:
            # Setup
            self._setup_environment()
            
            # Check if dashboard should be started
            # (Currently assumes dashboard is already running)
            # dashboard_ready = self._wait_for_dashboard()
            # if not dashboard_ready:
            #     logger.error("Dashboard not ready - aborting tests")
            #     return False
            
            # Run all iterations
            self.run_all_iterations()
            
            # Generate final reports
            self.generate_final_reports()
            
            # Print summary
            self.print_final_summary()
            
            overall_duration = time.time() - overall_start
            logger.info(f"Total execution time: {overall_duration:.1f}s")
            
            return True
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Test loop interrupted by user")
            return False
        except Exception as e:
            logger.error(f"\n❌ Test loop failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    # Setup logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('./outputs/phase5_e2e/logs/e2e_loop.log')
        ]
    )
    
    # Create orchestrator
    orchestrator = E2EOrchestrator('phase5_e2e_config.json')
    
    # Run test loop
    success = orchestrator.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
