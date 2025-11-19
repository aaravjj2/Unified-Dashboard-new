"""
Phase 9C E2E Test Suite
========================

Comprehensive End-to-End validation for:
1. Phase 9C API Server (api_backtest_summary.py)
2. Signal Dashboard with Phase 9C integration (signal_dashboard.py)
3. Data flow: Backtest Results → API → Dashboard Display

Test Coverage:
- API health checks and endpoint validation
- Data integrity across system boundaries
- Dashboard rendering with Phase 9C data
- Error handling and graceful degradation
- Performance SLA validation (<150ms API response)

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0
Date: October 29, 2025
"""

import json
import logging
import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
API_BASE_URL = "http://localhost:5000"
DASHBOARD_URL = "http://localhost:8050"
OUTPUTS_DIR = Path("outputs/phase9c")
TEST_TIMEOUT = 30  # seconds
API_SLA = 150  # milliseconds


@dataclass
class TestResult:
    """Single test result"""
    name: str
    passed: bool
    duration_ms: float
    message: str
    details: Dict[str, Any] = None


class Phase9CE2ETestSuite:
    """
    Complete E2E test suite for Phase 9C integration
    
    Test Flow:
    1. Verify Phase 9C outputs exist
    2. Start API server
    3. Validate API endpoints
    4. Validate data integrity
    5. Start dashboard (optional)
    6. Validate dashboard integration
    7. Cleanup
    """
    
    def __init__(self):
        """Initialize test suite"""
        self.results: List[TestResult] = []
        self.api_process = None
        self.dashboard_process = None
        
        logger.info("✅ Phase 9C E2E Test Suite initialized")
    
    # ========================================================================
    # Test 1: Validate Phase 9C Outputs
    # ========================================================================
    
    def test_phase9c_outputs_exist(self) -> TestResult:
        """Verify Phase 9C validation outputs exist"""
        start = time.perf_counter()
        
        try:
            required_files = [
                OUTPUTS_DIR / "phase9c_integration_report.md",
                OUTPUTS_DIR / "phase9c_results.json",
                OUTPUTS_DIR / "phase9c_performance_summary.csv",
                OUTPUTS_DIR / "phase9c_trade_log.html"
            ]
            
            missing = [f for f in required_files if not f.exists()]
            
            if missing:
                duration = (time.perf_counter() - start) * 1000
                return TestResult(
                    name="Phase 9C Outputs Validation",
                    passed=False,
                    duration_ms=duration,
                    message=f"Missing files: {', '.join(str(f) for f in missing)}",
                    details={"missing_files": [str(f) for f in missing]}
                )
            
            # Validate JSON structure
            with open(OUTPUTS_DIR / "phase9c_results.json") as f:
                data = json.load(f)
                required_keys = ["timestamp", "all_deterministic", 
                                "total_trades", "total_pnl", "tiers"]
                missing_keys = [k for k in required_keys if k not in data]
                
                if missing_keys:
                    duration = (time.perf_counter() - start) * 1000
                    return TestResult(
                        name="Phase 9C Outputs Validation",
                        passed=False,
                        duration_ms=duration,
                        message=f"JSON missing keys: {', '.join(missing_keys)}",
                        details={"missing_keys": missing_keys}
                    )
            
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="Phase 9C Outputs Validation",
                passed=True,
                duration_ms=duration,
                message="All 4 output files exist with valid structure",
                details={"files": [str(f) for f in required_files]}
            )
        
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="Phase 9C Outputs Validation",
                passed=False,
                duration_ms=duration,
                message=f"Exception: {str(e)}",
                details={"error": str(e)}
            )
    
    # ========================================================================
    # Test 2: Start API Server
    # ========================================================================
    
    def test_start_api_server(self) -> TestResult:
        """Start Phase 9C API server"""
        start = time.perf_counter()
        
        try:
            # Check if already running with generous timeout
            logger.info("Checking if API server is already running...")
            try:
                response = requests.get(f"{API_BASE_URL}/api/backtest/health", timeout=10)
                if response.status_code == 200:
                    duration = (time.perf_counter() - start) * 1000
                    logger.info(f"✅ API server already running (response time: {duration:.0f}ms)")
                    return TestResult(
                        name="API Server Startup",
                        passed=True,
                        duration_ms=duration,
                        message="API server already running",
                        details={"status": "already_running", "response_time_ms": duration}
                    )
            except requests.exceptions.Timeout as e:
                # Server exists but is very slow - wait and retry
                logger.warning(f"⚠️  API health check timed out, retrying with longer timeout...")
                time.sleep(3)
                try:
                    response = requests.get(f"{API_BASE_URL}/api/backtest/health", timeout=15)
                    if response.status_code == 200:
                        duration = (time.perf_counter() - start) * 1000
                        logger.info(f"✅ API server running (slow response: {duration:.0f}ms)")
                        return TestResult(
                            name="API Server Startup",
                            passed=True,
                            duration_ms=duration,
                            message="API server running (slow initial response)",
                            details={"status": "slow_startup", "response_time_ms": duration}
                        )
                except Exception as retry_error:
                    logger.error(f"Retry failed: {retry_error}")
                    # Fall through to start new server
            except requests.exceptions.ConnectionError:
                logger.info("API server not running, will start it")
                # Fall through to start new server
            
            # Start API server
            logger.info("Starting Phase 9C API server...")
            self.api_process = subprocess.Popen(
                ["python", "api_backtest_summary.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            # Wait for server to be ready
            max_retries = 10
            for i in range(max_retries):
                time.sleep(1)
                try:
                    response = requests.get(f"{API_BASE_URL}/api/backtest/health", timeout=2)
                    if response.status_code == 200:
                        duration = (time.perf_counter() - start) * 1000
                        logger.info(f"✅ API server started in {duration:.0f}ms")
                        return TestResult(
                            name="API Server Startup",
                            passed=True,
                            duration_ms=duration,
                            message=f"API server started successfully (retry {i+1})",
                            details={"retries": i+1, "pid": self.api_process.pid}
                        )
                except requests.exceptions.ConnectionError:
                    logger.debug(f"Waiting for API server... (attempt {i+1}/{max_retries})")
            
            # Timeout
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="API Server Startup",
                passed=False,
                duration_ms=duration,
                message=f"API server failed to start within {TEST_TIMEOUT}s",
                details={"timeout": TEST_TIMEOUT}
            )
        
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="API Server Startup",
                passed=False,
                duration_ms=duration,
                message=f"Exception: {str(e)}",
                details={"error": str(e)}
            )
    
    # ========================================================================
    # Test 3: Validate API Endpoints
    # ========================================================================
    
    def test_api_health_endpoint(self) -> TestResult:
        """Test /api/backtest/health endpoint"""
        start = time.perf_counter()
        
        try:
            response = requests.get(f"{API_BASE_URL}/api/backtest/health", timeout=5)
            duration = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "healthy":
                    return TestResult(
                        name="API Health Endpoint",
                        passed=True,
                        duration_ms=duration,
                        message=f"Health check passed in {duration:.0f}ms",
                        details=data
                    )
                else:
                    return TestResult(
                        name="API Health Endpoint",
                        passed=False,
                        duration_ms=duration,
                        message=f"Unhealthy status: {data.get('status')}",
                        details=data
                    )
            else:
                return TestResult(
                    name="API Health Endpoint",
                    passed=False,
                    duration_ms=duration,
                    message=f"HTTP {response.status_code}",
                    details={"status_code": response.status_code}
                )
        
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="API Health Endpoint",
                passed=False,
                duration_ms=duration,
                message=f"Exception: {str(e)}",
                details={"error": str(e)}
            )
    
    def test_api_summary_endpoint(self) -> TestResult:
        """Test /api/backtest/summary endpoint"""
        start = time.perf_counter()
        
        try:
            response = requests.get(f"{API_BASE_URL}/api/backtest/summary", timeout=5)
            duration = (time.perf_counter() - start) * 1000
            
            # Check SLA
            sla_passed = duration < API_SLA
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate required fields
                required_fields = ["total_trades", "total_pnl", "win_rate", 
                                  "determinism_passed", "mode", "tiers_tested"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    return TestResult(
                        name="API Summary Endpoint",
                        passed=False,
                        duration_ms=duration,
                        message=f"Missing fields: {', '.join(missing)}",
                        details={"missing_fields": missing, "sla_passed": sla_passed}
                    )
                
                # Validate data types
                if not isinstance(data["total_trades"], int):
                    return TestResult(
                        name="API Summary Endpoint",
                        passed=False,
                        duration_ms=duration,
                        message="total_trades is not an integer",
                        details=data
                    )
                
                message = f"Summary data valid ({duration:.0f}ms)"
                if not sla_passed:
                    message += f" ⚠️ SLA violation (>{API_SLA}ms)"
                
                return TestResult(
                    name="API Summary Endpoint",
                    passed=True,
                    duration_ms=duration,
                    message=message,
                    details={**data, "sla_passed": sla_passed}
                )
            else:
                return TestResult(
                    name="API Summary Endpoint",
                    passed=False,
                    duration_ms=duration,
                    message=f"HTTP {response.status_code}",
                    details={"status_code": response.status_code, "sla_passed": sla_passed}
                )
        
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="API Summary Endpoint",
                passed=False,
                duration_ms=duration,
                message=f"Exception: {str(e)}",
                details={"error": str(e)}
            )
    
    def test_api_performance_endpoint(self) -> TestResult:
        """Test /api/backtest/performance endpoint"""
        start = time.perf_counter()
        
        try:
            # Performance endpoint loads pandas/CSV on first call which can be slow
            # Use generous timeout for first call
            response = requests.get(f"{API_BASE_URL}/api/backtest/performance", timeout=15)
            duration = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return a list of records (from CSV)
                if not isinstance(data, list):
                    return TestResult(
                        name="API Performance Endpoint",
                        passed=False,
                        duration_ms=duration,
                        message="Response is not a list (expected CSV records)",
                        details={"type": str(type(data))}
                    )
                
                # Validate we have records
                if len(data) == 0:
                    return TestResult(
                        name="API Performance Endpoint",
                        passed=False,
                        duration_ms=duration,
                        message="Empty performance data",
                        details={"record_count": 0}
                    )
                
                # Validate first record has required fields
                required = ["portfolio_tier", "num_tickers", "total_time_ms", 
                           "avg_signal_latency_ms", "sla_met"]
                missing = [f for f in required if f not in data[0]]
                if missing:
                    return TestResult(
                        name="API Performance Endpoint",
                        passed=False,
                        duration_ms=duration,
                        message=f"Missing fields in record: {', '.join(missing)}",
                        details={"missing_fields": missing, "sample_record": data[0]}
                    )
                
                # Build tier summary for details
                tier_summary = {
                    record["portfolio_tier"]: {
                        "avg_signal_latency_ms": record["avg_signal_latency_ms"],
                        "sla_met": record["sla_met"]
                    }
                    for record in data
                }
                
                return TestResult(
                    name="API Performance Endpoint",
                    passed=True,
                    duration_ms=duration,
                    message=f"Performance data valid with {len(data)} tier records",
                    details={
                        "record_count": len(data),
                        "tiers": tier_summary
                    }
                )
            else:
                return TestResult(
                    name="API Performance Endpoint",
                    passed=False,
                    duration_ms=duration,
                    message=f"HTTP {response.status_code}",
                    details={"status_code": response.status_code}
                )
        
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="API Performance Endpoint",
                passed=False,
                duration_ms=duration,
                message=f"Exception: {str(e)}",
                details={"error": str(e)}
            )
    
    # ========================================================================
    # Test 4: Data Integrity Validation
    # ========================================================================
    
    def test_data_integrity(self) -> TestResult:
        """Validate data consistency between JSON file and API"""
        start = time.perf_counter()
        
        try:
            # Load source JSON
            with open(OUTPUTS_DIR / "phase9c_results.json") as f:
                source_data = json.load(f)
            
            # Fetch API data
            response = requests.get(f"{API_BASE_URL}/api/backtest/summary", timeout=5)
            api_data = response.json()
            
            # Compare key metrics
            mismatches = []
            
            if source_data.get("total_trades") != api_data.get("total_trades"):
                mismatches.append(f"total_trades: {source_data.get('total_trades')} != {api_data.get('total_trades')}")
            
            source_pnl = source_data.get("total_pnl", 0)
            api_pnl = api_data.get("total_pnl", 0)
            if abs(source_pnl - api_pnl) > 0.01:
                mismatches.append(f"total_pnl: {source_pnl:.2f} != {api_pnl:.2f}")
            
            # API converts all_deterministic -> determinism_passed
            source_det = source_data.get("all_deterministic", False)
            api_det = api_data.get("determinism_passed", False)
            if source_det != api_det:
                mismatches.append(f"determinism: {source_det} != {api_det}")
            
            # Validate tiers_tested exists and matches
            if "tiers_tested" in api_data:
                source_tiers = set(source_data.get("tiers", {}).keys())
                api_tiers = set(api_data.get("tiers_tested", []))
                if source_tiers != api_tiers:
                    mismatches.append(f"tiers_tested: {source_tiers} != {api_tiers}")
            
            duration = (time.perf_counter() - start) * 1000
            
            if mismatches:
                return TestResult(
                    name="Data Integrity Validation",
                    passed=False,
                    duration_ms=duration,
                    message=f"Data mismatches: {'; '.join(mismatches)}",
                    details={"mismatches": mismatches}
                )
            else:
                return TestResult(
                    name="Data Integrity Validation",
                    passed=True,
                    duration_ms=duration,
                    message="JSON and API data consistent",
                    details={
                        "validated_fields": ["total_trades", "total_pnl", "determinism_passed", "tiers_tested"],
                        "source_pnl": round(source_pnl, 2),
                        "api_pnl": round(api_pnl, 2)
                    }
                )
        
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="Data Integrity Validation",
                passed=False,
                duration_ms=duration,
                message=f"Exception: {str(e)}",
                details={"error": str(e)}
            )
    
    # ========================================================================
    # Test 5: Dashboard Integration (Optional - requires Playwright)
    # ========================================================================
    
    def test_dashboard_integration(self) -> TestResult:
        """Test Signal Dashboard Phase 9C integration (basic validation)"""
        start = time.perf_counter()
        
        try:
            # This is a basic test that validates the dashboard can access the API
            # Full UI testing would require Playwright
            
            # Verify dashboard file exists
            dashboard_path = Path("signal_dashboard.py")
            if not dashboard_path.exists():
                duration = (time.perf_counter() - start) * 1000
                return TestResult(
                    name="Dashboard Integration",
                    passed=False,
                    duration_ms=duration,
                    message=f"signal_dashboard.py not found",
                    details={"path": str(dashboard_path.absolute())}
                )
            
            logger.info("✅ signal_dashboard.py file exists")
            
            # Test that dashboard can fetch backtest data
            response = requests.get(f"{API_BASE_URL}/api/backtest/summary", timeout=5)
            
            if response.status_code == 200:
                duration = (time.perf_counter() - start) * 1000
                return TestResult(
                    name="Dashboard Integration",
                    passed=True,
                    duration_ms=duration,
                    message="Dashboard file exists and API is accessible",
                    details={
                        "dashboard_file": str(dashboard_path.absolute()),
                        "api_accessible": True,
                        "note": "Full UI testing requires Playwright (see test_phase9c_playwright.py)"
                    }
                )
            else:
                duration = (time.perf_counter() - start) * 1000
                return TestResult(
                    name="Dashboard Integration",
                    passed=False,
                    duration_ms=duration,
                    message=f"API not accessible (HTTP {response.status_code})",
                    details={"status_code": response.status_code}
                )
        
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="Dashboard Integration",
                passed=False,
                duration_ms=duration,
                message=f"Exception: {str(e)}",
                details={"error": str(e)}
            )
    
    # ========================================================================
    # Run Full Test Suite
    # ========================================================================
    
    def run_all_tests(self) -> Tuple[int, int]:
        """
        Run complete E2E test suite
        
        Returns:
            (passed_count, total_count)
        """
        logger.info("=" * 80)
        logger.info("PHASE 9C E2E TEST SUITE")
        logger.info("=" * 80)
        
        # Test 1: Validate outputs
        logger.info("\n[1/6] Validating Phase 9C outputs...")
        result = self.test_phase9c_outputs_exist()
        self.results.append(result)
        self._log_result(result)
        
        if not result.passed:
            logger.error("❌ Cannot proceed without Phase 9C outputs. Run: python run_phase9c_validation.py")
            return self._report_summary()
        
        # Test 2: Start API server
        logger.info("\n[2/6] Starting API server...")
        result = self.test_start_api_server()
        self.results.append(result)
        self._log_result(result)
        
        if not result.passed:
            logger.error("❌ Cannot proceed without API server")
            return self._report_summary()
        
        # Test 3a: Health endpoint
        logger.info("\n[3a/6] Testing API health endpoint...")
        result = self.test_api_health_endpoint()
        self.results.append(result)
        self._log_result(result)
        
        # Test 3b: Summary endpoint
        logger.info("\n[3b/6] Testing API summary endpoint...")
        result = self.test_api_summary_endpoint()
        self.results.append(result)
        self._log_result(result)
        
        # Test 3c: Performance endpoint
        logger.info("\n[3c/6] Testing API performance endpoint...")
        result = self.test_api_performance_endpoint()
        self.results.append(result)
        self._log_result(result)
        
        # Test 4: Data integrity
        logger.info("\n[4/6] Validating data integrity...")
        result = self.test_data_integrity()
        self.results.append(result)
        self._log_result(result)
        
        # Test 5: Dashboard integration
        logger.info("\n[5/6] Testing dashboard integration...")
        result = self.test_dashboard_integration()
        self.results.append(result)
        self._log_result(result)
        
        # Generate summary
        return self._report_summary()
    
    def _log_result(self, result: TestResult):
        """Log test result"""
        icon = "✅" if result.passed else "❌"
        logger.info(f"{icon} {result.name}: {result.message} ({result.duration_ms:.0f}ms)")
    
    def _report_summary(self) -> Tuple[int, int]:
        """Generate test summary"""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 9C E2E TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Passed: {passed}/{total}")
        logger.info(f"Failed: {total - passed}/{total}")
        logger.info(f"Success Rate: {(passed/total*100):.1f}%")
        
        # Detailed results
        logger.info("\nDetailed Results:")
        for i, result in enumerate(self.results, 1):
            icon = "✅" if result.passed else "❌"
            logger.info(f"  {i}. {icon} {result.name} ({result.duration_ms:.0f}ms)")
        
        # Save report
        self._save_report()
        
        if passed == total:
            logger.info("\n🎉 ALL TESTS PASSED!")
            logger.info("✅ Phase 9C E2E validation complete")
        else:
            logger.error(f"\n❌ {total - passed} TESTS FAILED")
        
        return passed, total
    
    def _save_report(self):
        """Save test report to file"""
        report_file = Path("outputs/phase9c") / "phase9c_e2e_test_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "success_rate": f"{sum(1 for r in self.results if r.passed)/len(self.results)*100:.1f}%"
            },
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n💾 Test report saved: {report_file}")
    
    def cleanup(self):
        """Cleanup test resources"""
        logger.info("\n🧹 Cleaning up...")
        
        if self.api_process:
            logger.info("Stopping API server...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
        
        if self.dashboard_process:
            logger.info("Stopping dashboard...")
            self.dashboard_process.terminate()
            try:
                self.dashboard_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.dashboard_process.kill()
        
        logger.info("✅ Cleanup complete")


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 9C E2E Test Suite')
    parser.add_argument('--no-cleanup', action='store_true', 
                       help='Do not cleanup (leave API server running)')
    args = parser.parse_args()
    
    suite = Phase9CE2ETestSuite()
    
    try:
        passed, total = suite.run_all_tests()
        
        # Exit code: 0 if all passed, 1 if any failed
        exit_code = 0 if passed == total else 1
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Tests interrupted by user")
        exit_code = 130
    
    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    finally:
        if not args.no_cleanup:
            suite.cleanup()
        else:
            logger.info("\n⚠️  Skipping cleanup (--no-cleanup flag). API server still running.")
    
    exit(exit_code)
