"""
Graph Diff Utilities for Options Lab Validation

Provides L2 norm computation, trace count comparison, NaN detection,
and IV surface grid validation.

Phase 31 Agent 1A - STEP 8
"""

import json
import math
from typing import Dict, List, Any, Tuple, Optional


def compute_l2_norm(arr1: List[float], arr2: List[float]) -> float:
    """
    Compute L2 (Euclidean) norm between two numeric arrays.
    
    Args:
        arr1: First array
        arr2: Second array
        
    Returns:
        L2 norm distance
        
    Raises:
        ValueError: If arrays have different lengths
    """
    if len(arr1) != len(arr2):
        raise ValueError(f"Array length mismatch: {len(arr1)} != {len(arr2)}")
    
    squared_diff_sum = sum((a - b) ** 2 for a, b in zip(arr1, arr2))
    return math.sqrt(squared_diff_sum)


def compute_trace_count_diff(data1: Any, data2: Any) -> int:
    """
    Compare trace counts between two Plotly data objects.
    
    Args:
        data1: First Plotly data (array of traces)
        data2: Second Plotly data
        
    Returns:
        Absolute difference in trace count
    """
    count1 = len(data1) if isinstance(data1, list) else 1
    count2 = len(data2) if isinstance(data2, list) else 1
    return abs(count1 - count2)


def detect_nans(arr: List[Any]) -> Tuple[bool, int]:
    """
    Detect NaN values in array.
    
    Args:
        arr: Array to check
        
    Returns:
        Tuple of (has_nans, nan_count)
    """
    nan_count = sum(1 for x in arr if isinstance(x, float) and math.isnan(x))
    return (nan_count > 0, nan_count)


def validate_iv_grid_shape(grid: List[List[float]], min_rows: int = 5, min_cols: int = 5) -> Dict[str, Any]:
    """
    Validate IV surface grid shape and content.
    
    Args:
        grid: 2D array representing IV surface
        min_rows: Minimum expected rows
        min_cols: Minimum expected columns
        
    Returns:
        Validation result dict with shape, valid flag, and issues
    """
    result = {
        'valid': True,
        'shape': (0, 0),
        'issues': []
    }
    
    if not grid or not isinstance(grid, list):
        result['valid'] = False
        result['issues'].append('Grid is not a list')
        return result
    
    num_rows = len(grid)
    num_cols = len(grid[0]) if grid else 0
    result['shape'] = (num_rows, num_cols)
    
    # Check minimum dimensions
    if num_rows < min_rows:
        result['valid'] = False
        result['issues'].append(f'Rows {num_rows} < minimum {min_rows}')
    
    if num_cols < min_cols:
        result['valid'] = False
        result['issues'].append(f'Cols {num_cols} < minimum {min_cols}')
    
    # Check for NaNs
    flat_values = [val for row in grid for val in row if isinstance(val, (int, float))]
    has_nans, nan_count = detect_nans(flat_values)
    if has_nans:
        result['valid'] = False
        result['issues'].append(f'{nan_count} NaN values detected')
    
    # Check value range (IV should be in [0.01, 3.0])
    out_of_range = [v for v in flat_values if not math.isnan(v) and (v < 0.01 or v > 3.0)]
    if out_of_range:
        result['valid'] = False
        result['issues'].append(f'{len(out_of_range)} values outside [0.01, 3.0] range')
    
    return result


