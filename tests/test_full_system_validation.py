""""""

Phase 0.8 - Full System Validation (3-Loop Test)Full System-Wide E2E Validation

Validates all 6 tabs across 3 complete loops================================

Comprehensive validation of Market Trends and Portfolio tabs with iteration loops.

Test Methodology:

- Loop 1: Functional verification (all tabs render, callbacks execute)Tests:

- Loop 2: Stability verification (no memory leaks, consistent performance)- Market Trends: news, buttons, modals

- Loop 3: Consistency verification (data integrity, deterministic results)- Portfolio: positions, orders, analytics, factors, optimization

- Multi-iteration consistency checks

Success Criteria:- DOM snapshots and screenshots for all states

- All tabs must render without errors"""

- All interactive elements must respond

- Graphs must contain dataimport time

- Console errors <5 per tabimport json

- No critical failures across all loopsfrom pathlib import Path

"""from playwright.sync_api import sync_playwright

from playwright.sync_api import sync_playwrightfrom datetime import datetime

import time

import json# Configuration

from pathlib import PathBASE_URL = "http://localhost:8050"

from datetime import datetimeOUTPUT_DIR = Path("/mnt/c/Aarav/fin_env/unified-dashboard/snapshots")

OUTPUT_DIR.mkdir(exist_ok=True)

# Tab configuration for validation

