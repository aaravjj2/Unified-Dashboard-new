"""
Simple manual verification - just load the page and take screenshots 
to confirm the bug is fixed visually.
"""

from playwright.sync_api import sync_playwright
import time

def manual_verification():
    """Simple visual verification that critical bug is fixed."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()
        
        try:
            # Load the page
            page.goto('http://localhost:8054', timeout=60000)
            page.wait_for_load_state('domcontentloaded')
            time.sleep(2)
            
            print("✓ Page loaded")
            page.screenshot(path='verify_1_initial.png', full_page=True)
            
            # Click Attribution Analysis tab
            try:
                page.locator('a:has-text("Attribution Analysis")').first.click(timeout=5000)
                time.sleep(1)
                print("✓ Attribution Analysis tab clicked")
            except:
                print("  (Already on Attribution tab)")
            
            # Take screenshot before clicking button
            page.screenshot(path='verify_2_before_run.png', full_page=True)
            
            # Click Run Attribution Analysis
            try:
                page.locator('button:has-text("Run Attribution Analysis")').click(timeout=5000)
                print("✓ Clicked Run Attribution Analysis")
                time.sleep(6)  # Wait for analysis to complete
                
                # Take screenshot after analysis
                page.screenshot(path='verify_3_after_run.png', full_page=True)
                print("✓ Screenshot taken after analysis")
            except Exception as e:
                print(f"  Button click failed: {e}")
            
            # Try Portfolio Analytics
            try:
                page.locator('a:has-text("Portfolio Analytics")').first.click(timeout=5000)
                time.sleep(1)
                print("✓ Portfolio Analytics tab clicked")
                page.screenshot(path='verify_4_portfolio.png', full_page=True)
            except Exception as e:
                print(f"  Portfolio tab failed: {e}")
            
            # Try Scenario Tester
            try:
                page.locator('a:has-text("Scenario Testing")').first.click(timeout=5000)
                time.sleep(1)
                print("✓ Scenario Testing tab clicked")
                page.screenshot(path='verify_5_scenario.png', full_page=True)
            except Exception as e:
                print(f"  Scenario tab failed: {e}")
            
            print("\n" + "="*60)
            print("Screenshots saved. Please review:")
            print("  verify_1_initial.png - Initial page load")
            print("  verify_2_before_run.png - Before running analysis")
            print("  verify_3_after_run.png - After running analysis (should show graphs)")
            print("  verify_4_portfolio.png - Portfolio Analytics tab")
            print("  verify_5_scenario.png - Scenario Testing tab")
            print("="*60)
            
            input("Press Enter to close browser...")
            
        finally:
            browser.close()

if __name__ == '__main__':
    manual_verification()
