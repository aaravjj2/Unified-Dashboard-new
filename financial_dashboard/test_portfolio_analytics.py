"""Test script to verify Portfolio Analytics functionality."""
import time
from playwright.sync_api import sync_playwright

def test_portfolio_analytics():
    """Test that the Calculate Analytics button works in Portfolio Analytics tab."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to Analysis Hub
        print("Navigating to Analysis Hub...")
        page.goto('http://127.0.0.1:8054', timeout=10000)
        
        # Wait for the page to load
        page.wait_for_selector('h2:has-text("Analysis Hub")', timeout=5000)
        print("✓ Analysis Hub loaded")
        
        # Click Portfolio Analytics tab (try multiple selectors)
        print("Clicking Portfolio Analytics tab...")
        
        # First try: look for anchors with data-_target
        portfolio_tab = page.locator('a[data-_target="#attr-panel-1"]')
        if portfolio_tab.count() == 0:
            # Second try: look by text content
            portfolio_tab = page.locator('a:has-text("Portfolio Analytics")')
        
        if portfolio_tab.count() > 0:
            portfolio_tab.first.click()
            time.sleep(2)
            print("✓ Portfolio Analytics tab clicked")
        else:
            print("✗ Portfolio Analytics tab not found")
            print("  Available tabs:")
            tabs = page.locator('a.nav-link').all()
            for tab in tabs:
                print(f"    - {tab.text_content()}")
            browser.close()
            return False
        
        # Find and click Calculate Analytics button
        print("Clicking Calculate Analytics button...")
        calc_button = page.locator('button#pa-calc-btn')
        if calc_button.count() > 0:
            calc_button.click()
            print("✓ Calculate Analytics button clicked")
            
            # Wait for results to appear (check if metrics update)
            time.sleep(2)
            
            # Check if metrics have been updated (should not be "0.00%" anymore)
            total_return = page.locator('#pa-total-return').text_content()
            sharpe = page.locator('#pa-sharpe').text_content()
            
            print(f"  Total Return: {total_return}")
            print(f"  Sharpe Ratio: {sharpe}")
            
            if total_return and total_return != "0.00%":
                print("✓ Portfolio Analytics calculated successfully!")
                success = True
            else:
                print("✗ Portfolio Analytics did not update (still showing 0.00%)")
                success = False
        else:
            print("✗ Calculate Analytics button not found")
            success = False
        
        # Take a screenshot
        page.screenshot(path='portfolio_analytics_test.png')
        print("✓ Screenshot saved as portfolio_analytics_test.png")
        
        browser.close()
        return success

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Testing Portfolio Analytics Functionality")
    print("="*60 + "\n")
    
    success = test_portfolio_analytics()
    
    print("\n" + "="*60)
    if success:
        print("✅ Test PASSED: Portfolio Analytics is working!")
    else:
        print("❌ Test FAILED: Portfolio Analytics has issues")
    print("="*60 + "\n")
