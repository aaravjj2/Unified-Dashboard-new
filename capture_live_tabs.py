"""
Simple test - just capture screenshots of each tab
"""
from playwright.sync_api import sync_playwright
import time

def capture_tabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("Loading dashboard...")
        page.goto('http://localhost:8051/', timeout=60000)
        page.wait_for_load_state('networkidle')
        time.sleep(5)
        
        print("Capturing initial state...")
        page.screenshot(path='reports/fix_verification/screenshots/dashboard_loaded.png')
        
        # Find all tab links by text
        print("\nLooking for tabs...")
        
        # Try to click Research Lab by text
        print("Clicking Research Lab...")
        page.get_by_role("tab", name="🔬 Research Lab").click()
        time.sleep(3)
        page.screenshot(path='reports/fix_verification/screenshots/research_lab_tab.png')
        
        # Click Factor Analysis subtab
        print("Clicking Factor Analysis...")
        page.get_by_text("Factor Analysis").first.click()
        time.sleep(2)
        page.screenshot(path='reports/fix_verification/screenshots/factor_analysis_live.png')
        
        # Click Market Forecast
        print("Clicking Market Forecast...")
        page.get_by_role("tab", name="Market Forecast").click()
        time.sleep(3)
        page.screenshot(path='reports/fix_verification/screenshots/market_forecast_live.png')
        
        # Click Portfolio
        print("Clicking Portfolio...")
        page.get_by_role("tab", name="Portfolio").click()
        time.sleep(2)
        page.screenshot(path='reports/fix_verification/screenshots/portfolio_live.png')
        
        print("\n✅ All screenshots captured!")
        browser.close()

if __name__ == '__main__':
    capture_tabs()
