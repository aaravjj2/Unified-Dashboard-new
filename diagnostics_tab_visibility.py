#!/usr/bin/env python3
"""
Attribution Lab Deep Diagnostic - Phase 2
Investigates why tab doesn't appear in UI despite app export fix.

Focus areas:
1. Tab registration in index.py
2. Layout structure and tab entries
3. Callback registration
4. DOM element visibility
"""

import sys
import os
from pathlib import Path
import json

# Setup paths
sys.path.insert(0, 'financial_dashboard')

print("=" * 80)
print("ATTRIBUTION LAB DEEP DIAGNOSTIC - Phase 2")
print("=" * 80)

# ============================================================================
# PHASE 1: TAB REGISTRATION AUDIT
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 1: Tab Registration Audit")
print("=" * 80)

try:
    import index
    
    # Check for loaded_tabs dictionary
    if hasattr(index, 'loaded_tabs'):
        loaded_tabs = index.loaded_tabs
        print(f"\n✅ loaded_tabs exists: {len(loaded_tabs)} tabs loaded")
        print("\nLoaded tabs:")
        for tab_id, tab_info in loaded_tabs.items():
            print(f"  - {tab_id:20} | {tab_info.get('name', 'NO NAME')}")
            
        if 'attribution_lab' in loaded_tabs:
            print("\n✅ Attribution Lab IS in loaded_tabs!")
            attr_info = loaded_tabs['attribution_lab']
            print(f"   Name: {attr_info.get('name')}")
            print(f"   Layout callable: {callable(attr_info.get('layout'))}")
        else:
            print("\n❌ Attribution Lab NOT in loaded_tabs!")
            print("   Available tabs:", list(loaded_tabs.keys()))
    else:
        print("❌ No loaded_tabs attribute found")
    
    # Check TAB_CONFIG
    if hasattr(index, 'TAB_CONFIG'):
        tab_config = index.TAB_CONFIG
        print(f"\n✅ TAB_CONFIG exists: {len(tab_config)} entries")
        
        attr_config = None
        for cfg in tab_config:
            if cfg.get('id') == 'attribution_lab':
                attr_config = cfg
                break
        
        if attr_config:
            print("\n✅ Attribution Lab in TAB_CONFIG:")
            print(f"   ID: {attr_config.get('id')}")
            print(f"   Name: {attr_config.get('name')}")
            print(f"   Module: {attr_config.get('module')}")
        else:
            print("\n❌ Attribution Lab NOT in TAB_CONFIG!")
    
    # Check enabled_tabs
    if hasattr(index, 'enabled_tabs'):
        enabled = index.enabled_tabs
        print(f"\n✅ enabled_tabs exists: {enabled}")
        
        if 'attribution_lab' in enabled:
            print("   ✅ attribution_lab is ENABLED")
        else:
            print("   ❌ attribution_lab is NOT ENABLED!")
    else:
        print("\n⚠️ No enabled_tabs attribute at module level")
        print("   (May be defined inside functions)")

