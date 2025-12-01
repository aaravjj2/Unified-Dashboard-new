"""
Simple tab finder using exact selectors
"""
import asyncio
from playwright.async_api import async_playwright

async def find_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        await page.goto("http://127.0.0.1:8051", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Take screenshot
        await page.screenshot(path="screenshots/debug_page.png", full_page=True)
        print("📸 Screenshot saved: screenshots/debug_page.png")
        
        # Check for tabs container
        print("\n🔍 Looking for tab structures...")
        
        # Try different selectors
        selectors = [
            ('dbc.Tabs', '.tab'),
            ('Nav tabs', '.nav-tabs'),
            ('Tab buttons', 'button[role="tab"]'),
            ('Tab items', '.nav-item'),
            ('Market Trends text', 'text=Market Trends'),
            ('Research Lab text', 'text=Research Lab'),
            ('Any tabs', '[id^="tab-"]')
        ]
        
        for name, selector in selectors:
            try:
                elements = await page.locator(selector).all()
                print(f"\n{name} ({selector}): Found {len(elements)} elements")
                if elements:
                    for i, el in enumerate(elements[:5]):
                        try:
                            text = await el.inner_text()
                            visible = await el.is_visible()
                            print(f"  [{i+1}] Text: '{text[:50]}' | Visible: {visible}")
                        except:
                            print(f"  [{i+1}] Could not get text")
            except Exception as e:
                print(f"{name}: Error - {e}")
        
        # Get page HTML snippet
        print("\n🔍 Checking page structure...")
        body_html = await page.locator('body').inner_html()
        
        # Check for key markers
        markers = ["market_trends", "research_lab", "Market Trends", "Research Lab", "tab-container"]
        for marker in markers:
            if marker in body_html:
                print(f"✅ Found '{marker}' in HTML")
            else:
                print(f"❌ '{marker}' NOT in HTML")
        
        print("\n⏸️  Browser open for inspection (30s)...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_tabs())
