"""
Command Center E2E Tests
=========================
Tests for Command Center tab functionality:
- Portfolio Value loading
- Today's P/L display
- Market Status
- Quick Stats cards
"""
import json
import time
from playwright.sync_api import sync_playwright, Page, expect
from config import DASHBOARD_URL, TEST_AREAS, TIMEOUT, HEADLESS, VIEWPORT_WIDTH, VIEWPORT_HEIGHT


def extract_command_center_data(page: Page) -> dict:
    """Extract all relevant data from Command Center UI."""
    data = {
        "timestamp": time.time(),
        "url": page.url,
        "status": "success",
        "data": {}
    }
    
    try:
        # Portfolio Value (home_v2.py)
        portfolio_value_el = page.locator("#home-portfolio-value-quick").first
        if portfolio_value_el.count() > 0:
            data["data"]["portfolioValue"] = portfolio_value_el.inner_text().strip()
        else:
            data["data"]["portfolioValue"] = "--"
        
        # Today's P/L (home_v2.py)
        pnl_el = page.locator("#home-pnl-quick").first
        if pnl_el.count() > 0:
            data["data"]["todaysPnL"] = pnl_el.inner_text().strip()
        else:
            data["data"]["todaysPnL"] = "--"
        
        # Market Status (home_v2.py)
        market_status_el = page.locator("#home-market-status-quick").first
        if market_status_el.count() > 0:
            data["data"]["marketStatus"] = market_status_el.inner_text().strip()
        else:
            data["data"]["marketStatus"] = "Unknown"
        
        # Quick Stats (Win Rate, Avg Trade Duration, etc.)
        quick_stats = {}
        for stat_id in ["win-rate", "avg-trade-duration", "volatility-percentile"]:
            el = page.locator(f"#{stat_id}, [id*='{stat_id}']").first
            if el.count() > 0:
                quick_stats[stat_id] = el.inner_text().strip()
            else:
                quick_stats[stat_id] = "--"
        data["data"]["quickStats"] = quick_stats
        
        # Check for loading states
        loading_elements = page.locator(".loading, .spinner, [class*='loading']").count()
        data["data"]["loadingVisible"] = loading_elements > 0
        
        # Check for error states
        error_elements = page.locator(".error, .alert-danger, [class*='error']").count()
        data["data"]["errorVisible"] = error_elements > 0
        
        print(f"✅ Extracted Command Center data:")
        print(f"   Portfolio Value: {data['data']['portfolioValue']}")
        print(f"   Today's P/L: {data['data']['todaysPnL']}")
        print(f"   Market Status: {data['data']['marketStatus']}")
        
    except Exception as e:
        data["status"] = "error"
        data["error"] = str(e)
        print(f"❌ Error extracting data: {e}")
    
    return data


def test_command_center():
    """Main test function for Command Center."""
    config = TEST_AREAS["command_center"]
    
    print("="*70)
    print("COMMAND CENTER E2E TEST")
    print("="*70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        
        try:
            # Navigate to dashboard
            print(f"\n[1] Loading dashboard: {DASHBOARD_URL}")
            page.goto(DASHBOARD_URL, timeout=TIMEOUT)
            page.wait_for_load_state("networkidle", timeout=TIMEOUT)
            time.sleep(2)
            
            # Click Command Center tab
            print("\n[2] Clicking Command Center tab...")
            cc_tab = page.locator(f"text={config['tab_text']}").first
            if cc_tab.is_visible():
                cc_tab.click()
                time.sleep(3)
                print("   ✓ Command Center tab clicked")
            else:
                print("   ⚠️  Command Center tab not found (may be default active)")
            
            # Extract data
            print("\n[3] Extracting Command Center data...")
            test_data = extract_command_center_data(page)
            
            # Save to JSON
            output_file = config["output_file"]
            with open(output_file, 'w') as f:
                json.dump(test_data, f, indent=2)
            print(f"\n   ✅ Test data saved: {output_file}")
            
            # Screenshot
            screenshot_path = output_file.parent / "command-center-screenshot.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"   📸 Screenshot saved: {screenshot_path}")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        finally:
            browser.close()
    
    print("\n" + "="*70)
    print("✅ COMMAND CENTER TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_command_center()
