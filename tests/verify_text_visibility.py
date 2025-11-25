#!/usr/bin/env python3
"""
Text Visibility Verification Test

Checks that all text elements across dashboard tabs have proper black styling.
Uses Playwright to capture screenshots and verify no white-on-white text.

Author: Autonomous Lead Engineer (Agent v2)
Date: October 28, 2025
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8050"
SCREENSHOT_DIR = Path("test_screenshots/text_visibility")

# Tabs to verify
TABS_TO_CHECK = [
    ("home-lab-tab", "Home Lab"),
    ("attribution-lab-tab", "Attribution Lab"),
    ("strategy-lab-tab", "Strategy Lab"),
    ("options-lab-tab", "Options Lab"),
    ("portfolio-tab", "Portfolio"),
    ("research-lab-tab", "Research Lab"),
]

async def check_text_visibility(page, tab_id, tab_name):
    """
    Navigate to tab and verify text elements have black color.
    """
    results = {
        'tab_id': tab_id,
        'tab_name': tab_name,
        'status': 'PASS',
        'issues': [],
        'screenshot': None
    }
    
    try:
        print(f"\n📍 Checking {tab_name}...")
        
        # Click tab (handle both button and link selectors)
        try:
            await page.click(f'[id="{tab_id}"]', timeout=3000)
        except:
            try:
                await page.click(f'[data-tab="{tab_id}"]', timeout=3000)
            except:
                await page.click(f'a:has-text("{tab_name}")', timeout=3000)
        
        await page.wait_for_timeout(2000)
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / f"{tab_id.replace('-', '_')}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        results['screenshot'] = str(screenshot_path)
        print(f"  📸 Screenshot: {screenshot_path}")
        
        # Check for text-muted classes (should not exist)
        text_muted_elements = await page.query_selector_all('.text-muted')
        if text_muted_elements:
            # Check if they have inline style override
            for elem in text_muted_elements:
                style = await elem.get_attribute('style')
                if not style or 'color' not in style:
                    results['status'] = 'FAIL'
                    results['issues'].append(f"Found .text-muted without style override")
                    print(f"  ❌ Found text-muted element without color override")
        
        # Check for white text (color: #fff or color: white)
        white_text = await page.query_selector_all('[style*="color: #fff"], [style*="color: white"], [style*="color:#fff"], [style*="color:white"]')
        if white_text:
            results['status'] = 'FAIL'
            results['issues'].append(f"Found {len(white_text)} white text elements")
            print(f"  ❌ Found {len(white_text)} white text elements")
        
        # Check for explicit black text
        black_text = await page.query_selector_all('[style*="color: #000"], [style*="color:#000"], [style*="color: black"]')
        print(f"  ✅ Found {len(black_text)} explicit black text elements")
        
        if results['status'] == 'PASS':
            print(f"  ✅ {tab_name}: All text visible")
        
    except Exception as e:
        results['status'] = 'ERROR'
        results['issues'].append(str(e))
        print(f"  ❌ ERROR: {e}")
    
    return results

async def main():
    print("=" * 70)
    print("TEXT VISIBILITY VERIFICATION TEST")
    print("=" * 70)
    
    # Create screenshot directory
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Navigate to dashboard
        print(f"\n🌐 Navigating to {DASHBOARD_URL}...")
        try:
            await page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=30000)
            print("✅ Dashboard loaded")
        except Exception as e:
            print(f"❌ Failed to load dashboard: {e}")
            await browser.close()
            return
        
        # Wait for initial render
        await page.wait_for_timeout(3000)
        
        # Check each tab
        for tab_id, tab_name in TABS_TO_CHECK:
            result = await check_text_visibility(page, tab_id, tab_name)
            all_results.append(result)
        
        await browser.close()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in all_results if r['status'] == 'PASS')
    failed = sum(1 for r in all_results if r['status'] == 'FAIL')
    errors = sum(1 for r in all_results if r['status'] == 'ERROR')
    
    print(f"✅ PASSED: {passed}/{len(all_results)}")
    print(f"❌ FAILED: {failed}/{len(all_results)}")
    print(f"⚠️  ERRORS: {errors}/{len(all_results)}")
    print()
    
    # Failed tabs details
    if failed > 0 or errors > 0:
        print("ISSUES FOUND:")
        for r in all_results:
            if r['status'] != 'PASS':
                print(f"\n{r['tab_name']} ({r['status']}):")
                for issue in r['issues']:
                    print(f"  - {issue}")
    
    # Save results
    results_file = Path("outputs/text_visibility_verification.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📄 Full results: {results_file}")
    print(f"📸 Screenshots: {SCREENSHOT_DIR}")
    print()
    
    # Exit code
    return 0 if (failed == 0 and errors == 0) else 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
