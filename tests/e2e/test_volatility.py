"""
Volatility Lab E2E Tests
=========================
Tests for IV Surface and volatility analytics.
"""
import json
import time
from playwright.sync_api import sync_playwright, Page
from config import DASHBOARD_URL, TEST_AREAS, TIMEOUT, HEADLESS, VIEWPORT_WIDTH, VIEWPORT_HEIGHT


def extract_volatility_data(page: Page) -> dict:
    """Extract volatility lab data."""
    data = {
        "timestamp": time.time(),
        "url": page.url,
        "status": "success",
        "data": {}
    }
    
    try:
        # Check for IV Surface (Plotly chart or data)
        plotly_charts = page.locator(".plotly, .js-plotly-plot").count()
        data["data"]["ivSurfaceDataExists"] = plotly_charts > 0
        
        # Color legend visibility
        legend_el = page.locator(".legend, [class*='legend'], [class*='colorbar']").count()
        data["data"]["colorLegendVisible"] = legend_el > 0
        
        # Check for "No data" messages
        no_data = page.locator("text=/No data|No IV surface/i").count()
        data["data"]["noDataMessageVisible"] = no_data > 0
        
        # IV Percentile
        iv_percentile = page.locator("[id*='iv-percentile'], [id*='percentile']").first
        data["data"]["ivPercentile"] = iv_percentile.inner_text().strip() if iv_percentile.count() > 0 else "--"
        
        # Skew metrics
        skew_el = page.locator("[id*='skew']").first
        data["data"]["skew"] = skew_el.inner_text().strip() if skew_el.count() > 0 else "--"
        
        print(f"✅ Extracted Volatility data:")
        print(f"   IV Surface exists: {data['data']['ivSurfaceDataExists']}")
        print(f"   Legend visible: {data['data']['colorLegendVisible']}")
        print(f"   No data message: {data['data']['noDataMessageVisible']}")
        
    except Exception as e:
        data["status"] = "error"
        data["error"] = str(e)
        print(f"❌ Error: {e}")
    
    return data


def test_volatility():
    """Main test for Volatility Lab."""
    config = TEST_AREAS["volatility"]
    
    print("="*70)
    print("VOLATILITY LAB E2E TEST")
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
            
            print("\n[3] Extracting data...")
            test_data = extract_volatility_data(page)
            
            with open(config["output_file"], 'w') as f:
                json.dump(test_data, f, indent=2)
            print(f"\n   ✅ Saved: {config['output_file']}")
            
            screenshot = config["output_file"].parent / "volatility-screenshot.png"
            page.screenshot(path=str(screenshot), full_page=True)
            
        finally:
            browser.close()
    
    print("\n" + "="*70)
    print("✅ VOLATILITY TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_volatility()
