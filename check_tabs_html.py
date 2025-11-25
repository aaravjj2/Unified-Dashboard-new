"""
Check HTML structure of tabs
"""
import asyncio
from playwright.async_api import async_playwright

async def check_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8051')
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Get tabs container HTML
        tabs_html = await page.locator('#dashboard-tabs').inner_html()
        
        # Save to file for inspection
        with open('/tmp/tabs_html.html', 'w') as f:
            f.write(tabs_html)
        
        print("📄 Tabs HTML saved to /tmp/tabs_html.html")
        print("\nFirst 2000 characters:")
        print(tabs_html[:2000])
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(check_html())
