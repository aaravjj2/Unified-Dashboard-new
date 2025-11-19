#!/usr/bin/env python3
"""
Debug specific failing subtabs
"""

import asyncio
from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8051"

async def debug_failing_subtabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        await page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_selector("#dashboard-tabs", state="visible", timeout=10000)
        
        print("🔍 Investigating Azure ML Lab → Performance")
        await page.click("#tab-azure_ml_lab", timeout=15000)
        await asyncio.sleep(2)
        
        # Find all subtab links
        subtabs = await page.query_selector_all("a[role='tab']")
        print(f"\n📋 Azure ML Lab subtabs found: {len(subtabs)}")
        for idx, tab in enumerate(subtabs):
            text = await tab.text_content()
            classes = await tab.get_attribute("class")
            print(f"  {idx}. '{text}' | Classes: {classes}")
        
        # Try to click "Performance"
        print("\n🎯 Attempting to click 'Performance' subtab:")
        selectors = [
            "a[role='tab']:has-text('Performance')",
            "a[role='tab']:has-text('📈 Performance')",
            "a.nav-link:has-text('Performance')"
        ]
        
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    text = await elem.text_content()
                    print(f"  ✅ Found with '{sel}': text='{text}'")
                    await elem.click(timeout=5000)
                    await asyncio.sleep(2)
                    print(f"  ✅ Click successful!")
                    break
                else:
                    print(f"  ❌ Not found: {sel}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print("\n" + "="*60)
        print("🔍 Investigating Volatility Lab failing subtabs")
        await page.click("#tab-volatility_lab", timeout=15000)
        await asyncio.sleep(2)
        
        subtabs = await page.query_selector_all("a[role='tab']")
        print(f"\n📋 Volatility Lab subtabs found: {len(subtabs)}")
        for idx, tab in enumerate(subtabs):
            text = await tab.text_content()
            classes = await tab.get_attribute("class")
            is_visible = await tab.is_visible()
            print(f"  {idx}. '{text}' | Visible: {is_visible} | Classes: {classes}")
        
        # Try to click failing subtabs
        failing_names = ["Correlation", "Factor Analytics", "Advanced Charts", "Metrics Table", "Custom Scenarios"]
        
        for name in failing_names:
            print(f"\n🎯 Testing '{name}':")
            selectors = [
                f"a[role='tab']:has-text('{name}')",
                f"a.nav-link:has-text('{name}')"
            ]
            
            found = False
            for sel in selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem:
                        is_visible = await elem.is_visible()
                        text = await elem.text_content()
                        print(f"  ✅ Found: text='{text}', visible={is_visible}")
                        if is_visible:
                            await elem.click(timeout=5000)
                            await asyncio.sleep(1)
                            print(f"  ✅ Click successful!")
                        else:
                            print(f"  ⚠️  Element not visible!")
                        found = True
                        break
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            if not found:
                print(f"  ❌ Not found with any selector")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_failing_subtabs())
