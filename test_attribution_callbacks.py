#!/usr/bin/env python3
"""
Test script to verify attribution_lab callbacks are not duplicated.
"""
import sys
import os

# Add financial_dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'financial_dashboard'))

# Import app
from financial_dashboard.app import app

# Check callback_map for attribution_lab duplicates
callback_map = getattr(app, 'callback_map', {})

print(f"\n{'='*70}")
print(f"ATTRIBUTION LAB CALLBACK TEST")
print(f"{'='*70}\n")

# Group by output IDs
output_counts = {}
for callback_id, callback_info in callback_map.items():
    outputs = callback_info.get('outputs', callback_info.get('output', []))
    if not isinstance(outputs, list):
        outputs = [outputs]
    
    for output in outputs:
        if isinstance(output, dict):
            output_id = f"{output.get('id', 'unknown')}.{output.get('property', 'unknown')}"
        else:
            output_id = str(output)
        
        if output_id not in output_counts:
            output_counts[output_id] = []
        output_counts[output_id].append(callback_id)

# Check attribution_lab specific outputs
attr_outputs = {
    'perf-total-return.children': 'Performance Total Return',
    'perf-total-return.className': 'Performance Total Return Class',
    'factors-exposures-container.children': 'Factor Exposures',
    'sectors-weights-pie.figure': 'Sector Weights Pie',
    'residual-alpha.children': 'Residual Alpha',
    'residual-alpha.className': 'Residual Alpha Class'
}

print("Attribution Lab Callback Status:\n")

all_good = True
for output_id, description in attr_outputs.items():
    if output_id in output_counts:
        count = len(output_counts[output_id])
        if count == 1:
            print(f"  ✅ {description:40s} - Registered once")
        else:
            print(f"  ❌ {description:40s} - Registered {count} times (DUPLICATE!)")
            all_good = False
            for cb_id in output_counts[output_id]:
                print(f"      - {cb_id}")
    else:
        print(f"  ⚠️  {description:40s} - Not found")

print()
if all_good:
    print("✅ All attribution_lab callbacks are properly registered (no duplicates)")
else:
    print("❌ Found duplicate attribution_lab callbacks")

print(f"\n{'='*70}\n")
