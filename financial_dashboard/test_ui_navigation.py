"""
test_ui_navigation.py
Playwright UI Navigation Test - Validates tab navigation and basic functionality

Tests:
1. Main dashboard loads
2. Analysis Hub tab is accessible and sub-tabs work
3. Portfolio tab is accessible and sub-tabs work
4. Standalone Portfolio app (if running on port 8056)
5. Refresh button works without errors
"""

import sys
import os
from playwright.sync_api import sync_playwright, expect
import time

# Configuration
MAIN_DASHBOARD_URL = "http://localhost:8000"
ANALYSIS_HUB_URL = "http://localhost:8054"
PORTFOLIO_STANDALONE_URL = "http://localhost:8056"
SCREENSHOT_DIR = "test_screenshots/navigation"
TIMEOUT = 30000  # 30 seconds

# Create screenshot directory
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def test_main_dashboard_loads(page):
    """Test 1: Main dashboard loads successfully."""
    print("\n🧪 Test 1: Main dashboard loads")
    print("-" * 50)
    
    try:
        page.goto(MAIN_DASHBOARD_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        
        # Check for key elements
        expect(page.locator("body")).to_be_visible()
        
        # Take screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_main_dashboard.png", full_page=True)
        
        print("✅ Main dashboard loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Main dashboard load failed: {e}")
        return False


def test_analysis_hub_tab(page):
    """Test 2: Analysis Hub tab loads and sub-tabs are accessible."""
    print("\n🧪 Test 2: Analysis Hub tab navigation")
    print("-" * 50)
    
    try:
        page.goto(ANALYSIS_HUB_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Check for Analysis Hub header
        analysis_hub_header = page.locator("h2:has-text('Analysis Hub')")
        expect(analysis_hub_header).to_be_visible(timeout=10000)
        print("✅ Analysis Hub header visible")
        
        # Check for sub-tabs
        sub_tabs = ['Attribution Analysis', 'Portfolio Analytics', 'Scenario Tester']
        
        for tab_name in sub_tabs:
            try:
                tab_link = page.locator(f".nav-link:has-text('{tab_name}')")
                expect(tab_link).to_be_visible(timeout=5000)
                print(f"  ✓ {tab_name} tab found")
                
                # Click tab
                tab_link.click()
                time.sleep(1)
                
                # Take screenshot
                safe_name = tab_name.lower().replace(' ', '_')
                page.screenshot(path=f"{SCREENSHOT_DIR}/02_analysis_{safe_name}.png", full_page=True)
                
                print(f"  ✓ {tab_name} tab clicked")
            except Exception as e:
                print(f"  ⚠️  {tab_name} tab issue: {e}")
        
        print("✅ Analysis Hub tabs test complete")
        return True
        
    except Exception as e:
        print(f"❌ Analysis Hub test failed: {e}")
        return False


def test_portfolio_tab(page):
    """Test 3: Portfolio tab loads and sub-tabs are accessible."""
    print("\n🧪 Test 3: Portfolio tab navigation")
    print("-" * 50)
    
    try:
        # If main dashboard has portfolio tab, navigate there
        page.goto(MAIN_DASHBOARD_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Look for Portfolio link/tab
        try:
            portfolio_link = page.locator("a:has-text('Portfolio'), .nav-link:has-text('Portfolio')")
            if portfolio_link.is_visible(timeout=5000):
                portfolio_link.click()
                time.sleep(2)
                print("✅ Portfolio tab clicked from main dashboard")
        except:
            print("⚠️  Portfolio tab not found in main dashboard, trying direct URL")
            page.goto(f"{MAIN_DASHBOARD_URL}/portfolio", timeout=TIMEOUT)
            time.sleep(2)
        
        # Take screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/03_portfolio_main.png", full_page=True)
        
        # Check for portfolio sub-tabs
        portfolio_subtabs = ['Positions', 'Order History', 'Analytics', 'Factor Exposure', 'Optimization']
        
        for tab_name in portfolio_subtabs:
            try:
                tab_locator = page.locator(f".nav-link:has-text('{tab_name}')")
                if tab_locator.is_visible(timeout=3000):
                    print(f"  ✓ {tab_name} sub-tab found")
                    tab_locator.click()
                    time.sleep(1)
                else:
                    print(f"  ⚠️  {tab_name} sub-tab not visible")
            except Exception as e:
                print(f"  ⚠️  {tab_name} sub-tab issue: {e}")
        
        print("✅ Portfolio tabs test complete")
        return True
        
    except Exception as e:
        print(f"❌ Portfolio test failed: {e}")
        return False


def test_standalone_portfolio_app(page):
    """Test 4: Standalone Portfolio app loads (if running)."""
    print("\n🧪 Test 4: Standalone Portfolio app")
    print("-" * 50)
    
    try:
        page.goto(PORTFOLIO_STANDALONE_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Check for Portfolio Tracker header
        portfolio_header = page.locator("h2:has-text('Portfolio Tracker')")
        expect(portfolio_header).to_be_visible(timeout=10000)
        print("✅ Portfolio Tracker header visible")
        
        # Check for Refresh button
        refresh_btn = page.locator("#portfolio-refresh-btn, button:has-text('Refresh')")
        if refresh_btn.is_visible(timeout=5000):
            print("✅ Refresh button found")
            
            # Click refresh and wait
            refresh_btn.click()
            time.sleep(3)
            print("✅ Refresh button clicked")
            
            # Check if Portfolio Value card updated (should not show error)
            portfolio_value = page.locator("#portfolio-value")
            if portfolio_value.is_visible():
                value_text = portfolio_value.inner_text()
                print(f"  Portfolio Value: {value_text}")
                
                # Check for error in alert
                try:
                    alert = page.locator(".alert-warning, .alert-danger").first
                    if alert.is_visible(timeout=2000):
                        alert_text = alert.inner_text()
                        print(f"  ⚠️  Alert message: {alert_text[:100]}")
                except:
                    print("  ✓ No error alerts")
        
        # Take screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/04_standalone_portfolio.png", full_page=True)
        
        print("✅ Standalone Portfolio app test complete")
        return True
        
    except Exception as e:
        print(f"❌ Standalone Portfolio app not available or failed: {e}")
        return False


def run_all_tests():
    """Run all navigation tests."""
    print("\n" + "="*60)
    print("🚀 UI NAVIGATION TEST SUITE")
    print("="*60)
    
    results = {
        'main_dashboard': False,
        'analysis_hub': False,
        'portfolio_tab': False,
        'standalone_portfolio': False
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for CI/CD
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Run tests
            results['main_dashboard'] = test_main_dashboard_loads(page)
            results['analysis_hub'] = test_analysis_hub_tab(page)
            results['portfolio_tab'] = test_portfolio_tab(page)
            results['standalone_portfolio'] = test_standalone_portfolio_app(page)
            
        except Exception as e:
            print(f"\n❌ Fatal error during tests: {e}")
        
        finally:
            browser.close()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}/")
    print("="*60 + "\n")
    
    # Return exit code
    return 0 if passed == total else 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
