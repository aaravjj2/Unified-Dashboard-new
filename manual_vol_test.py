"""Simple test to manually check Volatility Lab in browser"""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        print("Loading dashboard...")
        await page.goto("http://localhost:8050/", wait_until="networkidle")
        await asyncio.sleep(10)
        
        print("Taking screenshot of homepage...")
        await page.screenshot(path="homepage.png", full_page=True)
        
        print("\nPlease manually:")
        print("1. Click on Volatility Lab tab")
        print("2. Click Quick Compute button")
        print("3. Check if ATM IV value changes from '--'")
        
        print("\nBrowser will stay open for 120 seconds...")
        await asyncio.sleep(120)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
