#!/usr/bin/env python3
"""Find all IDs across all tabs and subtabs."""

from playwright.sync_api import sync_playwright
import time

def explore_all_tabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8053/", timeout=30000)
        time.sleep(3)
        
        print("\n" + "="*60)
        print("FULL ELEMENT EXPLORATION")
        print("="*60)
        
        all_ids = set()
        
        # Main tabs
        main_tabs = ["Scanner", "Strategy", "Command", "Admin"]
        
        for main_tab in main_tabs:
            print(f"\n📁 Tab: {main_tab}")
            print("-" * 40)
            
            tab = page.locator(f"//div[contains(@class, 'tab') and contains(text(), '{main_tab}')]").first
            if tab.count() > 0:
                tab.click()
                time.sleep(1.5)
                
                # Get all IDs on this tab
                ids = page.eval_on_selector_all(
                    "[id]",
                    "elements => elements.map(el => el.id).filter(id => id.length > 0)"
                )
                
                new_ids = [id for id in ids if id not in all_ids]
                all_ids.update(ids)
                
                print(f"   Total IDs visible: {len(ids)}")
                print(f"   New unique IDs: {len(new_ids)}")
                
                # Print interesting ones
                interesting = [id for id in new_ids if any(k in id.lower() for k in ['ai', 'chart', 'gex', 'vol', 'flow', 'position', 'trade', 'status', 'forecast', 'ml', 'predict'])]
                if interesting:
                    print(f"   Interesting IDs:")
                    for id in interesting[:20]:
                        print(f"      - {id}")
                
                # Check for subtabs
                subtabs = page.locator(".tab:not([id*='workspace']), [class*='subtab'], .nav-link, .card-header:has-text('Tab')").all()
                if subtabs:
                    print(f"   Found {len(subtabs)} possible subtabs")
        
        print("\n" + "="*60)
        print(f"TOTAL UNIQUE IDS FOUND: {len(all_ids)}")
        print("="*60)
        
        # Print all unique IDs grouped
        print("\nAll unique IDs (grouped):")
        prefixes = {}
        for id in sorted(all_ids):
            prefix = id.split('-')[0] if '-' in id else id[:10]
            if prefix not in prefixes:
                prefixes[prefix] = []
            prefixes[prefix].append(id)
        
        for prefix in sorted(prefixes.keys()):
            if len(prefixes[prefix]) > 1:
                print(f"\n{prefix}* ({len(prefixes[prefix])} elements):")
                for id in prefixes[prefix][:10]:
                    print(f"   - {id}")
                if len(prefixes[prefix]) > 10:
                    print(f"   ... and {len(prefixes[prefix])-10} more")
        
        browser.close()

if __name__ == "__main__":
    explore_all_tabs()
