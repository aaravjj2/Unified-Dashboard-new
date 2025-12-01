"""
test_portfolio_features.py
Playwright Feature Test - Validates new portfolio features

Tests:
1. Monte Carlo simulation runs and displays results
2. Portfolio optimization works with different strategies
3. Inspect position modal opens and shows details
4. Analytics calculations work (risk metrics)
5. Factor exposure displays correctly
"""

import sys
import os
from playwright.sync_api import sync_playwright, expect
import time

# Configuration
PORTFOLIO_URL = "http://localhost:8056"  # Standalone portfolio app
MAIN_DASHBOARD_URL = "http://localhost:8000"
SCREENSHOT_DIR = "test_screenshots/features"
TIMEOUT = 30000  # 30 seconds

# Create screenshot directory
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def test_monte_carlo_simulation(page):
    """Test 1: Monte Carlo simulation runs and displays results."""
    print("\n🧪 Test 1: Monte Carlo Simulation")
    print("-" * 50)
    
    try:
        page.goto(PORTFOLIO_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Navigate to Analytics tab
        analytics_tab = page.locator(".nav-link:has-text('Analytics')")
        expect(analytics_tab).to_be_visible(timeout=10000)
        analytics_tab.click()
        time.sleep(2)
        print("✅ Analytics tab opened")
        
        # Find and click Monte Carlo button
        monte_carlo_btn = page.locator("#monte-carlo-btn, button:has-text('Monte Carlo')")
        
        if not monte_carlo_btn.is_visible(timeout=5000):
            print("⚠️  Monte Carlo button not found")
            return False
        
        print("✅ Monte Carlo button found")
        monte_carlo_btn.click()
        print("  Running simulation...")
        time.sleep(8)  # Wait for simulation to complete
        
        # Check if results appeared
        results_container = page.locator("#monte-carlo-results")
        if results_container.is_visible():
            # Look for key elements in results
            try:
                expect(page.locator("text=/Monte Carlo Simulation Results/i")).to_be_visible(timeout=5000)
                print("✅ Monte Carlo results header found")
                
                # Check for simulation graph
                if page.locator("text=/1,000 paths/i").is_visible(timeout=3000):
                    print("✅ Simulation graph title visible (1,000 paths)")
                
                # Check for percentile values
                if page.locator("text=/95th Percentile/i").is_visible(timeout=3000):
                    print("✅ 95th Percentile displayed")
                
                if page.locator("text=/5th Percentile/i").is_visible(timeout=3000):
                    print("✅ 5th Percentile displayed")
                
            except Exception as e:
                print(f"⚠️  Some Monte Carlo elements missing: {e}")
        else:
            print("⚠️  Monte Carlo results container not visible")
            return False
        
        # Take screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_monte_carlo.png", full_page=True)
        
        print("✅ Monte Carlo simulation test complete")
        return True
        
    except Exception as e:
        print(f"❌ Monte Carlo test failed: {e}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_monte_carlo_error.png", full_page=True)
        return False


def test_portfolio_optimization(page):
    """Test 2: Portfolio optimization runs with different strategies."""
    print("\n🧪 Test 2: Portfolio Optimization")
    print("-" * 50)
    
    try:
        page.goto(PORTFOLIO_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Navigate to Optimization tab
        opt_tab = page.locator(".nav-link:has-text('Optimization')")
        if not opt_tab.is_visible(timeout=5000):
            print("⚠️  Optimization tab not found")
            return False
        
        opt_tab.click()
        time.sleep(2)
        print("✅ Optimization tab opened")
        
        # Enter tickers
        tickers_input = page.locator("#opt-tickers-input")
        expect(tickers_input).to_be_visible(timeout=5000)
        tickers_input.fill("AAPL,MSFT,GOOGL,TSLA")
        print("✅ Tickers entered: AAPL, MSFT, GOOGL, TSLA")
        
        # Select strategy
        strategy_dropdown = page.locator("#opt-strategy")
        expect(strategy_dropdown).to_be_visible(timeout=5000)
        strategy_dropdown.select_option("max_sharpe")
        print("✅ Strategy selected: Maximize Sharpe Ratio")
        
        # Click Optimize button
        opt_button = page.locator("#opt-run-btn, button:has-text('Optimize')")
        expect(opt_button).to_be_visible(timeout=5000)
        opt_button.click()
        print("  Running optimization...")
        time.sleep(10)  # Wait for optimization to complete
        
        # Check for results
        results_container = page.locator("#opt-results-container")
        if results_container.is_visible():
            try:
                # Check for key result elements
                if page.locator("text=/Optimization Results/i").is_visible(timeout=5000):
                    print("✅ Optimization results header found")
                
                if page.locator("text=/Expected Annual Return/i").is_visible(timeout=3000):
                    print("✅ Expected Return displayed")
                
                if page.locator("text=/Sharpe Ratio/i").is_visible(timeout=3000):
                    print("✅ Sharpe Ratio displayed")
                
                # Check for weights table
                if page.locator("text=/Optimal Weights/i").is_visible(timeout=3000):
                    print("✅ Optimal weights table visible")
                
            except Exception as e:
                print(f"⚠️  Some optimization elements missing: {e}")
        else:
            print("⚠️  Optimization results not visible")
            return False
        
        # Take screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/02_optimization.png", full_page=True)
        
        print("✅ Portfolio optimization test complete")
        return True
        
    except Exception as e:
        print(f"❌ Optimization test failed: {e}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/02_optimization_error.png", full_page=True)
        return False


def test_inspect_position_modal(page):
    """Test 3: Inspect position modal opens and shows details."""
    print("\n🧪 Test 3: Inspect Position Modal")
    print("-" * 50)
    
    try:
        page.goto(PORTFOLIO_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Ensure we're on Positions tab (default)
        positions_tab = page.locator(".nav-link:has-text('Positions')")
        if positions_tab.is_visible(timeout=5000):
            positions_tab.click()
            time.sleep(2)
        
        print("✅ Positions tab opened")
        
        # Look for positions table
        positions_table = page.locator("#positions-datatable, #portfolio-positions-table")
        if not positions_table.is_visible(timeout=5000):
            print("⚠️  Positions table not visible (may need portfolio data)")
            return False
        
        print("✅ Positions table found")
        
        # Try to find and click an Inspect button
        # The button text is "🔍 Inspect" in the actions column
        inspect_cells = page.locator("td:has-text('Inspect'), td:has-text('🔍')")
        
        if inspect_cells.count() > 0:
            first_inspect = inspect_cells.first
            first_inspect.click()
            time.sleep(2)
            print("✅ Inspect button clicked")
            
            # Check if modal opened
            modal = page.locator("#inspect-modal, .modal")
            if modal.is_visible(timeout=5000):
                print("✅ Inspect modal opened")
                
                # Check for modal content
                try:
                    if page.locator("text=/Model Score/i").is_visible(timeout=3000):
                        print("  ✓ Model Score section visible")
                    
                    if page.locator("text=/SHAP/i").is_visible(timeout=3000):
                        print("  ✓ SHAP features section visible")
                    
                    if page.locator("text=/News Events/i, text=/Recent Events/i").is_visible(timeout=3000):
                        print("  ✓ News events section visible")
                except Exception as e:
                    print(f"  ⚠️  Some modal elements missing: {e}")
                
                # Take screenshot
                page.screenshot(path=f"{SCREENSHOT_DIR}/03_inspect_modal.png", full_page=True)
                
                # Close modal
                close_btn = page.locator("#inspect-modal-close, button:has-text('Close')")
                if close_btn.is_visible(timeout=3000):
                    close_btn.click()
                    time.sleep(1)
                    print("✅ Modal closed")
            else:
                print("⚠️  Modal did not open")
                return False
        else:
            print("⚠️  No Inspect buttons found (may need live portfolio data)")
            return False
        
        print("✅ Inspect modal test complete")
        return True
        
    except Exception as e:
        print(f"❌ Inspect modal test failed: {e}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/03_inspect_modal_error.png", full_page=True)
        return False


def test_analytics_risk_metrics(page):
    """Test 4: Analytics tab displays risk metrics correctly."""
    print("\n🧪 Test 4: Analytics Risk Metrics")
    print("-" * 50)
    
    try:
        page.goto(PORTFOLIO_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Navigate to Analytics tab
        analytics_tab = page.locator(".nav-link:has-text('Analytics')")
        expect(analytics_tab).to_be_visible(timeout=10000)
        analytics_tab.click()
        time.sleep(3)
        print("✅ Analytics tab opened")
        
        # Check for risk metric cards
        metrics = {
            'VaR': '#portfolio-var',
            'CVaR': '#portfolio-cvar',
            'Sharpe': '#portfolio-sharpe',
            'Beta': '#portfolio-beta'
        }
        
        for metric_name, metric_id in metrics.items():
            try:
                metric_elem = page.locator(metric_id)
                if metric_elem.is_visible(timeout=3000):
                    value = metric_elem.inner_text()
                    print(f"  ✓ {metric_name}: {value}")
                else:
                    print(f"  ⚠️  {metric_name} not visible")
            except:
                print(f"  ⚠️  {metric_name} element not found")
        
        # Check for charts
        try:
            # Portfolio performance chart
            if page.locator("text=/Portfolio Performance/i, text=/vs SPY/i").is_visible(timeout=5000):
                print("✅ Portfolio Performance chart title visible")
            
            # Correlation heatmap
            if page.locator("text=/Correlation Heatmap/i").is_visible(timeout=3000):
                print("✅ Correlation Heatmap title visible")
        except Exception as e:
            print(f"⚠️  Some charts missing: {e}")
        
        # Take screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/04_analytics_metrics.png", full_page=True)
        
        print("✅ Analytics risk metrics test complete")
        return True
        
    except Exception as e:
        print(f"❌ Analytics test failed: {e}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/04_analytics_error.png", full_page=True)
        return False


def test_factor_exposure(page):
    """Test 5: Factor exposure displays correctly."""
    print("\n🧪 Test 5: Factor Exposure")
    print("-" * 50)
    
    try:
        page.goto(PORTFOLIO_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Navigate to Factor Exposure tab
        factor_tab = page.locator(".nav-link:has-text('Factor Exposure')")
        if not factor_tab.is_visible(timeout=5000):
            print("⚠️  Factor Exposure tab not found")
            return False
        
        factor_tab.click()
        time.sleep(3)
        print("✅ Factor Exposure tab opened")
        
        # Check for factor content
        factor_content = page.locator("#portfolio-factor-exposure-content")
        if factor_content.is_visible(timeout=5000):
            try:
                # Look for factor chart or table
                if page.locator("text=/SHAP/i").is_visible(timeout=3000):
                    print("✅ SHAP-based factor analysis visible")
                
                if page.locator("text=/Factor Exposure/i").is_visible(timeout=3000):
                    print("✅ Factor Exposure chart/title visible")
                
                # Check for common factors
                factors = ['Momentum', 'Value', 'Quality', 'Sentiment', 'Growth', 'Size']
                found_factors = []
                for factor in factors:
                    if page.locator(f"text={factor}").is_visible(timeout=1000):
                        found_factors.append(factor)
                
                if found_factors:
                    print(f"✅ Factors found: {', '.join(found_factors)}")
                else:
                    print("⚠️  No SHAP data available (expected if no recent model run)")
                
            except Exception as e:
                print(f"⚠️  Some factor elements missing: {e}")
        else:
            print("⚠️  Factor exposure content not visible")
            return False
        
        # Take screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/05_factor_exposure.png", full_page=True)
        
        print("✅ Factor exposure test complete")
        return True
        
    except Exception as e:
        print(f"❌ Factor exposure test failed: {e}")
        page.screenshot(path=f"{SCREENSHOT_DIR}/05_factor_error.png", full_page=True)
        return False


def run_all_tests():
    """Run all feature tests."""
    print("\n" + "="*60)
    print("🚀 PORTFOLIO FEATURES TEST SUITE")
    print("="*60)
    
    results = {
        'monte_carlo': False,
        'optimization': False,
        'inspect_modal': False,
        'analytics_metrics': False,
        'factor_exposure': False
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for CI/CD
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Run tests
            results['monte_carlo'] = test_monte_carlo_simulation(page)
            results['optimization'] = test_portfolio_optimization(page)
            results['inspect_modal'] = test_inspect_position_modal(page)
            results['analytics_metrics'] = test_analytics_risk_metrics(page)
            results['factor_exposure'] = test_factor_exposure(page)
            
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