def validate_forecast_series(series: List[Dict], min_length: int = 5) -> Dict[str, Any]:
    """
    Validate forecast series data.
    
    Args:
        series: List of forecast data points with predicted_iv
        min_length: Minimum expected series length
        
    Returns:
        Validation result dict
    """
    result = {
        'valid': True,
        'length': len(series) if series else 0,
        'issues': []
    }
    
    if not series or not isinstance(series, list):
        result['valid'] = False
        result['issues'].append('Series is not a list')
        return result
    
    if len(series) < min_length:
        result['valid'] = False
        result['issues'].append(f'Series length {len(series)} < minimum {min_length}')
    
    # Check for predicted_iv values
    iv_values = []
    for i, point in enumerate(series):
        if not isinstance(point, dict):
            result['issues'].append(f'Point {i} is not a dict')
            continue
        
        if 'predicted_iv' in point:
            iv = point['predicted_iv']
            if isinstance(iv, (int, float)):
                iv_values.append(iv)
    
    if len(iv_values) == 0:
        result['valid'] = False
        result['issues'].append('No predicted_iv values found')
    else:
        # Check for NaNs
        has_nans, nan_count = detect_nans(iv_values)
        if has_nans:
            result['valid'] = False
            result['issues'].append(f'{nan_count} NaN IV values')
    
    return result


def validate_backtest_metrics(metrics: Dict) -> Dict[str, Any]:
    """
    Validate backtest metrics.
    
    Args:
        metrics: Dict with total_return, win_rate, trades count, etc.
        
    Returns:
        Validation result dict
    """
    result = {
        'valid': True,
        'issues': []
    }
    
    required_fields = ['total_return']
    for field in required_fields:
        if field not in metrics:
            result['valid'] = False
            result['issues'].append(f'Missing required field: {field}')
    
    # Check numeric fields
    if 'total_return' in metrics:
        tr = metrics['total_return']
        if not isinstance(tr, (int, float)) or math.isnan(tr):
            result['valid'] = False
            result['issues'].append('total_return is not a valid number')
    
    if 'win_rate' in metrics:
        wr = metrics['win_rate']
        if isinstance(wr, (int, float)) and math.isnan(wr):
            result['valid'] = False
            result['issues'].append('win_rate contains NaN')
    
    return result


def validate_greeks(greeks: Dict) -> Dict[str, Any]:
    """
    Validate Greeks values are within expected ranges.
    
    Args:
        greeks: Dict with delta, gamma, vega, theta, rho
        
    Returns:
        Validation result dict
    """
    result = {
        'valid': True,
        'issues': []
    }
    
    # Delta range: -5 to 5 (allowing for position multipliers)
    if 'delta' in greeks:
        delta = greeks['delta']
        if isinstance(delta, (int, float)):
            if math.isnan(delta):
                result['valid'] = False
                result['issues'].append('delta is NaN')
            elif delta < -5 or delta > 5:
                result['valid'] = False
                result['issues'].append(f'delta {delta} outside [-5, 5] range')
    
    # Gamma: must be >= 0
    if 'gamma' in greeks:
        gamma = greeks['gamma']
        if isinstance(gamma, (int, float)):
            if math.isnan(gamma):
                result['valid'] = False
                result['issues'].append('gamma is NaN')
            elif gamma < 0:
                result['valid'] = False
                result['issues'].append(f'gamma {gamma} is negative')
    
    # Vega: must be > 0 for options
    if 'vega' in greeks:
        vega = greeks['vega']
        if isinstance(vega, (int, float)):
            if math.isnan(vega):
                result['valid'] = False
                result['issues'].append('vega is NaN')
            elif vega <= 0:
                result['valid'] = False
                result['issues'].append(f'vega {vega} must be positive')
    
    # Theta: typically negative for long options
    if 'theta' in greeks:
        theta = greeks['theta']
        if isinstance(theta, (int, float)) and math.isnan(theta):
            result['valid'] = False
            result['issues'].append('theta is NaN')
    
    return result


