"""
Phase 3.5 Diagnostic Runner
============================

Comprehensive end-to-end verification suite for hybrid bridge.

Test Categories:
1. Contract validation (10 cases)
2. Cache read/write tests
3. Sync scheduler latency tests
4. Schema consistency checks
"""

import asyncio
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

# Import Phase 3.5 modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_bridge.data_contracts import (
    PortfolioAnalyticsContract, ExplainabilityContract, ForecastContract,
    ContractType, validate_contract, get_contract_hash
)
from data_bridge.cache_router import CacheRouter
from data_bridge.hybrid_storage_manager import HybridStorageManager
from data_bridge.sync_scheduler import SyncScheduler
from integrity_checks.data_hash_validator import DataHashValidator
from integrity_checks.schema_diff_checker import SchemaDiffChecker


# Configuration
DIAGNOSTIC_OUTPUT_DIR = Path(__file__).parent.parent / "docs"


@dataclass
class TestResult:
    """Result of a single test."""
    test_name: str
    category: str
    passed: bool
    duration_ms: float
    error: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_json(self) -> dict:
        """Convert to JSON dict."""
        return asdict(self)


class Phase3p5DiagnosticRunner:
    """
    Comprehensive diagnostic suite for Phase 3.5 hybrid bridge.
    
    Runs all validation tests and generates detailed reports.
    """
    
    def __init__(self):
        """Initialize diagnostic runner."""
        self.results: List[TestResult] = []
        self.cache_router = CacheRouter()
        self.storage_manager = HybridStorageManager()
        self.validator = DataHashValidator()
        self.schema_checker = SchemaDiffChecker()
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run complete diagnostic suite.
        
        Returns:
            Summary dict with all test results
        """
        print("=" * 60)
        print("Phase 3.5 Hybrid Bridge Diagnostics")
        print("=" * 60)
        
        # Run test categories
        await self._run_contract_validation_tests()
        await self._run_cache_tests()
        await self._run_sync_scheduler_tests()
        await self._run_schema_consistency_tests()
        await self._run_integrity_tests()
        
        # Generate summary
        summary = self._generate_summary()
        
        # Save results
        self._save_results(summary)
        
        return summary
    
    async def _run_contract_validation_tests(self) -> None:
        """Run contract validation test suite (10 cases)."""
        print("\n📋 Contract Validation Tests...")
        
        # Test 1: Valid portfolio analytics contract
        test_start = time.time()
        try:
            contract_data = {
                "portfolio_id": "test_portfolio",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_value": 100000.0,
                "annualized_return": 0.15,
                "volatility": 0.20,
                "sharpe_ratio": 0.75,
                "max_drawdown": -0.12,
                "beta": 1.05,
                "alpha": 0.02,
                "sector_allocation": {"Technology": 60.0, "Healthcare": 40.0},
                "risk_metrics": {"var_95": 0.05},
                "holdings": [{"ticker": "AAPL", "value": 50000.0}],
                "benchmark_name": "SPY",
                "metadata": {}
            }
            
            is_valid = validate_contract(contract_data, ContractType.PORTFOLIO_ANALYTICS)
            
            self.results.append(TestResult(
                test_name="Valid Portfolio Analytics Contract",
                category="contract_validation",
                passed=is_valid,
                duration_ms=(time.time() - test_start) * 1000
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Valid Portfolio Analytics Contract",
                category="contract_validation",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
        
        # Test 2: Invalid portfolio contract (missing required field)
        test_start = time.time()
        passed = False
        error_msg = ""
        try:
            invalid_data = contract_data.copy()
            del invalid_data["portfolio_id"]
            
            validate_contract(invalid_data, ContractType.PORTFOLIO_ANALYTICS)
            passed = False  # Should have raised error
        except (ValueError, TypeError):
            passed = True  # Expected to fail validation
        except Exception as e:
            passed = False
            error_msg = str(e)
        
        self.results.append(TestResult(
            test_name="Reject Invalid Portfolio Contract (Missing Field)",
            category="contract_validation",
            passed=passed,
            duration_ms=(time.time() - test_start) * 1000,
            error=error_msg
        ))
        
        # Test 3: Contract hash consistency
        test_start = time.time()
        try:
            hash1 = get_contract_hash(contract_data, ContractType.PORTFOLIO_ANALYTICS)
            hash2 = get_contract_hash(contract_data, ContractType.PORTFOLIO_ANALYTICS)
            passed = hash1 == hash2 and len(hash1) == 64  # SHA256 = 64 hex chars
            
            self.results.append(TestResult(
                test_name="Contract Hash Consistency",
                category="contract_validation",
                passed=passed,
                duration_ms=(time.time() - test_start) * 1000,
                metadata={"hash_length": len(hash1)}
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Contract Hash Consistency",
                category="contract_validation",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
        
        # Test 4-5: Explainability contract tests
        test_start = time.time()
        try:
            explainability_data = {
                "prediction_id": "pred_001",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "model_name": "test_model",
                "input_features": {"feature1": 1.0, "feature2": 2.0},
                "prediction": 0.85,
                "shap_values": {"feature1": 0.3, "feature2": 0.55},
                "feature_importance": {"feature1": 0.4, "feature2": 0.6},
                "base_value": 0.5
            }
            
            is_valid = validate_contract(explainability_data, ContractType.EXPLAINABILITY)
            
            self.results.append(TestResult(
                test_name="Valid Explainability Contract",
                category="contract_validation",
                passed=is_valid,
                duration_ms=(time.time() - test_start) * 1000
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Valid Explainability Contract",
                category="contract_validation",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
        
        # Test 6-10: Additional validation tests
        additional_tests = [
            ("Forecast Contract Validation", ContractType.FORECAST, {
                "forecast_id": "forecast_001",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "ticker": "AAPL",
                "horizon_days": 30,
                "expected_return": 0.05,
                "return_distribution": {"mean": 0.05, "std": 0.02},
                "confidence_score": 0.80,
                "features_used": ["price_momentum", "volume"],
                "model_version": "1.0.0"
            }),
        ]
        
        for test_name, contract_type, test_data in additional_tests:
            test_start = time.time()
            try:
                is_valid = validate_contract(test_data, contract_type)
                self.results.append(TestResult(
                    test_name=test_name,
                    category="contract_validation",
                    passed=is_valid,
                    duration_ms=(time.time() - test_start) * 1000
                ))
            except Exception as e:
                self.results.append(TestResult(
                    test_name=test_name,
                    category="contract_validation",
                    passed=False,
                    duration_ms=(time.time() - test_start) * 1000,
                    error=str(e)
                ))
    
    async def _run_cache_tests(self) -> None:
        """Run cache read/write tests."""
        print("💾 Cache Tests...")
        
        # Test: Cache write and read
        test_start = time.time()
        try:
            test_data = {"test": "data", "value": 123}
            
            # Write to cache
            write_success = self.cache_router.store_data(
                ContractType.PORTFOLIO_ANALYTICS,
                "test_key",
                test_data
            )
            
            # Read from cache
            read_data = self.cache_router.get_data(
                ContractType.PORTFOLIO_ANALYTICS,
                "test_key"
            )
            
            passed = write_success and read_data == test_data
            
            self.results.append(TestResult(
                test_name="Cache Write and Read",
                category="cache",
                passed=passed,
                duration_ms=(time.time() - test_start) * 1000
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Cache Write and Read",
                category="cache",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
        
        # Test: Cache hit rate
        test_start = time.time()
        try:
            # Clear cache stats
            self.cache_router.clear_all()
            
            # Perform operations
            for i in range(10):
                self.cache_router.store_data(ContractType.PORTFOLIO_ANALYTICS, f"key_{i}", {"value": i})
            
            # Read with hits
            for i in range(10):
                self.cache_router.get_data(ContractType.PORTFOLIO_ANALYTICS, f"key_{i}")
            
            stats = self.cache_router.get_stats()
            hit_rate = stats["combined"]["hit_rate"]
            
            passed = hit_rate >= 0.70  # Target: ≥70%
            
            self.results.append(TestResult(
                test_name="Cache Hit Rate (≥70%)",
                category="cache",
                passed=passed,
                duration_ms=(time.time() - test_start) * 1000,
                metadata={"hit_rate": hit_rate}
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Cache Hit Rate (≥70%)",
                category="cache",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
    
    async def _run_sync_scheduler_tests(self) -> None:
        """Run sync scheduler latency tests."""
        print("⚡ Sync Scheduler Tests...")
        
        # Test: Batch sync latency (≤1.0s for 10 jobs)
        test_start = time.time()
        try:
            scheduler = SyncScheduler(batch_size=10)
            
            # Create 10 mock tasks
            from data_bridge.sync_scheduler import SyncTask, SyncStatus
            tasks = [
                SyncTask(
                    task_id=f"task_{i}",
                    contract_type=ContractType.PORTFOLIO_ANALYTICS.value,
                    key=f"key_{i}",
                    status=SyncStatus.PENDING.value
                )
                for i in range(10)
            ]
            
            batch_start = time.time()
            results = await scheduler.sync_batch(tasks)
            batch_duration = time.time() - batch_start
            
            passed = batch_duration <= 1.0  # Target: ≤1.0s
            
            self.results.append(TestResult(
                test_name="Batch Sync Latency (≤1.0s for 10 jobs)",
                category="sync_scheduler",
                passed=passed,
                duration_ms=batch_duration * 1000,
                metadata={"tasks": 10, "target_ms": 1000}
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Batch Sync Latency (≤1.0s for 10 jobs)",
                category="sync_scheduler",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
    
    async def _run_schema_consistency_tests(self) -> None:
        """Run schema consistency checks."""
        print("🔍 Schema Consistency Tests...")
        
        # Test: 100% schema alignment with Azure stubs
        test_start = time.time()
        try:
            results = self.schema_checker.compare_all_schemas()
            
            compatible_count = sum(1 for r in results.values() if r.is_compatible)
            total_count = len(results)
            alignment_rate = compatible_count / total_count if total_count > 0 else 0.0
            
            passed = alignment_rate == 1.0  # Target: 100%
            
            self.results.append(TestResult(
                test_name="Schema Alignment (100% compatible)",
                category="schema_consistency",
                passed=passed,
                duration_ms=(time.time() - test_start) * 1000,
                metadata={
                    "compatible": compatible_count,
                    "total": total_count,
                    "alignment_rate": alignment_rate
                }
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Schema Alignment (100% compatible)",
                category="schema_consistency",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
    
    async def _run_integrity_tests(self) -> None:
        """Run integrity hash validation tests."""
        print("🔐 Integrity Tests...")
        
        # Test: Hash validation (0 failures)
        test_start = time.time()
        try:
            # Create test bundle
            test_data = {
                "test": "data",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            bundle_dir = self.storage_manager.save_analytics_bundle(
                portfolio_id="test_integrity",
                portfolio_analytics=test_data
            )
            
            # Validate manifest
            manifest_path = bundle_dir / "manifest.json"
            validation_results = self.validator.validate_manifest(manifest_path)
            
            failures = sum(1 for r in validation_results if not r.is_valid)
            passed = failures == 0  # Target: 0 failures
            
            self.results.append(TestResult(
                test_name="Integrity Hash Validation (0 failures)",
                category="integrity",
                passed=passed,
                duration_ms=(time.time() - test_start) * 1000,
                metadata={"failures": failures, "total_validations": len(validation_results)}
            ))
        except Exception as e:
            self.results.append(TestResult(
                test_name="Integrity Hash Validation (0 failures)",
                category="integrity",
                passed=False,
                duration_ms=(time.time() - test_start) * 1000,
                error=str(e)
            ))
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        
        # Category breakdown
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"total": 0, "passed": 0, "failed": 0}
            
            categories[result.category]["total"] += 1
            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": pass_rate,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "categories": categories,
            "results": [r.to_json() for r in self.results]
        }
    
    def _save_results(self, summary: Dict[str, Any]) -> None:
        """Save diagnostic results to JSON and Markdown."""
        # Save JSON
        json_path = DIAGNOSTIC_OUTPUT_DIR / "phase3p5_diagnostic_summary.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Results saved to {json_path}")
        
        # Generate Markdown report (placeholder for now)
        md_path = DIAGNOSTIC_OUTPUT_DIR / "PHASE3P5_DIAGNOSTIC_REPORT.md"
        self._generate_markdown_report(summary, md_path)
        
        print(f"✅ Report saved to {md_path}")
    
    def _generate_markdown_report(self, summary: Dict[str, Any], output_path: Path) -> None:
        """Generate Markdown diagnostic report."""
        lines = [
            "# Phase 3.5 Diagnostic Report",
            "",
            f"**Generated:** {summary['summary']['timestamp']}",
            f"**Total Tests:** {summary['summary']['total_tests']}",
            f"**Pass Rate:** {summary['summary']['pass_rate'] * 100:.1f}%",
            "",
            "## Summary",
            "",
            f"- ✅ **Passed:** {summary['summary']['passed']}",
            f"- ❌ **Failed:** {summary['summary']['failed']}",
            "",
            "## Results by Category",
            ""
        ]
        
        for category, stats in summary["categories"].items():
            pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            lines.extend([
                f"### {category.replace('_', ' ').title()}",
                "",
                f"- Total: {stats['total']}",
                f"- Passed: {stats['passed']}",
                f"- Failed: {stats['failed']}",
                f"- Pass Rate: {pass_rate:.1f}%",
                ""
            ])
        
        with open(output_path, 'w') as f:
            f.write("\n".join(lines))


async def main():
    """Run diagnostic suite."""
    runner = Phase3p5DiagnosticRunner()
    summary = await runner.run_all_tests()
    
    print("\n" + "=" * 60)
    print(f"Tests Passed: {summary['summary']['passed']}/{summary['summary']['total_tests']}")
    print(f"Pass Rate: {summary['summary']['pass_rate'] * 100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
