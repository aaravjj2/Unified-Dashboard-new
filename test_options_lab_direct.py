#!/usr/bin/env python3
"""
Options Lab Direct Test - Navigate directly to Options Lab tabs

Tests the Options Lab tab specifically with direct navigation.

Author: Options Lab Enhancement Phase
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright


BASE_URL = "http://localhost:8051"
SCREENSHOT_DIR = Path("/tmp/options_lab_direct")


async def main():
    """Navigate directly to Options Lab and test subtabs."""
    print("=" * 60)
    print("🎯 OPTIONS LAB DIRECT TEST")
    print("=" * 60)
    
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        # Navigate to dashboard
        print("\n1. Navigating to dashboard...")
        await page.goto(BASE_URL)
        await page.wait_for_timeout(5000)  # Wait for full load
        await page.screenshot(path=str(SCREENSHOT_DIR / "01_home.png"))
        
        # Find and click Options Lab tab specifically
        print("2. Looking for Options Lab tab...")
        
        # Get all nav links
        nav_items = await page.query_selector_all("a.nav-link, button.nav-link")
        
        options_lab_found = False
        for item in nav_items:
            try:
                text = await item.inner_text()
                if "Options Lab" in text:
                    print(f"   Found Options Lab tab: '{text}'")
                    await item.click()
                    await page.wait_for_timeout(3000)
                    options_lab_found = True
                    break
            except Exception as e:
                continue
        
        if not options_lab_found:
            print("   ⚠️ Options Lab tab not found, trying index-based approach...")
            # Try clicking by tab index (Options Lab is typically tab 5)
            all_tabs = await page.query_selector_all(".nav-link")
            if len(all_tabs) >= 6:
                for idx, tab in enumerate(all_tabs[:10]):
                    try:
                        text = await tab.inner_text()
                        print(f"   Tab {idx}: {text[:30]}")
                    except Exception as e:
                        pass
        
        await page.screenshot(path=str(SCREENSHOT_DIR / "02_options_lab_main.png"))
        
        # Now find subtabs within Options Lab
        print("\n3. Looking for Options Lab subtabs...")
        
        # Wait for Options Lab content to load
        await page.wait_for_timeout(2000)
        
        # Find the Options Lab subtabs container
        subtabs_container = await page.query_selector("#options-subtabs")
        
        if subtabs_container:
            print("   Found #options-subtabs container")
            subtab_links = await subtabs_container.query_selector_all(".nav-link")
            print(f"   Found {len(subtab_links)} subtabs")
            
            for idx, link in enumerate(subtab_links):
                try:
                    text = await link.inner_text()
                    text = text.strip()
                    print(f"   Clicking subtab: {text}...")
                    await link.click()
                    await page.wait_for_timeout(2000)
                    
                    # Screenshot
                    safe_name = text.replace(" ", "_").replace("/", "_")[:15]
                    await page.screenshot(path=str(SCREENSHOT_DIR / f"{idx+3:02d}_{safe_name}.png"))
                    print(f"   ✅ {text}")
                    
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
        else:
            print("   ⚠️ #options-subtabs container not found")
            
            # Try finding any visible tabs
            visible_tabs = await page.query_selector_all("[role='tab'], .nav-tabs .nav-link")
            print(f"   Found {len(visible_tabs)} visible tabs with alternative selector")
        
        # Final screenshot
        print("\n4. Final screenshot...")
        await page.screenshot(path=str(SCREENSHOT_DIR / "99_final.png"), full_page=True)
        
        print("\n" + "=" * 60)
        print("✅ TEST COMPLETE")
        print(f"📸 Screenshots: {SCREENSHOT_DIR}")
        print("=" * 60)
        
        # List screenshots
        for ss in sorted(SCREENSHOT_DIR.glob("*.png")):
            print(f"   {ss.name}")
        
        await page.wait_for_timeout(2000)  # Brief pause before closing
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
