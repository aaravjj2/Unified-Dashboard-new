"""
Quick visual inspection script to find tab buttons
"""
import asyncio
from playwright.async_api import async_playwright

async def inspect_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("🌐 Loading dashboard...")
        await page.goto("http://127.0.0.1:8051", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Find all button elements
        print("\n🔍 Finding all visible tab buttons...")
        buttons = await page.locator('button').all()
        
        print(f"Found {len(buttons)} buttons total\n")
        
        for i, button in enumerate(buttons[:30]):  # Check first 30
            try:
                if await button.is_visible():
                    text = await button.inner_text()
                    if text.strip():
                        print(f"{i+1}. Button text: '{text.strip()}'")
            except:
                pass
        
        print("\n⏸️  Keeping browser open for 60s inspection...")
        await page.wait_for_timeout(60000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_tabs())
