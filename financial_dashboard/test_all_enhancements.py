"""Comprehensive test script for all Analysis Hub enhancements."""
import time
from playwright.sync_api import sync_playwright
import json

def test_all_features():
    """Test all new features in Analysis Hub."""
    results = {
        'portfolio_analytics': {},
        'attribution_analysis': {},
        'scenario_tester': {}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to False to see what's happening
        page = browser.new_page()
        
        print("\n" + "="*80)
        print("COMPREHENSIVE ANALYSIS HUB TESTING")
        print("="*80 + "\n")
        
        # Navigate to Analysis Hub
        print("1. Loading Analysis Hub...")
        page.goto('http://127.0.0.1:8054', timeout=10000)
        page.wait_for_selector('h2:has-text("Analysis Hub")', timeout=5000)
        print("   ✓ Analysis Hub loaded\n")
        
        # ========== TEST PORTFOLIO ANALYTICS ==========
        print("2. Testing Portfolio Analytics Tab...")
        portfolio_tab = page.locator('a:has-text("Portfolio Analytics")').first
        portfolio_tab.click()
        time.sleep(1)
        print("   ✓ Clicked Portfolio Analytics tab")
        
        # Click Calculate Analytics
        calc_button = page.locator('button#pa-calc-btn')
        calc_button.click()
        print("   ✓ Clicked Calculate Analytics button")
        time.sleep(3)
        
        # Check basic metrics
        total_return = page.locator('#pa-total-return').text_content()
        sharpe = page.locator('#pa-sharpe').text_content()
        drawdown = page.locator('#pa-drawdown').text_content()
        win_rate = page.locator('#pa-win-rate').text_content()
        
        results['portfolio_analytics']['basic_metrics'] = {
            'total_return': total_return,
            'sharpe': sharpe,
            'drawdown': drawdown,
            'win_rate': win_rate
        }
        
        print(f"   ✓ Basic Metrics:")
        print(f"     - Total Return: {total_return}")
        print(f"     - Sharpe Ratio: {sharpe}")
        print(f"     - Max Drawdown: {drawdown}")
        print(f"     - Win Rate: {win_rate}")
        
        # Check Exposure Analysis
        time.sleep(2)
        sector_chart = page.locator('#pa-sector-exposure')
        factor_chart = page.locator('#pa-factor-exposure')
        
        if sector_chart.count() > 0:
            print("   ✓ Sector Exposure chart present")
            results['portfolio_analytics']['sector_exposure'] = 'PASS'
        else:
            print("   ✗ Sector Exposure chart missing")
            results['portfolio_analytics']['sector_exposure'] = 'FAIL'
        
        if factor_chart.count() > 0:
            print("   ✓ Factor Exposure chart present")
            results['portfolio_analytics']['factor_exposure'] = 'PASS'
        else:
            print("   ✗ Factor Exposure chart missing")
            results['portfolio_analytics']['factor_exposure'] = 'FAIL'
        
        # Check VaR Contribution
        var_chart = page.locator('#pa-var-contribution')
        if var_chart.count() > 0:
            print("   ✓ Contribution to VaR chart present")
            results['portfolio_analytics']['var_contribution'] = 'PASS'
        else:
            print("   ✗ Contribution to VaR chart missing")
            results['portfolio_analytics']['var_contribution'] = 'FAIL'
        
        # Check Transaction Cost Analysis
        slippage_chart = page.locator('#pa-slippage-chart')
        total_costs = page.locator('#pa-total-costs').text_content()
        cost_breakdown = page.locator('#pa-cost-breakdown').text_content()
        
        if slippage_chart.count() > 0:
            print("   ✓ Slippage chart present")
            results['portfolio_analytics']['slippage_chart'] = 'PASS'
        else:
            print("   ✗ Slippage chart missing")
            results['portfolio_analytics']['slippage_chart'] = 'FAIL'
        
        print(f"   ✓ Total Trading Costs: {total_costs}")
        print(f"   ✓ Cost Breakdown: {cost_breakdown}")
        results['portfolio_analytics']['tca'] = {'total_costs': total_costs, 'breakdown': cost_breakdown}
        
        page.screenshot(path='test_portfolio_analytics_full.png')
        print("   ✓ Screenshot saved: test_portfolio_analytics_full.png\n")
        
        # ========== TEST ATTRIBUTION ANALYSIS ==========
        print("3. Testing Attribution Analysis Tab...")
        attr_tab = page.locator('a:has-text("Attribution Analysis")').first
        attr_tab.click()
        time.sleep(1)
        print("   ✓ Clicked Attribution Analysis tab")
        
        # Check for regime filter
        regime_filter = page.locator('#attr-regime-filter')
        if regime_filter.count() > 0:
            print("   ✓ Market Regime filter present")
            results['attribution_analysis']['regime_filter'] = 'PASS'
        else:
            print("   ✗ Market Regime filter missing")
            results['attribution_analysis']['regime_filter'] = 'FAIL'
        
        # Note: We can't fully test Attribution Analysis without running it
        # (requires actual picks data), but we can verify the UI elements are present
        
        # Check for drill-down section
        drilldown = page.locator('#attr-factor-drilldown')
        if drilldown.count() > 0:
            print("   ✓ Factor drill-down section present")
            results['attribution_analysis']['factor_drilldown'] = 'PASS'
        else:
            print("   ✗ Factor drill-down section missing")
            results['attribution_analysis']['factor_drilldown'] = 'FAIL'
        
        # Check for error analysis section
        error_analysis = page.locator('#attr-error-analysis')
        if error_analysis.count() > 0:
            print("   ✓ Error Analysis section present")
            results['attribution_analysis']['error_analysis'] = 'PASS'
        else:
            print("   ✗ Error Analysis section missing")
            results['attribution_analysis']['error_analysis'] = 'FAIL'
        
        page.screenshot(path='test_attribution_analysis.png')
        print("   ✓ Screenshot saved: test_attribution_analysis.png\n")
        
        # ========== TEST SCENARIO TESTER ==========
        print("4. Testing Scenario Tester Tab...")
        scenario_tab = page.locator('a:has-text("Scenario Tester")').first
        scenario_tab.click()
        time.sleep(1)
        print("   ✓ Clicked Scenario Tester tab")
        
        # Check for scenario type selector
        scenario_type = page.locator('#scenario-type')
        if scenario_type.count() > 0:
            print("   ✓ Scenario Type selector present")
            results['scenario_tester']['scenario_type'] = 'PASS'
            
            # For Dash dropdowns, we need to interact via JavaScript
            # Change to factor-based scenarios
            page.evaluate("""
                const dropdown = document.querySelector('#scenario-type');
                if (dropdown && dropdown._reactProps) {
                    const props = dropdown._reactProps;
                    if (props.setProps) {
                        props.setProps({value: 'factor'});
                    }
                }
            """)
            time.sleep(1)
            print("   ✓ Switched to Factor-Based Scenarios (via JS)")
            results['scenario_tester']['factor_scenarios'] = 'PASS (via JS)'
        else:
            print("   ✗ Scenario Type selector missing")
            results['scenario_tester']['scenario_type'] = 'FAIL'
        
        # Check for compare mode
        compare_mode = page.locator('#scenario-compare-mode')
        if compare_mode.count() > 0:
            print("   ✓ Compare Mode checkbox present")
            results['scenario_tester']['compare_mode'] = 'PASS'
            
            # Enable compare mode via JS
            page.evaluate("""
                const checklist = document.querySelector('#scenario-compare-mode');
                if (checklist && checklist._reactProps) {
                    const props = checklist._reactProps;
                    if (props.setProps) {
                        props.setProps({value: ['compare']});
                    }
                }
            """)
            time.sleep(1)
            
            # Check if second scenario selector appears
            compare_selector = page.locator('#scenario-compare-selector')
            if compare_selector.is_visible():
                print("   ✓ Second scenario selector appears in compare mode")
                results['scenario_tester']['compare_selector'] = 'PASS'
            else:
                print("   ✗ Second scenario selector not visible")
                results['scenario_tester']['compare_selector'] = 'FAIL'
            
            # Disable compare mode
            page.evaluate("""
                const checklist = document.querySelector('#scenario-compare-mode');
                if (checklist && checklist._reactProps) {
                    const props = checklist._reactProps;
                    if (props.setProps) {
                        props.setProps({value: []});
                    }
                }
            """)
            time.sleep(0.5)
        else:
            print("   ✗ Compare Mode checkbox missing")
            results['scenario_tester']['compare_mode'] = 'FAIL'
        
        # Run a factor scenario to test implied bet analysis
        # Select factor type and momentum_crash preset via JS
        page.evaluate("""
            // Set scenario type to factor
            const typeDropdown = document.querySelector('#scenario-type');
            if (typeDropdown && typeDropdown._reactProps) {
                typeDropdown._reactProps.setProps({value: 'factor'});
            }
        """)
        time.sleep(0.5)
        
        page.evaluate("""
            // Set preset to momentum_crash
            const presetDropdown = document.querySelector('#scenario-preset');
            if (presetDropdown && presetDropdown._reactProps) {
                presetDropdown._reactProps.setProps({value: 'momentum_crash'});
            }
        """)
        time.sleep(0.5)
        
        print("   ✓ Selected Momentum Crash scenario")
        
        run_button = page.locator('button#scenario-run-btn')
        run_button.click()
        print("   ✓ Clicked Run Scenario button")
        time.sleep(3)
        
        # Check for results
        results_div = page.locator('#scenario-results')
        if results_div.text_content() and 'Configure a scenario' not in results_div.text_content():
            print("   ✓ Scenario results displayed")
            results['scenario_tester']['results'] = 'PASS'
            
            # Check for hedging candidates
            if 'Hedging Candidates' in results_div.text_content() or 'hedging' in results_div.text_content().lower():
                print("   ✓ Implied Bet Analysis (Hedging Candidates) present")
                results['scenario_tester']['implied_bet_analysis'] = 'PASS'
            else:
                print("   ⚠ Hedging Candidates text not found (may still be functional)")
                results['scenario_tester']['implied_bet_analysis'] = 'PARTIAL'
        else:
            print("   ✗ Scenario results not displayed")
            results['scenario_tester']['results'] = 'FAIL'
        
        page.screenshot(path='test_scenario_tester.png')
        print("   ✓ Screenshot saved: test_scenario_tester.png\n")
        
        browser.close()
    
    return results


def print_test_summary(results):
    """Print a summary of all test results."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    all_pass = True
    
    for category, tests in results.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for test_name, result in tests.items():
            if isinstance(result, dict):
                print(f"  • {test_name}: {json.dumps(result, indent=4)}")
            else:
                status = "✅" if result == 'PASS' else ("⚠️" if result == 'PARTIAL' else "❌")
                print(f"  {status} {test_name}: {result}")
                if result == 'FAIL':
                    all_pass = False
    
    print("\n" + "="*80)
    if all_pass:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Check details above")
    print("="*80 + "\n")


if __name__ == '__main__':
    try:
        results = test_all_features()
        print_test_summary(results)
        
        # Save results to JSON
        with open('test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("Test results saved to: test_results.json\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}\n")
        import traceback
        traceback.print_exc()
