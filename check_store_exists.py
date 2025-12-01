#!/usr/bin/env python3
"""
Check if options-chain-store element actually exists in DOM.
"""
import time
from playwright.sync_api import sync_playwright

PORT = 8050
URL = f"http://localhost:{PORT}"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    print("Clicking Options Lab...")
    page.click("text=💹 Options Lab")
    time.sleep(5)
    
    # Check all stores in the page
    all_stores = page.evaluate("""
        () => {
            const stores = document.querySelectorAll('[id*="store"]');
            return Array.from(stores).map(s => ({
                id: s.id,
                tag: s.tagName,
                hasContent: s.textContent ? s.textContent.length > 0 : false,
                contentPreview: s.textContent ? s.textContent.substring(0, 100) : null
            }));
        }
    """)
    
    print(f"\n📦 All stores in page ({len(all_stores)}):")
    for store in all_stores:
        if 'options' in store['id'] or 'chain' in store['id']:
            print(f"   {store['id']}: {store}")
    
    # Specifically check options-chain-store
    chain_store = page.evaluate("""
        () => {
            const store = document.getElementById('options-chain-store');
            if (!store) {
                // Check if it exists anywhere
                const allIds = Array.from(document.querySelectorAll('[id]')).map(el => el.id);
                return {
                    exists: false,
                    all_option_ids: allIds.filter(id => id.includes('option'))
                };
            }
            
            return {
                exists: true,
                parent: store.parentElement?.id,
                innerHTML: store.innerHTML,
                data_attr: store.getAttribute('data')
            };
        }
    """)
    
    print(f"\n🔍 options-chain-store check:")
    import json
    print(json.dumps(chain_store, indent=2))
    
    browser.close()
