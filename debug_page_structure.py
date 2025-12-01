#!/usr/bin/env python3
"""
Debug script to inspect actual DOM structure
"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headed mode to see what's happening
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("Loading page...")
    page.goto('http://localhost:8050/azure-ml-lab', wait_until='networkidle')
    page.wait_for_load_state('networkidle')
    time.sleep(5)
    
    print("\n=== Checking for Run Prediction button ===")
    btn_count = page.locator('#azure-ml-run-prediction-btn').count()
    print(f"Button count: {btn_count}")
    
    if btn_count > 0:
        btn = page.locator('#azure-ml-run-prediction-btn')
        print(f"Is visible: {btn.is_visible()}")
        print(f"Is enabled: {btn.is_enabled()}")
        
        # Get computed styles
        styles = page.evaluate('''() => {
            const el = document.querySelector('#azure-ml-run-prediction-btn');
            if (!el) return 'Element not found';
            const computed = window.getComputedStyle(el);
            return {
                display: computed.display,
                visibility: computed.visibility,
                opacity: computed.opacity,
                position: computed.position,
                zIndex: computed.zIndex
            };
        }''')
        print(f"Computed styles: {styles}")
    
    print("\n=== Checking for tabs ===")
    tab_selectors = [
        'a.nav-link',
        'button.nav-link',
        '[role="tab"]'
    ]
    
    for selector in tab_selectors:
        count = page.locator(selector).count()
        print(f"{selector}: {count} elements")
        
        if count > 0:
            for i in range(min(count, 5)):
                el = page.locator(selector).nth(i)
                text = el.text_content() if el.count() > 0 else "N/A"
                visible = el.is_visible() if el.count() > 0 else False
                print(f"  [{i}] Text: '{text[:30]}', Visible: {visible}")
    
    print("\n=== Saving page HTML ===")
    html = page.content()
    with open('page_structure_debug.html', 'w') as f:
        f.write(html)
    print("Saved to page_structure_debug.html")
    
    print("\n=== Taking screenshot ===")
    page.screenshot(path='debug_screenshot.png', full_page=True)
    print("Saved to debug_screenshot.png")
    
    input("\nPress Enter to close browser...")
    browser.close()
