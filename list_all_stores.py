#!/usr/bin/env python3
"""
Check ALL stores in the entire page to see what's available.
"""
import time
from playwright.sync_api import sync_playwright

PORT = 8050
URL = f"http://localhost:{PORT}"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    
    # Check all dcc.Store elements (they render as divs with data- attributes)
    all_stores = page.evaluate("""
        () => {
            // dcc.Store renders as <div id="store-id" style="display:none"></div>
            const allDivs = document.querySelectorAll('div[id]');
            const stores = [];
            
            allDivs.forEach(div => {
                const style = window.getComputedStyle(div);
                // Check if it looks like a store (hidden, no children usually)
                if (style.display === 'none' && div.children.length === 0) {
                    stores.push({
                        id: div.id,
                        hasTextContent: div.textContent.length > 0,
                        textPreview: div.textContent.substring(0, 50)
                    });
                }
            });
            
            return stores;
        }
    """)
    
    print(f"Found {len(all_stores)} potential Store elements:")
    for store in all_stores:
        if 'store' in store['id'].lower() or 'chain' in store['id'] or 'options' in store['id']:
            print(f"  {store['id']}: {store}")
    
    browser.close()