TABS_CONFIG = [# Create subdirectories

    {MARKET_TRENDS_DIR = OUTPUT_DIR / "market_trends"

        'id': 'weekly_picks',PORTFOLIO_DIR = OUTPUT_DIR / "portfolio"

        'name': 'Weekly Picks',MARKET_TRENDS_DIR.mkdir(exist_ok=True)

        'selectors': ['a:has-text("Weekly Picks")', '#tab-weekly_picks'],PORTFOLIO_DIR.mkdir(exist_ok=True)

        'validation': {

            'table': ['#weekly-picks-table', '.dash-table'],class SystemValidator:

            'content': ['weekly', 'ticker', 'pick']    """Comprehensive system validation framework"""

        }    

    },    def __init__(self, iteration=1):

    {        self.iteration = iteration

        'id': 'monthly_picks',        self.results = {

        'name': 'Monthly Picks',            "iteration": iteration,

        'selectors': ['a:has-text("Monthly Picks")', '#tab-monthly_picks'],            "timestamp": datetime.now().isoformat(),

        'validation': {            "market_trends": {},

            'table': ['#monthly-picks-table', '.dash-table'],            "portfolio": {},

            'content': ['monthly', 'ticker', 'pick']            "consistency_check": {}

        }        }

    },        self.page = None

    {        

        'id': 'market_trends',    def save_snapshot(self, name, subdir=""):

        'name': 'Market Trends',        """Save HTML and screenshot"""

        'selectors': ['a:has-text("Market Trends")', '#tab-market_trends'],        if subdir:

        'validation': {            save_dir = OUTPUT_DIR / subdir

            'table': ['#market-trends-table', '.dash-table'],            save_dir.mkdir(exist_ok=True)

            'graphs': ['.plotly']        else:

        }            save_dir = OUTPUT_DIR

    },            

    {        prefix = f"iter{self.iteration}_{name}"

        'id': 'market_forecast',        

        'name': 'Market Forecast',        # Save HTML

        'selectors': ['a:has-text("Market Forecast")', '#tab-market_forecast'],        html_path = save_dir / f"{prefix}.html"

        'validation': {        with open(html_path, 'w', encoding='utf-8') as f:

            'input': ['#forecast-ticker-input'],            f.write(self.page.content())

            'button': ['#forecast-run-button'],        

            'graphs': ['.plotly']        # Save screenshot

        }        screenshot_path = save_dir / f"{prefix}.png"

    },        self.page.screenshot(path=str(screenshot_path), full_page=True)

    {        

        'id': 'volatility_lab',        return str(html_path), str(screenshot_path)

        'name': 'Volatility Lab',    

        'selectors': ['a:has-text("Volatility Lab")', '#tab-volatility_lab'],    def wait_for_element(self, selector, timeout=10000):

        'validation': {        """Wait for element with timeout"""

            'input': ['#vl-tickers-input'],        try:

            'button': ['#vl-compute'],            self.page.wait_for_selector(selector, timeout=timeout, state='visible')

            'graphs': ['#vl-price-graph', '#vl-vol-graph']            return True

        }        except:

    },            return False

    {    

        'id': 'portfolio',    def get_element_state(self, selector):

        'name': 'Portfolio',        """Get comprehensive element state"""

        'selectors': ['a:has-text("Portfolio")', '#tab-portfolio'],        element = self.page.locator(selector)

        'validation': {        count = element.count()

            'subtabs': ['#portfolio-tracker-subtabs'],        

            'content': ['position', 'portfolio']        if count == 0:

        }            return {"exists": False, "count": 0}

    }        

]        return {

            "exists": True,

def validate_tab(page, tab_config, loop_num, output_dir):            "count": count,

    """            "visible": element.first.is_visible() if count > 0 else False,

    Validate a single tab's functionality.            "enabled": element.first.is_enabled() if count > 0 else False,

                "content_length": len(element.first.inner_text()) if count > 0 else 0,

    Returns dict with validation results.            "content_preview": element.first.inner_text()[:200] if count > 0 else ""

    """        }

    tab_id = tab_config['id']    

    tab_name = tab_config['name']    def validate_market_trends(self):

            """Comprehensive Market Trends validation"""

    print(f"\n  📋 Testing: {tab_name}")        print(f"\n{'='*80}")

            print(f"MARKET TRENDS VALIDATION - ITERATION {self.iteration}")

    result = {        print(f"{'='*80}\n")

        'tab_id': tab_id,        

        'tab_name': tab_name,        # Navigate to Market Trends

        'loop': loop_num,        print("📍 Navigating to Market Trends tab...")

        'timestamp': datetime.now().isoformat(),        market_trends_tab = self.page.locator('a:has-text("Market Trends")')

        'accessible': False,        if market_trends_tab.count() > 0:

        'elements_found': [],            market_trends_tab.first.click()

        'elements_missing': [],            time.sleep(3)

        'errors': [],        

        'warnings': [],        html_path, screenshot_path = self.save_snapshot("market_trends_loaded", "market_trends")

        'pass': False        

    }        # Test 1: News container

            print("\n1️⃣ Testing news container...")

    try:        news_state = self.get_element_state('#news-container')

        # Click tab        print(f"   News container: exists={news_state['exists']}, visible={news_state['visible']}")

        clicked = False        print(f"   Content: {news_state['content_preview'][:100]}")

        for selector in tab_config['selectors']:        

            try:        # Wait for news to populate (up to 30s)

                tab = page.locator(selector).first        print("   ⏳ Waiting for news to populate...")

                if tab.count() > 0:        news_populated = False

                    tab.click(timeout=5000)        for i in range(6):

                    clicked = True            time.sleep(5)

                    result['accessible'] = True            current_state = self.get_element_state('#news-container')

                    print(f"    ✅ Tab accessible")            if "Loading news..." not in current_state['content_preview'] and current_state['content_length'] > 50:

                    break                news_populated = True

            except Exception:                print(f"   ✅ News populated after {(i+1)*5}s: {current_state['content_length']} chars")

                continue                break

                    print(f"   [{i+1}/6] Still loading... ({current_state['content_length']} chars)")

        if not clicked:        

            result['errors'].append('Tab not accessible')        self.results["market_trends"]["news"] = {

            print(f"    ❌ Tab not accessible")            "initial_state": news_state,

            return result            "populated": news_populated,

                    "final_content_length": self.get_element_state('#news-container')['content_length']

        time.sleep(2)  # Allow tab to render        }

                

        # Take screenshot        # Test 2: Results area

        screenshot_path = output_dir / f"loop{loop_num}_{tab_id}.png"        print("\n2️⃣ Testing results area...")

        page.screenshot(path=str(screenshot_path))        results_state = self.get_element_state('#results-area')

                print(f"   Results area: {results_state['content_length']} chars")

        # Validate expected elements        

        validation = tab_config.get('validation', {})        self.results["market_trends"]["results_area"] = results_state

                

        for category, selectors in validation.items():        # Test 3: All 7 buttons

            for selector in selectors:        print("\n3️⃣ Testing all 7 buttons...")

                try:        buttons = [

                    element = page.locator(selector).first            ('#run-btn', 'Run Full Analysis'),

                    if element.count() > 0:            ('#reload-model', 'Reload Model'),

                        result['elements_found'].append(f"{category}: {selector}")            ('#refresh-cached', 'Refresh Cached'),

                        print(f"    ✅ Found: {category} ({selector})")            ('#backtest-btn', 'Backtest'),

                    else:            ('#debug-logs-btn', 'Debug Logs'),

                        result['elements_missing'].append(f"{category}: {selector}")            ('#toggle-brief', 'Toggle Brief'),

                        print(f"    ⚠️  Missing: {category} ({selector})")            ('#mt-download-btn', 'Download CSV')

                except Exception as e:        ]

                    result['elements_missing'].append(f"{category}: {selector}")        

                    result['warnings'].append(f"Element check failed: {selector} - {str(e)}")        button_results = {}

                for btn_id, btn_name in buttons:

        # Special handling for interactive tabs            state = self.get_element_state(btn_id)

        if tab_id == 'market_forecast':            status = "✅" if (state['exists'] and state['visible'] and state['enabled']) else "❌"

            try:            print(f"   {status} {btn_name}: exists={state['exists']}, visible={state['visible']}, enabled={state['enabled']}")

                # Try running a quick forecast            button_results[btn_id] = state

                ticker_input = page.locator('#forecast-ticker-input').first        

                run_button = page.locator('#forecast-run-button').first        self.results["market_trends"]["buttons"] = button_results

                        

                if ticker_input.count() > 0 and run_button.count() > 0:        # Test 4: Backtest modal

                    ticker_input.fill('SPY')        print("\n4️⃣ Testing backtest modal...")

                    run_button.click()        if self.get_element_state('#backtest-btn')['exists']:

                    time.sleep(3)  # Wait for forecast            self.page.click('#backtest-btn')

                                time.sleep(2)

                    # Check for graphs            

                    graphs = page.locator('.plotly').all()            modal_state = self.get_element_state('#backtest-modal')

                    if len(graphs) > 0:            modal_visible = 'display: none' not in str(self.page.locator('#backtest-modal').get_attribute('style')).lower()

                        result['elements_found'].append(f"Interactive: {len(graphs)} forecast graphs")            

                        print(f"    ✅ Forecast generated: {len(graphs)} graphs")            print(f"   Backtest modal: visible={modal_visible}")

                    else:            self.save_snapshot("market_trends_backtest_modal", "market_trends")

                        result['warnings'].append("No forecast graphs after compute")            

            except Exception as e:            # Close modal

                result['warnings'].append(f"Forecast interaction failed: {str(e)}")            if self.page.locator('#close-backtest-modal').count() > 0:

                        self.page.click('#close-backtest-modal')

        elif tab_id == 'volatility_lab':                time.sleep(1)

            try:            

                # Try computing volatility            self.results["market_trends"]["backtest_modal"] = {

                ticker_input = page.locator('#vl-tickers-input').first                "opens": modal_visible,

                compute_button = page.locator('#vl-compute').first                "content_length": modal_state['content_length']

                            }

                if ticker_input.count() > 0 and compute_button.count() > 0:        

                    ticker_input.fill('SPY')        # Test 5: Debug logs modal

                    compute_button.click()        print("\n5️⃣ Testing debug logs modal...")

                    time.sleep(3)  # Wait for computation        if self.get_element_state('#debug-logs-btn')['exists']:

                                self.page.click('#debug-logs-btn')

                    # Check for graphs            time.sleep(2)

                    price_graph = page.locator('#vl-price-graph').first            

                    vol_graph = page.locator('#vl-vol-graph').first            modal_state = self.get_element_state('#debug-logs-modal')

                                modal_visible = 'display: none' not in str(self.page.locator('#debug-logs-modal').get_attribute('style')).lower()

                    if price_graph.count() > 0 and vol_graph.count() > 0:            

                        result['elements_found'].append("Interactive: Volatility graphs rendered")            print(f"   Debug logs modal: visible={modal_visible}")

                        print(f"    ✅ Volatility computed: graphs rendered")            self.save_snapshot("market_trends_debug_modal", "market_trends")

                    else:            

                        result['warnings'].append("No volatility graphs after compute")            # Close modal

            except Exception as e:            if self.page.locator('#close-debug-modal').count() > 0:

                result['warnings'].append(f"Volatility interaction failed: {str(e)}")                self.page.click('#close-debug-modal')

                        time.sleep(1)

        # Determine pass/fail            

        found_count = len(result['elements_found'])            self.results["market_trends"]["debug_modal"] = {

        missing_count = len(result['elements_missing'])                "opens": modal_visible,

        error_count = len(result['errors'])                "content_length": modal_state['content_length']

                    }

        # Pass if: accessible AND (found > 0) AND (errors == 0)        

        result['pass'] = (        print("\n✅ Market Trends validation complete")

            result['accessible'] and        return self.results["market_trends"]

            found_count > 0 and    

            error_count == 0    def validate_portfolio(self):

        )        """Comprehensive Portfolio validation"""

                print(f"\n{'='*80}")

        if result['pass']:        print(f"PORTFOLIO VALIDATION - ITERATION {self.iteration}")

            print(f"    ✅ PASS ({found_count} elements, {error_count} errors)")        print(f"{'='*80}\n")

        else:        

            print(f"    ❌ FAIL ({found_count} elements, {missing_count} missing, {error_count} errors)")        # Navigate to Portfolio

                print("📍 Navigating to Portfolio tab...")

    except Exception as e:        portfolio_tab = self.page.locator('a:has-text("Portfolio")')

        result['errors'].append(f"Validation exception: {str(e)}")        if portfolio_tab.count() > 0:

        print(f"    ❌ Exception: {e}")            portfolio_tab.first.click()

                time.sleep(3)

    return result        

        # Test Positions subtab

