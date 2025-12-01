"""
Unit tests for graph_diff utilities

Phase 31 Agent 1A - STEP 8
"""

import math
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.graph_diff import (
    compute_l2_norm,
    compute_trace_count_diff,
    detect_nans,
    validate_iv_grid_shape,
    validate_forecast_series,
    validate_backtest_metrics,
    validate_greeks,
    compare_plotly_data,
    compare_plotly_traces
)


def test_compute_l2_norm():
    """Test L2 norm computation"""
    # Identical arrays
    arr1 = [1.0, 2.0, 3.0]
    arr2 = [1.0, 2.0, 3.0]
    norm = compute_l2_norm(arr1, arr2)
    assert norm == 0.0, f"Expected 0.0, got {norm}"
    print("✅ L2 norm for identical arrays = 0.0")
    
    # Different arrays
    arr3 = [1.0, 2.0, 3.0]
    arr4 = [2.0, 3.0, 4.0]
    norm2 = compute_l2_norm(arr3, arr4)
    expected = math.sqrt(3)  # sqrt((1)^2 + (1)^2 + (1)^2)
    assert abs(norm2 - expected) < 0.001, f"Expected {expected}, got {norm2}"
    print(f"✅ L2 norm for different arrays = {norm2:.4f}")
    
    # Length mismatch
    try:
        compute_l2_norm([1, 2], [1, 2, 3])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "length mismatch" in str(e).lower()
        print("✅ L2 norm raises ValueError for length mismatch")
    
    return True


def test_trace_count_diff():
    """Test trace count comparison"""
    data1 = [{'y': [1, 2, 3]}, {'y': [4, 5, 6]}]
    data2 = [{'y': [1, 2, 3]}]
    
    diff = compute_trace_count_diff(data1, data2)
    assert diff == 1, f"Expected 1, got {diff}"
    print(f"✅ Trace count diff = {diff}")
    
    # Same count
    diff2 = compute_trace_count_diff(data1, [1, 2])
    assert diff2 == 0, f"Expected 0, got {diff2}"
    print(f"✅ Trace count diff for same count = {diff2}")
    
    return True


def test_detect_nans():
    """Test NaN detection"""
    arr_clean = [1.0, 2.0, 3.0]
    has_nans, count = detect_nans(arr_clean)
    assert not has_nans, "Should not detect NaNs"
    assert count == 0
    print("✅ NaN detection: clean array has 0 NaNs")
    
    arr_dirty = [1.0, float('nan'), 3.0, float('nan')]
    has_nans2, count2 = detect_nans(arr_dirty)
    assert has_nans2, "Should detect NaNs"
    assert count2 == 2, f"Expected 2 NaNs, got {count2}"
    print(f"✅ NaN detection: dirty array has {count2} NaNs")
    
    return True


def test_validate_iv_grid_shape():
    """Test IV grid validation"""
    # Valid grid
    valid_grid = [
        [0.25, 0.30, 0.35, 0.40, 0.45],
        [0.26, 0.31, 0.36, 0.41, 0.46],
        [0.27, 0.32, 0.37, 0.42, 0.47],
        [0.28, 0.33, 0.38, 0.43, 0.48],
        [0.29, 0.34, 0.39, 0.44, 0.49]
    ]
    
    result = validate_iv_grid_shape(valid_grid)
    assert result['valid'], f"Grid should be valid: {result['issues']}"
    assert result['shape'] == (5, 5)
    print(f"✅ Valid IV grid: shape={result['shape']}, valid={result['valid']}")
    
    # Too small
    small_grid = [[0.25, 0.30], [0.26, 0.31]]
    result2 = validate_iv_grid_shape(small_grid)
    assert not result2['valid'], "Small grid should be invalid"
    assert 'Rows' in str(result2['issues']) or 'Cols' in str(result2['issues'])
    print(f"✅ Small IV grid correctly rejected: {result2['issues']}")
    
    # Out of range values
    bad_grid = [
        [0.25, 0.30, 5.0, 0.40, 0.45],  # 5.0 is out of range
        [0.26, 0.31, 0.36, 0.41, 0.46],
        [0.27, 0.32, 0.37, 0.42, 0.47],
        [0.28, 0.33, 0.38, 0.43, 0.48],
        [0.29, 0.34, 0.39, 0.44, 0.49]
    ]
    result3 = validate_iv_grid_shape(bad_grid)
    assert not result3['valid'], "Grid with out-of-range values should be invalid"
    print(f"✅ Out-of-range IV grid rejected: {result3['issues']}")
    
    return True


def test_validate_forecast_series():
    """Test forecast series validation"""
    # Valid series
    valid_series = [
        {'date': '2024-01-01', 'predicted_iv': 0.25},
        {'date': '2024-01-02', 'predicted_iv': 0.26},
        {'date': '2024-01-03', 'predicted_iv': 0.27},
        {'date': '2024-01-04', 'predicted_iv': 0.28},
        {'date': '2024-01-05', 'predicted_iv': 0.29}
    ]
    
    result = validate_forecast_series(valid_series)
    assert result['valid'], f"Series should be valid: {result['issues']}"
    assert result['length'] == 5
    print(f"✅ Valid forecast series: length={result['length']}, valid={result['valid']}")
    
    # Too short
    short_series = [
        {'date': '2024-01-01', 'predicted_iv': 0.25},
        {'date': '2024-01-02', 'predicted_iv': 0.26}
    ]
    result2 = validate_forecast_series(short_series)
    assert not result2['valid'], "Short series should be invalid"
    print(f"✅ Short forecast series rejected: {result2['issues']}")
    
    return True


