"""
Detailed content inspection for Market Trends and Research Lab
"""
import asyncio
from playwright.async_api import async_playwright

async def inspect_content():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        await page.goto("http://127.0.0.1:8051", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        print("="*80)
        print("MARKET TRENDS TAB INSPECTION")
        print("="*80)
        
        # Click Market Trends
        mt_tab = page.locator('.nav-item:has-text("Market Trends")').first
        await mt_tab.click()
        await page.wait_for_timeout(3000)
        
        # Find active tab content
        print("\n🔍 Looking for active tab content...")
        
        # Try to find the content area
        content_selectors = [
            ('#market-trends', 'ID: market-trends'),
            ('.tab-pane.active', 'Active tab pane'),
            ('[role="tabpanel"]', 'Tab panel role'),
            ('[id^="market"]', 'IDs starting with "market"')
        ]
        
        for selector, desc in content_selectors:
            try:
                elements = await page.locator(selector).all()
                print(f"\n{desc} ({selector}): {len(elements)} found")
                for i, el in enumerate(elements[:3]):
                    try:
                        visible = await el.is_visible()
                        text = await el.inner_text()
                        print(f"  [{i+1}] Visible: {visible} | Text preview: {text[:100]}")
                    except:
                        print(f"  [{i+1}] Could not inspect")
            except Exception as e:
                print(f"{desc}: {e}")
        
        # Screenshot
        await page.screenshot(path="screenshots/mt_detailed.png")
        print("\n📸 Screenshot saved: mt_detailed.png")
        
        print("\n" + "="*80)
        print("RESEARCH LAB TAB INSPECTION")
        print("="*80)
        
        # Click Research Lab
        rl_tab = page.locator('.nav-item:has-text("Research Lab")').first
        await mt_tab.click()
        await page.wait_for_timeout(3000)
        
        # Find active tab content
        print("\n🔍 Looking for Research Lab content...")
        
        content_selectors = [
            ('#research-lab-container', 'ID: research-lab-container'),
            ('#research-lab', 'ID: research-lab'),
            ('.tab-pane.active', 'Active tab pane'),
            ('[id^="research"]', 'IDs starting with "research"'),
            ('[id*="brief"]', 'IDs containing "brief"')
        ]
        
        for selector, desc in content_selectors:
            try:
                elements = await page.locator(selector).all()
                print(f"\n{desc} ({selector}): {len(elements)} found")
                for i, el in enumerate(elements[:3]):
                    try:
                        visible = await el.is_visible()
                        text = await el.inner_text()
                        print(f"  [{i+1}] Visible: {visible} | Text preview: {text[:100]}")
                    except:
                        print(f"  [{i+1}] Could not inspect")
            except Exception as e:
                print(f"{desc}: {e}")
        
        # Screenshot
        await page.screenshot(path="screenshots/rl_detailed.png")
        print("\n📸 Screenshot saved: rl_detailed.png")
        
        print("\n⏸️  Keeping browser open for inspection (30s)...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_content())