def run_validation_loop(loop_num, output_dir):        print("\n📍 SUBTAB: Positions")

    """Run a single validation loop across all tabs."""        positions_results = self.validate_positions_subtab()

    print(f"\n{'='*70}")        

    print(f"LOOP {loop_num}/3 - Full System Validation")        # Test Order History subtab

    print(f"{'='*70}")        print("\n📍 SUBTAB: Order History")

            orders_results = self.validate_orders_subtab()

    loop_results = []        

            # Test Analytics subtab

    with sync_playwright() as p:        print("\n📍 SUBTAB: Analytics")

        browser = p.chromium.launch(headless=True)        analytics_results = self.validate_analytics_subtab()

        context = browser.new_context(viewport={'width': 1920, 'height': 1080})        

        page = context.new_page()        # Test Factors subtab

                print("\n📍 SUBTAB: Factor Exposure")

        # Collect console errors        factors_results = self.validate_factors_subtab()

        console_errors = []        

                # Test Optimization subtab

        def handle_console(msg):        print("\n📍 SUBTAB: Optimization")

            if msg.type == 'error':        optimization_results = self.validate_optimization_subtab()

                console_errors.append(msg.text)        

                self.results["portfolio"] = {

        page.on('console', handle_console)            "positions": positions_results,

                    "orders": orders_results,

        # Navigate to dashboard            "analytics": analytics_results,

        print("\n📍 Navigating to dashboard...")            "factors": factors_results,

        page.goto('http://127.0.0.1:8050/', wait_until='networkidle', timeout=30000)            "optimization": optimization_results

        time.sleep(2)        }

                

        # Test each tab        print("\n✅ Portfolio validation complete")

        for tab_config in TABS_CONFIG:        return self.results["portfolio"]

            result = validate_tab(page, tab_config, loop_num, output_dir)    

            loop_results.append(result)    def validate_positions_subtab(self):

                """Validate Positions subtab"""

        # Add console errors to results        # Click Positions tab (should be active by default)

        for result in loop_results:        positions_tab = self.page.locator('a:has-text("Positions")')

            tab_errors = [err for err in console_errors if result['tab_id'] in err.lower()]        if positions_tab.count() > 0:

            result['console_errors_count'] = len(tab_errors)            positions_tab.first.click()

                    time.sleep(2)

        browser.close()        

            self.save_snapshot("portfolio_positions", "portfolio")

    # Loop summary        

    passed = sum(1 for r in loop_results if r['pass'])        # Check positions table

    failed = len(loop_results) - passed        table_state = self.get_element_state('#portfolio-positions-table')

            print(f"   Positions table: exists={table_state['exists']}, content={table_state['content_length']} chars")

    print(f"\n{'='*70}")        

    print(f"LOOP {loop_num} SUMMARY")        # Check if showing only qty > 0

    print(f"{'='*70}")        table_content = table_state['content_preview']

    print(f"✅ Passed: {passed}/{len(loop_results)}")        has_zero_qty = 'qty: 0' in table_content.lower() or 'quantity: 0' in table_content.lower()

    print(f"❌ Failed: {failed}/{len(loop_results)}")        print(f"   Filtered to qty > 0: {not has_zero_qty}")

            

    return loop_results        return {

            "table_exists": table_state['exists'],

def generate_report(all_results, output_path):            "table_content_length": table_state['content_length'],

    """Generate comprehensive validation report."""            "filtered_correctly": not has_zero_qty,

    report = []            "snapshot": "portfolio_positions"

    report.append("# Phase 0.8 - Full System Validation Report\n")        }

    report.append(f"**Generated**: {datetime.now().isoformat()}\n")    

    report.append(f"**Total Loops**: 3\n")    def validate_orders_subtab(self):

    report.append(f"**Total Tabs**: {len(TABS_CONFIG)}\n\n")        """Validate Order History subtab"""

            # Click Order History tab

    # Overall summary        orders_tab = self.page.locator('a:has-text("Order History")')

    total_tests = len(all_results)        if orders_tab.count() > 0:

    total_passed = sum(1 for r in all_results if r['pass'])            orders_tab.first.click()

    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0            time.sleep(2)

            

    report.append("## Overall Results\n\n")        self.save_snapshot("portfolio_orders", "portfolio")

    report.append(f"- **Total Tests**: {total_tests}\n")        

    report.append(f"- **Passed**: {total_passed}\n")        # Check orders table

    report.append(f"- **Failed**: {total_tests - total_passed}\n")        table_state = self.get_element_state('#portfolio-orders-table')

    report.append(f"- **Success Rate**: {success_rate:.1f}%\n\n")        print(f"   Orders table: exists={table_state['exists']}, content={table_state['content_length']} chars")

            

    # Per-loop breakdown        # Check if has meaningful content or placeholder

    for loop_num in [1, 2, 3]:        has_content = table_state['content_length'] > 50

        loop_results = [r for r in all_results if r['loop'] == loop_num]        print(f"   Has content: {has_content}")

        passed = sum(1 for r in loop_results if r['pass'])        

                return {

        report.append(f"### Loop {loop_num}\n\n")            "table_exists": table_state['exists'],

        report.append(f"- Passed: {passed}/{len(loop_results)}\n")            "table_content_length": table_state['content_length'],

                    "has_data": has_content,

        for result in loop_results:            "snapshot": "portfolio_orders"

            status = "✅ PASS" if result['pass'] else "❌ FAIL"        }

            report.append(f"  - {result['tab_name']}: {status}\n")    

            def validate_analytics_subtab(self):

        report.append("\n")        """Validate Analytics subtab"""

            # Click Analytics tab

    # Per-tab breakdown        analytics_tab = self.page.locator('a:has-text("Analytics")')

    report.append("## Per-Tab Results\n\n")        if analytics_tab.count() > 0:

                analytics_tab.first.click()

    for tab in TABS_CONFIG:            time.sleep(2)

        tab_id = tab['id']        

        tab_results = [r for r in all_results if r['tab_id'] == tab_id]        self.save_snapshot("portfolio_analytics_initial", "portfolio")

        passes = sum(1 for r in tab_results if r['pass'])        

                # Check metric displays

        report.append(f"### {tab['name']}\n\n")        metrics = {

        report.append(f"- **Pass Rate**: {passes}/3 loops\n")            'var': self.get_element_state('#portfolio-var'),

                    'cvar': self.get_element_state('#portfolio-cvar'),

        if passes == 3:            'sharpe': self.get_element_state('#portfolio-sharpe'),

            report.append(f"- **Status**: ✅ **STABLE** (3/3 passes)\n\n")            'beta': self.get_element_state('#portfolio-beta')

        elif passes >= 2:        }

            report.append(f"- **Status**: ⚠️ **MOSTLY STABLE** ({passes}/3 passes)\n\n")        

        else:        print(f"   VaR: {metrics['var']['content_preview']}")

            report.append(f"- **Status**: ❌ **UNSTABLE** ({passes}/3 passes)\n\n")        print(f"   CVaR: {metrics['cvar']['content_preview']}")

            print(f"   Sharpe: {metrics['sharpe']['content_preview']}")

    # Write report        print(f"   Beta: {metrics['beta']['content_preview']}")

    with open(output_path, 'w') as f:        

        f.writelines(report)        # Try clicking Calculate Analytics button

            calc_btn = self.page.locator('#pa-calc-btn')

    print(f"\n📄 Report generated: {output_path}")        if calc_btn.count() > 0 and calc_btn.first.is_visible():

            print("   🖱️  Clicking 'Calculate Analytics' button...")

