"""
phase6_full_diagnostic.py - Main orchestrator for Phase 6 comprehensive diagnostics
Runs 3-iteration reproducibility loop across all phases (0-5).
Author: Agent 1B - Lead Engineer | Date: 2025-10-29
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List
from pathlib import Path
from datetime import datetime

from phase6_full_e2e_tests import Phase6TestSuite
from phase6_full_screenshots import capture_screenshots_for_iteration, PLAYWRIGHT_AVAILABLE
from phase6_full_reports import Phase6ReportGenerator

logger = logging.getLogger(__name__)

class Phase6Orchestrator:
    """Main orchestrator for full diagnostic suite"""
    
    def __init__(self, config_path: str = "phase6_full_diagnostic_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.iteration_results: List[Dict] = []
        self.screenshot_results: List[List[Dict]] = []
        
        # Setup environment
        self._setup_environment()
        
        # Setup output directories
        self._setup_output_directories()
        
        # Setup logging
        log_level = self.config.get('output_config', {}).get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger.info("="*80)
        logger.info("PHASE 6 FULL DIAGNOSTIC ORCHESTRATOR INITIALIZED")
        logger.info("="*80)
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Iterations: {self.config['test_execution']['iterations']}")
        logger.info(f"Output directory: {self.output_base_dir}")
        logger.info("="*80)
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _setup_environment(self):
        """Setup environment variables for offline mode"""
        azure_config = self.config.get('azure_mock_config', {})
        
        for key, value in azure_config.items():
            os.environ[key] = str(value)
        
        logger.info("Environment variables configured for offline mode")
    
    def _setup_output_directories(self):
        """Create output directory structure"""
        base_dir = Path(self.config['output_config']['base_directory'])
        subdirs = self.config['output_config']['subdirectories']
        
        self.output_base_dir = base_dir
        self.screenshots_dir = base_dir / subdirs['screenshots']
        self.reports_dir = base_dir / subdirs['reports']
        self.logs_dir = base_dir / subdirs['logs']
        self.cache_stats_dir = base_dir / subdirs['cache_stats']
        
        for dir_path in [self.output_base_dir, self.screenshots_dir, self.reports_dir, 
                         self.logs_dir, self.cache_stats_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.logs_dir / f"phase6_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logger.info(f"Output directories created: {self.output_base_dir}")
    
    def run_single_iteration(self, iteration: int) -> Dict:
        """Run single iteration of full diagnostic"""
        logger.info("\n" + "="*80)
        logger.info(f"STARTING ITERATION {iteration}/{self.config['test_execution']['iterations']}")
        logger.info("="*80 + "\n")
        
        start_time = time.time()
        
        # Run test suite
        logger.info("Running test suite...")
        suite = Phase6TestSuite(config_path=self.config_path)
        test_results = suite.run_all_tests(iteration=iteration)
        
        # Capture screenshots if enabled
        screenshot_results = []
        if self.config['test_execution']['capture_screenshots']:
            if PLAYWRIGHT_AVAILABLE:
                logger.info("\nCapturing screenshots...")
                try:
                    screenshot_results = capture_screenshots_for_iteration(
                        self.config_path, 
                        iteration=iteration
                    )
                    logger.info(f"Screenshots captured: {len(screenshot_results)}")
                except Exception as e:
                    logger.error(f"Screenshot capture failed: {e}")
            else:
                logger.warning("Playwright not available - skipping screenshots")
        
        iteration_duration = time.time() - start_time
        
        iteration_data = {
            'iteration': iteration,
            'test_results': test_results,
            'screenshot_results': screenshot_results,
            'duration_seconds': iteration_duration,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save iteration results immediately
        report_gen = Phase6ReportGenerator(self.config, output_dir=str(self.reports_dir))
        json_path = report_gen.generate_iteration_json(test_results, iteration)
        logger.info(f"\nIteration {iteration} JSON report saved: {json_path}")
        
        logger.info("\n" + "="*80)
        logger.info(f"ITERATION {iteration} COMPLETE - Duration: {iteration_duration:.2f}s")
        logger.info("="*80 + "\n")
        
        return iteration_data
    
    def run_all_iterations(self) -> List[Dict]:
        """Run all configured iterations"""
        iterations = self.config['test_execution']['iterations']
        delay = self.config['test_execution']['delay_between_iterations_seconds']
        
        for i in range(1, iterations + 1):
            iteration_data = self.run_single_iteration(i)
            self.iteration_results.append(iteration_data)
            self.screenshot_results.append(iteration_data['screenshot_results'])
            
            # Delay between iterations (except after last one)
            if i < iterations and delay > 0:
                logger.info(f"Waiting {delay}s before next iteration...")
                time.sleep(delay)
        
        return self.iteration_results
    
    def generate_final_reports(self):
        """Generate aggregated reports across all iterations"""
        logger.info("\n" + "="*80)
        logger.info("GENERATING FINAL REPORTS")
        logger.info("="*80 + "\n")
        
        report_gen = Phase6ReportGenerator(self.config, output_dir=str(self.reports_dir))
        
        # Extract test results from iterations
        all_test_results = [it['test_results'] for it in self.iteration_results]
        
        # Generate Markdown summary
        md_path = report_gen.generate_summary_markdown(all_test_results)
        logger.info(f"✅ Markdown summary: {md_path}")
        
        # Generate CSV metrics
        csv_path = report_gen.generate_csv_metrics(all_test_results)
        logger.info(f"✅ CSV metrics: {csv_path}")
        
        logger.info("\n" + "="*80)
        logger.info("REPORT GENERATION COMPLETE")
        logger.info("="*80 + "\n")
    
    def print_final_summary(self):
        """Print executive summary to console"""
        logger.info("\n" + "#"*80)
        logger.info("# PHASE 6 FULL DIAGNOSTIC - FINAL SUMMARY")
        logger.info("#"*80 + "\n")
        
        iterations = len(self.iteration_results)
        
        # Aggregate statistics
        total_tests = sum(it['test_results']['summary']['total'] for it in self.iteration_results)
        total_passed = sum(it['test_results']['summary']['passed'] for it in self.iteration_results)
        total_failed = sum(it['test_results']['summary']['failed'] for it in self.iteration_results)
        
        avg_success_rate = sum(it['test_results']['summary']['success_rate'] for it in self.iteration_results) / iterations
        total_duration = sum(it['duration_seconds'] for it in self.iteration_results)
        
        logger.info(f"Iterations: {iterations}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Total Passed: {total_passed} ✅")
        logger.info(f"Total Failed: {total_failed} ❌")
        logger.info(f"Average Success Rate: {avg_success_rate:.1f}%")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        logger.info(f"\nOutput Directory: {self.output_base_dir}")
        logger.info(f"Reports: {self.reports_dir}")
        logger.info(f"Screenshots: {self.screenshots_dir}")
        logger.info(f"Logs: {self.log_file}")
        
        # Reproducibility verdict
        if iterations >= 2:
            success_rates = [it['test_results']['summary']['success_rate'] for it in self.iteration_results]
            variation = max(success_rates) - min(success_rates)
            max_variation = self.config['reproducibility_validation']['max_variation_percent']
            
            logger.info(f"\n{'='*80}")
            logger.info("REPRODUCIBILITY ANALYSIS")
            logger.info(f"{'='*80}")
            logger.info(f"Success Rate Variation: {variation:.2f}%")
            logger.info(f"Threshold: {max_variation}%")
            
            if variation <= max_variation:
                logger.info(f"✅ REPRODUCIBILITY: PASS")
            else:
                logger.info(f"❌ REPRODUCIBILITY: FAIL (variation exceeds threshold)")
        
        # Final verdict
        logger.info(f"\n{'='*80}")
        if avg_success_rate >= 95.0:
            logger.info("✅ VERDICT: System is PRODUCTION-READY")
        elif avg_success_rate >= 80.0:
            logger.info("⚠️  VERDICT: System is FUNCTIONAL with minor issues")
        else:
            logger.info("❌ VERDICT: System requires REMEDIATION")
        logger.info(f"{'='*80}\n")
    
    def run(self):
        """Execute full diagnostic workflow"""
        logger.info("\n" + "#"*80)
        logger.info("# PHASE 6 FULL DIAGNOSTIC - STARTING")
        logger.info("#"*80 + "\n")
        
        start_time = time.time()
        
        try:
            # Run all iterations
            self.run_all_iterations()
            
            # Generate final reports
            self.generate_final_reports()
            
            # Print summary
            self.print_final_summary()
            
            total_duration = time.time() - start_time
            
            logger.info("\n" + "#"*80)
            logger.info(f"# PHASE 6 FULL DIAGNOSTIC - COMPLETE ({total_duration:.2f}s)")
            logger.info("#"*80 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ DIAGNOSTIC FAILED: {e}", exc_info=True)
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 6 Full Diagnostic Orchestrator")
    parser.add_argument('--config', default='phase6_full_diagnostic_config.json', 
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    orchestrator = Phase6Orchestrator(config_path=args.config)
    success = orchestrator.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
