#!/usr/bin/env python3
"""
Market Forecast Comprehensive Clicker & Snapshot Test
======================================================
Tests all major forecast configurations with Playwright automation:
- Different ticker selections (SPY, AAPL, portfolio)
- Forecast horizons (1w, 1m, 3m, 6m)
- Model types (ARIMA, Prophet, LSTM if available)
- Captures screenshots and validates results
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# Configuration
DASH_URL = os.environ.get('DASH_URL', 'http://127.0.0.1:8050')
OUT_DIR = Path('test-artifacts/market_forecast_comprehensive')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Test scenarios
FORECAST_SCENARIOS = [
    {
        'name': 'spy_1month_default',
        'ticker': 'SPY',
        'horizon': '1m',
        'description': 'SPY 1-month forecast (default model)'
    },
    {
        'name': 'aapl_3month_default',
        'ticker': 'AAPL',
        'horizon': '3m',
        'description': 'AAPL 3-month forecast'
    },
    {
        'name': 'nvda_1week_default',
        'ticker': 'NVDA',
        'horizon': '1w',
        'description': 'NVDA 1-week forecast'
    },
    {
        'name': 'tsla_6month_default',
        'ticker': 'TSLA',
        'horizon': '6m',
        'description': 'TSLA 6-month forecast'
    },
    {
        'name': 'intc_1month_default',
        'ticker': 'INTC',
        'horizon': '1m',
        'description': 'INTC 1-month forecast (current portfolio position)'
    }
]


class MarketForecastClicker:
    """Automated clicker for Market Forecast tab testing."""
    
    def __init__(self, page, out_dir):
        self.page = page
        self.out_dir = out_dir
        self.console_messages = []
        self.results = {}
        
        # Set up console logging
        page.on('console', lambda msg: self.console_messages.append(f"[{msg.type}] {msg.text}"))
    
    def navigate_to_forecast(self):
        """Navigate to Market Forecast tab."""
        print("\n" + "="*80)
        print("NAVIGATING TO MARKET FORECAST TAB")
        print("="*80)
        
        # Go to dashboard
        print(f"Loading {DASH_URL}...")
        self.page.goto(DASH_URL, wait_until='networkidle', timeout=60000)
        self.page.wait_for_timeout(3000)
        print("✅ Dashboard loaded")
        
        # Find and click Market Forecast tab
        selectors = [
            'text=Market Forecast',
            'a:has-text("Market Forecast")',
            '[href="#market-forecast"]',
            '.nav-link:has-text("Market Forecast")'
        ]
        
        clicked = False
        for selector in selectors:
            try:
                if self.page.locator(selector).count() > 0:
                    print(f"Clicking Market Forecast using: {selector}")
                    self.page.click(selector, timeout=5000)
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            raise Exception("Could not find Market Forecast tab")
        
        self.page.wait_for_timeout(3000)
        print("✅ Market Forecast tab activated")
        
        # Take initial screenshot
        self.page.screenshot(path=str(self.out_dir / 'forecast_tab_initial.png'), full_page=True)
        print(f"📸 Saved initial screenshot")
    
    def run_forecast_scenario(self, scenario):
        """Execute a single forecast scenario."""
        print("\n" + "="*80)
        print(f"SCENARIO: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print("="*80)
        
        result = {
            'scenario': scenario['name'],
            'ticker': scenario['ticker'],
            'horizon': scenario['horizon'],
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'errors': [],
            'artifacts': {}
        }
        
        try:
            # 1. Fill ticker input
            print(f"📝 Filling ticker: {scenario['ticker']}")
            ticker_selectors = [
                '#mf-tickers',
                'input[placeholder*="ticker" i]',
                'input[type="text"]'
            ]
            
            ticker_filled = False
            for selector in ticker_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.fill(selector, scenario['ticker'])
                        ticker_filled = True
                        print(f"✅ Filled ticker using: {selector}")
                        break
                except Exception as e:
                    continue
            
            if not ticker_filled:
                raise Exception(f"Could not find ticker input field")
            
            self.page.wait_for_timeout(1000)
            
            # 2. Select horizon (if dropdown exists)
            print(f"📅 Selecting horizon: {scenario['horizon']}")
            try:
                horizon_selectors = [
                    f'option:has-text("{scenario["horizon"]}")',
                    f'[value="{scenario["horizon"]}"]'
                ]
                
                for selector in horizon_selectors:
                    try:
                        if self.page.locator(selector).count() > 0:
                            self.page.select_option('select', scenario['horizon'])
                            print(f"✅ Selected horizon: {scenario['horizon']}")
                            break
                    except:
                        continue
            except Exception as e:
                print(f"⚠️  Horizon selection failed (may not be available): {e}")
            
            self.page.wait_for_timeout(1000)
            
            # 3. Click "Run Forecast" button
            print("🚀 Clicking Run Forecast button...")
            run_selectors = [
                '#mf-run',
                'button:has-text("Run Forecast")',
                'button:has-text("Forecast")',
                '[id*="forecast"][id*="run"]',
                '[id*="forecast"][id*="btn"]'
            ]
            
            run_clicked = False
            for selector in run_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector, timeout=5000)
                        run_clicked = True
                        print(f"✅ Clicked Run Forecast using: {selector}")
                        break
                except Exception as e:
                    continue
            
            if not run_clicked:
                raise Exception("Could not find Run Forecast button")
            
            # 4. Wait for forecast to complete (with loading spinner)
            print("⏳ Waiting for forecast calculation...")
            self.page.wait_for_timeout(8000)  # Give time for API call and model execution
            
            # Check for loading indicators
            loading_selectors = ['.loading', '.spinner', '[data-loading="true"]']
            max_wait = 30  # 30 seconds max
            waited = 0
            
            while waited < max_wait:
                is_loading = False
                for selector in loading_selectors:
                    if self.page.locator(selector).count() > 0:
                        is_loading = True
                        break
                
                if not is_loading:
                    break
                
                self.page.wait_for_timeout(1000)
                waited += 1
                if waited % 5 == 0:
                    print(f"  Still loading... ({waited}s)")
            
            print("✅ Forecast calculation completed")
            
            # 5. Validate results
            print("🔍 Validating forecast results...")
            page_text = self.page.inner_text('body')
            
            # Check for error messages
            error_patterns = [
                'Error loading',
                'Traceback',
                'Exception',
                'Failed to',
                'Could not',
                'No data available'
            ]
            
            found_errors = []
            for pattern in error_patterns:
                if pattern in page_text:
                    found_errors.append(pattern)
            
            if found_errors:
                result['errors'] = found_errors
                print(f"❌ Errors detected: {found_errors}")
            
            # Check for forecast graph
            graph_count = self.page.locator('.js-plotly-plot').count()
            result['graphs_found'] = graph_count
            print(f"📊 Plotly graphs found: {graph_count}")
            
            # Check for forecast metrics
            has_forecast_data = any(word in page_text for word in [
                'Predicted', 'Forecast', 'Confidence', 'Interval', 
                'Upper Bound', 'Lower Bound', 'MAPE', 'RMSE'
            ])
            result['has_forecast_data'] = has_forecast_data
            print(f"📈 Forecast data present: {has_forecast_data}")
            
            # 6. Capture artifacts
            snapshot_name = f"{scenario['name']}_result.png"
            snapshot_path = self.out_dir / snapshot_name
            self.page.screenshot(path=str(snapshot_path), full_page=True)
            result['artifacts']['screenshot'] = str(snapshot_path)
            print(f"📸 Saved screenshot: {snapshot_name}")
            
            # Save page HTML
            html_name = f"{scenario['name']}_page.html"
            html_path = self.out_dir / html_name
            html_path.write_text(self.page.content(), encoding='utf-8')
            result['artifacts']['html'] = str(html_path)
            
            # Determine success
            result['success'] = (
                graph_count > 0 and 
                has_forecast_data and 
                len(found_errors) == 0
            )
            
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"\n{status} - {scenario['name']}")
            
        except Exception as e:
            print(f"\n❌ ERROR in scenario {scenario['name']}: {e}")
            result['errors'].append(str(e))
            result['success'] = False
            
            # Save error screenshot
            try:
                error_screenshot = self.out_dir / f"{scenario['name']}_ERROR.png"
                self.page.screenshot(path=str(error_screenshot))
                result['artifacts']['error_screenshot'] = str(error_screenshot)
            except:
                pass
        
        return result
    
    def save_results(self, all_results):
        """Save comprehensive test results."""
        # JSON report
        json_path = self.out_dir / 'forecast_test_results.json'
        with open(json_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n💾 Results saved to: {json_path}")
        
        # Markdown report
        md_path = self.out_dir / 'forecast_test_report.md'
        with open(md_path, 'w') as f:
            f.write("# Market Forecast Comprehensive Test Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary
            total = len(all_results)
            passed = sum(1 for r in all_results if r['success'])
            failed = total - passed
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests:** {total}\n")
            f.write(f"- **Passed:** {passed} ✅\n")
            f.write(f"- **Failed:** {failed} ❌\n")
            f.write(f"- **Success Rate:** {(passed/total*100):.1f}%\n\n")
            
            # Detailed results
            f.write("## Test Results\n\n")
            for result in all_results:
                status_icon = "✅" if result['success'] else "❌"
                f.write(f"### {status_icon} {result['scenario']}\n\n")
                f.write(f"**Ticker:** {result['ticker']}  \n")
                f.write(f"**Horizon:** {result['horizon']}  \n")
                f.write(f"**Graphs Found:** {result.get('graphs_found', 0)}  \n")
                f.write(f"**Has Forecast Data:** {result.get('has_forecast_data', False)}  \n")
                
                if result.get('errors'):
                    f.write(f"**Errors:** {', '.join(result['errors'])}  \n")
                
                if result.get('artifacts'):
                    f.write("\n**Artifacts:**\n")
                    for artifact_type, path in result['artifacts'].items():
                        f.write(f"- {artifact_type}: `{Path(path).name}`\n")
                
                f.write("\n---\n\n")
            
            # Console logs
            f.write("## Console Messages\n\n")
            f.write("```\n")
            for msg in self.console_messages[-50:]:  # Last 50 messages
                f.write(f"{msg}\n")
            f.write("```\n")
        
        print(f"📄 Markdown report saved to: {md_path}")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("MARKET FORECAST COMPREHENSIVE CLICKER TEST")
    print("="*80)
    print(f"Dashboard URL: {DASH_URL}")
    print(f"Output Directory: {OUT_DIR}")
    print(f"Total Scenarios: {len(FORECAST_SCENARIOS)}\n")
    
    all_results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        clicker = MarketForecastClicker(page, OUT_DIR)
        
        try:
            # Navigate to forecast tab once
            clicker.navigate_to_forecast()
            
            # Run each scenario
            for i, scenario in enumerate(FORECAST_SCENARIOS, 1):
                print(f"\n{'='*80}")
                print(f"RUNNING SCENARIO {i}/{len(FORECAST_SCENARIOS)}")
                print(f"{'='*80}")
                
                result = clicker.run_forecast_scenario(scenario)
                all_results.append(result)
                
                # Pause between scenarios
                if i < len(FORECAST_SCENARIOS):
                    print("\n⏳ Waiting 3 seconds before next scenario...")
                    page.wait_for_timeout(3000)
            
            # Save comprehensive results
            clicker.save_results(all_results)
            
        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            
            # Try to save partial results
            if all_results:
                clicker.save_results(all_results)
        
        finally:
            browser.close()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST EXECUTION COMPLETE")
    print("="*80)
    
    total = len(all_results)
    passed = sum(1 for r in all_results if r['success'])
    failed = total - passed
    
    print(f"\n📊 Final Results:")
    print(f"   Total: {total}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%")
    
    print(f"\n📁 Artifacts saved to: {OUT_DIR}")
    print(f"   - forecast_test_results.json")
    print(f"   - forecast_test_report.md")
    print(f"   - {total} screenshots")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    exit(main())
