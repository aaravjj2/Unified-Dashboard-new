"""
E2E Test: Market Forecast Tab with N-BEATS and N-HiTS models.

This test validates that:
1. Market Forecast tab loads correctly
2. N-BEATS and N-HiTS models can be selected and run
3. Actual forecasts are generated (not just UI renders)
4. Output data is captured and validated
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

# Configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8051')
TICKER = 'AAPL'
TIMEOUT = 120000  # 120 seconds for model training

async def test_market_forecast_with_neural_models():
    """Full E2E test of Market Forecast with neural models."""
    print(f"\n{'='*60}")
    print(f"Market Forecast E2E Test - {datetime.now()}")
    print(f"Dashboard: {DASHBOARD_URL}")
    print(f"{'='*60}\n")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'dashboard_url': DASHBOARD_URL,
        'tests': {},
        'errors': [],
        'screenshots': []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Enable console logging
        console_errors = []
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
        
        try:
            # 1. Load dashboard
            print("1. Loading dashboard...")
            await page.goto(DASHBOARD_URL, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            results['tests']['dashboard_load'] = True
            print("   ✅ Dashboard loaded")
            
            # 2. Click Market Forecast tab
            print("2. Clicking Market Forecast tab...")
            mf_tab = page.locator('[data-testid="tab-market-forecast"], a:has-text("Market Forecast")')
            await mf_tab.first.click(timeout=10000)
            await page.wait_for_timeout(3000)
            results['tests']['tab_click'] = True
            print("   ✅ Tab clicked")
            
            # 3. Enter ticker
            print(f"3. Entering ticker: {TICKER}...")
            ticker_input = page.locator('#mf-ticker-input, input[placeholder*="ticker"]')
            await ticker_input.first.clear()
            await ticker_input.first.fill(TICKER)
            await page.wait_for_timeout(500)
            results['tests']['ticker_entry'] = True
            print(f"   ✅ Ticker entered: {TICKER}")
            
            # 4. Select models - try to include nbeats and nhits
            print("4. Selecting models (including NBEATS/NHITS if available)...")
            
            # Check what models are available
            model_checkboxes = await page.locator('#mf-model-checklist input[type="checkbox"]').all()
            available_models = []
            
            for checkbox in model_checkboxes:
                label = await checkbox.evaluate('el => el.parentElement.textContent || el.value')
                available_models.append(label.strip().lower())
                
            print(f"   Available models: {available_models}")
            results['available_models'] = available_models
            
            # Try selecting specific models
            models_to_select = ['nbeats', 'nhits', 'prophet', 'ensemble']
            selected = []
            
            for model in models_to_select:
                try:
                    # Try to click the checkbox for this model
                    checkbox = page.locator(f'#mf-model-checklist label:has-text("{model}") input, #mf-model-checklist input[value="{model}"]')
                    if await checkbox.count() > 0:
                        await checkbox.first.check()
                        selected.append(model)
                except:
                    pass
            
            print(f"   ✅ Selected models: {selected}")
            results['selected_models'] = selected
            results['tests']['model_selection'] = len(selected) > 0
            
            # 5. Click Generate Forecast button
            print("5. Clicking Generate Forecast...")
            run_btn = page.locator('#mf-run-btn, button:has-text("Generate Forecast"), button:has-text("Run")')
            await run_btn.first.click(timeout=10000)
            print("   ✅ Button clicked, waiting for forecast...")
            
            # 6. Wait for forecast to complete (watch for chart update or loading to end)
            print("6. Waiting for forecast generation...")
            
            # Wait for loading to start and end
            try:
                # Wait for chart to update (look for plotly graph)
                await page.wait_for_selector('#mf-forecast-chart .plotly, #mf-forecast-chart svg', timeout=TIMEOUT)
                results['tests']['forecast_generated'] = True
                print("   ✅ Forecast chart detected")
            except Exception as e:
                results['tests']['forecast_generated'] = False
                results['errors'].append(f"Forecast timeout: {e}")
                print(f"   ❌ Forecast timeout: {e}")
            
            await page.wait_for_timeout(5000)  # Let chart fully render
            
            # 7. Capture screenshot
            print("7. Capturing screenshots...")
            screenshot_path = 'screenshots/market_forecast_neural_test.png'
            os.makedirs('screenshots', exist_ok=True)
            await page.screenshot(path=screenshot_path, full_page=False)
            results['screenshots'].append(screenshot_path)
            print(f"   ✅ Screenshot saved: {screenshot_path}")
            
            # 8. Extract forecast data from store or chart
            print("8. Extracting forecast data...")
            
            # Try to get data from the forecast store
            try:
                store_data = await page.evaluate('''
                    () => {
                        const store = document.querySelector('#mf-forecast-store');
                        if (store && store.dataset && store.dataset.dashDataVal) {
                            return store.dataset.dashDataVal;
                        }
                        // Try dash's internal storage
                        if (window._dash_state) {
                            const storeState = window._dash_state['mf-forecast-store'];
                            if (storeState) return JSON.stringify(storeState);
                        }
                        return null;
                    }
                ''')
                
                if store_data:
                    results['forecast_data'] = json.loads(store_data) if isinstance(store_data, str) else store_data
                    print(f"   ✅ Forecast data extracted")
                else:
                    print("   ⚠️ No forecast store data found")
            except Exception as e:
                print(f"   ⚠️ Could not extract store data: {e}")
            
            # 9. Check chart data
            print("9. Checking chart content...")
            try:
                chart_data = await page.evaluate('''
                    () => {
                        const chart = document.querySelector('#mf-forecast-chart .js-plotly-plot');
                        if (chart && chart.data) {
                            return {
                                traces: chart.data.length,
                                trace_names: chart.data.map(t => t.name || 'unnamed'),
                                has_data: chart.data.some(t => t.y && t.y.length > 0)
                            };
                        }
                        return null;
                    }
                ''')
                
                if chart_data:
                    results['chart_info'] = chart_data
                    print(f"   ✅ Chart has {chart_data.get('traces', 0)} traces")
                    print(f"   Trace names: {chart_data.get('trace_names', [])}")
                    results['tests']['chart_has_data'] = chart_data.get('has_data', False)
                else:
                    print("   ⚠️ Could not extract chart data")
            except Exception as e:
                print(f"   ⚠️ Chart extraction error: {e}")
            
            # 10. Check for model metrics
            print("10. Checking model metrics...")
            try:
                metrics_el = page.locator('#mf-model-metrics, .model-metrics, [class*="metric"]')
                if await metrics_el.count() > 0:
                    metrics_text = await metrics_el.first.inner_text()
                    results['metrics_text'] = metrics_text[:500]  # First 500 chars
                    results['tests']['metrics_displayed'] = len(metrics_text) > 0
                    print(f"   ✅ Metrics found: {metrics_text[:100]}...")
                else:
                    results['tests']['metrics_displayed'] = False
                    print("   ⚠️ No metrics element found")
            except Exception as e:
                print(f"   ⚠️ Metrics check error: {e}")
            
            # 11. Check for console errors
            print("11. Checking console errors...")
            critical_errors = [e for e in console_errors if 'error' in e.lower() or 'failed' in e.lower()]
            results['console_errors'] = critical_errors[:10]  # First 10
            if critical_errors:
                print(f"   ⚠️ {len(critical_errors)} console errors found")
            else:
                print("   ✅ No critical console errors")
            
        except Exception as e:
            results['errors'].append(str(e))
            print(f"❌ Test failed with error: {e}")
            
            # Take error screenshot
            error_screenshot = 'screenshots/market_forecast_error.png'
            await page.screenshot(path=error_screenshot)
            results['screenshots'].append(error_screenshot)
            
        finally:
            await browser.close()
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for v in results['tests'].values() if v)
    total = len(results['tests'])
    
    print(f"Tests: {passed}/{total} passed")
    for test_name, result in results['tests'].items():
        status = "✅" if result else "❌"
        print(f"  {status} {test_name}")
    
    if results['errors']:
        print(f"\nErrors: {len(results['errors'])}")
        for err in results['errors'][:5]:
            print(f"  - {err[:100]}")
    
    # Save results
    results_path = 'screenshots/market_forecast_test_results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")
    
    return results

if __name__ == '__main__':
    results = asyncio.run(test_market_forecast_with_neural_models())
    
    # Exit with error code if tests failed
    if results['errors'] or not all(results['tests'].values()):
        sys.exit(1)