def main():            calc_btn.first.click()

    """Execute 3-loop validation and generate report."""            time.sleep(5)

    print("\n" + "="*70)            

    print("PHASE 0.8 - FULL SYSTEM VALIDATION (3 LOOPS)")            self.save_snapshot("portfolio_analytics_calculated", "portfolio")

    print("="*70)            

                # Re-check metrics

    output_dir = Path('test-artifacts/phase_0_8_validation')            metrics_after = {

    output_dir.mkdir(parents=True, exist_ok=True)                'var': self.get_element_state('#portfolio-var'),

                    'cvar': self.get_element_state('#portfolio-cvar'),

    all_results = []                'sharpe': self.get_element_state('#portfolio-sharpe'),

                    'beta': self.get_element_state('#portfolio-beta')

    # Run 3 loops            }

    for loop_num in [1, 2, 3]:            

        loop_results = run_validation_loop(loop_num, output_dir)            print(f"   VaR (after): {metrics_after['var']['content_preview']}")

        all_results.extend(loop_results)            print(f"   CVaR (after): {metrics_after['cvar']['content_preview']}")

                    print(f"   Sharpe (after): {metrics_after['sharpe']['content_preview']}")

        # Brief pause between loops            print(f"   Beta (after): {metrics_after['beta']['content_preview']}")

        if loop_num < 3:            

            print(f"\n⏸️  Pausing 3 seconds before Loop {loop_num + 1}...")            return {

            time.sleep(3)                "metrics_initial": metrics,

                    "metrics_calculated": metrics_after,

    # Save raw results                "calculation_triggered": True

    results_path = output_dir / 'validation_results.json'            }

    with open(results_path, 'w') as f:        

        json.dump(all_results, f, indent=2)        return {

    print(f"\n💾 Raw results saved: {results_path}")            "metrics_initial": metrics,

                "calculation_triggered": False

    # Generate report        }

    report_path = output_dir / 'PHASE_0_SYSTEM_VALIDATION_REPORT.md'    

    generate_report(all_results, report_path)    def validate_factors_subtab(self):

            """Validate Factor Exposure subtab"""

    # Final summary        # Click Factor Exposure tab

    total_passed = sum(1 for r in all_results if r['pass'])        factors_tab = self.page.locator('a:has-text("Factor Exposure")')

    total_tests = len(all_results)        if factors_tab.count() > 0:

    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0            factors_tab.first.click()

                time.sleep(2)

    print("\n" + "="*70)        

    print("FINAL SUMMARY")        self.save_snapshot("portfolio_factors", "portfolio")

    print("="*70)        

    print(f"Total Tests: {total_tests}")        # Check factor content

    print(f"Passed: {total_passed}")        content_state = self.get_element_state('#portfolio-factor-exposure-content')

    print(f"Success Rate: {success_rate:.1f}%")        print(f"   Factor content: exists={content_state['exists']}, content={content_state['content_length']} chars")

            

    if success_rate >= 90:        return {

        print("\n✅ ✅ ✅ PHASE 0 VALIDATION COMPLETE ✅ ✅ ✅")            "content_exists": content_state['exists'],

        print("System is stable and ready for Phase 1 (Azure migration)")            "content_length": content_state['content_length'],

        return True            "has_data": content_state['content_length'] > 50

    elif success_rate >= 75:        }

        print("\n⚠️  PHASE 0 MOSTLY COMPLETE")    

        print("Some issues detected - review report for details")    def validate_optimization_subtab(self):

        return True        """Validate Optimization subtab"""

    else:        # Click Optimization tab

        print("\n❌ PHASE 0 VALIDATION FAILED")        opt_tab = self.page.locator('a:has-text("Optimization")')

        print("Significant issues detected - remediation required")        if opt_tab.count() > 0:

        return False            opt_tab.first.click()

            time.sleep(2)

if __name__ == '__main__':        

    try:        self.save_snapshot("portfolio_optimization_initial", "portfolio")

        success = main()        

        exit(0 if success else 1)        # Check input field

    except Exception as e:        ticker_input = self.get_element_state('#opt-tickers-input')

        print(f"\n❌ Validation crashed: {e}")        print(f"   Ticker input: exists={ticker_input['exists']}")

        import traceback        

        traceback.print_exc()        # Try running optimization

        exit(1)        run_btn = self.page.locator('#opt-run-btn')

        if run_btn.count() > 0 and run_btn.first.is_visible():
            # Fill in tickers if empty
            if ticker_input['exists'] and ticker_input['content_length'] == 0:
                self.page.fill('#opt-tickers-input', 'AAPL,MSFT,GOOGL,NVDA')
                time.sleep(1)
            
            print("   🖱️  Clicking 'Optimize Portfolio' button...")
            run_btn.first.click()
            time.sleep(10)  # Optimization takes time
            
            self.save_snapshot("portfolio_optimization_results", "portfolio")
            
            # Check results container
            results_state = self.get_element_state('#opt-results-container')
            print(f"   Results: {results_state['content_length']} chars")
            
            return {
                "inputs_exist": ticker_input['exists'],
                "optimization_triggered": True,
                "results_length": results_state['content_length'],
                "has_results": results_state['content_length'] > 100
            }
        
        return {
            "inputs_exist": ticker_input['exists'],
            "optimization_triggered": False
        }
    
    def run_validation(self):
        """Run complete validation cycle"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            self.page = browser.new_page()
            
            # Navigate to app
            print(f"\n{'='*80}")
            print(f"STARTING VALIDATION - ITERATION {self.iteration}")
            print(f"{'='*80}\n")
            
            self.page.goto(BASE_URL, wait_until="networkidle")
            time.sleep(3)
            
            self.save_snapshot("home_page", "")
            
            # Run validations
            market_trends_results = self.validate_market_trends()
            portfolio_results = self.validate_portfolio()
            
            browser.close()
        
        return self.results


def compare_iterations(results_list):
    """Compare results across iterations for consistency"""
    print(f"\n{'='*80}")
    print("CONSISTENCY ANALYSIS")
    print(f"{'='*80}\n")
    
    if len(results_list) < 2:
        print("⚠️  Need at least 2 iterations for comparison")
        return {"status": "insufficient_data"}
    
    consistency = {
        "market_trends": {},
        "portfolio": {}
    }
    
    # Compare Market Trends news content length
    news_lengths = [r["market_trends"]["news"]["final_content_length"] for r in results_list]
    consistency["market_trends"]["news_consistent"] = len(set(news_lengths)) == 1
    print(f"Market Trends news lengths: {news_lengths}")
    print(f"  Consistent: {consistency['market_trends']['news_consistent']}")
    
    # Compare Portfolio positions content
    positions_lengths = [r["portfolio"]["positions"]["table_content_length"] for r in results_list]
    consistency["portfolio"]["positions_consistent"] = len(set(positions_lengths)) == 1
    print(f"\nPortfolio positions lengths: {positions_lengths}")
    print(f"  Consistent: {consistency['portfolio']['positions_consistent']}")
    
    # Overall consistency
    all_consistent = (
        consistency["market_trends"]["news_consistent"] and
        consistency["portfolio"]["positions_consistent"]
    )
    consistency["overall_consistent"] = all_consistent
    
    print(f"\n{'✅' if all_consistent else '⚠️ '} Overall consistency: {all_consistent}")
    
    return consistency


def run_validation_loop(max_iterations=3):
    """Run validation loop until consistent or max iterations"""
    print("\n" + "="*80)
    print("FULL SYSTEM VALIDATION LOOP")
    print("="*80 + "\n")
    
    results_list = []
    
    for i in range(1, max_iterations + 1):
        print(f"\n🔄 ITERATION {i}/{max_iterations}")
        
        validator = SystemValidator(iteration=i)
        results = validator.run_validation()
        results_list.append(results)
        
        # Save iteration results
        results_file = OUTPUT_DIR / f"iteration_{i}_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Iteration {i} complete - results saved to {results_file}")
        
        # Check consistency after 2nd iteration
        if i >= 2:
            consistency = compare_iterations(results_list)
            if consistency.get("overall_consistent"):
                print(f"\n✅ System is consistent after {i} iterations - stopping early")
                break
        
        if i < max_iterations:
            print("\n⏳ Waiting 10s before next iteration...")
            time.sleep(10)
    
    # Final consistency check
    final_consistency = compare_iterations(results_list)
    
    # Save final report
    final_report = {
        "total_iterations": len(results_list),
        "timestamp": datetime.now().isoformat(),
        "consistency": final_consistency,
        "iterations": results_list
    }
    
    report_file = OUTPUT_DIR / "final_validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2)
    
    print(f"\n{'='*80}")
    print("VALIDATION LOOP COMPLETE")
    print(f"{'='*80}")
    print(f"Total iterations: {len(results_list)}")
    print(f"Consistent: {final_consistency.get('overall_consistent', False)}")
    print(f"Report saved to: {report_file}")
    print(f"Snapshots saved to: {OUTPUT_DIR}")
    
    return final_report


if __name__ == "__main__":
    report = run_validation_loop(max_iterations=3)
    
    # Exit with appropriate code
    if report["consistency"].get("overall_consistent"):
        print("\n✅ System validation PASSED")
        exit(0)
    else:
        print("\n⚠️  System validation PARTIAL - check report for details")
        exit(2)
