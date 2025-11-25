#!/usr/bin/env python3
"""
Validate API responses for weekly/monthly picks.
Checks that all tickers have numeric values for required fields.
"""

import json
import sys
from pathlib import Path

# Weekly picks need: current_price, daily_change, week_start_price, profit_loss
# Monthly picks need: current_price, daily_change, month_start_price, profit_loss
WEEKLY_REQUIRED_FIELDS = ['current_price', 'week_start_price']
MONTHLY_REQUIRED_FIELDS = ['current_price', 'month_start_price']

def validate_picks(file_path, pick_type):
    """Validate picks JSON file"""
    print(f"\n{'='*80}")
    print(f"Validating {pick_type} Picks")
    print(f"{'='*80}")
    
    # Select required fields based on pick type
    if pick_type.lower() == 'weekly':
        required_fields = WEEKLY_REQUIRED_FIELDS
    elif pick_type.lower() == 'monthly':
        required_fields = MONTHLY_REQUIRED_FIELDS
    else:
        print(f"❌ Unknown pick type: {pick_type}")
        return False, {}
    
    print(f"Required fields: {', '.join(required_fields)}")
    
    try:
        with open(file_path, 'r') as f:
            response = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {file_path}: {e}")
        return False, {}
    
    # Handle API response format: {"status": "success", "data": [...]}
    if isinstance(response, dict):
        if 'data' in response:
            data = response['data']
        else:
            print(f"❌ Expected 'data' key in response, got keys: {list(response.keys())}")
            return False, {}
    else:
        data = response
    
    if not isinstance(data, list):
        print(f"❌ Expected list in 'data', got {type(data)}")
        return False, {}
    
    print(f"Total records: {len(data)}")
    
    valid_count = 0
    invalid_records = []
    missing_fields_summary = {}
    
    for idx, record in enumerate(data):
        ticker = record.get('ticker', f'UNKNOWN_{idx}')
        missing_fields = []
        
        for field in required_fields:
            value = record.get(field)
            
            # Check if value is numeric (float/int) and not None/empty
            if value is None:
                missing_fields.append(f"{field}=None")
            elif isinstance(value, str):
                if value.strip() == "" or value == "Data Unavailable":
                    missing_fields.append(f"{field}='{value}'")
            elif not isinstance(value, (int, float)):
                missing_fields.append(f"{field}={type(value).__name__}")
        
        if missing_fields:
            invalid_records.append({
                'ticker': ticker,
                'missing': missing_fields,
                'record': record
            })
            for field in missing_fields:
                field_name = field.split('=')[0]
                missing_fields_summary[field_name] = missing_fields_summary.get(field_name, 0) + 1
        else:
            valid_count += 1
    
    print(f"\nResults:")
    print(f"  ✅ Valid records: {valid_count}/{len(data)}")
    print(f"  ❌ Invalid records: {len(invalid_records)}/{len(data)}")
    
    if invalid_records:
        print(f"\nMissing/Invalid Fields Summary:")
        for field, count in sorted(missing_fields_summary.items(), key=lambda x: -x[1]):
            print(f"  {field}: {count} records")
        
        print(f"\nFirst 10 Invalid Records:")
        for record in invalid_records[:10]:
            print(f"  Ticker: {record['ticker']}")
            print(f"    Missing: {', '.join(record['missing'])}")
    
    success = len(invalid_records) == 0
    
    # Save summary
    summary = {
        'total_records': len(data),
        'valid_records': valid_count,
        'invalid_records': len(invalid_records),
        'missing_fields_summary': missing_fields_summary,
        'first_10_invalid': [
            {
                'ticker': r['ticker'],
                'missing': r['missing']
            } for r in invalid_records[:10]
        ] if invalid_records else []
    }
    
    return success, summary

if __name__ == '__main__':
    weekly_success, weekly_summary = validate_picks(
        'tests/logs/iteration_1/weekly_picks.json',
        'Weekly'
    )
    
    monthly_success, monthly_summary = validate_picks(
        'tests/logs/iteration_1/monthly_picks.json',
        'Monthly'
    )
    
    # Save summaries
    with open('tests/logs/iteration_1/weekly_summary.json', 'w') as f:
        json.dump(weekly_summary, f, indent=2)
    
    with open('tests/logs/iteration_1/monthly_summary.json', 'w') as f:
        json.dump(monthly_summary, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"OVERALL RESULT")
    print(f"{'='*80}")
    
    if weekly_success and monthly_success:
        print(f"✅ All API validations PASSED")
        print(f"   Weekly: {weekly_summary['valid_records']}/{weekly_summary['total_records']} valid")
        print(f"   Monthly: {monthly_summary['valid_records']}/{monthly_summary['total_records']} valid")
        sys.exit(0)
    else:
        print(f"❌ API validations FAILED")
        if not weekly_success:
            print(f"   Weekly: {weekly_summary['invalid_records']} invalid records")
        if not monthly_success:
            print(f"   Monthly: {monthly_summary['invalid_records']} invalid records")
        sys.exit(1)
