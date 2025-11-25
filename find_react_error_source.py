#!/usr/bin/env python3
"""
Find the source of React error #31 by inspecting the layout.
"""
import sys
import os

# Add financial_dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'financial_dashboard'))

from financial_dashboard.app import app
import json

def check_component(component, path="root"):
    """Recursively check components for invalid structures."""
    issues = []
    
    # Check if it's a dict with props, type, namespace (invalid!)
    if isinstance(component, dict):
        if 'props' in component and 'type' in component and 'namespace' in component:
            issues.append({
                'path': path,
                'type': component.get('type'),
                'namespace': component.get('namespace'),
                'issue': 'Raw component object (not instantiated)'
            })
            return issues
        
        # Check dict values
        for key, value in component.items():
            issues.extend(check_component(value, f"{path}.{key}"))
    
    # Check lists
    elif isinstance(component, (list, tuple)):
        for i, item in enumerate(component):
            issues.extend(check_component(item, f"{path}[{i}]"))
    
    # Check Dash components
    elif hasattr(component, '__dict__'):
        for key, value in component.__dict__.items():
            if key.startswith('_'):
                continue
            issues.extend(check_component(value, f"{path}.{key}"))
    
    return issues

print("\n" + "="*70)
print("REACT ERROR #31 SOURCE FINDER")
print("="*70 + "\n")

print("Analyzing layout for invalid component structures...")

try:
    layout = app.layout
    issues = check_component(layout)
    
    if issues:
        print(f"\n❌ Found {len(issues)} invalid component structures:\n")
        for i, issue in enumerate(issues[:10], 1):  # Show first 10
            print(f"{i}. Path: {issue['path']}")
            print(f"   Type: {issue['namespace']}.{issue['type']}")
            print(f"   Issue: {issue['issue']}\n")
    else:
        print("✅ No invalid component structures found in layout")
        print("\nThe React error might be coming from a callback return value.")
        print("Check callback outputs for components that aren't properly instantiated.")
    
except Exception as e:
    print(f"❌ Error analyzing layout: {e}")
    import traceback
    traceback.print_exc()

print("="*70 + "\n")
