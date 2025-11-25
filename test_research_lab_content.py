#!/usr/bin/env python3
"""
Test Research Lab subtabs to verify they have content
"""

import sys
sys.path.insert(0, 'financial_dashboard')

from tabs.research_lab.layout import create_layout
from dash import html
import json

def count_components(component, depth=0):
    """Recursively count components"""
    count = 1
    if hasattr(component, 'children'):
        children = component.children
        if isinstance(children, list):
            for child in children:
                count += count_components(child, depth+1)
        elif children is not None:
            count += count_components(children, depth+1)
    return count

def extract_text(component):
    """Extract text content from component"""
    text = []
    if hasattr(component, 'children'):
        children = component.children
        if isinstance(children, str):
            text.append(children)
        elif isinstance(children, list):
            for child in children:
                text.extend(extract_text(child))
        elif children is not None:
            text.extend(extract_text(children))
    return text

print("="*80)
print("RESEARCH LAB CONTENT VERIFICATION TEST")
print("="*80)

layout = create_layout()

# Extract tabs
tabs_component = layout.children[1]  # dbc.Tabs component
tabs = tabs_component.children

print(f"\nTotal tabs found: {len(tabs)}")

# Test each tab
tab_names = [
    'Market Scan',
    'Factor Analysis', 
    'Correlation Explorer',
    'Strategy Backtest',
    'Research Notes'
]

results = {}

for idx, (tab, name) in enumerate(zip(tabs, tab_names)):
    print(f"\n--- Tab {idx+1}: {name} ---")
    
    component_count = count_components(tab)
    text_content = extract_text(tab)
    text_length = sum(len(t) for t in text_content)
    
    # Check for specific indicators
    has_dropdown = 'Dropdown' in str(type(tab))
    has_table = 'Table' in str(type(tab))
    has_card = 'Card' in str(type(tab))
    
    print(f"Components: {component_count}")
    print(f"Text length: {text_length} chars")
    print(f"Has dropdowns: {has_dropdown}")
    print(f"Has tables: {has_table}")
    print(f"Has cards: {has_card}")
    
    # Determine if tab has content
    has_content = component_count > 5 and text_length > 50
    
    status = "✅ HAS CONTENT" if has_content else "❌ EMPTY"
    print(f"Status: {status}")
    
    results[name] = {
        'has_content': has_content,
        'component_count': component_count,
        'text_length': text_length,
        'status': status
    }

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

all_pass = all(r['has_content'] for r in results.values())

for name, result in results.items():
    print(f"{name:25s} {result['status']}")

print("\n" + "="*80)
if all_pass:
    print("✅ ALL TABS HAVE CONTENT")
else:
    print("❌ SOME TABS ARE EMPTY")
print("="*80)

# Save results
with open('reports/fix_verification/tests/research_lab_content_results.json', 'w') as f:
    json.dump(results, f, indent=2)

sys.exit(0 if all_pass else 1)
