#!/usr/bin/env python3
"""
Options Lab Clicker Test - Verify tabs visually

Simple test to click through Options Lab tabs and capture screenshots.

Author: Options Lab Enhancement Phase
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright


BASE_URL = "http://localhost:8051"
SCREENSHOT_DIR = Path("/tmp/options_lab_clicker")


async def main():
    """Click through Options Lab and capture screenshots."""
    print("=" * 60)
    print("🖱️ OPTIONS LAB CLICKER TEST")
    print("=" * 60)
    
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            # Navigate to dashboard
            print("\n1. Navigating to dashboard...")
            await page.goto(BASE_URL)
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCREENSHOT_DIR / "01_dashboard_home.png"))
            
            # Click Options Lab tab
            print("2. Clicking Options Lab tab...")
            
            # Find all nav links and click Options Lab
            nav_links = await page.query_selector_all(".nav-link, .nav-item a, button.nav-link")
            for link in nav_links:
                text = await link.inner_text()
                if "Options" in text or "📊" in text:
                    await link.click()
                    await page.wait_for_timeout(2000)
                    print(f"   Clicked: {text}")
                    break
            
            await page.screenshot(path=str(SCREENSHOT_DIR / "02_options_lab.png"))
            
            # Find all subtabs within Options Lab
            print("3. Looking for Options Lab subtabs...")
            
            # Get the tabs container
            await page.wait_for_timeout(1000)
            
            # Click on subtabs by looking for .nav-link elements
            subtab_links = await page.query_selector_all("#options-subtabs .nav-link, .nav-tabs .nav-link")
            
            if not subtab_links:
                # Try alternative selector
                subtab_links = await page.query_selector_all("[role='tab'], .tab-link, button.nav-link")
            
            print(f"   Found {len(subtab_links)} subtab links")
            
            # Click each subtab
            for idx, link in enumerate(subtab_links):
                try:
                    text = await link.inner_text()
                    text = text.strip()[:30]
                    
                    print(f"   Clicking subtab {idx+1}: {text}...")
                    await link.click()
                    await page.wait_for_timeout(1500)
                    
                    # Take screenshot
                    safe_name = text.replace(" ", "_").replace("/", "_").replace("&", "and")[:20]
                    screenshot_path = SCREENSHOT_DIR / f"{idx+3:02d}_{safe_name}.png"
                    await page.screenshot(path=str(screenshot_path))
                    print(f"   ✅ Screenshot: {screenshot_path.name}")
                    
                except Exception as e:
                    print(f"   ⚠️ Error on subtab {idx+1}: {e}")
            
            # Final full page screenshot
            print("\n4. Final screenshot...")
            await page.screenshot(path=str(SCREENSHOT_DIR / "99_final_state.png"), full_page=True)
            
            print("\n" + "=" * 60)
            print("✅ CLICKER TEST COMPLETE")
            print(f"📸 Screenshots saved to: {SCREENSHOT_DIR}")
            print("=" * 60)
            
            # List screenshots
            screenshots = list(SCREENSHOT_DIR.glob("*.png"))
            print(f"\nCaptured {len(screenshots)} screenshots:")
            for ss in sorted(screenshots):
                print(f"   - {ss.name}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            await page.screenshot(path=str(SCREENSHOT_DIR / "error_state.png"))
            
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
