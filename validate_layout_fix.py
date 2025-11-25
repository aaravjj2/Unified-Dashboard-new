#!/usr/bin/env python3
"""
Validation script for layout serialization fix
Tests that no module objects are present in the dashboard layout
"""

import sys
import types
sys.path.insert(0, '/home/aarav/unified-dashboard')

def find_modules_in_obj(obj, path="root", depth=0, max_depth=10):
    """Recursively search for module objects"""
    if depth > max_depth:
        return []
    
    found = []
    if isinstance(obj, types.ModuleType):
        found.append(path)
        return found
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.extend(find_modules_in_obj(v, f"{path}['{k}']", depth+1, max_depth))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            found.extend(find_modules_in_obj(v, f"{path}[{i}]", depth+1, max_depth))
    elif hasattr(obj, '__dict__') and not isinstance(obj, type):
        for k, v in obj.__dict__.items():
            if k.startswith('_'):
                continue
            found.extend(find_modules_in_obj(v, f"{path}.{k}", depth+1, max_depth))
    
    return found

print("=" * 80)
print("LAYOUT SERIALIZATION FIX VALIDATION")
print("=" * 80)

print("\n1. Testing command_center_pkg layout attribute...")
from financial_dashboard.tabs import command_center_pkg

if hasattr(command_center_pkg, 'layout'):
    layout_attr = command_center_pkg.layout
    print(f"   ✓ Has 'layout' attribute: {type(layout_attr)}")
    if isinstance(layout_attr, types.ModuleType):
        print(f"   ✗ ERROR: 'layout' is a MODULE (not a function)!")
    elif callable(layout_attr):
        print(f"   ✓ 'layout' is callable")
    else:
        print(f"   ⚠ 'layout' is NOT callable: {type(layout_attr)}")

if hasattr(command_center_pkg, 'create_layout'):
    create_layout_attr = command_center_pkg.create_layout
    print(f"   ✓ Has 'create_layout' attribute: {type(create_layout_attr)}")
    if callable(create_layout_attr):
        print(f"   ✓ 'create_layout' is callable")

print("\n2. Testing layout creation logic...")
layout_func = None
if hasattr(command_center_pkg, 'create_layout'):
    layout_func = command_center_pkg.create_layout
    print(f"   ✓ Using create_layout")
elif hasattr(command_center_pkg, 'layout') and callable(getattr(command_center_pkg, 'layout', None)):
    layout_func = command_center_pkg.layout
    print(f"   ✓ Using callable layout")

if layout_func and callable(layout_func):
    print(f"   ✓ Selected layout function is callable")
    try:
        content = layout_func()
        print(f"   ✓ Layout created successfully: {type(content)}")
        
        # Check for modules in the created layout
        modules_found = find_modules_in_obj(content, "layout_content")
        if modules_found:
            print(f"   ✗ ERROR: Found {len(modules_found)} module objects in layout:")
            for path in modules_found[:5]:
                print(f"      - {path}")
        else:
            print(f"   ✓ No module objects found in layout content")
    except Exception as e:
        print(f"   ✗ ERROR creating layout: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"   ✗ ERROR: No valid layout function found!")

print("\n3. Testing full app creation...")
try:
    from financial_dashboard.app import create_app
    app = create_app()
    print(f"   ✓ App created: {type(app)}")
    
    if hasattr(app, 'layout'):
        print(f"   ✓ App has layout")
        modules_in_layout = find_modules_in_obj(app.layout, "app.layout", max_depth=15)
        if modules_in_layout:
            print(f"   ✗ ERROR: Found {len(modules_in_layout)} module objects in app layout:")
            for path in modules_in_layout[:10]:
                print(f"      - {path}")
        else:
            print(f"   ✓ No module objects in app layout - FIX SUCCESSFUL!")
    else:
        print(f"   ⚠ App has no layout set")
        
except Exception as e:
    print(f"   ✗ ERROR creating app: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)
