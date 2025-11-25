#!/usr/bin/env python3
"""
Dump callback map to check if research-lab-content callback is registered.
"""

import requests
import json

# Get callback dependencies from Dash
response = requests.get('http://localhost:8051/_dash-dependencies')
deps = response.json()

print(f"Total callbacks: {len(deps)}")
print("\nSearching for 'research-lab' callbacks...\n")

count = 0
for cb in deps:
    # Check if any output has 'research-lab' in the ID
    if 'output' in cb:
        if isinstance(cb['output'], list):
            outputs = cb['output']
        else:
            outputs = [cb['output']]
        
        for output in outputs:
            if isinstance(output, dict) and 'research-lab' in output.get('id', ''):
                count += 1
                print(f"Callback #{count}:")
                print(f"  Output: {output}")
                if 'inputs' in cb:
                    print(f"  Inputs: {cb['inputs']}")
                print()

if count == 0:
    print("❌ NO callbacks found with 'research-lab' output!")
    print("\nAll callback output IDs:")
    for cb in deps:
        if 'output' in cb:
            outputs = cb['output'] if isinstance(cb['output'], list) else [cb['output']]
            for out in outputs:
                if isinstance(out, dict):
                    print(f"  - {out.get('id', 'unknown')}")
else:
    print(f"✅ Found {count} research-lab callbacks")