def compare_plotly_traces(trace_a: Any, trace_b: Any) -> Dict[str, Any]:
    """
    Compare two Plotly traces and return difference metrics.
    
    Args:
        trace_a: First Plotly trace
        trace_b: Second Plotly trace
        
    Returns:
        Comparison result with trace count diff and L2 norms
    """
    result = {
        'trace_count_diff': 0,
        'l2_norms': {},
        'changed': False
    }
    
    # Wrap in lists if not already
    traces_a = trace_a if isinstance(trace_a, list) else [trace_a]
    traces_b = trace_b if isinstance(trace_b, list) else [trace_b]
    
    # Count difference
    result['trace_count_diff'] = abs(len(traces_a) - len(traces_b))
    if result['trace_count_diff'] > 0:
        result['changed'] = True
    
    # Compare numeric data if same length
    if len(traces_a) == len(traces_b) and len(traces_a) > 0:
        for i, (ta, tb) in enumerate(zip(traces_a, traces_b)):
            if isinstance(ta, dict) and isinstance(tb, dict):
                for key in ['x', 'y', 'z']:
                    if key in ta and key in tb:
                        arr_a = ta[key]
                        arr_b = tb[key]
                        
                        if isinstance(arr_a, list) and isinstance(arr_b, list):
                            if len(arr_a) == len(arr_b) and len(arr_a) > 0:
                                try:
                                    numeric_a = [float(v) for v in arr_a if isinstance(v, (int, float))]
                                    numeric_b = [float(v) for v in arr_b if isinstance(v, (int, float))]
                                    
                                    if len(numeric_a) == len(numeric_b) and len(numeric_a) > 0:
                                        l2 = compute_l2_norm(numeric_a, numeric_b)
                                        result['l2_norms'][f'trace{i}_{key}'] = l2
                                        if l2 > 0.001:
                                            result['changed'] = True
                                except Exception:
                                    pass
    
    return result


def compare_plotly_data(pre_data: Any, post_data: Any) -> Dict[str, Any]:
    """
    Comprehensive comparison of Plotly graph data.
    
    Args:
        pre_data: Pre-action Plotly data
        post_data: Post-action Plotly data
        
    Returns:
        Comparison result with metrics and verdict
    """
    result = {
        'changed': False,
        'change_type': None,
        'metrics': {},
        'valid': True,
        'issues': []
    }
    
    if not pre_data or not post_data:
        result['valid'] = False
        result['issues'].append('Missing graph data')
        return result
    
    # Trace count comparison
    trace_diff = compute_trace_count_diff(pre_data, post_data)
    result['metrics']['trace_count_diff'] = trace_diff
    
    if trace_diff > 0:
        result['changed'] = True
        result['change_type'] = f'trace_count_changed: {trace_diff} traces difference'
    
    # If both are lists, try numeric comparison
    if isinstance(pre_data, list) and isinstance(post_data, list) and len(pre_data) == len(post_data):
        # Extract numeric arrays from first trace if available
        try:
            if len(pre_data) > 0 and isinstance(pre_data[0], dict):
                for key in ['y', 'z', 'x']:
                    if key in pre_data[0] and key in post_data[0]:
                        pre_arr = pre_data[0][key]
                        post_arr = post_data[0][key]
                        
                        if isinstance(pre_arr, list) and isinstance(post_arr, list):
                            if len(pre_arr) == len(post_arr) and len(pre_arr) > 0:
                                # Convert to floats
                                pre_numeric = [float(x) for x in pre_arr if isinstance(x, (int, float))]
                                post_numeric = [float(x) for x in post_arr if isinstance(x, (int, float))]
                                
                                if len(pre_numeric) == len(post_numeric) and len(pre_numeric) > 0:
                                    l2_norm = compute_l2_norm(pre_numeric, post_numeric)
                                    result['metrics'][f'l2_norm_{key}'] = l2_norm
                                    
                                    if l2_norm > 0.001:  # Small epsilon
                                        result['changed'] = True
                                        result['change_type'] = f'{key}_data_changed: L2 norm = {l2_norm:.4f}'
        except Exception as e:
            result['issues'].append(f'Numeric comparison error: {str(e)}')
    
    return result


def save_graph_diff(elem_id: str, diff_result: Dict, output_dir: str = 'reports/options_validation/playwright/graph_diffs'):
    """
    Save graph diff result to JSON file.
    
    Args:
        elem_id: Element ID
        diff_result: Comparison result dict
        output_dir: Output directory
    """
    import os
    from pathlib import Path
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    output_file = output_path / f'{elem_id}_diff.json'
    
    output = {
        'elem_id': elem_id,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'diff_result': diff_result
    }
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
