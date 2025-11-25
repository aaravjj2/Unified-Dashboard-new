"""
Final verification - Command Center with NO placeholders
"""
import asyncio
from playwright.async_api import async_playwright

async def final_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("=" * 80)
        print("FINAL VERIFICATION - Command Center NO Placeholders")
        print("=" * 80)
        
        # Load dashboard
        print("\n[1/3] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        print("✓ Dashboard loaded")
        
        # Get page text
        page_text = await page.evaluate("() => document.body.innerText")
        
        # Check for ALL old placeholder values
        placeholders_found = {
            '$125,430.50': '$125,430.50' in page_text,
            '$2,340.20': '$2,340.20' in page_text,
            '4,567.80': '4,567.80' in page_text,
            '14,234.50': '14,234.50' in page_text,
            '35,678.90': '35,678.90' in page_text,
            '$178.50': '$178.50' in page_text,
            '$242.80': '$242.80' in page_text,
        }
        
        print("\n[2/3] Checking for placeholder values...")
        for placeholder, found in placeholders_found.items():
            status = "✗ FOUND" if found else "✓ REMOVED"
            print(f"  {status}: {placeholder}")
        
        # Capture screenshot
        print("\n[3/3] Capturing final screenshot...")
        await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_command_center_clean.png', full_page=True)
        print("✓ Screenshot saved")
        
        await browser.close()
        
        all_removed = not any(placeholders_found.values())
        
        print("\n" + "=" * 80)
        print("VERIFICATION RESULT")
        print("=" * 80)
        if all_removed:
            print("✅ SUCCESS: All placeholders removed!")
        else:
            print("❌ FAILURE: Some placeholders still present")
            print("Remaining:", [k for k, v in placeholders_found.items() if v])

if __name__ == '__main__':
    asyncio.run(final_verification())
