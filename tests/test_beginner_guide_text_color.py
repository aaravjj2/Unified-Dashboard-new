"""
Quick test to verify beginner guide text color is dark/readable.
Tests Research Lab beginner guide accordion content.
"""

import asyncio
from playwright.async_api import async_playwright
import time

DASHBOARD_URL = "http://localhost:8050"

async def test_beginner_guide_text_color():
    """Test that beginner guide text is dark and readable."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("\n" + "="*70)
        print("BEGINNER GUIDE TEXT COLOR VALIDATION")
        print("="*70)
        
        # Step 1: Load dashboard
        print("\n[1] Loading dashboard...")
        await page.goto(DASHBOARD_URL, timeout=60000)
        await asyncio.sleep(3)
        print("  ✅ Dashboard loaded")
        
        # Step 2: Navigate to Research Lab
        print("\n[2] Navigating to Research Lab...")
        await page.click('a:has-text("Research Lab")')
        await asyncio.sleep(2)
        print("  ✅ Research Lab loaded")
        
        # Step 3: Find and expand beginner guide accordion
        print("\n[3] Expanding beginner guide accordion...")
        accordion_button = page.locator('button:has-text("Beginner\'s Guide to Research Lab")').first
        
        if await accordion_button.count() > 0:
            print("  ✅ Found Research Lab beginner guide accordion button")
            
            # Click to expand
            await accordion_button.click()
            await asyncio.sleep(1.5)
            print("  ✅ Accordion expanded")
            
            # Take screenshot of expanded content
            screenshot_path = 'test_screenshots/beginner_guide_text_color.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"  ✅ Screenshot saved: {screenshot_path}")
            
            # Step 4: Check text color of markdown content
            print("\n[4] Checking text color...")
            
            # Try multiple selectors for markdown content
            selectors_to_try = [
                '.accordion-body .markdown',
                '.accordion-body [class*="markdown"]',
                '.accordion-body p',
                '.accordion-body',
                '.accordion-item .accordion-body'
            ]
            
            color = None
            found_selector = None
            
            for selector in selectors_to_try:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    color = await elem.evaluate('(element) => window.getComputedStyle(element).color')
                    found_selector = selector
                    print(f"  ✅ Found element with selector: {selector}")
                    print(f"  📊 Computed color: {color}")
                    break
            
            if color:
                # Check if color is dark (rgb should be low values for dark text)
                # Expected: rgb(33, 37, 41) or similar dark color
                # Unacceptable: rgb(248, 249, 250) or similar light color
                
                if 'rgb(33, 37, 41)' in color or 'rgb(0, 0, 0)' in color or 'rgb(34, 34, 34)' in color:
                    print("  ✅ TEXT COLOR IS DARK - READABLE")
                    result = "PASS"
                elif 'rgb(248' in color or 'rgb(255' in color or 'rgb(250' in color:
                    print("  ❌ TEXT COLOR IS LIGHT - UNREADABLE")
                    result = "FAIL"
                else:
                    print(f"  ⚠️  TEXT COLOR UNCERTAIN: {color}")
                    result = "UNCERTAIN"
            else:
                print("  ❌ Markdown element not found in accordion")
                result = "ERROR"
                
        else:
            print("  ❌ Beginner guide accordion button not found")
            result = "ERROR"
        
        await browser.close()
        
        print("\n" + "="*70)
        print(f"FINAL RESULT: {result}")
        print("="*70)
        
        return result

if __name__ == "__main__":
    result = asyncio.run(test_beginner_guide_text_color())
    exit(0 if result == "PASS" else 1)
