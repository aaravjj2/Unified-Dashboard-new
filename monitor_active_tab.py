#!/usr/bin/env python3
"""
Monitor active_tab property changes in Research Lab.
"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    page.goto("http://localhost:8051/", timeout=30000)
    time.sleep(2)
    
    # Click Research Lab tab
    page.click('a[role="tab"]:has-text("Research Lab")')
    time.sleep(2)
    
    # Inject script to monitor active_tab changes
    page.evaluate("""
        const tabs = document.querySelector('#research-lab-tabs');
        if (tabs) {
            console.log('✅ Found research-lab-tabs element');
            console.log('Current active_tab:', tabs.getAttribute('data-active-tab') || 'unknown');
            
            // Set up MutationObserver to watch for changes
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'data-active-tab') {
                        console.log('🔥 active_tab CHANGED to:', tabs.getAttribute('data-active-tab'));
                    }
                });
            });
            
            observer.observe(tabs, { attributes: true });
            console.log('👀 Watching for active_tab changes...');
        } else {
            console.error('❌ #research-lab-tabs not found!');
        }
    """)
    
    # Click Market Scan
    print("\nClicking Market Scan...")
    page.click('a[role="tab"]:has-text("Market Scan")')
    time.sleep(2)
    
    # Click Research Notes
    print("\nClicking Research Notes...")
    page.click('a[role="tab"]:has-text("Research Notes")')
    time.sleep(2)
    
    # Get final active_tab
    active_tab = page.evaluate("""
        const tabs = document.querySelector('#research-lab-tabs');
        tabs ? tabs.getAttribute('data-active-tab') : null
    """)
    print(f"\nFinal active_tab: {active_tab}")
    
    time.sleep(3)
    browser.close()
