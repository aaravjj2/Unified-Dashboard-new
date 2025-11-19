#!/usr/bin/env python3
"""
🧪 PHASE 0 VALIDATION ORCHESTRATOR
==================================

Full validation loop for Home & Strategy Labs (Clicker-Driven, Dockerized)

Execution Order:
1. Phase 0: Boot & Diagnostics
2. Phase 1: Playwright Clicker Functional Testing (CORE LAYER)
3. Phase 2: Snapshot Regression Testing (Visual Layer)
4. Phase 3: HTML Render Inspection
5. Phase 4: Consolidated Health & Summary

Target Labs: Home → Strategy → Attribution → Volatility → Research → Forecast → Options → Portfolio
"""

import sys
import os
import json
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# CONFIGURATION
# ============================================================================

class ValidationConfig:
    """Central configuration for Phase 0 validation"""
    
    # Environment
    DOCKER_COMPOSE_FILE = Path(__file__).parent.parent / "docker-compose.yml"
    DASHBOARD_URL = "http://localhost:8050"
    DASHBOARD_SERVICE = "dash_app"
    
    # Timing thresholds
    MAX_STARTUP_TIME_SEC = 60
    MAX_CALLBACK_LATENCY_SEC = 4
    MIN_DOM_MUTATION_RATIO = 1.0
    MAX_SNAPSHOT_DIFF_PCT = 0.5
    
    # Test order (strict sequence)
    LAB_TEST_SEQUENCE = [
        "home_lab",
        "strategy_lab",
        "attribution_lab",
        "volatility_lab",
        "research_lab",
        "market_forecast",
        "options_lab",
        "portfolio"
    ]
    
    # Output directories
    OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "phase0_validation"
    SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"
    SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"
    REPORTS_DIR = OUTPUT_DIR / "reports"
    LOGS_DIR = OUTPUT_DIR / "logs"
    ARCHIVE_DIR = Path(__file__).parent.parent / "outputs" / "phase0_validation_archive"
    
    # Cleanup targets
    CACHE_DIRS = [
        Path(__file__).parent.parent / "financial_dashboard" / "__pycache__",
        Path(__file__).parent.parent / "financial_dashboard" / "tabs" / "__pycache__",
        Path(__file__).parent.parent / ".pytest_cache",
        Path(__file__).parent.parent / "dash_temp"
    ]
    
    @classmethod
    def init_directories(cls):
        """Create all output directories"""
        for dir_path in [cls.OUTPUT_DIR, cls.SCREENSHOT_DIR, cls.SNAPSHOT_DIR, 
                         cls.REPORTS_DIR, cls.LOGS_DIR, cls.ARCHIVE_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def clear_cache(cls):
        """Clear Python cache directories"""
        for cache_dir in cls.CACHE_DIRS:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                print(f"🧹 Cleared cache: {cache_dir}")


# ============================================================================
# LOGGER
# ============================================================================

class ValidationLogger:
    """Structured logging for validation phases"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.start_time = datetime.now()
        self.events = []
        
        # Initialize log file
        with open(self.log_file, 'w') as f:
            f.write(f"Phase 0 Validation Log - {self.start_time.isoformat()}\n")
            f.write("=" * 80 + "\n\n")
    
    def log(self, level: str, category: str, message: str):
        """Log event with timestamp"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp = datetime.now().isoformat()
        
        event = {
            "timestamp": timestamp,
            "elapsed_sec": round(elapsed, 3),
            "level": level,
            "category": category,
            "message": message
        }
        
        self.events.append(event)
        
        # Console output with color
        color_map = {
            "INFO": "\033[94m",      # Blue
            "SUCCESS": "\033[92m",   # Green
            "WARNING": "\033[93m",   # Yellow
            "ERROR": "\033[91m",     # Red
            "RESET": "\033[0m"
        }
        
        color = color_map.get(level, "")
        reset = color_map["RESET"]
        
        console_msg = f"{color}[{elapsed:>7.2f}s] [{level:^8}] [{category:^20}] {message}{reset}"
        print(console_msg)
        
        # File output (no color codes)
        with open(self.log_file, 'a') as f:
            f.write(f"[{elapsed:>7.2f}s] [{level:^8}] [{category:^20}] {message}\n")
    
    def info(self, category: str, message: str):
        self.log("INFO", category, message)
    
    def success(self, category: str, message: str):
        self.log("SUCCESS", category, message)
    
    def warning(self, category: str, message: str):
        self.log("WARNING", category, message)
    
    def error(self, category: str, message: str):
        self.log("ERROR", category, message)
    
    def separator(self, title: str = ""):
        """Print visual separator"""
        sep = "=" * 80
        if title:
            print(f"\n{sep}")
            print(f"  {title}")
            print(f"{sep}\n")
            with open(self.log_file, 'a') as f:
                f.write(f"\n{sep}\n  {title}\n{sep}\n\n")
        else:
            print(sep)
            with open(self.log_file, 'a') as f:
                f.write(f"{sep}\n")
    
    def save_json_summary(self, output_path: Path):
        """Save events to JSON"""
        with open(output_path, 'w') as f:
            json.dump({
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_events": len(self.events),
                "events": self.events
            }, f, indent=2)


# ============================================================================
# PHASE 0: BOOT & DIAGNOSTICS
# ============================================================================

class Phase0BootDiagnostics:
    """Phase 0: Boot & diagnostics validation"""
    
    def __init__(self, logger: ValidationLogger):
        self.logger = logger
        self.results = {
            "startup_time_sec": 0,
            "app_boots": False,
            "no_layout_errors": False,
            "all_tabs_present": False,
            "diagnostics_passed": False,
            "errors": []
        }
    
    def run(self) -> Dict:
        """Execute Phase 0 diagnostics"""
        self.logger.separator("PHASE 0: Boot & Diagnostics")
        
        # Step 1: Clear cache
        self.logger.info("SETUP", "Clearing Python cache...")
        ValidationConfig.clear_cache()
        self.logger.success("SETUP", "Cache cleared")
        
        # Step 2: Start Docker services
        self.logger.info("DOCKER", "Starting Docker services...")
        startup_success, startup_time = self._start_docker_services()
        self.results["startup_time_sec"] = startup_time
        self.results["app_boots"] = startup_success
        
        if not startup_success:
            self.logger.error("DOCKER", f"Dashboard failed to start within {ValidationConfig.MAX_STARTUP_TIME_SEC}s")
            return self.results
        
        self.logger.success("DOCKER", f"Dashboard started in {startup_time:.2f}s")
        
        # Step 3: Run startup diagnostics
        self.logger.info("DIAGNOSTICS", "Running diagnostics_dashboard_startup.py...")
        diag_passed = self._run_startup_diagnostics()
        self.results["diagnostics_passed"] = diag_passed
        
        # Step 4: Validate layout structure
        self.logger.info("LAYOUT", "Validating app layout structure...")
        layout_valid, tabs_present = self._validate_layout()
        self.results["no_layout_errors"] = layout_valid
        self.results["all_tabs_present"] = tabs_present
        
        # Generate Phase 0 report
        self._generate_phase0_report()
        
        return self.results
    
    def _start_docker_services(self) -> Tuple[bool, float]:
        """Start Docker Compose and wait for dashboard"""
        start_time = time.time()
        
        try:
            # Build and start services
            cmd = ["docker-compose", "-f", str(ValidationConfig.DOCKER_COMPOSE_FILE), 
                   "up", "--build", "-d", ValidationConfig.DASHBOARD_SERVICE]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                self.logger.error("DOCKER", f"docker-compose up failed: {result.stderr}")
                self.results["errors"].append(f"Docker startup failed: {result.stderr}")
                return False, 0
            
            # Wait for dashboard to be ready
            self.logger.info("DOCKER", "Waiting for dashboard to be ready...")
            
            max_wait = ValidationConfig.MAX_STARTUP_TIME_SEC
            poll_interval = 2
            elapsed = 0
            
            while elapsed < max_wait:
                try:
                    import requests
                    response = requests.get(ValidationConfig.DASHBOARD_URL, timeout=5)
                    if response.status_code == 200:
                        startup_time = time.time() - start_time
                        return True, startup_time
                except:
                    pass
                
                time.sleep(poll_interval)
                elapsed += poll_interval
                self.logger.info("DOCKER", f"Still waiting... ({elapsed}s / {max_wait}s)")
            
            # Timeout
            self.logger.error("DOCKER", f"Dashboard did not respond within {max_wait}s")
            self.results["errors"].append(f"Dashboard startup timeout ({max_wait}s)")
            return False, time.time() - start_time
            
        except Exception as e:
            self.logger.error("DOCKER", f"Docker startup exception: {e}")
            self.results["errors"].append(f"Docker exception: {str(e)}")
            return False, 0
    
    def _run_startup_diagnostics(self) -> bool:
        """Run diagnostics_dashboard_startup.py inside container"""
        try:
            cmd = [
                "docker", "exec", "dash_app",
                "python", "-m", "diagnostics_dashboard_startup"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Save diagnostic output
            diag_output_path = ValidationConfig.LOGS_DIR / "diagnostics_dashboard_startup.log"
            with open(diag_output_path, 'w') as f:
                f.write(result.stdout)
                f.write(result.stderr)
            
            self.logger.info("DIAGNOSTICS", f"Output saved to {diag_output_path}")
            
            # Check for critical errors
            if "ERROR" in result.stdout or result.returncode != 0:
                self.logger.warning("DIAGNOSTICS", "Diagnostics reported errors")
                return False
            
            self.logger.success("DIAGNOSTICS", "Diagnostics passed")
            return True
            
        except Exception as e:
            self.logger.error("DIAGNOSTICS", f"Failed to run diagnostics: {e}")
            self.results["errors"].append(f"Diagnostics error: {str(e)}")
            return False
    
    def _validate_layout(self) -> Tuple[bool, bool]:
        """Validate layout structure via HTTP request"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(ValidationConfig.DASHBOARD_URL, timeout=10)
            
            if response.status_code != 200:
                self.logger.error("LAYOUT", f"HTTP {response.status_code}")
                self.results["errors"].append(f"Layout fetch failed: HTTP {response.status_code}")
                return False, False
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for React root
            react_root = soup.find('div', id='react-entry-point')
            if not react_root:
                self.logger.error("LAYOUT", "No React root found")
                self.results["errors"].append("No React root div")
                return False, False
            
            # Check for tabs (look for tab navigation)
            tabs_found = []
            tab_elements = soup.find_all('a', {'class': 'nav-link'})
            
            for tab in tab_elements:
                tab_text = tab.get_text(strip=True)
                tabs_found.append(tab_text)
            
            self.logger.info("LAYOUT", f"Found {len(tabs_found)} tabs: {', '.join(tabs_found[:5])}...")
            
            # Check if all target labs are present
            target_labs = ["Home", "Command Center", "Strategy", "Attribution", "Volatility"]
            all_present = all(any(target in tab for tab in tabs_found) for target in target_labs)
            
            if all_present:
                self.logger.success("LAYOUT", "All target labs present")
            else:
                self.logger.warning("LAYOUT", "Some target labs missing")
            
            return True, all_present
            
        except Exception as e:
            self.logger.error("LAYOUT", f"Layout validation failed: {e}")
            self.results["errors"].append(f"Layout validation error: {str(e)}")
            return False, False
    
    def _generate_phase0_report(self):
        """Generate Phase 0 JSON report"""
        report_path = ValidationConfig.REPORTS_DIR / "phase0_boot_diagnostics.json"
        
        with open(report_path, 'w') as f:
            json.dump({
                "phase": "Phase 0: Boot & Diagnostics",
                "timestamp": datetime.now().isoformat(),
                "results": self.results,
                "thresholds": {
                    "max_startup_time_sec": ValidationConfig.MAX_STARTUP_TIME_SEC
                },
                "pass_criteria": {
                    "startup_time": self.results["startup_time_sec"] < ValidationConfig.MAX_STARTUP_TIME_SEC,
                    "app_boots": self.results["app_boots"],
                    "no_layout_errors": self.results["no_layout_errors"],
                    "all_tabs_present": self.results["all_tabs_present"],
                    "diagnostics_passed": self.results["diagnostics_passed"]
                },
                "overall_pass": all([
                    self.results["startup_time_sec"] < ValidationConfig.MAX_STARTUP_TIME_SEC,
                    self.results["app_boots"],
                    self.results["no_layout_errors"],
                    self.results["diagnostics_passed"]
                ])
            }, f, indent=2)
        
        self.logger.info("REPORT", f"Phase 0 report saved to {report_path}")


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class ValidationOrchestrator:
    """Master orchestrator for full validation loop"""
    
    def __init__(self):
        # Initialize directories
        ValidationConfig.init_directories()
        
        # Initialize logger
        log_file = ValidationConfig.LOGS_DIR / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger = ValidationLogger(log_file)
        
        # Results tracking
        self.phase_results = {}
    
    def run_full_validation(self):
        """Execute complete validation loop"""
        self.logger.separator("🧪 PHASE 0 VALIDATION - FULL LOOP")
        self.logger.info("ORCHESTRATOR", f"Dashboard URL: {ValidationConfig.DASHBOARD_URL}")
        self.logger.info("ORCHESTRATOR", f"Output directory: {ValidationConfig.OUTPUT_DIR}")
        
        try:
            # Phase 0: Boot & Diagnostics
            phase0 = Phase0BootDiagnostics(self.logger)
            self.phase_results["phase0"] = phase0.run()
            
            if not self.phase_results["phase0"]["app_boots"]:
                self.logger.error("ORCHESTRATOR", "Phase 0 failed - aborting remaining phases")
                self._generate_final_report()
                return False
            
            # Phase 1: Clicker Tests
            self.logger.separator("PHASE 1: Playwright Clicker Testing")
            self.logger.info("PHASE1", "Loading clicker test suite...")
            
            try:
                from tests.phase1_clicker_tests import ClickerTestExecutor
                import asyncio
                
                self.logger.info("PHASE1", "Initializing Playwright clicker tests...")
                executor = ClickerTestExecutor()
                
                self.logger.info("PHASE1", "Running click-through validation...")
                phase1_results = asyncio.run(executor.run_all_tests())
                
                self.phase_results["phase1"] = {
                    "total_clicks": phase1_results.get("total_clicks", 0),
                    "successful_clicks": phase1_results.get("successful_clicks", 0),
                    "failed_clicks": phase1_results.get("failed_clicks", 0),
                    "avg_latency_ms": sum(phase1_results.get("callback_latencies", [])) / len(phase1_results.get("callback_latencies", [1])),
                    "errors": phase1_results.get("errors", [])
                }
                
                if phase1_results.get("failed_clicks", 0) > 0:
                    self.logger.warning("PHASE1", f"{phase1_results['failed_clicks']} clicks failed - reviewing for auto-retry")
                    
                    # Auto-retry logic: clear cache and retry once
                    self.logger.info("PHASE1", "Clearing cache and retrying failed tests...")
                    ValidationConfig.clear_cache()
                    time.sleep(5)
                    
                    retry_executor = ClickerTestExecutor()
                    retry_results = asyncio.run(retry_executor.run_all_tests())
                    
                    self.phase_results["phase1_retry"] = {
                        "total_clicks": retry_results.get("total_clicks", 0),
                        "successful_clicks": retry_results.get("successful_clicks", 0),
                        "failed_clicks": retry_results.get("failed_clicks", 0)
                    }
                    
                    if retry_results.get("failed_clicks", 0) == 0:
                        self.logger.success("PHASE1", "All tests passed on retry!")
                    else:
                        self.logger.error("PHASE1", f"Retry still has {retry_results['failed_clicks']} failures")
                else:
                    self.logger.success("PHASE1", "All clicker tests passed on first attempt!")
                    
            except Exception as e:
                self.logger.error("PHASE1", f"Clicker tests failed with exception: {e}")
                import traceback
                self.logger.error("PHASE1", traceback.format_exc())
                self.phase_results["phase1"] = {"error": str(e), "traceback": traceback.format_exc()}
            
            # Phase 2: Snapshot Tests (to be implemented)
            self.logger.separator("PHASE 2: Snapshot Regression Testing")
            self.logger.info("PHASE2", "Snapshot tests not yet implemented")
            
            # Phase 3: HTML Inspection (to be implemented)
            self.logger.separator("PHASE 3: HTML Render Inspection")
            self.logger.info("PHASE3", "HTML inspection not yet implemented")
            
            # Phase 4: Final Report
            self._generate_final_report()
            
            return True
            
        except KeyboardInterrupt:
            self.logger.warning("ORCHESTRATOR", "Validation interrupted by user")
            self._generate_final_report()
            return False
        
        except Exception as e:
            self.logger.error("ORCHESTRATOR", f"Validation failed with exception: {e}")
            import traceback
            self.logger.error("ORCHESTRATOR", traceback.format_exc())
            self._generate_final_report()
            return False
    
    def _generate_final_report(self):
        """Generate consolidated final report"""
        self.logger.separator("PHASE 4: Consolidated Health & Summary")
        
        report = {
            "validation_run": datetime.now().isoformat(),
            "dashboard_url": ValidationConfig.DASHBOARD_URL,
            "phases_completed": list(self.phase_results.keys()),
            "phase_results": self.phase_results,
            "thresholds": {
                "startup_time_sec": ValidationConfig.MAX_STARTUP_TIME_SEC,
                "callback_latency_sec": ValidationConfig.MAX_CALLBACK_LATENCY_SEC,
                "dom_mutation_ratio": ValidationConfig.MIN_DOM_MUTATION_RATIO,
                "snapshot_diff_pct": ValidationConfig.MAX_SNAPSHOT_DIFF_PCT
            }
        }
        
        # Compute overall health
        health_checks = {}
        
        if "phase0" in self.phase_results:
            p0 = self.phase_results["phase0"]
            health_checks["Startup Time"] = {
                "target": f"< {ValidationConfig.MAX_STARTUP_TIME_SEC} s",
                "actual": f"{p0.get('startup_time_sec', 0):.2f} s",
                "status": "✅" if p0.get('startup_time_sec', 999) < ValidationConfig.MAX_STARTUP_TIME_SEC else "❌"
            }
            health_checks["App Boots"] = {
                "target": "True",
                "actual": str(p0.get('app_boots', False)),
                "status": "✅" if p0.get('app_boots', False) else "❌"
            }
            health_checks["Layout Valid"] = {
                "target": "True",
                "actual": str(p0.get('no_layout_errors', False)),
                "status": "✅" if p0.get('no_layout_errors', False) else "❌"
            }
            health_checks["Diagnostics"] = {
                "target": "Pass",
                "actual": "Pass" if p0.get('diagnostics_passed', False) else "Fail",
                "status": "✅" if p0.get('diagnostics_passed', False) else "❌"
            }
        
        report["health_checks"] = health_checks
        
        # Save report
        report_path = ValidationConfig.REPORTS_DIR / "PHASE0_VALIDATION_FINAL_REPORT.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate Markdown report
        md_path = ValidationConfig.REPORTS_DIR / "PHASE0_VALIDATION_FINAL_REPORT.md"
        self._generate_markdown_report(report, md_path)
        
        self.logger.success("REPORT", f"Final report saved to {report_path}")
        self.logger.success("REPORT", f"Markdown report saved to {md_path}")
        
        # Print summary
        self.logger.separator("VALIDATION SUMMARY")
        for check_name, check_data in health_checks.items():
            self.logger.info("SUMMARY", f"{check_name}: {check_data['status']} (Target: {check_data['target']}, Actual: {check_data['actual']})")
    
    def _generate_markdown_report(self, report: Dict, output_path: Path):
        """Generate human-readable Markdown report"""
        with open(output_path, 'w') as f:
            f.write("# 🧪 Phase 0 Validation Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Dashboard URL:** {report['dashboard_url']}\n\n")
            
            f.write("## Health Checks\n\n")
            f.write("| Metric | Target | Actual | Status |\n")
            f.write("|--------|--------|--------|--------|\n")
            
            for check_name, check_data in report.get('health_checks', {}).items():
                f.write(f"| {check_name} | {check_data['target']} | {check_data['actual']} | {check_data['status']} |\n")
            
            f.write("\n## Phase Results\n\n")
            
            if "phase0" in report['phase_results']:
                f.write("### Phase 0: Boot & Diagnostics\n\n")
                p0 = report['phase_results']['phase0']
                f.write(f"- **Startup Time:** {p0.get('startup_time_sec', 0):.2f} seconds\n")
                f.write(f"- **App Boots:** {p0.get('app_boots', False)}\n")
                f.write(f"- **Layout Valid:** {p0.get('no_layout_errors', False)}\n")
                f.write(f"- **All Tabs Present:** {p0.get('all_tabs_present', False)}\n")
                f.write(f"- **Diagnostics Passed:** {p0.get('diagnostics_passed', False)}\n")
                
                if p0.get('errors'):
                    f.write("\n**Errors:**\n\n")
                    for error in p0['errors']:
                        f.write(f"- {error}\n")
            
            f.write("\n## Thresholds\n\n")
            f.write(f"- **Max Startup Time:** {report['thresholds']['startup_time_sec']} seconds\n")
            f.write(f"- **Max Callback Latency:** {report['thresholds']['callback_latency_sec']} seconds\n")
            f.write(f"- **Min DOM Mutation Ratio:** {report['thresholds']['dom_mutation_ratio']}\n")
            f.write(f"- **Max Snapshot Diff:** {report['thresholds']['snapshot_diff_pct']}%\n")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("  🧪 PHASE 0 VALIDATION ORCHESTRATOR")
    print("  Clicker-Driven, Dockerized Testing for Financial Dashboard")
    print("="*80 + "\n")
    
    orchestrator = ValidationOrchestrator()
    success = orchestrator.run_full_validation()
    
    if success:
        print("\n✅ Validation completed successfully!\n")
        return 0
    else:
        print("\n❌ Validation failed - check reports for details\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
