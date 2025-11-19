#!/usr/bin/env python3
"""
Diagnostic script to identify duplicate callback registrations.
"""
import sys
import os

# Add financial_dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'financial_dashboard'))

# Import app
from financial_dashboard.app import app

# Check callback_map for duplicates
callback_map = getattr(app, 'callback_map', {})

print(f"\n{'='*70}")
print(f"CALLBACK DIAGNOSTICS")
print(f"{'='*70}\n")

print(f"Total callbacks registered: {len(callback_map)}\n")

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

# Find duplicates
duplicates = {k: v for k, v in output_counts.items() if len(v) > 1}

if duplicates:
    print(f"❌ FOUND {len(duplicates)} DUPLICATE OUTPUT IDS:\n")
    for output_id, callback_ids in sorted(duplicates.items()):
        print(f"  Output: {output_id}")
        print(f"  Registered {len(callback_ids)} times:")
        for cb_id in callback_ids:
            print(f"    - {cb_id}")
        print()
else:
    print("✅ No duplicate output IDs found\n")

# Check for attribution_lab specific outputs
attr_outputs = [k for k in output_counts.keys() if any(x in k for x in ['perf-', 'factors-', 'sectors-', 'residual-'])]
if attr_outputs:
    print(f"\nAttribution Lab Outputs ({len(attr_outputs)}):")
    for output_id in sorted(attr_outputs):
        count = len(output_counts[output_id])
        status = "❌ DUPLICATE" if count > 1 else "✅"
        print(f"  {status} {output_id} (registered {count} time(s))")

print(f"\n{'='*70}\n")
