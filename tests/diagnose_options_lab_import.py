#!/usr/bin/env python3
"""
Diagnostic: Options Lab Module Import Test

Tests if Options Lab can be imported and has required exports
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/mnt/c/Aarav/fin_env/unified-dashboard')

print("=" * 80)
print("🔬 OPTIONS LAB MODULE IMPORT DIAGNOSTIC")
print("=" * 80)

# Test 1: Import the module
print("\n1️⃣ Testing module import...")
try:
    import importlib
    options_lab = importlib.import_module('financial_dashboard.tabs.options_lab')
    print("   ✅ Module imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Check for required exports
print("\n2️⃣ Checking required exports...")
required_attrs = ['layout', 'register_callbacks', '__all__']
for attr in required_attrs:
    if hasattr(options_lab, attr):
        value = getattr(options_lab, attr)
        print(f"   ✅ {attr}: {type(value).__name__}")
        if attr == '__all__':
            print(f"      Contents: {value}")
    else:
        print(f"   ❌ Missing: {attr}")

# Test 3: Check if layout is callable or a component
print("\n3️⃣ Testing layout attribute...")
if hasattr(options_lab, 'layout'):
    layout_obj = options_lab.layout
    print(f"   Type: {type(layout_obj).__name__}")
    print(f"   Callable: {callable(layout_obj)}")
    
    if callable(layout_obj):
        print("   🧪 Attempting to call layout()...")
        try:
            result = layout_obj()
            print(f"   ✅ Layout callable returns: {type(result).__name__}")
            print(f"   ✅ Result has 'children': {hasattr(result, 'children')}")
        except Exception as e:
            print(f"   ❌ Layout call failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"   ✅ Layout is a direct component: {hasattr(layout_obj, 'children')}")
else:
    print("   ❌ No layout attribute found")

# Test 4: List all module attributes
print("\n4️⃣ All module attributes:")
attrs = [a for a in dir(options_lab) if not a.startswith('_')]
for attr in attrs:
    print(f"   - {attr}")

# Test 5: Check the module file structure
print("\n5️⃣ Module file structure:")
module_path = options_lab.__file__
module_dir = os.path.dirname(module_path)
print(f"   Module location: {module_dir}")
if os.path.exists(module_dir):
    files = os.listdir(module_dir)
    for f in sorted(files):
        print(f"   - {f}")

print("\n" + "=" * 80)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 80)
