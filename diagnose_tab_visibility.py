"""
Diagnose why tabs are not visible in the browser
"""
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:8050/', wait_until='networkidle')
    
    # Get the tab container structure
    tab_info = page.evaluate("""
        () => {
            const tabs = document.querySelectorAll('.nav-link');
            const navItems = document.querySelectorAll('.nav-item');
            const container = document.getElementById('dashboard-tabs');
            
            return {
                total_nav_links: tabs.length,
                total_nav_items: navItems.length,
                first_9_tabs: Array.from(tabs).slice(0, 9).map((t, i) => ({
                    index: i + 1,
                    text: t.textContent.trim(),
                    display: window.getComputedStyle(t).display,
                    visibility: window.getComputedStyle(t).visibility,
                    opacity: window.getComputedStyle(t).opacity,
                    parent_display: window.getComputedStyle(t.parentElement).display,
                    offsetWidth: t.offsetWidth,
                    offsetHeight: t.offsetHeight
                })),
                container_exists: !!container,
                container_display: container ? window.getComputedStyle(container).display : 'N/A',
                container_children: container ? container.children.length : 0
            }
        }
    """)
    
    print("=== TAB VISIBILITY DIAGNOSTIC ===\n")
    print(f"Total .nav-link elements: {tab_info['total_nav_links']}")
    print(f"Total .nav-item elements: {tab_info['total_nav_items']}")
    print(f"Container exists: {tab_info['container_exists']}")
    print(f"Container display: {tab_info['container_display']}")
    print(f"Container children: {tab_info['container_children']}")
    
    print("\n=== FIRST 9 TABS (Main Navigation) ===")
    for tab in tab_info['first_9_tabs']:
        visible = tab['display'] != 'none' and tab['visibility'] != 'hidden' and float(tab['opacity']) > 0
        status = "✅ VISIBLE" if visible and tab['offsetWidth'] > 0 else "❌ HIDDEN"
        print(f"{tab['index']}. {tab['text']:<20} {status}")
        if not visible or tab['offsetWidth'] == 0:
            print(f"   Display: {tab['display']}, Visibility: {tab['visibility']}, Opacity: {tab['opacity']}")
            print(f"   Dimensions: {tab['offsetWidth']}x{tab['offsetHeight']}px")
            print(f"   Parent display: {tab['parent_display']}")
    
    browser.close()
