"""Minimal test to click Market Trends tab and verify callback fires."""
import asyncio
from playwright.async_api import async_playwright
import time

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Loading dashboard...")
        await page.goto('http://localhost:8050', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        print("Looking for Market Trends tab...")
        tab = page.locator('a.nav-link:has-text("Market Trends")')
        count = await tab.count()
        print(f"  Found {count} tab(s)")
        
        if count > 0:
            print("Clicking Market Trends tab...")
            await tab.first.click()
            await page.wait_for_timeout(4000)
            
            print("Checking for results...")
            results_area = page.locator('#results-area')
            results_count = await results_area.count()
            print(f"  results-area elements: {results_count}")
            
            if results_count > 0:
                text = await results_area.first.text_content()
                print(f"  results-area text: {text[:200] if text else 'None'}")
            
            # Check debug log
            import os
            if os.path.exists('/tmp/tab_activate_debug.log'):
                with open('/tmp/tab_activate_debug.log') as f:
                    debug_content = f.read()
                print(f"\\nDebug log content:\\n{debug_content}")
            else:
                print("\\nNo debug log file created!")
        
        await browser.close()

asyncio.run(main())
