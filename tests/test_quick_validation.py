"""
Quick System Validation
========================
Single-iteration validation of Market Trends and Portfolio tabs.
"""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime

BASE_URL = "http://localhost:8050"
OUTPUT_DIR = Path("/mnt/c/Aarav/fin_env/unified-dashboard/snapshots/quick")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def quick_validate():
    """Quick validation of both tabs"""
    results = {"timestamp": datetime.now().isoformat()}
    
    with sync_playwright() as p:
        print("🌐 Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate
        print(f"📍 Navigating to {BASE_URL}...")
        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        # Save home
        page.screenshot(path=str(OUTPUT_DIR / "01_home.png"), full_page=True)
        print("✅ Home page loaded")
        
        # Market Trends
        print("\n📊 Testing Market Trends...")
        mt_tab = page.locator('a:has-text("Market Trends")')
        if mt_tab.count() > 0:
            mt_tab.first.click()
            time.sleep(3)
            page.screenshot(path=str(OUTPUT_DIR / "02_market_trends.png"), full_page=True)
            
            # Check news
            news = page.locator('#news-container')
            news_text = news.inner_text() if news.count() > 0 else ""
            print(f"   News: {len(news_text)} chars - {news_text[:100]}...")
            
            # Check results
            results_area = page.locator('#results-area')
            results_text = results_area.inner_text() if results_area.count() > 0 else ""
            print(f"   Results: {len(results_text)} chars")
            
            # Check buttons
            buttons = ['#run-btn', '#backtest-btn', '#debug-logs-btn']
            for btn_id in buttons:
                btn = page.locator(btn_id)
                exists = btn.count() > 0
                visible = btn.first.is_visible() if exists else False
                print(f"   Button {btn_id}: exists={exists}, visible={visible}")
            
            results["market_trends"] = {
                "news_length": len(news_text),
                "results_length": len(results_text),
                "buttons_visible": all([page.locator(bid).count() > 0 for bid in buttons])
            }
        
        # Portfolio
        print("\n💼 Testing Portfolio...")
        pf_tab = page.locator('a:has-text("Portfolio")')
        if pf_tab.count() > 0:
            pf_tab.first.click()
            time.sleep(3)
            page.screenshot(path=str(OUTPUT_DIR / "03_portfolio_positions.png"), full_page=True)
            
            # Positions
            pos_table = page.locator('#portfolio-positions-table')
            pos_text = pos_table.inner_text() if pos_table.count() > 0 else ""
            print(f"   Positions: {len(pos_text)} chars")
            
            # Order History
            orders_tab = page.locator('a:has-text("Order History")')
            if orders_tab.count() > 0:
                orders_tab.first.click()
                time.sleep(2)
                page.screenshot(path=str(OUTPUT_DIR / "04_portfolio_orders.png"), full_page=True)
                
                orders_table = page.locator('#portfolio-orders-table')
                orders_text = orders_table.inner_text() if orders_table.count() > 0 else ""
                print(f"   Orders: {len(orders_text)} chars")
            
            # Analytics
            analytics_tab = page.locator('a:has-text("Analytics")')
            if analytics_tab.count() > 0:
                analytics_tab.first.click()
                time.sleep(2)
                page.screenshot(path=str(OUTPUT_DIR / "05_portfolio_analytics.png"), full_page=True)
                
                var_el = page.locator('#portfolio-var')
                var_text = var_el.inner_text() if var_el.count() > 0 else "N/A"
                print(f"   VaR: {var_text}")
            
            results["portfolio"] = {
                "positions_length": len(pos_text),
                "orders_length": len(orders_text) if orders_tab.count() > 0 else 0,
                "var_displayed": var_text if analytics_tab.count() > 0 else "N/A"
            }
        
        browser.close()
    
    # Save results
    results_file = OUTPUT_DIR / "results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Validation complete - results saved to {results_file}")
    print(f"📸 Screenshots saved to {OUTPUT_DIR}")
    
    return results

if __name__ == "__main__":
    results = quick_validate()
    print("\n" + "="*80)
    print("QUICK VALIDATION RESULTS")
    print("="*80)
    print(json.dumps(results, indent=2))
