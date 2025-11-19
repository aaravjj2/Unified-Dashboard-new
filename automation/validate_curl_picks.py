#!/usr/bin/env python3
"""
Agent 1B: Validate curl JSON responses for Market Trends picks.
"""
import json
import sys
from pathlib import Path

def validate_picks_response(filepath, expected_count=20, pick_type='weekly'):
    """
    Validate a picks API response JSON.
    
    Args:
        filepath: Path to JSON file
        expected_count: Expected number of tickers
        pick_type: 'weekly' or 'monthly' (determines required fields)
    
    Returns:
        dict with validation results
    """
    result = {
        'success': True,
        'filepath': str(filepath),
        'pick_type': pick_type,
        'errors': [],
        'ticker_count': 0,
        'failing_tickers': []
    }
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result['success'] = False
        result['errors'].append(f"JSON parse error: {e}")
        return result
    except FileNotFoundError:
        result['success'] = False
        result['errors'].append(f"File not found: {filepath}")
        return result
    
    # Check structure
    if not isinstance(data, dict):
        result['success'] = False
        result['errors'].append("Response is not a JSON object")
        return result
    
    # Get picks data
    picks = data.get('data', [])
    if not isinstance(picks, list):
        result['success'] = False
        result['errors'].append("'data' field is not a list")
        return result
    
    result['ticker_count'] = len(picks)
    
    if len(picks) != expected_count:
        result['success'] = False
        result['errors'].append(f"Expected {expected_count} tickers, got {len(picks)}")
    
    # Define required numeric fields based on pick type
    if pick_type == 'weekly':
        required_fields = ['current_price', 'week_start_price']
    else:  # monthly
        required_fields = ['current_price', 'month_start_price']
    
    # Validate each ticker
    for idx, pick in enumerate(picks):
        ticker = pick.get('ticker', f'UNKNOWN_{idx}')
        ticker_errors = []
        
        for field in required_fields:
            value = pick.get(field)
            
            if value is None:
                ticker_errors.append(f"{field} is null")
                continue
            
            try:
                numeric_val = float(value)
                if numeric_val <= 0:
                    ticker_errors.append(f"{field}={numeric_val} (not > 0)")
            except (ValueError, TypeError):
                ticker_errors.append(f"{field}={value} (not numeric)")
        
        if ticker_errors:
            result['failing_tickers'].append({
                'ticker': ticker,
                'index': idx,
                'errors': ticker_errors
            })
            result['success'] = False
    
    return result


def main():
    base_dir = Path(__file__).parent.parent
    logs_dir = base_dir / 'tests' / 'logs' / 'iteration_1'
    
    weekly_path = logs_dir / 'weekly_picks_curl.json'
    monthly_path = logs_dir / 'monthly_picks_curl.json'
    
    print("=" * 80)
    print("AGENT 1B: CURL VALIDATION")
    print("=" * 80)
    
    # Validate weekly
    print("\n[WEEKLY PICKS]")
    weekly_result = validate_picks_response(weekly_path, expected_count=20, pick_type='weekly')
    print(f"File: {weekly_result['filepath']}")
    print(f"Ticker count: {weekly_result['ticker_count']}")
    print(f"Success: {weekly_result['success']}")
    
    if weekly_result['errors']:
        print("\nERRORS:")
        for err in weekly_result['errors']:
            print(f"  ❌ {err}")
    
    if weekly_result['failing_tickers']:
        print(f"\nFailing tickers: {len(weekly_result['failing_tickers'])}")
        for fail in weekly_result['failing_tickers'][:5]:  # Show first 5
            print(f"  ❌ {fail['ticker']}: {', '.join(fail['errors'])}")
        if len(weekly_result['failing_tickers']) > 5:
            print(f"  ... and {len(weekly_result['failing_tickers']) - 5} more")
    else:
        print("  ✅ All tickers valid")
    
    # Validate monthly
    print("\n[MONTHLY PICKS]")
    monthly_result = validate_picks_response(monthly_path, expected_count=20, pick_type='monthly')
    print(f"File: {monthly_result['filepath']}")
    print(f"Ticker count: {monthly_result['ticker_count']}")
    print(f"Success: {monthly_result['success']}")
    
    if monthly_result['errors']:
        print("\nERRORS:")
        for err in monthly_result['errors']:
            print(f"  ❌ {err}")
    
    if monthly_result['failing_tickers']:
        print(f"\nFailing tickers: {len(monthly_result['failing_tickers'])}")
        for fail in monthly_result['failing_tickers'][:5]:
            print(f"  ❌ {fail['ticker']}: {', '.join(fail['errors'])}")
        if len(monthly_result['failing_tickers']) > 5:
            print(f"  ... and {len(monthly_result['failing_tickers']) - 5} more")
    else:
        print("  ✅ All tickers valid")
    
    # Write summary
    summary = {
        'weekly': weekly_result,
        'monthly': monthly_result,
        'overall_success': weekly_result['success'] and monthly_result['success']
    }
    
    summary_path = logs_dir / 'curl_validation_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 80)
    print(f"OVERALL: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}")
    print(f"Summary saved to: {summary_path}")
    print("=" * 80)
    
    sys.exit(0 if summary['overall_success'] else 1)


if __name__ == '__main__':
    main()
