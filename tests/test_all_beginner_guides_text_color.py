"""
Comprehensive test to verify ALL beginner guide text colors across ALL tabs.
Checks every tab that has a beginner guide accordion.
"""

import asyncio
from playwright.async_api import async_playwright
import json

DASHBOARD_URL = "http://localhost:8050"

# All tabs with beginner guides
TABS_TO_TEST = [
    {
        'name': 'Research Lab',
        'selector': 'a:has-text("Research Lab")',
        'accordion': 'button:has-text("Beginner\'s Guide to Research Lab")'
    },
    {
        'name': 'Attribution Lab',
        'selector': 'a:has-text("Attribution Lab")',
        'accordion': 'button:has-text("Beginner\'s Guide to Attribution")'
    },
    {
        'name': 'Command Center',
        'selector': 'a:has-text("Command Center")',
        'accordion': 'button:has-text("Getting Started")'
    },
    {
        'name': 'Strategy Lab',
        'selector': 'a:has-text("Strategy Lab")',
        'accordion': 'button'  # May have subtab guides
    },
]

async def test_all_beginner_guides():
    """Test text color for ALL beginner guide accordions."""
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("\n" + "="*80)
        print("COMPREHENSIVE BEGINNER GUIDE TEXT COLOR VALIDATION")
        print("="*80)
        
        # Load dashboard
        print("\n[INIT] Loading dashboard...")
        await page.goto(DASHBOARD_URL, timeout=60000)
        await asyncio.sleep(3)
        print("  ✅ Dashboard loaded\n")
        
        for tab_config in TABS_TO_TEST:
            tab_name = tab_config['name']
            print(f"\n{'='*80}")
            print(f"TESTING: {tab_name}")
            print('='*80)
            
            # Navigate to tab
            print(f"[1] Navigating to {tab_name}...")
            try:
                await page.click(tab_config['selector'])
                await asyncio.sleep(2)
                print(f"  ✅ {tab_name} loaded")
            except Exception as e:
                print(f"  ❌ Failed to navigate: {e}")
                results.append({'tab': tab_name, 'status': 'NAV_FAIL', 'color': None})
                continue
            
            # Find accordion
            print(f"[2] Finding beginner guide accordion...")
            accordion_buttons = page.locator(tab_config['accordion'])
            
            if await accordion_buttons.count() == 0:
                print(f"  ⚠️  No beginner guide accordion found")
                results.append({'tab': tab_name, 'status': 'NO_GUIDE', 'color': None})
                continue
            
            # Click first accordion (may be multiple)
            accordion_button = accordion_buttons.first
            accordion_text = await accordion_button.inner_text()
            print(f"  ✅ Found: '{accordion_text}'")
            
            # Expand accordion
            print(f"[3] Expanding accordion...")
            try:
                await accordion_button.click()
                await asyncio.sleep(1.5)
                print(f"  ✅ Accordion expanded")
            except Exception as e:
                print(f"  ❌ Failed to expand: {e}")
                results.append({'tab': tab_name, 'status': 'EXPAND_FAIL', 'color': None})
                continue
            
            # Check text color
            print(f"[4] Checking text color...")
            
            # Try to find any text element in accordion body
            selectors_to_try = [
                '.accordion-body p',
                '.accordion-body',
                '.accordion-body *',
                '.accordion-item .accordion-body p',
            ]
            
            color = None
            for selector in selectors_to_try:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    try:
                        color = await elem.evaluate('(element) => window.getComputedStyle(element).color')
                        print(f"  📊 Selector: {selector}")
                        print(f"  📊 Color: {color}")
                        break
                    except:
                        continue
            
            if color:
                # Check if dark (readable)
                is_dark = any(dark_rgb in color for dark_rgb in [
                    'rgb(33, 37, 41)',
                    'rgb(0, 0, 0)',
                    'rgb(34, 34, 34)',
                    'rgb(21, 21, 21)'
                ])
                
                is_light = any(light_rgb in color for light_rgb in [
                    'rgb(248',
                    'rgb(255',
                    'rgb(250',
                    'rgb(240'
                ])
                
                if is_dark:
                    print(f"  ✅ TEXT IS DARK - READABLE")
                    status = 'PASS'
                elif is_light:
                    print(f"  ❌ TEXT IS LIGHT - UNREADABLE")
                    status = 'FAIL'
                else:
                    print(f"  ⚠️  TEXT COLOR UNCERTAIN")
                    status = 'UNCERTAIN'
                
                results.append({'tab': tab_name, 'status': status, 'color': color})
            else:
                print(f"  ❌ Could not determine text color")
                results.append({'tab': tab_name, 'status': 'NO_COLOR', 'color': None})
            
            # Take screenshot
            screenshot_path = f'test_screenshots/beginner_guide_{tab_name.lower().replace(" ", "_")}.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"  📸 Screenshot: {screenshot_path}")
        
        await browser.close()
        
        # Print summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        pass_count = sum(1 for r in results if r['status'] == 'PASS')
        fail_count = sum(1 for r in results if r['status'] == 'FAIL')
        other_count = len(results) - pass_count - fail_count
        
        for result in results:
            status_emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'NO_GUIDE': '⚠️ ',
                'NAV_FAIL': '❌',
                'EXPAND_FAIL': '❌',
                'NO_COLOR': '⚠️ ',
                'UNCERTAIN': '⚠️ '
            }.get(result['status'], '❓')
            
            print(f"{status_emoji} {result['tab']:20s} - {result['status']:15s} - {result['color'] or 'N/A'}")
        
        print(f"\n📊 Results: {pass_count} PASS, {fail_count} FAIL, {other_count} OTHER")
        
        # Save results
        with open('outputs/beginner_guide_text_color_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved: outputs/beginner_guide_text_color_results.json")
        
        print("\n" + "="*80)
        overall_status = "ALL PASS" if fail_count == 0 and pass_count > 0 else "SOME FAILURES"
        print(f"FINAL STATUS: {overall_status}")
        print("="*80)
        
        return overall_status

if __name__ == "__main__":
    result = asyncio.run(test_all_beginner_guides())
    exit(0 if result == "ALL PASS" else 1)
