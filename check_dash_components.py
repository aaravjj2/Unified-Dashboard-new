#!/usr/bin/env python
"""Check if stores appear after JavaScript execution (Playwright wait)."""
from playwright.sync_api import sync_playwright
import time

def check_dom_evolution():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading http://localhost:8050...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        
        print("\n⏳ Waiting for Dash to initialize...")
        time.sleep(3)
        
        # Try to wait for any store to appear
        try:
            page.wait_for_selector('[data-dash-component-type="Store"]', timeout=5000)
            print("✅ Found Store component via data attribute!")
        except:
            print("❌ No Store component found via data attribute")
        
        # Check all elements with data-dash attributes
        dash_components = page.query_selector_all('[data-dash-component-type]')
        print(f"\n📦 Found {len(dash_components)} Dash components total")
        
        # Get unique component types
        component_types = set()
        for comp in dash_components[:50]:  # First 50
            comp_type = comp.get_attribute('data-dash-component-type')
            component_types.add(comp_type)
        
        print(f"\n🔍 Component types found: {sorted(component_types)}")
        
        # Check if Store is among them
        if 'Store' in component_types:
            print("\n✅ Store components ARE being created by JavaScript!")
            stores = page.query_selector_all('[data-dash-component-type="Store"]')
            print(f"📦 Found {len(stores)} Store components:")
            for store in stores[:10]:
                store_id = store.get_attribute('id')
                print(f"  - {store_id}")
        else:
            print("\n❌ Store components NOT being created")
        
        browser.close()

if __name__ == '__main__':
    check_dom_evolution()
