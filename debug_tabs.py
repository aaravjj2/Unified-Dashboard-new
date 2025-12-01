"""Debug: Check what tabs exist on the page"""
import asyncio
from playwright.async_api import async_playwright

async def debug_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("Loading dashboard...")
        await page.goto("http://localhost:8050/", wait_until="networkidle")
        await asyncio.sleep(10)
        
        # Find all buttons and links
        print("\nAll buttons on page:")
        buttons = await page.locator('button').all_text_contents()
        for i, btn_text in enumerate(buttons[:20]):
            if btn_text.strip():
                print(f"  {i+1}. '{btn_text}'")
        
        print("\nSearching for 'Vol' in page content...")
        vol_elements = await page.locator('text=/vol/i').all_text_contents()
        for elem in vol_elements[:10]:
            print(f"  - {elem}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_tabs())
