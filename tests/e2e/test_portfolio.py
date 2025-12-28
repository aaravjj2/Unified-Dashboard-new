"""
Portfolio Tracker E2E Tests
============================
Tests for Portfolio tab analytics:
- Sharpe Ratio
- Max Drawdown
- Beta
- Positions count
"""
import json
import time
from playwright.sync_api import sync_playwright, Page
from config import DASHBOARD_URL, TEST_AREAS, TIMEOUT, HEADLESS, VIEWPORT_WIDTH, VIEWPORT_HEIGHT


def extract_portfolio_data(page: Page) -> dict:
    """Extract portfolio analytics data."""
    data = {
        "timestamp": time.time(),
        "url": page.url,
        "status": "success",
        "data": {}
    }
    
    try:
        # Sharpe Ratio
        sharpe_el = page.locator("#sharpe-ratio, [id*='sharpe']").first
        data["data"]["sharpe"] = sharpe_el.inner_text().strip() if sharpe_el.count() > 0 else "--"
        
        # Max Drawdown
        drawdown_el = page.locator("#max-drawdown, [id*='drawdown']").first
        data["data"]["drawdown"] = drawdown_el.inner_text().strip() if drawdown_el.count() > 0 else "--"
        
        # Beta
        beta_el = page.locator("#beta, [id*='beta']").first
        data["data"]["beta"] = beta_el.inner_text().strip() if beta_el.count() > 0 else "--"
        
        # Positions count (from table rows)
        table_rows = page.locator("table tbody tr, .ag-row").count()
        data["data"]["positionsCount"] = table_rows
        
        # Portfolio Value
        value_el = page.locator("#portfolio-value, [id*='portfolio-value']").first
        data["data"]["portfolioValue"] = value_el.inner_text().strip() if value_el.count() > 0 else "--"
        
        # Unrealized P/L
        pnl_el = page.locator("#unrealized-pnl, [id*='unrealized']").first
        data["data"]["unrealizedPnL"] = pnl_el.inner_text().strip() if pnl_el.count() > 0 else "--"
        
        print(f"✅ Extracted Portfolio data:")
        print(f"   Sharpe: {data['data']['sharpe']}")
        print(f"   Drawdown: {data['data']['drawdown']}")
        print(f"   Beta: {data['data']['beta']}")
        print(f"   Positions: {data['data']['positionsCount']}")
        
    except Exception as e:
        data["status"] = "error"
        data["error"] = str(e)
        print(f"❌ Error: {e}")
    
    return data


def test_portfolio():
    """Main test for Portfolio tab."""
    config = TEST_AREAS["portfolio"]
    
    print("="*70)
    print("PORTFOLIO TRACKER E2E TEST")
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
            test_data = extract_portfolio_data(page)
            
            with open(config["output_file"], 'w') as f:
                json.dump(test_data, f, indent=2)
            print(f"\n   ✅ Saved: {config['output_file']}")
            
            screenshot = config["output_file"].parent / "portfolio-screenshot.png"
            page.screenshot(path=str(screenshot), full_page=True)
            
        finally:
            browser.close()
    
    print("\n" + "="*70)
    print("✅ PORTFOLIO TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_portfolio()
