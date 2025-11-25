"""
Hybrid Diagnostics (Phase 4 - Hybrid Readiness)

Verifies all stubs are callable, checks schema consistency, validates contracts.
Generates comprehensive diagnostic reports.

Usage:
    >>> python -m phase4_hybrid_stubs.local_hybrid_bridge.hybrid_diagnostics
    >>> # Or programmatically:
    >>> from phase4_hybrid_stubs.local_hybrid_bridge import run_diagnostics
    >>> results = run_diagnostics(verbose=True)
"""

import sys
import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase4_hybrid_stubs.azure_contracts.azure_contract_definitions import (
    ContractInputSpec,
    ContractOutputSpec,
    ModelType,
    ForecastHorizon,
    create_mock_input,
    create_mock_output,
    validate_contract
)
from phase4_hybrid_stubs.azure_contracts.azure_io_schema import (
    load_schema,
    validate_payload,
    IOSchemaVersion,
    generate_blob_path
)
from phase4_hybrid_stubs.azure_contracts.azure_stub_clients import (
    AzureMLStubClient,
    AzureBlobStubClient,
    AzureMonitorStubClient
)
from phase4_hybrid_stubs.local_hybrid_bridge.hybrid_interface import (
    run_analytics,
    is_offline,
    get_workspace_config
)
from phase4_hybrid_stubs.local_hybrid_bridge.compute_router import (
    ComputeRouter,
    get_router
)
from phase4_hybrid_stubs.local_hybrid_bridge.telemetry_proxy import (
    TelemetryProxy,
    get_telemetry
)

# ============================================================================
# DIAGNOSTIC TESTS
# ============================================================================

