#!/usr/bin/env python3
"""
Discover actual tab IDs and button IDs in the dashboard.
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def discover_tabs():
    """Discover all tabs and their IDs."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8052', wait_until='networkidle', timeout=60000)
        await page.wait_for_selector('#react-entry-point', timeout=30000)
        await asyncio.sleep(3)
        
        print("\n📋 Discovering tabs...")
        
        # Find all potential tab elements
        tab_selectors = [
            'a[role="tab"]',
            'button[role="tab"]',
            '.nav-link',
            '[data-rb-event-key]',
            '.nav-item a',
            '.tab'
        ]
        
        discovered_tabs = {}
        
        for selector in tab_selectors:
            try:
                tabs = await page.query_selector_all(selector)
                print(f"\n  Checking selector: {selector} (found {len(tabs)})")
                
                for i, tab in enumerate(tabs):
                    tab_id = await tab.get_attribute('id')
                    tab_text = await tab.inner_text()
                    tab_href = await tab.get_attribute('href')
                    tab_data_key = await tab.get_attribute('data-rb-event-key')
                    tab_class = await tab.get_attribute('class')
                    
                    if tab_text and tab_text.strip():
                        key = f"{selector}_{i}"
                        discovered_tabs[key] = {
                            'text': tab_text.strip(),
                            'id': tab_id,
                            'href': tab_href,
                            'data_key': tab_data_key,
                            'class': tab_class,
                            'selector': selector
                        }
                        
                        print(f"    Tab {i}: '{tab_text.strip()}'")
                        if tab_id:
                            print(f"      ID: {tab_id}")
                        if tab_href:
                            print(f"      HREF: {tab_href}")
                        if tab_data_key:
                            print(f"      Data Key: {tab_data_key}")
                        
            except Exception as e:
                print(f"  Error with selector {selector}: {e}")
        
        # Save discoveries
        with open('reports/tab_tests/discovered_tabs.json', 'w') as f:
            json.dump(discovered_tabs, f, indent=2)
        
        print(f"\n💾 Saved to reports/tab_tests/discovered_tabs.json")
        
        # Try clicking first few tabs to test
        print("\n🧪 Testing tab clicks...")
        nav_tabs = await page.query_selector_all('a[role="tab"]')
        
        for i, tab in enumerate(nav_tabs[:5]):
            tab_text = await tab.inner_text()
            print(f"\n  Testing tab {i}: '{tab_text.strip()}'")
            try:
                await tab.click(timeout=3000)
                await asyncio.sleep(2)
                
                # Check what's visible
                page_content = await page.content()
                print(f"    ✅ Clicked successfully")
                
                # Find all buttons on this tab
                buttons = await page.query_selector_all('button:visible')
                print(f"    Found {len(buttons)} visible buttons")
                
                for j, btn in enumerate(buttons[:10]):
                    btn_id = await btn.get_attribute('id')
                    btn_text = await btn.inner_text()
                    if btn_id:
                        print(f"      Button: {btn_id} - {btn_text[:50]}")
                
            except Exception as e:
                print(f"    ❌ Click failed: {e}")
        
        print("\n👁️  Browser will stay open for 30 seconds...")
        await asyncio.sleep(30)
        
        await browser.close()

if __name__ == '__main__':
    import os
    os.makedirs('reports/tab_tests', exist_ok=True)
    asyncio.run(discover_tabs())
