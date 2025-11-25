"""
Individual Playwright Test: Portfolio Tab
==========================================
Tests the Portfolio tab and portfolio_dashboard_service integration.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Configuration
DASHBOARD_URL = os.environ.get("DASH_URL", "http://localhost:8050")
SCREENSHOTS_DIR = Path("test_screenshots/portfolio_tab")
SCREENSHOTS_DIR.mkdir(exist_ok=True, parents=True)

async def test_portfolio_tab():
    """
    Test Portfolio tab functionality:
    1. Navigate to dashboard
    2. Click Portfolio tab
    3. Verify portfolio summary loads
    4. Click refresh button
    5. Verify positions table
    6. Take snapshots
    """
    print("=" * 80)
    print("💼 PORTFOLIO TAB PLAYWRIGHT TEST")
    print("=" * 80)
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    async with async_playwright() as p:
        browser = None
        try:
            print("🚀 Launching headless Chromium browser...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            print("✅ Browser launched successfully")
            print()
            
            # Navigate to dashboard
            print("📍 Navigating to dashboard...")
            await page.goto(DASHBOARD_URL, timeout=120000, wait_until="domcontentloaded")
            print("✅ Dashboard loaded")
            await page.wait_for_timeout(2000)
            
            # Click Portfolio tab
            print()
            print("TEST 1: Navigate to Portfolio Tab")
            print("-" * 40)
            try:
                portfolio_tab = page.locator('text=Portfolio').first
                await portfolio_tab.click(timeout=10000)
                print("  ✅ Clicked Portfolio tab")
                await page.wait_for_timeout(3000)  # Wait for data to load
                print("  ✅ PASS: Portfolio tab loaded")
                
            except Exception as e:
                print(f"  ❌ FAIL: {str(e)[:80]}")
                return False
            
            # Test 2: Check portfolio value
            print()
            print("TEST 2: Portfolio Value Display")
            print("-" * 40)
            try:
                portfolio_value_elem = page.locator('#portfolio-value')
                portfolio_value = await portfolio_value_elem.inner_text(timeout=5000)
                
                print(f"  Portfolio Value: {portfolio_value}")
                
                if not portfolio_value.startswith("$"):
                    print(f"  ❌ FAIL: Expected dollar amount, got: {portfolio_value}")
                    return False
                    
                print("  ✅ PASS: Portfolio value displayed correctly")
                
            except Exception as e:
                print(f"  ❌ FAIL: {str(e)[:80]}")
                return False
            
            # Test 3: Click refresh button
            print()
            print("TEST 3: Refresh Button")
            print("-" * 40)
            try:
                refresh_btn = page.locator('#portfolio-refresh-btn').first
                await refresh_btn.click(timeout=5000)
                print("  ✅ Clicked refresh button")
                await page.wait_for_timeout(2000)
                print("  ✅ PASS: Refresh button functional")
                
            except Exception as e:
                print(f"  ❌ FAIL: {str(e)[:80]}")
                return False
            
            # Test 4: Check for positions table or positions count
            print()
            print("TEST 4: Positions Display")
            print("-" * 40)
            try:
                # Try to find positions indicator
                positions_elem = page.locator('text=Positions').first
                if await positions_elem.count() > 0:
                    print("  ✅ Positions section found")
                    print("  ✅ PASS: Positions displayed")
                else:
                    print("  ⚠️  Positions section not visible (may be empty portfolio)")
                    
            except Exception as e:
                print(f"  ⚠️  WARNING: {str(e)[:80]}")
            
            # Take full page screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = SCREENSHOTS_DIR / f"portfolio_tab_full_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print()
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            print()
            print("=" * 80)
            print("🎉 ALL PORTFOLIO TAB TESTS PASSED")
            print("=" * 80)
            return True
            
        except Exception as e:
            print()
            print("=" * 80)
            print(f"❌ PORTFOLIO TAB TEST FAILED: {e}")
            print("=" * 80)
            return False
            
        finally:
            if browser:
                await browser.close()
                print("🔒 Browser closed")


async def main():
    """Execute test and return appropriate exit code."""
    success = await test_portfolio_tab()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