except Exception as e:
    print(f"\n❌ PHASE 1 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# PHASE 2: LAYOUT STRUCTURE ANALYSIS
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 2: Layout Structure Analysis")
print("=" * 80)

try:
    if hasattr(index, 'app') and index.app:
        app = index.app
        
        # Check if layout is callable or static
        if callable(app.layout):
            print("✅ app.layout is a function (deferred layout)")
            print("   Calling layout function to inspect structure...")
            
            try:
                layout = app.layout()
                print(f"✅ Layout generated: {type(layout).__name__}")
            except Exception as e:
                print(f"❌ Layout function failed: {e}")
                layout = None
        else:
            print("✅ app.layout is static")
            layout = app.layout
        
        if layout:
            # Convert to string and search for attribution_lab references
            layout_str = str(layout)
            
            checks = {
                'attribution_lab': 'attribution_lab' in layout_str.lower(),
                'tab-attribution_lab': 'tab-attribution_lab' in layout_str,
                'Attribution Lab': 'Attribution Lab' in layout_str,
                '📊': '📊' in layout_str,
                'attr-': 'attr-' in layout_str  # Callback namespace
            }
            
            print("\nLayout string search results:")
            for key, found in checks.items():
                status = "✅" if found else "❌"
                print(f"  {status} '{key}': {found}")
            
            # Try to extract tab structure
            if hasattr(layout, 'children'):
                print(f"\n✅ Layout has children attribute")
                
                # Try to find dcc.Tabs or custom tab navigation
                def find_tabs_component(component, depth=0):
                    if depth > 5:  # Limit recursion
                        return None
                    
                    comp_type = type(component).__name__
                    
                    if 'Tabs' in comp_type:
                        return component
                    
                    if hasattr(component, 'children'):
                        children = component.children
                        if isinstance(children, list):
                            for child in children:
                                result = find_tabs_component(child, depth + 1)
                                if result:
                                    return result
                    
                    return None
                
                tabs_component = find_tabs_component(layout)
                if tabs_component:
                    print(f"✅ Found Tabs component: {type(tabs_component).__name__}")
                    
                    if hasattr(tabs_component, 'children'):
                        tab_count = len(tabs_component.children) if isinstance(tabs_component.children, list) else 1
                        print(f"   Tab count: {tab_count}")
                else:
                    print("⚠️ No Tabs component found in layout")
            
            # Save layout snapshot
            try:
                snapshot_file = Path("layout_snapshot.json")
                
                # Try to serialize layout to JSON
                def serialize_component(comp):
                    try:
                        return {
                            'type': type(comp).__name__,
                            'id': getattr(comp, 'id', None),
                            'children': 'HAS_CHILDREN' if hasattr(comp, 'children') else None
                        }
                    except:
                        return {'type': 'SERIALIZATION_FAILED'}
                
                snapshot = serialize_component(layout)
                
                with open(snapshot_file, 'w') as f:
                    json.dump(snapshot, f, indent=2)
                
                print(f"\n✅ Layout snapshot saved to {snapshot_file}")
            except Exception as e:
                print(f"⚠️ Could not save layout snapshot: {e}")
        
    else:
        print("❌ No app object available")

except Exception as e:
    print(f"\n❌ PHASE 2 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# PHASE 3: CALLBACK REGISTRATION CHECK
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 3: Callback Registration Check")
print("=" * 80)

try:
    if hasattr(index, 'app') and index.app:
        app = index.app
        
        if hasattr(app, 'callback_map'):
            callback_map = app.callback_map
            print(f"✅ callback_map accessible: {len(callback_map)} callbacks")
            
            # Find attribution-related callbacks
            attr_callbacks = []
            for cb_id, cb_info in callback_map.items():
                cb_str = str(cb_id).lower()
                if 'attr' in cb_str:
                    attr_callbacks.append(cb_id)
            
            if attr_callbacks:
                print(f"\n✅ Found {len(attr_callbacks)} attribution-related callbacks:")
                for i, cb_id in enumerate(attr_callbacks[:5], 1):
                    print(f"   {i}. {str(cb_id)[:80]}...")
                if len(attr_callbacks) > 5:
                    print(f"   ... and {len(attr_callbacks) - 5} more")
            else:
                print("\n❌ NO attribution-related callbacks found!")
                print("   This means callbacks were NOT registered properly")
        else:
            print("⚠️ callback_map not accessible")
    else:
        print("❌ No app object")

except Exception as e:
    print(f"\n❌ PHASE 3 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# PHASE 4: ATTRIBUTION LAB MODULE INTEGRITY
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 4: Attribution Lab Module Integrity")
print("=" * 80)

try:
    from tabs.attribution_lab import layout as attr_layout
    from tabs.attribution_lab import register_callbacks as attr_callbacks
    
    print("✅ attribution_lab modules import successfully")
    
    # Test layout generation
    print("\nTesting layout() call...")
    try:
        test_layout = attr_layout()
        print(f"✅ Layout generated: {type(test_layout).__name__}")
        
        # Check for tab IDs in layout
        layout_str = str(test_layout)
        
        subtab_checks = {
            'Performance': 'performance' in layout_str.lower(),
            'Factor': 'factor' in layout_str.lower(),
            'Sector': 'sector' in layout_str.lower(),
            'Residual': 'residual' in layout_str.lower()
        }
        
        print("\nSubtab presence in layout:")
        for subtab, present in subtab_checks.items():
            status = "✅" if present else "❌"
            print(f"  {status} {subtab}: {present}")
        
    except Exception as e:
        print(f"❌ Layout generation failed: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"\n❌ PHASE 4 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# PHASE 5: CREATE_LAYOUT FUNCTION INSPECTION
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 5: create_layout() Function Inspection")
print("=" * 80)

try:
    if hasattr(index, 'create_layout'):
        print("✅ create_layout function exists")
        
        # Call it to see what it generates
        print("\nCalling create_layout()...")
        try:
            full_layout = index.create_layout()
            print(f"✅ Layout created: {type(full_layout).__name__}")
            
            # Search for tab navigation
            layout_str = str(full_layout)
            
            # Look for tab creation patterns
            patterns = {
                'dcc.Tabs': 'dcc.Tabs' in layout_str or 'Tabs(' in layout_str,
                'dcc.Tab': 'dcc.Tab' in layout_str or 'Tab(' in layout_str,
                'dbc.Tabs': 'dbc.Tabs' in layout_str,
                'dbc.Tab': 'dbc.Tab' in layout_str,
                'custom tabs': 'tab-' in layout_str
            }
            
            print("\nTab component patterns found:")
            for pattern, found in patterns.items():
                status = "✅" if found else "❌"
                print(f"  {status} {pattern}: {found}")
            
            # Count 'tab-' IDs
            tab_id_count = layout_str.count('tab-')
            print(f"\n   Total 'tab-' ID occurrences: {tab_id_count}")
            
        except Exception as e:
            print(f"❌ create_layout() failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ create_layout function NOT found!")
        print("   Available functions:", [x for x in dir(index) if not x.startswith('_')][:20])

except Exception as e:
    print(f"\n❌ PHASE 5 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

print("""
Key Checks:
1. ✓/✗ loaded_tabs contains attribution_lab
2. ✓/✗ TAB_CONFIG contains attribution_lab
3. ✓/✗ enabled_tabs includes attribution_lab
4. ✓/✗ Layout string contains attribution_lab references
5. ✓/✗ Callbacks registered for attribution_lab
6. ✓/✗ Attribution lab layout() function works
7. ✓/✗ create_layout() includes tab navigation

Review the output above for ❌ marks - these indicate failure points.
""")

print("\nDiagnostic complete. Check output for specific issues.")
print("=" * 80)
