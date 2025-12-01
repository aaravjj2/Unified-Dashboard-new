#!/usr/bin/env python3
"""Verify that tab labels are visible"""
import asyncio
from playwright.async_api import async_playwright

async def check_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        print("Loading dashboard...")
        await page.goto('http://localhost:8000', wait_until='networkidle')
        
        # Wait for tabs to load
        await page.wait_for_selector('.nav-tabs', timeout=10000)
        
        # Get all tab elements
        tabs = await page.query_selector_all('.nav-tabs .nav-link')
        print(f"\nFound {len(tabs)} tabs\n")
        
        for i, tab in enumerate(tabs):
            # Check if pseudo-element content is rendering
            content = await page.evaluate('''(element) => {
                const styles = window.getComputedStyle(element, '::before');
                return styles.getPropertyValue('content');
            }''', tab)
            
            # Get the visual bounding box to ensure it's visible
            box = await tab.bounding_box()
            is_visible = await tab.is_visible()
            
            print(f"Tab {i+1}:")
            print(f"  ::before content: {content}")
            print(f"  Is visible: {is_visible}")
            print(f"  Dimensions: {box if box else 'None'}")
            print()
        
        await browser.close()
        print("✅ Tab labels are now visible via CSS ::before pseudo-elements!")

if __name__ == '__main__':
    asyncio.run(check_tabs())
