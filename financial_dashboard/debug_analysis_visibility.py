#!/usr/bin/env python3
"""Debug Analysis Hub visibility"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto("http://localhost:8054", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)
    
    print("\n1. Check if welcome element exists:")
    welcome = page.locator('#attr-initial-instructions')
    print(f"Count: {welcome.count()}")
    
    if welcome.count() > 0:
        print(f"\n2. Check visibility:")
        print(f"is_visible(): {welcome.is_visible()}")
        
        print(f"\n3. Get computed style:")
        display = page.evaluate("""() => {
            const el = document.getElementById('attr-initial-instructions');
            if (el) {
                const style = window.getComputedStyle(el);
                return {
                    display: style.display,
                    visibility: style.visibility,
                    opacity: style.opacity,
                    position: style.position,
                    zIndex: style.zIndex
                };
            }
            return null;
        }""")
        print(f"Computed style: {display}")
        
        print(f"\n4. Check parent container:")
        parent_info = page.evaluate("""() => {
            const el = document.getElementById('attr-initial-instructions');
            if (el && el.parentElement) {
                const parent = el.parentElement;
                const parentStyle = window.getComputedStyle(parent);
                return {
                    parentTag: parent.tagName,
                    parentId: parent.id,
                    parentDisplay: parentStyle.display,
                    parentVisibility: parentStyle.visibility
                };
            }
            return null;
        }""")
        print(f"Parent info: {parent_info}")
        
        print(f"\n5. Check tab structure:")
        tabs = page.locator('.nav-link').all()
        print(f"Found {len(tabs)} tabs")
        for i, tab in enumerate(tabs):
            print(f"  Tab {i}: {tab.text_content().strip()}")
        
        print(f"\n6. Check active tab:")
        active_tab = page.evaluate("""() => {
            const activeTab = document.querySelector('.nav-link.active');
            return activeTab ? activeTab.textContent.trim() : 'none';
        }""")
        print(f"Active tab: {active_tab}")
        
        print(f"\n7. Check tab content visibility:")
        tab_panes = page.evaluate("""() => {
            const panes = document.querySelectorAll('.tab-pane');
            return Array.from(panes).map((p, i) => ({
                index: i,
                id: p.id,
                classes: p.className,
                display: window.getComputedStyle(p).display,
                hasActiveClass: p.classList.contains('active')
            }));
        }""")
        print(f"Tab panes: {tab_panes}")
    
    browser.close()
