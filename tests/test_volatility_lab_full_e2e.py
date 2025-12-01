"""
Volatility Lab - Full 8-Subtab E2E Validation Test
Phase 3: Deterministic testing with screenshots and logs

Test Structure:
- Loop 1: Verify all 8 tabs are visible
- Loop 2: Execute deterministic interactions for each subtab
- Loop 3: Capture screenshots and validate outputs

Author: Phase 0/1 Full Stabilization
"""
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# Test configuration
BASE_URL = 'http://127.0.0.1:8050'
SCREENSHOT_DIR = 'test-artifacts/volatility_lab_e2e'
TEST_TIMEOUT = 30000  # 30 seconds per interaction

def test_volatility_lab_full_e2e():
    """
    Comprehensive E2E test for all 8 Volatility Lab subtabs
    """
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Track test results
        results = {
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'screenshots': [],
            'console_errors': []
        }
        
        # Capture console errors
        page.on('console', lambda msg: 
            results['console_errors'].append(f"{msg.type}: {msg.text}") 
            if msg.type in ['error', 'warning'] else None
        )
        
        print("="*80)
        print("VOLATILITY LAB - FULL 8-SUBTAB E2E TEST")
        print("="*80)
        
        # ====================================================================
        # LOOP 1: VERIFY ALL 8 TABS VISIBLE
        # ====================================================================
        print("\n[LOOP 1] Verifying 8 subtabs are visible...")
        
        page.goto(BASE_URL, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)  # Allow initial render
        
        # Navigate to Volatility Lab tab
        vol_lab_tab = page.locator('a.nav-link:has-text("⚡ Volatility Lab")')
        expect(vol_lab_tab).to_be_visible(timeout=10000)
        vol_lab_tab.click()
        page.wait_for_timeout(2000)
        
        # Verify all 8 subtabs
        expected_subtabs = [
            'Historical HV',
            'IV Surface',
            'Correlation',
            'Factor Analytics',
            'Advanced Charts',
            'Metrics Table',
            'Custom Scenarios',
            'Alerts'
        ]
        
        found_subtabs = []
        for subtab_name in expected_subtabs:
            subtab = page.locator(f'a.nav-link:has-text("{subtab_name}")')
            is_visible = subtab.is_visible()
            found_subtabs.append({'name': subtab_name, 'visible': is_visible})
            print(f"  {'✅' if is_visible else '❌'} {subtab_name}")
        
        results['tests'].append({
            'test': 'LOOP 1 - 8 Subtabs Visibility',
            'result': 'PASS' if all(s['visible'] for s in found_subtabs) else 'FAIL',
            'details': found_subtabs
        })
        
        # Screenshot: All subtabs visible
        screenshot_path = f'{SCREENSHOT_DIR}/01_all_subtabs_visible.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        print(f"  📸 Screenshot: {screenshot_path}")
        
        # ====================================================================
        # LOOP 2: DETERMINISTIC INTERACTIONS FOR EACH SUBTAB
        # ====================================================================
        print("\n[LOOP 2] Testing deterministic interactions for each subtab...")
        
        # --------------------------------------------------------------------
        # Subtab 1: Historical HV
        # --------------------------------------------------------------------
        print("\n  [1/8] Historical HV...")
        page.locator('a.nav-link:has-text("Historical HV")').click()
        page.wait_for_timeout(1500)
        
        # Enter ticker
        page.fill('#vl-hv-ticker', 'SPY')
        page.wait_for_timeout(500)
        
        # Click compute
        page.click('#vl-hv-btn')
        page.wait_for_timeout(8000)  # Wait for computation + chart render
        
        # Verify chart rendered
        hv_chart = page.locator('#vl-hv-chart .js-plotly-plot')
        hv_chart_visible = hv_chart.is_visible()
        print(f"    {'✅' if hv_chart_visible else '❌'} HV chart rendered")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/02_hv_spy.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'Historical HV',
            'ticker': 'SPY',
            'chart_rendered': hv_chart_visible,
            'result': 'PASS' if hv_chart_visible else 'FAIL'
        })
        
        # --------------------------------------------------------------------
        # Subtab 2: IV Surface
        # --------------------------------------------------------------------
        print("\n  [2/8] IV Surface...")
        page.locator('a.nav-link:has-text("IV Surface")').click()
        page.wait_for_timeout(1500)
        
        # Enter ticker
        page.fill('#vl-iv-ticker', 'SPY')
        
        # Load options chain
        page.click('#vl-iv-load')
        page.wait_for_timeout(10000)  # Wait for expirations to load
        
        # Select first expiration (should be >7 days due to filter)
        page.select_option('#vl-iv-exp', index=0)
        page.wait_for_timeout(500)
        
        # Generate IV surface
        page.click('#vl-iv-gen')
        page.wait_for_timeout(18000)  # Wait for 3-expiration fetch + IV calc + interpolation
        
        # Verify surface rendered
        iv_surface = page.locator('#vl-iv-surface .js-plotly-plot')
        iv_surface_visible = iv_surface.is_visible()
        print(f"    {'✅' if iv_surface_visible else '❌'} IV Surface 3D rendered")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/03_iv_surface_spy.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'IV Surface',
            'ticker': 'SPY',
            'surface_rendered': iv_surface_visible,
            'result': 'PASS' if iv_surface_visible else 'FAIL'
        })
        
        # --------------------------------------------------------------------
        # Subtab 3: Correlation
        # --------------------------------------------------------------------
        print("\n  [3/8] Correlation...")
        page.locator('a.nav-link:has-text("Correlation")').click()
        page.wait_for_timeout(1500)
        
        # Enter tickers
        page.fill('#vl-corr-tickers', 'SPY, AAPL, QQQ')
        
        # Compute correlation
        page.click('#vl-corr-btn')
        page.wait_for_timeout(8000)
        
        # Verify heatmap rendered
        corr_heatmap = page.locator('#vl-corr-heat .js-plotly-plot')
        corr_heatmap_visible = corr_heatmap.is_visible()
        print(f"    {'✅' if corr_heatmap_visible else '❌'} Correlation heatmap rendered")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/04_correlation_multi_ticker.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'Correlation',
            'tickers': 'SPY, AAPL, QQQ',
            'heatmap_rendered': corr_heatmap_visible,
            'result': 'PASS' if corr_heatmap_visible else 'FAIL'
        })
        
        # --------------------------------------------------------------------
        # Subtab 4: Factor Analytics
        # --------------------------------------------------------------------
        print("\n  [4/8] Factor Analytics...")
        page.locator('a.nav-link:has-text("Factor Analytics")').click()
        page.wait_for_timeout(1500)
        
        # Enter ticker and benchmark
        page.fill('#fa-ticker', 'AAPL')
        page.fill('#fa-benchmark', 'SPY')
        
        # Calculate factors
        page.click('#fa-btn')
        page.wait_for_timeout(10000)
        
        # Verify beta chart rendered
        fa_beta_chart = page.locator('#fa-beta-chart .js-plotly-plot')
        fa_beta_chart_visible = fa_beta_chart.is_visible()
        
        # Check if metrics populated (not "--")
        beta_val = page.locator('#fa-beta-val').inner_text()
        metrics_populated = beta_val != '--'
        print(f"    {'✅' if fa_beta_chart_visible else '❌'} Rolling beta chart rendered")
        print(f"    {'✅' if metrics_populated else '❌'} Metrics populated (Beta={beta_val})")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/05_factor_analytics_aapl_spy.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'Factor Analytics',
            'ticker': 'AAPL',
            'benchmark': 'SPY',
            'beta_chart_rendered': fa_beta_chart_visible,
            'metrics_populated': metrics_populated,
            'beta_value': beta_val,
            'result': 'PASS' if (fa_beta_chart_visible and metrics_populated) else 'FAIL'
        })
        
        # --------------------------------------------------------------------
        # Subtab 5: Advanced Charts
        # --------------------------------------------------------------------
        print("\n  [5/8] Advanced Charts...")
        page.locator('a.nav-link:has-text("Advanced Charts")').click()
        page.wait_for_timeout(1500)
        
        # Enter tickers
        page.fill('#ac-tickers', 'SPY, AAPL')
        
        # Select chart type: Multi-ticker HV
        page.select_option('#ac-chart-type', value='multi_hv')
        page.wait_for_timeout(500)
        
        # Generate chart
        page.click('#ac-btn')
        page.wait_for_timeout(10000)
        
        # Verify chart rendered
        ac_chart = page.locator('#ac-main-chart .js-plotly-plot')
        ac_chart_visible = ac_chart.is_visible()
        print(f"    {'✅' if ac_chart_visible else '❌'} Multi-ticker HV chart rendered")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/06_advanced_charts_multi_hv.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'Advanced Charts',
            'chart_type': 'multi_hv',
            'tickers': 'SPY, AAPL',
            'chart_rendered': ac_chart_visible,
            'result': 'PASS' if ac_chart_visible else 'FAIL'
        })
        
        # --------------------------------------------------------------------
        # Subtab 6: Metrics Table
        # --------------------------------------------------------------------
        print("\n  [6/8] Metrics Table...")
        page.locator('a.nav-link:has-text("Metrics Table")').click()
        page.wait_for_timeout(1500)
        
        # Enter tickers
        page.fill('#mt-tickers', 'SPY, AAPL, QQQ')
        
        # Compute metrics
        page.click('#mt-btn')
        page.wait_for_timeout(12000)
        
        # Verify table populated
        table_rows = page.locator('#mt-table tbody tr')
        row_count = table_rows.count()
        table_populated = row_count >= 3
        print(f"    {'✅' if table_populated else '❌'} Metrics table populated ({row_count} rows)")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/07_metrics_table_multi_ticker.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'Metrics Table',
            'tickers': 'SPY, AAPL, QQQ',
            'row_count': row_count,
            'table_populated': table_populated,
            'result': 'PASS' if table_populated else 'FAIL'
        })
        
        # --------------------------------------------------------------------
        # Subtab 7: Custom Scenarios
        # --------------------------------------------------------------------
        print("\n  [7/8] Custom Scenarios...")
        page.locator('a.nav-link:has-text("Custom Scenarios")').click()
        page.wait_for_timeout(1500)
        
        # Enter scenario name
        page.fill('#cs-name', 'Test Scenario')
        
        # Select analysis type: HV
        page.select_option('#cs-analysis-type', value='hv')
        
        # Enter tickers
        page.fill('#cs-tickers', 'SPY, AAPL')
        
        # Run scenario
        page.click('#cs-btn')
        page.wait_for_timeout(10000)
        
        # Verify chart rendered
        cs_chart = page.locator('#cs-chart .js-plotly-plot')
        cs_chart_visible = cs_chart.is_visible()
        
        # Verify results panel populated
        cs_results = page.locator('#cs-results').inner_text()
        results_populated = len(cs_results) > 50  # Should have scenario name + ticker results
        print(f"    {'✅' if cs_chart_visible else '❌'} Scenario chart rendered")
        print(f"    {'✅' if results_populated else '❌'} Results panel populated")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/08_custom_scenario_hv.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'Custom Scenarios',
            'scenario_name': 'Test Scenario',
            'analysis_type': 'hv',
            'chart_rendered': cs_chart_visible,
            'results_populated': results_populated,
            'result': 'PASS' if (cs_chart_visible and results_populated) else 'FAIL'
        })
        
        # --------------------------------------------------------------------
        # Subtab 8: Alerts & Diagnostics
        # --------------------------------------------------------------------
        print("\n  [8/8] Alerts & Diagnostics...")
        page.locator('a.nav-link:has-text("Alerts")').click()
        page.wait_for_timeout(1500)
        
        # Refresh diagnostics
        page.click('#alert-refresh')
        page.wait_for_timeout(5000)
        
        # Verify API status populated
        api_status = page.locator('#alert-api-status').inner_text()
        api_ok = 'yfinance' in api_status.lower()
        
        # Verify timestamp updated
        timestamp = page.locator('#alert-timestamp').inner_text()
        timestamp_updated = 'Updated:' in timestamp or 'Last updated:' in timestamp
        print(f"    {'✅' if api_ok else '❌'} API status displayed")
        print(f"    {'✅' if timestamp_updated else '❌'} Timestamp updated")
        
        # Screenshot
        screenshot_path = f'{SCREENSHOT_DIR}/09_alerts_diagnostics.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        results['tests'].append({
            'subtab': 'Alerts & Diagnostics',
            'api_status_ok': api_ok,
            'timestamp_updated': timestamp_updated,
            'result': 'PASS' if (api_ok and timestamp_updated) else 'FAIL'
        })
        
        # ====================================================================
        # LOOP 3: FINAL SCREENSHOT & SUMMARY
        # ====================================================================
        print("\n[LOOP 3] Capturing final state and generating summary...")
        
        # Final screenshot: Back to Historical HV tab
        page.locator('a.nav-link:has-text("Historical HV")').click()
        page.wait_for_timeout(1500)
        screenshot_path = f'{SCREENSHOT_DIR}/10_final_state.png'
        page.screenshot(path=screenshot_path)
        results['screenshots'].append(screenshot_path)
        
        # ====================================================================
        # RESULTS SUMMARY
        # ====================================================================
        results['end_time'] = datetime.now().isoformat()
        results['total_tests'] = len(results['tests'])
        results['passed_tests'] = sum(1 for t in results['tests'] if t.get('result') == 'PASS')
        results['failed_tests'] = results['total_tests'] - results['passed_tests']
        results['total_screenshots'] = len(results['screenshots'])
        results['console_error_count'] = len([e for e in results['console_errors'] if 'error' in e.lower()])
        
        # Save results to JSON
        results_file = f'{SCREENSHOT_DIR}/test_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"  Total Tests:       {results['total_tests']}")
        print(f"  Passed:            {results['passed_tests']} ✅")
        print(f"  Failed:            {results['failed_tests']} {'❌' if results['failed_tests'] > 0 else ''}")
        print(f"  Screenshots:       {results['total_screenshots']}")
        print(f"  Console Errors:    {results['console_error_count']}")
        print(f"  Results saved to:  {results_file}")
        print("="*80)
        
        # Close browser
        browser.close()
        
        # Assert all tests passed
        assert results['failed_tests'] == 0, f"{results['failed_tests']} subtab tests failed!"
        
        print("\n✅ VOLATILITY LAB FULL E2E TEST PASSED!")


if __name__ == '__main__':
    import os
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    test_volatility_lab_full_e2e()