def test_validate_backtest_metrics():
    """Test backtest metrics validation"""
    # Valid metrics
    valid_metrics = {
        'total_return': 0.15,
        'win_rate': 0.65,
        'sharpe_ratio': 1.2
    }
    
    result = validate_backtest_metrics(valid_metrics)
    assert result['valid'], f"Metrics should be valid: {result['issues']}"
    print(f"✅ Valid backtest metrics: valid={result['valid']}")
    
    # Missing total_return
    invalid_metrics = {
        'win_rate': 0.65
    }
    result2 = validate_backtest_metrics(invalid_metrics)
    assert not result2['valid'], "Metrics without total_return should be invalid"
    print(f"✅ Missing total_return correctly rejected: {result2['issues']}")
    
    # NaN total_return
    nan_metrics = {
        'total_return': float('nan')
    }
    result3 = validate_backtest_metrics(nan_metrics)
    assert not result3['valid'], "NaN total_return should be invalid"
    print(f"✅ NaN total_return rejected: {result3['issues']}")
    
    return True


def test_compare_plotly_data():
    """Test Plotly data comparison"""
    # Same data
    data1 = [{'y': [1.0, 2.0, 3.0]}]
    data2 = [{'y': [1.0, 2.0, 3.0]}]
    
    result = compare_plotly_data(data1, data2)
    assert result['valid'], "Comparison should be valid"
    assert not result['changed'], "Data should not be marked as changed (within epsilon)"
    print(f"✅ Same Plotly data: changed={result['changed']}")
    
    # Different data
    data3 = [{'y': [1.0, 2.0, 3.0]}]
    data4 = [{'y': [2.0, 3.0, 4.0]}]
    
    result2 = compare_plotly_data(data3, data4)
    assert result2['valid'], "Comparison should be valid"
    assert result2['changed'], "Data should be marked as changed"
    assert 'l2_norm_y' in result2['metrics']
    print(f"✅ Different Plotly data: changed={result2['changed']}, L2={result2['metrics'].get('l2_norm_y', 0):.4f}")
    
    # Trace count difference
    data5 = [{'y': [1, 2]}, {'y': [3, 4]}]
    data6 = [{'y': [1, 2]}]
    
    result3 = compare_plotly_data(data5, data6)
    assert result3['changed'], "Trace count change should be detected"
    assert result3['metrics']['trace_count_diff'] == 1
    print(f"✅ Trace count difference detected: {result3['change_type']}")
    
    return True


def test_validate_greeks():
    """Test Greeks validation"""
    # Valid Greeks
    valid_greeks = {
        'delta': 0.5,
        'gamma': 0.05,
        'vega': 0.15,
        'theta': -0.02,
        'rho': 0.01
    }
    
    result = validate_greeks(valid_greeks)
    assert result['valid'], f"Valid Greeks should pass: {result['issues']}"
    print(f"✅ Valid Greeks: valid={result['valid']}")
    
    # Delta out of range
    bad_delta = {'delta': 10.0}
    result2 = validate_greeks(bad_delta)
    assert not result2['valid'], "Delta out of range should be invalid"
    print(f"✅ Bad delta rejected: {result2['issues']}")
    
    # Negative gamma
    bad_gamma = {'gamma': -0.05}
    result3 = validate_greeks(bad_gamma)
    assert not result3['valid'], "Negative gamma should be invalid"
    print(f"✅ Negative gamma rejected: {result3['issues']}")
    
    # Zero vega
    bad_vega = {'vega': 0}
    result4 = validate_greeks(bad_vega)
    assert not result4['valid'], "Zero vega should be invalid"
    print(f"✅ Zero vega rejected: {result4['issues']}")
    
    return True


def test_compare_plotly_traces():
    """Test Plotly traces comparison wrapper"""
    trace1 = [{'x': [1, 2, 3], 'y': [1.0, 2.0, 3.0]}]
    trace2 = [{'x': [1, 2, 3], 'y': [1.1, 2.1, 3.1]}]
    
    result = compare_plotly_traces(trace1, trace2)
    assert result['trace_count_diff'] == 0, "Same number of traces"
    assert 'trace0_y' in result['l2_norms'], "Should have L2 norm for y"
    print(f"✅ Trace comparison: L2 norms computed, changed={result['changed']}")
    
    # Different trace counts
    trace3 = [{'y': [1, 2]}, {'y': [3, 4]}]
    trace4 = [{'y': [1, 2]}]
    
    result2 = compare_plotly_traces(trace3, trace4)
    assert result2['trace_count_diff'] == 1
    assert result2['changed'], "Should detect change"
    print(f"✅ Trace count diff detected: {result2['trace_count_diff']}")
    
    return True


if __name__ == '__main__':
    print("="*60)
    print("GRAPH DIFF UTILITIES TEST SUITE")
    print("="*60)
    
    tests = [
        ("L2 norm computation", test_compute_l2_norm),
        ("Trace count diff", test_trace_count_diff),
        ("NaN detection", test_detect_nans),
        ("IV grid validation", test_validate_iv_grid_shape),
        ("Forecast series validation", test_validate_forecast_series),
        ("Backtest metrics validation", test_validate_backtest_metrics),
        ("Greeks validation", test_validate_greeks),
        ("Plotly data comparison", test_compare_plotly_data),
        ("Plotly traces comparison", test_compare_plotly_traces)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    if failed == 0:
        print(f"✅ ALL GRAPH DIFF TESTS PASSED ({passed}/{len(tests)})")
        print("="*60)
        sys.exit(0)
    else:
        print(f"❌ SOME TESTS FAILED: {failed}/{len(tests)} failed, {passed}/{len(tests)} passed")
        print("="*60)
        sys.exit(1)
