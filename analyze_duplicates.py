#!/usr/bin/env python3
"""Analyze duplicate callback errors in detail"""
import json

# Load the diagnostic report
with open('/home/aarav/unified-dashboard/reports/console_error_diagnostic.json') as f:
    data = json.load(f)

# Extract error messages and count duplicates
error_patterns = {}
for error in data['console_errors']:
    text = error['text']
    
    # Extract component ID from error message
    # Format: "In the callback for output(s):\n  {component-id}..."
    if 'In the callback for output(s):' in text:
        lines = text.split('\n')
        if len(lines) > 1:
            component = lines[1].strip().split('.')[0].split('}')[0]
            if component not in error_patterns:
                error_patterns[component] = 0
            error_patterns[component] += 1

# Sort by frequency
sorted_patterns = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)

print("\n" + "="*80)
print("DUPLICATE CALLBACK OUTPUT ANALYSIS")
print("="*80 + "\n")

print(f"Total unique components with duplicates: {len(sorted_patterns)}\n")
print("Top 20 components by duplicate count:\n")

for i, (component, count) in enumerate(sorted_patterns[:20], 1):
    print(f"{i:2}. {component:40} - {count:3} duplicates")

print("\n" + "="*80)
print(f"Total errors: {len(data['console_errors'])}")
print("="*80 + "\n")
