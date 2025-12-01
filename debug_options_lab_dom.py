#!/usr/bin/env python3
"""
Debug Options Lab DOM structure to find why subtabs aren't visible.
"""
import time
from playwright.sync_api import sync_playwright

PORT = 8050
URL = f"http://localhost:{PORT}"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("=" * 80)
    print("OPTIONS LAB DOM INSPECTION")
    print("=" * 80)
    
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    print("\n1. Clicking Options Lab tab...")
    page.click("text=💹 Options Lab")
    time.sleep(5)
    
    # Check if options-subtabs exists
    subtabs_info = page.evaluate("""
        () => {
            const subtabs = document.getElementById('options-subtabs');
            if (!subtabs) {
                return {
                    exists: false,
                    all_ids: Array.from(document.querySelectorAll('[id]')).map(el => el.id).filter(id => id.includes('option'))
                };
            }
            
            return {
                exists: true,
                visible: subtabs.offsetParent !== null,
                innerHTML_length: subtabs.innerHTML.length,
                child_count: subtabs.children.length,
                classList: Array.from(subtabs.classList),
                display_style: window.getComputedStyle(subtabs).display,
                // Get all tab elements
                tab_elements: Array.from(subtabs.querySelectorAll('[role="tab"], .nav-link, [id*="tab"]')).map(el => ({
                    id: el.id,
                    classes: Array.from(el.classList),
                    text: el.textContent.trim().substring(0, 50)
                }))
            };
        }
    """)
    
    print(f"\n📊 options-subtabs Info:")
    import json
    print(json.dumps(subtabs_info, indent=2))
    
    # Check for individual tab IDs
    print("\n2. Checking individual subtab IDs...")
    for tab_id in ['options-chain-tab', 'options-greeks-tab', 'options-vol-tab', 
                   'options-manual-tab', 'options-backtest-tab', 'options-settings-tab']:
        exists = page.evaluate(f"() => !!document.getElementById('{tab_id}')")
        print(f"   {tab_id}: {'✓ EXISTS' if exists else '✗ MISSING'}")
    
    # Get all elements with 'options' in ID
    print("\n3. All elements with 'options' in ID:")
    options_ids = page.evaluate("""
        () => Array.from(document.querySelectorAll('[id*="options"]')).map(el => ({
            id: el.id,
            tag: el.tagName,
            visible: el.offsetParent !== null
        }))
    """)
    for item in options_ids[:20]:  # First 20
        print(f"   {item['id']} ({item['tag']}) - {'visible' if item['visible'] else 'hidden'}")
    
    # Check parent container
    print("\n4. Checking Options Lab container...")
    container_info = page.evaluate("""
        () => {
            const tabContent = document.getElementById('tab-options_lab');
            if (!tabContent) return { exists: false };
            
            return {
                exists: true,
                visible: tabContent.offsetParent !== null,
                innerHTML_length: tabContent.innerHTML.length,
                child_count: tabContent.children.length,
                first_child_tag: tabContent.children[0]?.tagName,
                first_child_id: tabContent.children[0]?.id
            };
        }
    """)
    print(json.dumps(container_info, indent=2))
    
    print("\n✅ Inspection complete")
    time.sleep(5)
    browser.close()
