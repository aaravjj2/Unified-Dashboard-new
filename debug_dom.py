"""
Debug script to find actual DOM selectors
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://localhost:8053", wait_until='networkidle')
        
        # Get page HTML
        html = await page.content()
        
        # Find tab-related elements
        tab_elements = await page.query_selector_all('.nav-link, .tab-link, [role="tab"]')
        print(f"Found {len(tab_elements)} tab elements")
        
        for i, el in enumerate(tab_elements):
            text = await el.text_content()
            class_name = await el.get_attribute('class')
            tab_id = await el.get_attribute('id')
            print(f"Tab {i}: text='{text}', class='{class_name}', id='{tab_id}'")
        
        # Check for DBC Tabs
        tabs_container = await page.query_selector('.nav-tabs, .nav, [class*="tab"]')
        if tabs_container:
            inner = await tabs_container.inner_html()
            print("\nTabs container HTML:")
            print(inner[:2000])
        
        # Save full page screenshot
        await page.screenshot(path="/home/aarav/Unified-Dashboard/test_screenshots/debug_full_page.png", full_page=True)
        print("\nSaved full page screenshot to test_screenshots/debug_full_page.png")
        
        await browser.close()

asyncio.run(main())