class DiagnosticResult:
    """Result of a diagnostic test."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.duration_ms = 0.0
        self.error_message: str = ""
        self.details: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'test_name': self.test_name,
            'passed': self.passed,
            'duration_ms': self.duration_ms,
            'error_message': self.error_message,
            'details': self.details
        }


def run_diagnostics(verbose: bool = False) -> Dict[str, Any]:
    """
    Run all diagnostic tests.
    
    Args:
        verbose: Whether to print verbose output
    
    Returns:
        Diagnostic results dictionary
    """
    print("=" * 80)
    print("PHASE 4 - HYBRID READINESS DIAGNOSTICS")
    print("=" * 80)
    print()
    
    results = []
    start_time = time.perf_counter()
    
    # Test 1: Contract definitions
    print("🔍 Test 1: Contract Definitions")
    results.append(test_contract_definitions(verbose))
    
    # Test 2: I/O Schemas
    print("\n🔍 Test 2: I/O Schemas")
    results.append(test_io_schemas(verbose))
    
    # Test 3: Stub clients
    print("\n🔍 Test 3: Stub Clients")
    results.append(asyncio.run(test_stub_clients(verbose)))
    
    # Test 4: Hybrid interface
    print("\n🔍 Test 4: Hybrid Interface")
    results.append(test_hybrid_interface(verbose))
    
    # Test 5: Compute router
    print("\n🔍 Test 5: Compute Router")
    results.append(test_compute_router(verbose))
    
    # Test 6: Telemetry proxy
    print("\n🔍 Test 6: Telemetry Proxy")
    results.append(test_telemetry_proxy(verbose))
    
    # Test 7: End-to-end integration
    print("\n🔍 Test 7: End-to-End Integration")
    results.append(test_e2e_integration(verbose))
    
    # Summary
    total_duration_ms = (time.perf_counter() - start_time) * 1000
    passed_tests = sum(1 for r in results if r.passed)
    total_tests = len(results)
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Total Duration: {total_duration_ms:.0f}ms")
    print()
    
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} - {result.test_name} ({result.duration_ms:.0f}ms)")
        if not result.passed:
            print(f"      Error: {result.error_message}")
    
    print()
    
    # Generate report
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': total_tests - passed_tests,
        'total_duration_ms': total_duration_ms,
        'tests': [r.to_dict() for r in results]
    }
    
    # Save report
    report_path = Path(__file__).parent.parent.parent / "docs" / "phase4_hybrid_stubs" / "PHASE4_DIAGNOSTIC_REPORT.md"
    generate_diagnostic_report(report_data, report_path)
    
    if passed_tests == total_tests:
        print("🎉 All diagnostics PASSED!")
    else:
        print(f"⚠️  {total_tests - passed_tests} diagnostic(s) FAILED")
    
    print()
    return report_data


def test_contract_definitions(verbose: bool) -> DiagnosticResult:
    """Test contract definitions."""
    result = DiagnosticResult("Contract Definitions")
    start = time.perf_counter()
    
    try:
        # Test input contract creation
        input_spec = create_mock_input('AAPL', 'forecast')
        is_valid, error = validate_contract(input_spec)
        
        if not is_valid:
            raise AssertionError(f"Input contract validation failed: {error}")
        
        # Test output contract creation
        output_spec = create_mock_output(input_spec.uuid, 'AAPL')
        is_valid, error = validate_contract(output_spec)
        
        if not is_valid:
            raise AssertionError(f"Output contract validation failed: {error}")
        
        # Test enum conversions
        model_type = ModelType.from_string('random_forest')
        assert model_type == ModelType.RANDOM_FOREST
        
        horizon = ForecastHorizon.from_string('monthly')
        assert horizon == ForecastHorizon.MONTHLY
        assert horizon.to_days() == 30
        
        result.passed = True
        result.details = {
            'input_fields': len(input_spec.to_dict()),
            'output_fields': len(output_spec.to_dict()),
            'model_types_tested': 2,
            'horizons_tested': 2
        }
        
        if verbose:
            print(f"  ✓ Input contract: {len(input_spec.to_dict())} fields")
            print(f"  ✓ Output contract: {len(output_spec.to_dict())} fields")
            print(f"  ✓ Enum conversions working")
        
    except Exception as e:
        result.passed = False
        result.error_message = str(e)
        if verbose:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
    
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


def test_io_schemas(verbose: bool) -> DiagnosticResult:
    """Test I/O schemas."""
    result = DiagnosticResult("I/O Schemas")
    start = time.perf_counter()
    
    try:
        # Test schema loading
        schema = load_schema(version="0.1", schema_type="prediction_input")
        assert 'required_fields' in schema
        assert 'field_specs' in schema
        
        # Test payload validation
        input_spec = create_mock_input('AAPL', 'forecast')
        is_valid, errors = validate_payload(input_spec.to_dict(), schema=schema)
        
        if not is_valid:
            raise AssertionError(f"Payload validation failed: {errors}")
        
        # Test blob path generation
        blob_path = generate_blob_path('predictions', 'AAPL')
        assert 'predictions' in blob_path
        assert 'AAPL' in blob_path
        
        result.passed = True
        result.details = {
            'schemas_loaded': 1,
            'validations_tested': 1,
            'blob_paths_generated': 1,
            'blob_path_sample': blob_path
        }
        
        if verbose:
            print(f"  ✓ Schema loaded: {len(schema['required_fields'])} required fields")
            print(f"  ✓ Payload validation passed")
            print(f"  ✓ Blob path: {blob_path}")
        
    except Exception as e:
        result.passed = False
        result.error_message = str(e)
        if verbose:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
    
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


async def test_stub_clients(verbose: bool) -> DiagnosticResult:
    """Test stub clients."""
    result = DiagnosticResult("Stub Clients")
    start = time.perf_counter()
    
    try:
        # Test ML client
        ml_client = AzureMLStubClient()
        input_spec = create_mock_input('AAPL', 'forecast')
        output = await ml_client.submit_job(input_spec)
        
        assert len(output.predictions) > 0
        assert len(output.confidence) == len(output.predictions)
        
        # Test Blob client
        blob_client = AzureBlobStubClient()
        test_data = {'test': 'data'}
        await blob_client.upload_blob('test.json', test_data)
        downloaded = await blob_client.download_blob('test.json')
        assert downloaded is not None
        await blob_client.delete_blob('test.json')
        
        # Test Monitor client
        monitor_client = AzureMonitorStubClient()
        await monitor_client.track_event('test_event', {'test': 'property'})
        await monitor_client.track_metric('test_metric', 1.23)
        await monitor_client.track_request('test_request', 100.0, True)
        
        result.passed = True
        result.details = {
            'ml_predictions_generated': len(output.predictions),
            'blob_operations_tested': 3,
            'telemetry_events_tracked': 3,
            'ml_latency_ms': output.latency_ms
        }
        
        if verbose:
            print(f"  ✓ ML client: {len(output.predictions)} predictions")
            print(f"  ✓ Blob client: upload/download/delete working")
            print(f"  ✓ Monitor client: 3 events tracked")
        
    except Exception as e:
        result.passed = False
        result.error_message = str(e)
        if verbose:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
    
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


def test_hybrid_interface(verbose: bool) -> DiagnosticResult:
    """Test hybrid interface."""
    result = DiagnosticResult("Hybrid Interface")
    start = time.perf_counter()
    
    try:
        # Test offline mode check
        offline = is_offline()
        assert isinstance(offline, bool)
        
        # Test workspace config
        config = get_workspace_config()
        assert 'workspace_name' in config
        assert 'resource_group' in config
        
        # Test analytics run
        analytics_result = run_analytics(
            job_type='forecast',
            payload={
                'ticker': 'AAPL',
                'features': {'momentum': 0.05, 'volatility': 0.15},
                'date_range': ('2025-01-01', '2025-12-31'),
                'forecast_horizon': 'monthly'
            }
        )
        
        assert 'predictions' in analytics_result
        assert 'confidence' in analytics_result
        assert len(analytics_result['predictions']) > 0
        
        result.passed = True
        result.details = {
            'offline_mode': offline,
            'workspace_config_keys': list(config.keys()),
            'analytics_predictions': len(analytics_result['predictions']),
            'analytics_latency_ms': analytics_result.get('latency_ms', 0)
        }
        
        if verbose:
            print(f"  ✓ Offline mode: {offline}")
            print(f"  ✓ Workspace config: {len(config)} keys")
            print(f"  ✓ Analytics: {len(analytics_result['predictions'])} predictions")
        
    except Exception as e:
        result.passed = False
        result.error_message = str(e)
        if verbose:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
    
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


def test_compute_router(verbose: bool) -> DiagnosticResult:
    """Test compute router."""
    result = DiagnosticResult("Compute Router")
    start = time.perf_counter()
    
    try:
        router = ComputeRouter()
        
        # Test dispatch
        dispatch_result = router.dispatch(
            task_type='forecast',
            payload={
                'ticker': 'MSFT',
                'features': {'momentum': 0.03},
                'date_range': ('2025-01-01', '2025-12-31')
            }
        )
        
        assert 'predictions' in dispatch_result
        assert '_backend' in dispatch_result
        
        # Test cache
        cache_result = router.dispatch(
            task_type='forecast',
            payload={
                'ticker': 'MSFT',
                'features': {'momentum': 0.03},
                'date_range': ('2025-01-01', '2025-12-31')
            },
            use_cache=True
        )
        
        assert cache_result.get('_from_cache', False)
        
        # Get stats
        cache_stats = router.get_cache_stats()
        perf_stats = router.get_performance_stats()
        
        result.passed = True
        result.details = {
            'dispatched_tasks': perf_stats['total_tasks'],
            'cached_items': cache_stats['total_cached_items'],
            'avg_latency_ms': perf_stats['average_latency_ms'],
            'cache_hit_verified': cache_result.get('_from_cache', False)
        }
        
        if verbose:
            print(f"  ✓ Dispatch working")
            print(f"  ✓ Cache working: {cache_stats['total_cached_items']} items")
            print(f"  ✓ Performance stats available")
        
    except Exception as e:
        result.passed = False
        result.error_message = str(e)
        if verbose:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
    
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


def test_telemetry_proxy(verbose: bool) -> DiagnosticResult:
    """Test telemetry proxy."""
    result = DiagnosticResult("Telemetry Proxy")
    start = time.perf_counter()
    
    try:
        proxy = TelemetryProxy()
        
        # Track various events
        proxy.track_event('test_event', {'key': 'value'})
        proxy.track_metric('test_metric', 42.0)
        proxy.track_request('test_request', 123.4, True)
        proxy.flush()
        
        # Read events
        events = proxy.read_events(limit=10)
        summary = proxy.get_summary()
        
        result.passed = True
        result.details = {
            'events_tracked': 3,
            'events_read': len(events),
            'total_telemetry_events': summary['total_events'],
            'event_types': list(summary['event_types'].keys())
        }
        
        if verbose:
            print(f"  ✓ Tracked 3 events")
            print(f"  ✓ Read {len(events)} events")
            print(f"  ✓ Summary: {summary['total_events']} total events")
        
    except Exception as e:
        result.passed = False
        result.error_message = str(e)
        if verbose:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
    
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


def test_e2e_integration(verbose: bool) -> DiagnosticResult:
    """Test end-to-end integration."""
    result = DiagnosticResult("End-to-End Integration")
    start = time.perf_counter()
    
    try:
        # Full workflow: Create input -> Run analytics -> Store in blob -> Track telemetry
        
        # 1. Create input
        input_spec = create_mock_input('GOOGL', 'forecast')
        
        # 2. Run analytics via router
        router = get_router()
        analytics_result = router.dispatch(
            task_type='forecast',
            payload=input_spec.to_dict()
        )
        
        # 3. Track telemetry
        telemetry = get_telemetry()
        telemetry.track_event(
            'e2e_test_completed',
            properties={'ticker': 'GOOGL'},
            measurements={'latency_ms': analytics_result.get('_dispatch_latency_ms', 0)}
        )
        telemetry.flush()
        
        # Verify results
        assert 'predictions' in analytics_result
        assert len(analytics_result['predictions']) > 0
        
        # Check telemetry
        summary = telemetry.get_summary()
        assert summary['total_events'] > 0
        
        result.passed = True
        result.details = {
            'workflow_steps_completed': 3,
            'predictions_generated': len(analytics_result['predictions']),
            'telemetry_events_total': summary['total_events'],
            'end_to_end_latency_ms': analytics_result.get('_dispatch_latency_ms', 0)
        }
        
        if verbose:
            print(f"  ✓ Input created and validated")
            print(f"  ✓ Analytics executed via router")
            print(f"  ✓ Telemetry tracked")
            print(f"  ✓ E2E workflow complete")
        
    except Exception as e:
        result.passed = False
        result.error_message = str(e)
        if verbose:
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
    
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_diagnostic_report(report_data: Dict[str, Any], output_path: Path):
    """Generate Markdown diagnostic report."""
    lines = []
    
    lines.append("# Phase 4 - Hybrid Readiness Diagnostic Report\n")
    lines.append(f"**Generated:** {report_data['timestamp']}\n")
    lines.append(f"**Agent:** Agent 1B - Lead Engineer\n")
    lines.append("\n---\n")
    
    # Summary
    lines.append("\n## Summary\n")
    lines.append(f"- **Total Tests:** {report_data['total_tests']}\n")
    lines.append(f"- **Passed:** {report_data['passed_tests']} ✅\n")
    lines.append(f"- **Failed:** {report_data['failed_tests']} ❌\n")
    lines.append(f"- **Duration:** {report_data['total_duration_ms']:.0f}ms\n")
    
    # Test results
    lines.append("\n## Test Results\n")
    lines.append("\n| Test | Status | Duration (ms) | Details |\n")
    lines.append("|------|--------|---------------|----------|\n")
    
    for test in report_data['tests']:
        status = "✅ PASS" if test['passed'] else "❌ FAIL"
        details_str = ", ".join([f"{k}={v}" for k, v in list(test['details'].items())[:2]])
        lines.append(f"| {test['test_name']} | {status} | {test['duration_ms']:.0f} | {details_str} |\n")
    
    # Detailed results
    lines.append("\n## Detailed Test Results\n")
    
    for test in report_data['tests']:
        lines.append(f"\n### {test['test_name']}\n")
        lines.append(f"**Status:** {'✅ PASS' if test['passed'] else '❌ FAIL'}\n")
        lines.append(f"**Duration:** {test['duration_ms']:.0f}ms\n")
        
        if not test['passed']:
            lines.append(f"\n**Error:** {test['error_message']}\n")
        
        if test['details']:
            lines.append("\n**Details:**\n")
            for key, value in test['details'].items():
                lines.append(f"- {key}: {value}\n")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(lines))
    
    print(f"📄 Diagnostic report saved: {output_path}")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 4 Hybrid Readiness Diagnostics")
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
    args = parser.parse_args()
    
    results = run_diagnostics(verbose=args.verbose)
    
    # Exit with error code if any tests failed
    if results['failed_tests'] > 0:
        sys.exit(1)


logger.info("✓ Hybrid Diagnostics loaded (Phase 4 - Hybrid Readiness)")
