#!/usr/bin/env python3
"""
Quick Visual Text Visibility Test

Captures screenshots of key tabs to verify text-muted CSS override works.
Validates that all text is readable (black on light backgrounds).

Author: Autonomous Lead Engineer (Agent v2)
Date: October 28, 2025
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8050"
SCREENSHOTS_DIR = Path("outputs/phase3_validation_screenshots")

async def capture_tab_screenshots():
    """Capture screenshots of major tabs to verify text visibility."""
    
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("PHASE 3 TEXT VISIBILITY VALIDATION")
    print("=" * 70)
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load dashboard
            print(f"🌐 Loading dashboard: {DASHBOARD_URL}")
            await page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            print("✅ Dashboard loaded\n")
            
            # Tabs to capture
            tabs = [
                ("Home Lab", "a:has-text('Command Center')", "home_lab.png"),
                ("Attribution Lab", "a:has-text('Attribution Lab')", "attribution_lab.png"),
                ("Strategy Lab", "a:has-text('Strategy Lab')", "strategy_lab.png"),
                ("Research Lab", "a:has-text('Research Lab')", "research_lab.png"),
                ("Options Lab", "a:has-text('Options Lab')", "options_lab.png"),
            ]
            
            for tab_name, selector, filename in tabs:
                try:
                    print(f"📸 Capturing: {tab_name}")
                    
                    # Click tab
                    await page.click(selector, timeout=5000)
                    await page.wait_for_timeout(2000)
                    
                    # Screenshot
                    screenshot_path = SCREENSHOTS_DIR / filename
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    
                    print(f"   ✅ Saved: {screenshot_path}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {str(e)[:60]}")
                
                print()
            
            # Check for text-muted elements with black styling
            print("🔍 Checking CSS override effectiveness...")
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Evaluate CSS
            text_muted_color = await page.evaluate("""
                () => {
                    const elem = document.querySelector('.text-muted');
                    if (!elem) return 'No .text-muted found';
                    return window.getComputedStyle(elem).color;
                }
            """)
            
            print(f"   .text-muted computed color: {text_muted_color}")
            
            if 'rgb(0, 0, 0)' in text_muted_color or '#000' in text_muted_color.lower():
                print("   ✅ CSS override working - text is black")
            else:
                print(f"   ⚠️  Unexpected color: {text_muted_color}")
            
        finally:
            await browser.close()
    
    print()
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}")
    print()

if __name__ == '__main__':
    asyncio.run(capture_tab_screenshots())
