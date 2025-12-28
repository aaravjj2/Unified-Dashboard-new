"""
Options Lab E2E Tests
======================
Tests for Options Lab chain viewer and Greeks calculator.
"""
import json
import time
from playwright.sync_api import sync_playwright, Page
from config import DASHBOARD_URL, TEST_AREAS, TIMEOUT, HEADLESS, VIEWPORT_WIDTH, VIEWPORT_HEIGHT


def extract_options_data(page: Page) -> dict:
    """Extract options lab data."""
    data = {
        "timestamp": time.time(),
        "url": page.url,
        "status": "success",
        "data": {}
    }
    
    try:
        # Option chain rows
        chain_rows = page.locator("table tbody tr, .ag-row").count()
        data["data"]["chainRows"] = chain_rows
        
        # Check for Greeks columns (Delta, Gamma, Vega, Theta)
        greeks_visible = any([
            page.locator("text=/Delta/i").count() > 0,
            page.locator("text=/Gamma/i").count() > 0,
            page.locator("text=/Vega/i").count() > 0,
        ])
        data["data"]["greeksVisible"] = greeks_visible
        
        # Check for "Use Mock Data" button
        mock_button = page.locator("button:has-text('Mock Data'), button:has-text('Load Mock')").count()
        data["data"]["mockButtonExists"] = mock_button > 0
        
        # Check if data is loaded (non-empty chain)
        data["data"]["mockDataLoaded"] = chain_rows > 0
        
        # Spot price
        spot_el = page.locator("[id*='spot-price'], [id*='underlying']").first
        data["data"]["spotPrice"] = spot_el.inner_text().strip() if spot_el.count() > 0 else "--"
        
        # Check for strategy builder
        strategy_builder = page.locator("[id*='strategy'], text=/Strategy Builder/i").count()
        data["data"]["strategyBuilderVisible"] = strategy_builder > 0
        
        print(f"✅ Extracted Options data:")
        print(f"   Chain rows: {data['data']['chainRows']}")
        print(f"   Greeks visible: {data['data']['greeksVisible']}")
        print(f"   Mock data loaded: {data['data']['mockDataLoaded']}")
        
    except Exception as e:
        data["status"] = "error"
        data["error"] = str(e)
        print(f"❌ Error: {e}")
    
    return data


def test_options():
    """Main test for Options Lab."""
    config = TEST_AREAS["options"]
    
    print("="*70)
    print("OPTIONS LAB E2E TEST")
    print("="*70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        
        try:
            print(f"\n[1] Loading: {DASHBOARD_URL}")
            page.goto(DASHBOARD_URL, timeout=TIMEOUT)
            page.wait_for_load_state("networkidle", timeout=TIMEOUT)
            time.sleep(2)
            
            print(f"\n[2] Clicking {config['tab_text']} tab...")
            tab = page.locator(f"text={config['tab_text']}").first
            if tab.is_visible():
                tab.click()
                time.sleep(3)
            
            # Try to click "Use Mock Data" if available
            print("\n[2.5] Looking for Mock Data button...")
            mock_btn = page.locator("button:has-text('Mock Data'), button:has-text('Load Mock')").first
            if mock_btn.count() > 0 and mock_btn.is_visible():
                print("   Clicking Mock Data button...")
                mock_btn.click()
                time.sleep(2)
            
            print("\n[3] Extracting data...")
            test_data = extract_options_data(page)
            
            with open(config["output_file"], 'w') as f:
                json.dump(test_data, f, indent=2)
            print(f"\n   ✅ Saved: {config['output_file']}")
            
            screenshot = config["output_file"].parent / "options-screenshot.png"
            page.screenshot(path=str(screenshot), full_page=True)
            
        finally:
            browser.close()
    
    print("\n" + "="*70)
    print("✅ OPTIONS TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_options()
