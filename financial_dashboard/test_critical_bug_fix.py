"""
Quick test to verify the critical update_picks_table bug is fixed.
Tests that:
1. Attribution Analysis graphs populate after running analysis
2. Portfolio Analytics button works
3. Scenario Tester button works
"""

from playwright.sync_api import sync_playwright, expect
import time

def test_critical_bug_fixed():
    """Verify the critical callback bug is fixed and tabs work properly."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        # Navigate to app (standalone analysis app - already on Analysis Hub)
        page.goto('http://localhost:8054')
        page.wait_for_load_state('networkidle')
        
        print("✓ Page loaded (standalone Analysis Hub)")
        
        # Click on Attribution Analysis sub-tab (should be first tab)
        attr_tab = page.locator('a:has-text("Attribution Analysis")')
        if attr_tab.count() > 0:
            attr_tab.first.click()
            time.sleep(1)
            print("✓ Attribution Analysis sub-tab clicked")
        
        # Test 1: Run Attribution Analysis and check if graphs populate
        print("\n--- Test 1: Attribution Analysis ---")
        
        # Click Run Attribution Analysis button
        run_button = page.locator('button:has-text("Run Attribution Analysis")')
        run_button.click()
        print("  ✓ Clicked Run Attribution Analysis")
        
        # Wait for results to load (container should become visible via callback)
        time.sleep(5)
        
        # Check if attr-results-container is visible (was being destroyed by bug)
        results_container = page.locator('#attr-results-container')
        # Wait for the container to become visible (up to 10 seconds)
        results_container.wait_for(state='visible', timeout=10000)
        expect(results_container).to_be_visible()
        print("  ✓ Results container is visible (not destroyed!)")
        
        # Check if graphs are present
        alpha_beta_chart = page.locator('#attr-alpha-beta-chart')
        expect(alpha_beta_chart).to_be_visible()
        print("  ✓ Alpha/Beta chart is visible")
        
        factor_chart = page.locator('#attr-factor-chart')
        expect(factor_chart).to_be_visible()
        print("  ✓ Factor chart is visible")
        
        # Test 2: Portfolio Analytics button works
        print("\n--- Test 2: Portfolio Analytics ---")
        
        # Click Portfolio Analytics tab (was becoming non-functional due to bug)
        portfolio_tab = page.locator('a:has-text("Portfolio Analytics")')
        portfolio_tab.click()
        time.sleep(1)
        print("  ✓ Portfolio Analytics tab clicked")
        
        # Check if Calculate Analytics button is present and clickable
        calc_button = page.locator('button:has-text("Calculate Analytics")')
        expect(calc_button).to_be_visible()
        print("  ✓ Calculate Analytics button is visible")
        
        calc_button.click()
        time.sleep(2)
        print("  ✓ Calculate Analytics button clicked (button functionality works!)")
        
        # Check if metrics appeared
        total_return = page.locator('#pa-total-return')
        expect(total_return).to_be_visible()
        print("  ✓ Total Return metric is visible")
        
        # Test 3: Scenario Tester button works
        print("\n--- Test 3: Scenario Tester ---")
        
        # Click Scenario Tester tab
        scenario_tab = page.locator('a:has-text("Scenario Testing")')
        scenario_tab.click()
        time.sleep(1)
        print("  ✓ Scenario Testing tab clicked")
        
        # Check if Run Scenario button is present and clickable
        scenario_button = page.locator('button:has-text("Run Scenario")')
        expect(scenario_button).to_be_visible()
        print("  ✓ Run Scenario button is visible")
        
        scenario_button.click()
        time.sleep(2)
        print("  ✓ Run Scenario button clicked (button functionality works!)")
        
        # Check if results appeared
        scenario_results = page.locator('#scenario-results')
        expect(scenario_results).to_be_visible()
        print("  ✓ Scenario results are visible")
        
        # Take screenshot
        page.screenshot(path='test_critical_bug_fixed.png', full_page=True)
        print("\n✓ Screenshot saved: test_critical_bug_fixed.png")
        
        browser.close()
        
        print("\n" + "="*60)
        print("SUCCESS! Critical bug is FIXED!")
        print("="*60)
        print("✓ Attribution Analysis graphs populate properly")
        print("✓ Portfolio Analytics button works")
        print("✓ Scenario Tester button works")
        print("✓ No DOM elements destroyed by update_picks_table callback")
        print("="*60)

if __name__ == '__main__':
    test_critical_bug_fixed()
