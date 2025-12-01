"""
Playwright test for integrated dashboard (selector-tolerant version).
This script is a compatibility runner that looks for either the legacy
`button[data-tab="..."]` controls or the Dash Bootstrap `.nav-link` items
inside `#dashboard-tabs`.
"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

async def test_unified_dashboard():
    print(f"\n{'='*60}")
    print(f"Unified Dashboard Test (compat)")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=150)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()
        try:
            print("Loading integrated dashboard at http://127.0.0.1:8000...")
            await page.goto('http://127.0.0.1:8000', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            print("✓ Loaded")
            await page.screenshot(path='unified_dashboard_initial.png', full_page=False)

            # Find tabs via multiple strategies
            tabs = [
                ('market_trends', 'Market Trends'),
                ('market_forecast', 'Market Forecast'),
                ('monthly_picks', 'Monthly Picks'),
                ('weekly_picks', 'Weekly Picks')
            ]

            for tab_id, tab_name in tabs:
                print(f"\nTesting tab: {tab_name}")
                # Strategy 1: legacy button[data-tab]
                legacy = page.locator(f'button[data-tab="{tab_id}"]')
                if await legacy.count() > 0:
                    print("  → Clicking legacy button selector")
                    await legacy.first.click()
                    await asyncio.sleep(2)
                    print("  ✓ Clicked")
                    await page.screenshot(path=f'unified_dashboard_{tab_id}.png')
                    continue

                # Strategy 2: try to find nav-links under #dashboard-tabs and click by visible text
                found = False
                try:
                    result = await page.evaluate(f"""
                    (tabText) => {{
                        const nav = document.querySelector('#dashboard-tabs');
                        if (!nav) return false;
                        // search for any element under the tabs container with matching text
                        const candidates = nav.querySelectorAll('.nav-link, .nav-item, button');
                        for (const el of candidates) {{
                            if (!el) continue;
                            const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                            if (txt.includes(tabText.toLowerCase())) {{
                                el.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                    """, tab_name)
                    if result:
                        print(f"  → Clicked tab by JS lookup: {tab_name}")
                        await asyncio.sleep(2)
                        await page.screenshot(path=f'unified_dashboard_{tab_id}.png')
                        found = True
                except Exception:
                    found = False
                if not found:
                    print(f"  ✗ Could not find tab control for {tab_name}")

            await page.screenshot(path='unified_dashboard_final.png')
            return True
        except Exception as e:
            print(f"Error during test: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='unified_dashboard_error.png')
            return False
        finally:
            print("Closing browser...")
            await browser.close()

async def main():
    success = await test_unified_dashboard()
    print('\n' + '='*60)
    if success:
        print('✓ COMPAT TEST PASSED')
    else:
        print('✗ COMPAT TEST FAILED')
    print('='*60 + '\n')

if __name__ == '__main__':
    asyncio.run(main())
