#!/usr/bin/env python3
"""
Discover actual button IDs for each tab.
"""
import asyncio
from playwright.async_api import async_playwright
import json

TABS_TO_SCAN = [
    "🔬 Research Lab",
    "Market Forecast",
    "⚡ Volatility Lab",
    "Market Trends",
    "Portfolio"
]

async def scan_tab_buttons():
    """Scan each tab for buttons."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8052', wait_until='networkidle', timeout=60000)
        await page.wait_for_selector('#react-entry-point', timeout=30000)
        await asyncio.sleep(3)
        
        all_buttons = {}
        
        for tab_text in TABS_TO_SCAN:
            print(f"\n{'='*80}")
            print(f"📋 Scanning tab: {tab_text}")
            print(f"{'='*80}")
            
            # Click tab
            try:
                await page.click(f'a[role="tab"]:has-text("{tab_text}")', timeout=10000)
                await asyncio.sleep(3)
                print(f"  ✅ Switched to tab")
            except Exception as e:
                print(f"  ❌ Failed to switch: {e}")
                continue
            
            # Find all buttons
            buttons = await page.query_selector_all('button')
            print(f"  Found {len(buttons)} total buttons")
            
            tab_buttons = []
            
            for i, btn in enumerate(buttons):
                btn_id = await btn.get_attribute('id')
                btn_text = (await btn.inner_text()).strip()
                is_visible = await btn.is_visible()
                btn_class = await btn.get_attribute('class')
                
                if is_visible and btn_id:
                    tab_buttons.append({
                        'id': btn_id,
                        'text': btn_text[:100],
                        'visible': is_visible,
                        'class': btn_class
                    })
                    print(f"    Button: {btn_id}")
                    if btn_text:
                        print(f"      Text: {btn_text[:50]}")
            
            all_buttons[tab_text] = tab_buttons
            print(f"  📊 {len(tab_buttons)} visible buttons with IDs")
        
        # Save
        with open('reports/tab_tests/button_scan.json', 'w') as f:
            json.dump(all_buttons, f, indent=2)
        
        print(f"\n💾 Saved to reports/tab_tests/button_scan.json")
        print("\n👁️  Browser will stay open for 15 seconds...")
        await asyncio.sleep(15)
        
        await browser.close()
        
        # Print summary
        print(f"\n{'='*80}")
        print("📊 BUTTON SUMMARY")
        print(f"{'='*80}")
        for tab, buttons in all_buttons.items():
            print(f"\n{tab}:")
            for btn in buttons[:10]:
                print(f"  - {btn['id']}: {btn['text'][:40]}")

if __name__ == '__main__':
    import os
    os.makedirs('reports/tab_tests', exist_ok=True)
    asyncio.run(scan_tab_buttons())
