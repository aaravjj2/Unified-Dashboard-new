#!/usr/bin/env python
"""Debug: Check if our layout changes are actually in the running app."""
import sys
sys.path.insert(0, '/home/aarav/unified-dashboard')

# Import the layout directly
from financial_dashboard.index import create_layout

# Create layout and traverse to find stores
layout = create_layout()

def find_stores(component, path="root"):
    """Recursively find all dcc.Store components."""
    stores = []
    
    # Check if this component has children
    if hasattr(component, 'children'):
        children = component.children
        if children is None:
            return stores
        
        # Handle list of children
        if isinstance(children, list):
            for i, child in enumerate(children):
                if hasattr(child, 'id') and 'store' in str(child.id).lower():
                    stores.append((path + f"/children[{i}]", child.id))
                stores.extend(find_stores(child, path + f"/children[{i}]"))
        # Handle single child
        else:
            if hasattr(children, 'id') and 'store' in str(children.id).lower():
                stores.append((path + "/children", children.id))
            stores.extend(find_stores(children, path + "/children"))
    
    return stores

print("🔍 Searching for stores in create_layout() output...")
stores = find_stores(layout)

print(f"\n📦 Found {len(stores)} stores:\n")
for path, store_id in stores:
    print(f"  {store_id}")
    
# Check for our specific stores
our_stores = ['options-chain-store', 'options-surface-store', 'ol-backtest-store', 'ol-settings-store']
print(f"\n🎯 Our Options Lab stores:")
for s in our_stores:
    found = any(store_id == s for _, store_id in stores)
    print(f"  {'✅' if found else '❌'} {s}")
