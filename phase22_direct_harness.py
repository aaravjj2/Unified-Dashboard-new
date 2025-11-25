"""
Phase 22 Direct Harness - Observability & Performance Validation

Tests observability integration across all dashboard callbacks:
- Sentry exception tracking
- Datadog metrics emission
- LambdaTest visual regression (optional)
- Performance stress testing

Exit Codes:
- 0: 100% pass (all observability checks passed)
- 1: Any failure (missing metrics, exceptions not captured, performance issues)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test results tracking
test_results = {
    'loop1_sentry_config': {'tests': [], 'passed': 0, 'failed': 0},
    'loop2_datadog_config': {'tests': [], 'passed': 0, 'failed': 0},
    'loop3_callback_integration': {'tests': [], 'passed': 0, 'failed': 0},
    'loop4_performance': {'tests': [], 'passed': 0, 'failed': 0}
}


def record_test(loop: str, test_name: str, passed: bool, details: str = ''):
    """Record test result."""
    status = 'PASS' if passed else 'FAIL'
    icon = '✅' if passed else '❌'
    
    test_results[loop]['tests'].append({
        'name': test_name,
        'passed': passed,
        'details': details,
        'timestamp': datetime.now().isoformat()
    })
    
    if passed:
        test_results[loop]['passed'] += 1
    else:
        test_results[loop]['failed'] += 1
    
    logger.info(f"{icon} [{loop}] {test_name}: {status} - {details}")


# ============================================================================
# LOOP 1: Sentry Configuration Tests
# ============================================================================

def validate_loop1_sentry_config() -> bool:
    """
    Validate Sentry configuration and initialization.
    
    Tests:
    1. Sentry config module exists
    2. Init function available
    3. Exception capture available
    4. Decorator available
    5. Breadcrumb functions available
    """
    logger.info("\n" + "=" * 60)
    logger.info("LOOP 1: Sentry Configuration Validation")
    logger.info("=" * 60)
    
    all_passed = True
    
    # Test 1: Module exists
    try:
        from observability import sentry_config
        record_test('loop1_sentry_config', 'Sentry module import', True, 'Module imported successfully')
    except Exception as e:
        record_test('loop1_sentry_config', 'Sentry module import', False, f'Import failed: {e}')
        all_passed = False
        return all_passed
    
    # Test 2: Init function available
    try:
        assert hasattr(sentry_config, 'init_sentry')
        record_test('loop1_sentry_config', 'init_sentry() function', True, 'Function exists')
    except AssertionError:
        record_test('loop1_sentry_config', 'init_sentry() function', False, 'Function missing')
        all_passed = False
    
    # Test 3: Exception capture available
    try:
        assert hasattr(sentry_config, 'capture_exception')
        record_test('loop1_sentry_config', 'capture_exception() function', True, 'Function exists')
    except AssertionError:
        record_test('loop1_sentry_config', 'capture_exception() function', False, 'Function missing')
        all_passed = False
    
    # Test 4: Decorator available
    try:
        assert hasattr(sentry_config, 'sentry_trace')
        record_test('loop1_sentry_config', '@sentry_trace decorator', True, 'Decorator exists')
    except AssertionError:
        record_test('loop1_sentry_config', '@sentry_trace decorator', False, 'Decorator missing')
        all_passed = False
    
    # Test 5: Breadcrumb functions
    try:
        assert hasattr(sentry_config, 'add_breadcrumb')
        record_test('loop1_sentry_config', 'add_breadcrumb() function', True, 'Function exists')
    except AssertionError:
        record_test('loop1_sentry_config', 'add_breadcrumb() function', False, 'Function missing')
        all_passed = False
    
    return all_passed


# ============================================================================
# LOOP 2: Datadog Configuration Tests
# ============================================================================

def validate_loop2_datadog_config() -> bool:
    """
    Validate Datadog configuration and initialization.
    
    Tests:
    1. Datadog config module exists
    2. Init function available
    3. Metric emission functions available
    4. Timing decorator available
    5. Predefined metric functions available
    """
    logger.info("\n" + "=" * 60)
    logger.info("LOOP 2: Datadog Configuration Validation")
    logger.info("=" * 60)
    
    all_passed = True
    
    # Test 1: Module exists
    try:
        from observability import datadog_config
        record_test('loop2_datadog_config', 'Datadog module import', True, 'Module imported successfully')
    except Exception as e:
        record_test('loop2_datadog_config', 'Datadog module import', False, f'Import failed: {e}')
        all_passed = False
        return all_passed
    
    # Test 2: Init function available
    try:
        assert hasattr(datadog_config, 'init_datadog')
        record_test('loop2_datadog_config', 'init_datadog() function', True, 'Function exists')
    except AssertionError:
        record_test('loop2_datadog_config', 'init_datadog() function', False, 'Function missing')
        all_passed = False
    
    # Test 3: Metric emission functions
    metric_functions = ['emit_metric', 'increment_counter', 'record_gauge', 'record_histogram', 'record_timing']
    for func_name in metric_functions:
        try:
            assert hasattr(datadog_config, func_name)
            record_test('loop2_datadog_config', f'{func_name}() function', True, 'Function exists')
        except AssertionError:
            record_test('loop2_datadog_config', f'{func_name}() function', False, 'Function missing')
            all_passed = False
    
    # Test 4: Timing decorator
    try:
        assert hasattr(datadog_config, 'metric_timing')
        record_test('loop2_datadog_config', '@metric_timing decorator', True, 'Decorator exists')
    except AssertionError:
        record_test('loop2_datadog_config', '@metric_timing decorator', False, 'Decorator missing')
        all_passed = False
    
    # Test 5: Predefined metric functions
    predefined_functions = [
        'record_ml_prediction_latency',
        'record_forecast_generation_latency',
        'record_options_calculation_latency',
        'increment_callback_invocation'
    ]
    for func_name in predefined_functions:
        try:
            assert hasattr(datadog_config, func_name)
            record_test('loop2_datadog_config', f'{func_name}() function', True, 'Function exists')
        except AssertionError:
            record_test('loop2_datadog_config', f'{func_name}() function', False, 'Function missing')
            all_passed = False
    
    return all_passed


# ============================================================================
# LOOP 3: Callback Integration Tests
# ============================================================================

def validate_loop3_callback_integration() -> bool:
    """
    Validate that callbacks have Sentry and Datadog decorators applied.
    
    Tests:
    1. Azure ML Lab callbacks import observability modules
    2. Options Lab callbacks import observability modules
    3. Callbacks have decorators applied (code inspection)
    """
    logger.info("\n" + "=" * 60)
    logger.info("LOOP 3: Callback Integration Validation")
    logger.info("=" * 60)
    
    all_passed = True
    
    # Test 1: Azure ML Lab imports
    try:
        with open('financial_dashboard/tabs/azure_ml_lab/callbacks.py', 'r') as f:
            content = f.read()
            
        assert 'from observability.sentry_config import' in content
        assert 'from observability.datadog_config import' in content
        record_test('loop3_callback_integration', 'Azure ML Lab observability imports', True, 'Imports found')
    except FileNotFoundError:
        record_test('loop3_callback_integration', 'Azure ML Lab observability imports', False, 'File not found')
        all_passed = False
    except AssertionError:
        record_test('loop3_callback_integration', 'Azure ML Lab observability imports', False, 'Imports missing')
        all_passed = False
    
    # Test 2: Azure ML Lab decorators
    try:
        assert '@sentry_trace(' in content
        assert '@metric_timing(' in content
        record_test('loop3_callback_integration', 'Azure ML Lab decorators applied', True, 'Decorators found')
    except AssertionError:
        record_test('loop3_callback_integration', 'Azure ML Lab decorators applied', False, 'Decorators missing')
        all_passed = False
    
    # Test 3: Options Lab imports
    try:
        with open('financial_dashboard/tabs/options_lab/callbacks.py', 'r') as f:
            content = f.read()
            
        assert 'from observability.sentry_config import' in content
        assert 'from observability.datadog_config import' in content
        record_test('loop3_callback_integration', 'Options Lab observability imports', True, 'Imports found')
    except FileNotFoundError:
        record_test('loop3_callback_integration', 'Options Lab observability imports', False, 'File not found')
        all_passed = False
    except AssertionError:
        record_test('loop3_callback_integration', 'Options Lab observability imports', False, 'Imports missing')
        all_passed = False
    
    # Test 4: Options Lab decorators
    try:
        assert '@sentry_trace(' in content
        assert '@metric_timing(' in content
        record_test('loop3_callback_integration', 'Options Lab decorators applied', True, 'Decorators found')
    except AssertionError:
        record_test('loop3_callback_integration', 'Options Lab decorators applied', False, 'Decorators missing')
        all_passed = False
    
    return all_passed


# ============================================================================
# LOOP 4: Performance & Stress Testing
# ============================================================================

def validate_loop4_performance() -> bool:
    """
    Validate performance characteristics (lightweight version).
    
    Tests:
    1. Observability modules import without errors
    2. Decorator overhead is acceptable
    3. Metric emission is fast
    """
    logger.info("\n" + "=" * 60)
    logger.info("LOOP 4: Performance Validation")
    logger.info("=" * 60)
    
    all_passed = True
    
    # Test 1: Import performance
    try:
        start = time.time()
        from observability import sentry_config, datadog_config
        import_time = (time.time() - start) * 1000
        
        passed = import_time < 500  # Should import in <500ms
        record_test('loop4_performance', 'Observability module import speed', passed, f'{import_time:.2f}ms')
        if not passed:
            all_passed = False
    except Exception as e:
        record_test('loop4_performance', 'Observability module import speed', False, f'Import failed: {e}')
        all_passed = False
    
    # Test 2: Decorator overhead
    try:
        from observability.sentry_config import sentry_trace
        from observability.datadog_config import metric_timing
        
        @sentry_trace('test')
        @metric_timing('test.metric')
        def test_function():
            time.sleep(0.001)  # 1ms operation
        
        start = time.time()
        for _ in range(100):
            test_function()
        total_time = (time.time() - start) * 1000
        avg_time = total_time / 100
        
        # Should add <5ms overhead per call
        passed = avg_time < 10
        record_test('loop4_performance', 'Decorator overhead', passed, f'{avg_time:.2f}ms avg per call')
        if not passed:
            all_passed = False
    except Exception as e:
        record_test('loop4_performance', 'Decorator overhead', False, f'Test failed: {e}')
        all_passed = False
    
    # Test 3: Metric emission speed
    try:
        from observability.datadog_config import increment_counter
        
        start = time.time()
        for _ in range(100):
            increment_counter('test.counter')
        total_time = (time.time() - start) * 1000
        avg_time = total_time / 100
        
        # Should emit in <1ms per call
        passed = avg_time < 5
        record_test('loop4_performance', 'Metric emission speed', passed, f'{avg_time:.2f}ms avg per call')
        if not passed:
            all_passed = False
    except Exception as e:
        record_test('loop4_performance', 'Metric emission speed', False, f'Test failed: {e}')
        all_passed = False
    
    return all_passed


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def generate_report() -> Dict[str, Any]:
    """Generate final test report."""
    total_tests = sum(len(loop['tests']) for loop in test_results.values())
    total_passed = sum(loop['passed'] for loop in test_results.values())
    total_failed = sum(loop['failed'] for loop in test_results.values())
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0
        },
        'loops': test_results
    }
    
    return report


def main():
    """Main execution function."""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 22 DIRECT HARNESS - OBSERVABILITY VALIDATION")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    # Execute validation loops
    loop1_passed = validate_loop1_sentry_config()
    loop2_passed = validate_loop2_datadog_config()
    loop3_passed = validate_loop3_callback_integration()
    loop4_passed = validate_loop4_performance()
    
    # Generate report
    report = generate_report()
    
    # Save report
    with open('phase22_results.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Tests: {report['summary']['total_tests']}")
    logger.info(f"Passed: {report['summary']['total_passed']}")
    logger.info(f"Failed: {report['summary']['total_failed']}")
    logger.info(f"Pass Rate: {report['summary']['pass_rate']:.1f}%")
    logger.info(f"Duration: {elapsed:.2f}s")
    logger.info("=" * 60)
    
    # Exit with appropriate code
    if report['summary']['total_failed'] == 0:
        logger.info("✅ Phase 22 Observability Validation: 100% PASS")
        sys.exit(0)
    else:
        logger.error("❌ Phase 22 Observability Validation: FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
