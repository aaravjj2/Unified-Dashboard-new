#!/usr/bin/env python3
"""
Strategy Lab Callback Diagnostic
Identifies missing component IDs causing callback errors.

Console errors show:
- ReferenceError: 'sl-validation-result' not found
- ReferenceError: 'sl-start-date' not found
"""

import re
from pathlib import Path

# Parse all callback IDs
callback_file = Path("/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/strategy_lab/callbacks.py")
callback_ids = {
    'Input': set(),
    'Output': set(),
    'State': set()
}

with open(callback_file) as f:
    content = f.read()
    for match in re.finditer(r"(Input|Output|State)\(['\"]([^'\"]+)['\"]", content):
        callback_type, component_id = match.groups()
        if component_id.startswith('sl-'):
            callback_ids[callback_type].add(component_id)

# Parse all subtab component IDs
subtabs_dir = Path("/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/strategy_lab/subtabs")
subtab_ids = set()

for subtab_file in subtabs_dir.glob("*.py"):
    if subtab_file.name.startswith('__'):
        continue
    with open(subtab_file) as f:
        content = f.read()
        for match in re.finditer(r"id=['\"]([^'\"]+)['\"]", content):
            component_id = match.group(1)
            if component_id.startswith('sl-'):
                subtab_ids.add(component_id)

# Find missing components
all_callback_ids = callback_ids['Input'] | callback_ids['Output'] | callback_ids['State']
missing_ids = all_callback_ids - subtab_ids

print("=" * 80)
print("STRATEGY LAB CALLBACK DIAGNOSTIC REPORT")
print("=" * 80)

print(f"\n📊 SUMMARY:")
print(f"   Callbacks reference: {len(all_callback_ids)} unique sl-* component IDs")
print(f"   Subtabs provide:     {len(subtab_ids)} unique sl-* component IDs")
print(f"   ⚠️  Missing:          {len(missing_ids)} component IDs")

print(f"\n❌ MISSING COMPONENT IDs (causing callback errors):")
print("=" * 80)
for comp_id in sorted(missing_ids):
    # Find which callback uses it
    usage_types = []
    if comp_id in callback_ids['Input']:
        usage_types.append('Input')
    if comp_id in callback_ids['Output']:
        usage_types.append('Output')
    if comp_id in callback_ids['State']:
        usage_types.append('State')
    
    print(f"   • {comp_id}")
    print(f"     Used as: {', '.join(usage_types)}")
    
    # Find line numbers in callbacks.py
    with open(callback_file) as f:
        for i, line in enumerate(f, 1):
            if f"'{comp_id}'" in line or f'"{comp_id}"' in line:
                print(f"     callbacks.py:{i}: {line.strip()}")

print(f"\n✅ EXISTING COMPONENTS (correctly defined):")
print("=" * 80)

# Group by subtab
subtab_components = {}
for subtab_file in subtabs_dir.glob("*.py"):
    if subtab_file.name.startswith('__'):
        continue
    subtab_name = subtab_file.stem
    with open(subtab_file) as f:
        content = f.read()
        ids_in_file = set(re.findall(r"id=['\"]([^'\"]+)['\"]", content))
        sl_ids = {id for id in ids_in_file if id.startswith('sl-')}
        if sl_ids:
            subtab_components[subtab_name] = sorted(sl_ids)

for subtab_name in sorted(subtab_components.keys()):
    print(f"\n   {subtab_name}.py ({len(subtab_components[subtab_name])} components):")
    for comp_id in subtab_components[subtab_name]:
        usage = []
        if comp_id in callback_ids['Input']:
            usage.append('Input')
        if comp_id in callback_ids['Output']:
            usage.append('Output')
        if comp_id in callback_ids['State']:
            usage.append('State')
        
        status = "✓ Used" if usage else "⚠️  Unused"
        usage_str = f" ({', '.join(usage)})" if usage else ""
        print(f"      • {comp_id}{usage_str} {status}")

print(f"\n🔧 RECOMMENDED FIXES:")
print("=" * 80)
print("""
1. SETUP.PY FIXES:
   - Rename 'sl-validation-feedback' → 'sl-validation-result'
   
2. BACKTEST.PY MISSING COMPONENTS:
   Add these missing date pickers:
   - sl-start-date (dcc.DatePickerSingle)
   - sl-end-date (dcc.DatePickerSingle)
   
   Add missing inputs:
   - sl-transaction-cost (dcc.Input)
   - sl-position-size (dcc.Input)
   - sl-max-positions (dcc.Input)
   - sl-reset-btn (dbc.Button)
   
3. RESULTS.PY FIXES:
   Rename components to match callbacks:
   - sl-cagr-value → sl-metric-cagr
   - sl-sharpe-value → sl-metric-sharpe
   - sl-drawdown-value → sl-metric-maxdd
   - sl-winrate-value → sl-metric-winrate
   
4. BENCHMARK.PY MISSING COMPONENTS:
   Add these missing charts:
   - sl-vs-benchmark (dcc.Graph)
   - sl-factor-attribution (dcc.Graph)
   - sl-exposure-breakdown (dcc.Graph)
""")

print("\n" + "=" * 80)
print(f"Diagnostic complete. Fix {len(missing_ids)} missing components to resolve errors.")
print("=" * 80)
