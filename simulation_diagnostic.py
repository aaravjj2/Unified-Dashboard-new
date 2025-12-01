"""
Phase 7 — Simulation Diagnostic: Automated Test Harness & Validation
=====================================================================

Comprehensive testing framework for scenario engine, portfolio simulator,
and options risk simulator to ensure correctness, reproducibility, and performance.

Features:
- Deterministic reproducibility validation
- Risk metric calculation verification
- Greeks accuracy checks
- Scenario coverage testing
- Performance benchmarking
- Regression testing
- Multi-format diagnostic reports (JSON/Markdown)

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 7 - Offline Simulation Framework)
Date: October 29, 2025
"""

import json
import numpy as np
import time
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

# Import simulation components
from scenario_engine import (
    ScenarioEngine, ScenarioParameters, ScenarioType,
    StressType, EventType, create_monte_carlo_scenario,
    create_stress_scenario, create_event_scenario
)
from portfolio_simulator import (
    Portfolio, PortfolioLoader, PortfolioSimulator,
    RiskCalculator
)
from options_risk_simulator import (
    OptionsRiskSimulator, create_option_contract,
    BlackScholesModel, OptionType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# TEST RESULT DATA STRUCTURES
# ============================================================================

@dataclass
class TestResult:
    """Single test result"""
    test_name: str
    category: str
    passed: bool
    message: str
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        # Convert numpy types to native Python types
        details_serializable = {}
        for k, v in self.details.items():
            if isinstance(v, (np.integer, np.floating)):
                details_serializable[k] = float(v)
            elif isinstance(v, np.bool_):
                details_serializable[k] = bool(v)
            else:
                details_serializable[k] = v
        
        return {
            "test_name": self.test_name,
            "category": self.category,
            "passed": bool(self.passed),
            "message": self.message,
            "duration_ms": float(self.duration_ms),
            "details": details_serializable,
            "timestamp": self.timestamp
        }


@dataclass
class DiagnosticReport:
    """Complete diagnostic test report"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    test_results: List[TestResult]
    summary: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": self.success_rate,
            "test_results": [t.to_dict() for t in self.test_results],
            "summary": self.summary
        }


# ============================================================================
# SIMULATION DIAGNOSTIC FRAMEWORK
# ============================================================================

class SimulationDiagnostic:
    """
    Automated testing framework for Phase 7 simulation components.
    """
    
    def __init__(self, output_dir: str = "outputs/phase7_diagnostics"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_results: List[TestResult] = []
    
    # ========================================================================
    # SCENARIO ENGINE TESTS
    # ========================================================================
    
    def test_monte_carlo_reproducibility(self) -> TestResult:
        """Test that Monte Carlo simulations are deterministic with same seed"""
        test_name = "Monte Carlo Reproducibility"
        start_time = time.time()
        
        try:
            # Run twice with same seed
            scenario1 = create_monte_carlo_scenario(
                tickers=["SPY"],
                num_simulations=100,
                num_days=30,
                random_seed=42
            )
            
            scenario2 = create_monte_carlo_scenario(
                tickers=["SPY"],
                num_simulations=100,
                num_days=30,
                random_seed=42
            )
            
            # Compare prices
            prices1 = scenario1.paths[0].prices
            prices2 = scenario2.paths[0].prices
            
            max_diff = max(abs(p1 - p2) for p1, p2 in zip(prices1, prices2))
            
            passed = max_diff < 1e-10
            message = f"Max difference: {max_diff:.2e}" if passed else f"Reproducibility failed: {max_diff:.2e}"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="scenario_engine",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={"max_diff": max_diff}
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="scenario_engine",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    def test_stress_scenario_coverage(self) -> TestResult:
        """Test all stress scenario types"""
        test_name = "Stress Scenario Coverage"
        start_time = time.time()
        
        try:
            stress_types = [
                StressType.VOLATILITY_SPIKE,
                StressType.SECTOR_SHOCK,
                StressType.BLACK_SWAN
            ]
            
            scenarios_generated = []
            
            for stress_type in stress_types:
                scenario = create_stress_scenario(
                    tickers=["SPY"],
                    stress_type=stress_type,
                    num_days=30,
                    random_seed=42
                )
                scenarios_generated.append(stress_type.value)
            
            passed = len(scenarios_generated) == len(stress_types)
            message = f"Generated {len(scenarios_generated)}/{len(stress_types)} stress scenarios"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="scenario_engine",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={"scenarios": scenarios_generated}
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="scenario_engine",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    def test_event_driven_scenarios(self) -> TestResult:
        """Test event-driven scenario generation"""
        test_name = "Event-Driven Scenarios"
        start_time = time.time()
        
        try:
            events = [
                EventType.EARNINGS_BEAT,
                EventType.FED_RATE_HIKE
            ]
            
            scenarios_generated = []
            
            for event_type in events:
                scenario = create_event_scenario(
                    tickers=["SPY"],
                    event_type=event_type,
                    event_day=50,
                    num_days=100,
                    random_seed=42
                )
                scenarios_generated.append(event_type.value)
            
            passed = len(scenarios_generated) == len(events)
            message = f"Generated {len(scenarios_generated)}/{len(events)} event scenarios"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="scenario_engine",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={"events": scenarios_generated}
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="scenario_engine",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    # ========================================================================
    # PORTFOLIO SIMULATOR TESTS
    # ========================================================================
    
    def test_var_calculation(self) -> TestResult:
        """Test VaR calculation accuracy"""
        test_name = "VaR Calculation"
        start_time = time.time()
        
        try:
            # Known distribution: Normal(0, 1)
            np.random.seed(42)
            returns = np.random.standard_normal(10000)
            
            var_95 = RiskCalculator.calculate_var(returns, 0.95)
            var_99 = RiskCalculator.calculate_var(returns, 0.99)
            
            # Theoretical values for standard normal
            theoretical_var_95 = 1.645  # 95th percentile
            theoretical_var_99 = 2.326  # 99th percentile
            
            error_95 = abs(var_95 - theoretical_var_95)
            error_99 = abs(var_99 - theoretical_var_99)
            
            # Allow 5% tolerance
            passed = error_95 < 0.1 and error_99 < 0.1
            message = f"VaR95 error: {error_95:.3f}, VaR99 error: {error_99:.3f}"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="portfolio_simulator",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={
                    "var_95_calculated": var_95,
                    "var_95_theoretical": theoretical_var_95,
                    "var_99_calculated": var_99,
                    "var_99_theoretical": theoretical_var_99
                }
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="portfolio_simulator",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    def test_sharpe_ratio_calculation(self) -> TestResult:
        """Test Sharpe Ratio calculation"""
        test_name = "Sharpe Ratio Calculation"
        start_time = time.time()
        
        try:
            # Known scenario: 10% annual return, 15% annual volatility
            np.random.seed(42)
            daily_return = 0.10 / 252
            daily_vol = 0.15 / np.sqrt(252)
            
            returns = np.random.normal(daily_return, daily_vol, 252)
            
            sharpe = RiskCalculator.calculate_sharpe_ratio(returns, risk_free_rate=0.0)
            
            # Theoretical Sharpe: 0.10 / 0.15 = 0.667
            theoretical_sharpe = 0.10 / 0.15
            
            error = abs(sharpe - theoretical_sharpe)
            
            # Allow 20% tolerance (Monte Carlo variation)
            passed = error < 0.20
            message = f"Sharpe calculated: {sharpe:.2f}, theoretical: {theoretical_sharpe:.2f}, error: {error:.2f}"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="portfolio_simulator",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={"sharpe": sharpe, "theoretical": theoretical_sharpe}
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="portfolio_simulator",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    def test_max_drawdown_calculation(self) -> TestResult:
        """Test maximum drawdown calculation"""
        test_name = "Max Drawdown Calculation"
        start_time = time.time()
        
        try:
            # Known scenario: peak of 100, trough of 70, drawdown = -30%
            values = np.array([100, 105, 110, 100, 90, 80, 70, 75, 80, 85])
            
            max_dd, duration_days = RiskCalculator.calculate_max_drawdown(values)
            
            # Expected: (70 - 110) / 110 = -0.364
            expected_dd = -0.364
            
            error = abs(max_dd - expected_dd)
            
            passed = error < 0.01
            message = f"Max DD: {max_dd:.2%}, expected: {expected_dd:.2%}, duration: {duration_days} days"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="portfolio_simulator",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={"max_dd": max_dd, "duration": duration_days}
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="portfolio_simulator",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    # ========================================================================
    # OPTIONS SIMULATOR TESTS
    # ========================================================================
    
    def test_black_scholes_put_call_parity(self) -> TestResult:
        """Test Black-Scholes put-call parity"""
        test_name = "Black-Scholes Put-Call Parity"
        start_time = time.time()
        
        try:
            S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
            
            call_price = BlackScholesModel.price_call(S, K, T, r, sigma)
            put_price = BlackScholesModel.price_put(S, K, T, r, sigma)
            
            # Put-Call Parity: C - P = S - K*exp(-rT)
            lhs = call_price - put_price
            rhs = S - K * np.exp(-r * T)
            
            error = abs(lhs - rhs)
            
            passed = error < 0.01
            message = f"Put-Call Parity error: {error:.6f}"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="options_simulator",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={
                    "call_price": call_price,
                    "put_price": put_price,
                    "lhs": lhs,
                    "rhs": rhs,
                    "error": error
                }
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="options_simulator",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    def test_greeks_delta_bounds(self) -> TestResult:
        """Test that Delta is bounded correctly"""
        test_name = "Greeks Delta Bounds"
        start_time = time.time()
        
        try:
            S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
            
            call_greeks = BlackScholesModel.calculate_greeks(S, K, T, r, sigma, OptionType.CALL)
            put_greeks = BlackScholesModel.calculate_greeks(S, K, T, r, sigma, OptionType.PUT)
            
            # Call delta: 0 < Δ < 1
            # Put delta: -1 < Δ < 0
            call_delta_valid = 0 <= call_greeks.delta <= 1
            put_delta_valid = -1 <= put_greeks.delta <= 0
            
            passed = call_delta_valid and put_delta_valid
            message = f"Call Δ: {call_greeks.delta:.3f}, Put Δ: {put_greeks.delta:.3f}"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="options_simulator",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={
                    "call_delta": call_greeks.delta,
                    "put_delta": put_greeks.delta
                }
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="options_simulator",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    def test_greeks_gamma_positive(self) -> TestResult:
        """Test that Gamma is always positive"""
        test_name = "Greeks Gamma Positivity"
        start_time = time.time()
        
        try:
            S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
            
            call_greeks = BlackScholesModel.calculate_greeks(S, K, T, r, sigma, OptionType.CALL)
            put_greeks = BlackScholesModel.calculate_greeks(S, K, T, r, sigma, OptionType.PUT)
            
            passed = call_greeks.gamma > 0 and put_greeks.gamma > 0
            message = f"Call Γ: {call_greeks.gamma:.4f}, Put Γ: {put_greeks.gamma:.4f}"
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                category="options_simulator",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={
                    "call_gamma": call_greeks.gamma,
                    "put_gamma": put_greeks.gamma
                }
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="options_simulator",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    def test_scenario_generation_performance(self) -> TestResult:
        """Test scenario generation performance"""
        test_name = "Scenario Generation Performance"
        start_time = time.time()
        
        try:
            # Generate 1000 simulations × 252 days
            scenario = create_monte_carlo_scenario(
                tickers=["SPY", "QQQ", "IWM"],
                num_simulations=1000,
                num_days=252,
                random_seed=42
            )
            
            duration = (time.time() - start_time) * 1000
            
            # Should complete in <2 seconds
            passed = duration < 2000
            message = f"Generated in {duration:.0f}ms"
            
            return TestResult(
                test_name=test_name,
                category="performance",
                passed=passed,
                message=message,
                duration_ms=duration,
                details={"num_paths": len(scenario.paths)}
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                category="performance",
                passed=False,
                message=f"Exception: {str(e)}",
                duration_ms=duration
            )
    
    # ========================================================================
    # TEST ORCHESTRATION
    # ========================================================================
    
    def run_all_tests(self) -> DiagnosticReport:
        """Run all diagnostic tests"""
        logger.info("=" * 80)
        logger.info("PHASE 7 — SIMULATION DIAGNOSTIC TEST SUITE")
        logger.info("=" * 80)
        
        self.test_results = []
        
        # Scenario Engine Tests
        logger.info("\n📊 Testing Scenario Engine...")
        self.test_results.append(self.test_monte_carlo_reproducibility())
        self.test_results.append(self.test_stress_scenario_coverage())
        self.test_results.append(self.test_event_driven_scenarios())
        
        # Portfolio Simulator Tests
        logger.info("\n💼 Testing Portfolio Simulator...")
        self.test_results.append(self.test_var_calculation())
        self.test_results.append(self.test_sharpe_ratio_calculation())
        self.test_results.append(self.test_max_drawdown_calculation())
        
        # Options Simulator Tests
        logger.info("\n📈 Testing Options Simulator...")
        self.test_results.append(self.test_black_scholes_put_call_parity())
        self.test_results.append(self.test_greeks_delta_bounds())
        self.test_results.append(self.test_greeks_gamma_positive())
        
        # Performance Tests
        logger.info("\n⚡ Testing Performance...")
        self.test_results.append(self.test_scenario_generation_performance())
        
        # Generate summary
        passed = sum(1 for t in self.test_results if t.passed)
        failed = len(self.test_results) - passed
        success_rate = passed / len(self.test_results) if self.test_results else 0.0
        
        summary = self._generate_summary()
        
        report = DiagnosticReport(
            total_tests=len(self.test_results),
            passed_tests=passed,
            failed_tests=failed,
            success_rate=success_rate,
            test_results=self.test_results,
            summary=summary
        )
        
        # Print results
        self._print_results(report)
        
        return report
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary by category"""
        categories = {}
        
        for result in self.test_results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0, "total": 0}
            
            categories[result.category]["total"] += 1
            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
        
        return {
            "by_category": categories,
            "total_duration_ms": sum(t.duration_ms for t in self.test_results)
        }
    
    def _print_results(self, report: DiagnosticReport) -> None:
        """Print test results to console"""
        logger.info("\n" + "=" * 80)
        logger.info("DIAGNOSTIC TEST RESULTS")
        logger.info("=" * 80)
        
        for result in self.test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            logger.info(f"{status} | {result.test_name} | {result.duration_ms:.0f}ms")
            if not result.passed:
                logger.info(f"     Message: {result.message}")
        
        logger.info("\n" + "-" * 80)
        logger.info(f"Total Tests: {report.total_tests}")
        logger.info(f"Passed: {report.passed_tests} ✅")
        logger.info(f"Failed: {report.failed_tests} ❌")
        logger.info(f"Success Rate: {report.success_rate:.1%}")
        logger.info("=" * 80)
    
    def save_report(self, report: DiagnosticReport, filename: str = "diagnostic_report.json") -> str:
        """Save diagnostic report to JSON"""
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"\n💾 Saved diagnostic report: {filepath}")
        return str(filepath)
    
    def save_markdown_report(self, report: DiagnosticReport, filename: str = "diagnostic_summary.md") -> str:
        """Save diagnostic report as Markdown"""
        filepath = self.output_dir / filename
        
        md = []
        md.append("# Phase 7 Simulation Framework - Diagnostic Report\n")
        md.append(f"**Generated:** {report.timestamp}\n")
        md.append(f"**Success Rate:** {report.success_rate:.1%}\n")
        md.append("\n---\n")
        
        md.append("## Summary\n")
        md.append(f"- **Total Tests:** {report.total_tests}\n")
        md.append(f"- **Passed:** {report.passed_tests} ✅\n")
        md.append(f"- **Failed:** {report.failed_tests} ❌\n")
        md.append("\n")
        
        md.append("## Test Results by Category\n")
        for category, stats in report.summary["by_category"].items():
            success = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            md.append(f"### {category.replace('_', ' ').title()}\n")
            md.append(f"- Passed: {stats['passed']}/{stats['total']} ({success:.1%})\n")
            md.append("\n")
        
        md.append("## Individual Test Results\n")
        md.append("| Test Name | Category | Status | Duration |\n")
        md.append("|-----------|----------|--------|----------|\n")
        
        for result in report.test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            md.append(f"| {result.test_name} | {result.category} | {status} | {result.duration_ms:.0f}ms |\n")
        
        md.append("\n")
        
        with open(filepath, 'w') as f:
            f.write(''.join(md))
        
        logger.info(f"💾 Saved Markdown report: {filepath}")
        return str(filepath)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    diagnostic = SimulationDiagnostic()
    report = diagnostic.run_all_tests()
    
    # Save reports
    diagnostic.save_report(report)
    diagnostic.save_markdown_report(report)
    
    logger.info("\n✅ DIAGNOSTIC SUITE COMPLETE")
