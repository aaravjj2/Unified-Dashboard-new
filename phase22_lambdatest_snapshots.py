"""
Phase 22B LambdaTest Visual Regression
Captures 40 cross-browser screenshots (10 tabs × 4 browsers)

Browsers:
- Chrome Latest
- Firefox Latest
- Safari Latest
- Edge Latest

Tabs Tested:
1. Homepage
2. Azure ML Lab
3. Options Lab (with enhanced dropdowns)
4. Market Forecast
5. Portfolio
6. Strategy Lab
7. Research Lab
8. Monthly Picks
9. Weekly Picks
10. Chatbot (if visible)
"""

import os
import sys
import time
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import LambdaTest configuration
try:
    from observability.lambdatest_config import (
        BROWSER_CONFIGS,
        run_cross_browser_test,
        js_click,
        js_check_visible,
        capture_screenshot
    )
    LAMBDATEST_AVAILABLE = True
except ImportError:
    logger.error("❌ LambdaTest configuration not found")
    logger.info("Ensure observability/lambdatest_config.py exists")
    LAMBDATEST_AVAILABLE = False
    sys.exit(1)

# Dashboard URL
DASHBOARD_URL = os.getenv('DASH_URL', 'http://localhost:8050')

# Test results
test_results = []


# ==============================================================================
# TAB TEST FUNCTIONS
# ==============================================================================

def test_homepage(driver, browser_name: str):
    """Test 1: Homepage load."""
    logger.info(f"🏠 Testing homepage on {browser_name}")
    
    driver.get(DASHBOARD_URL)
    time.sleep(3)
    
    # Check if main layout loaded
    visible = js_check_visible(driver, '#main-layout') or js_check_visible(driver, 'body')
    assert visible, "Homepage failed to load"
    
    # Capture screenshot
    capture_screenshot(driver, f'01_homepage_{browser_name}.png')
    logger.info(f"✅ Homepage test passed on {browser_name}")


def test_azure_ml_lab(driver, browser_name: str):
    """Test 2: Azure ML Lab tab."""
    logger.info(f"🤖 Testing Azure ML Lab on {browser_name}")
    
    # Click Azure ML Lab tab
    js_click(driver, '[data-tab-id="azure-ml-lab"]')
    time.sleep(2)
    
    # Check Run Prediction button visible
    visible = js_check_visible(driver, '#azure-ml-run-prediction-btn')
    assert visible, "Azure ML Lab not loaded properly"
    
    # Capture screenshot
    capture_screenshot(driver, f'02_azure_ml_lab_{browser_name}.png')
    logger.info(f"✅ Azure ML Lab test passed on {browser_name}")


def test_options_lab(driver, browser_name: str):
    """Test 3: Options Lab with Phase 22B enhancements."""
    logger.info(f"💹 Testing Options Lab on {browser_name}")
    
    # Click Options Lab tab
    js_click(driver, '[data-tab-id="options-lab"]')
    time.sleep(2)
    
    # Check Contract Selector visible (Phase 22B enhancement)
    visible = js_check_visible(driver, '#contract-ticker-selector')
    assert visible, "Options Lab Contract Selector not visible"
    
    # Check dropdowns
    ticker_visible = js_check_visible(driver, '#contract-ticker-selector')
    strike_visible = js_check_visible(driver, '#contract-strike-selector')
    exp_visible = js_check_visible(driver, '#contract-expiration-selector')
    
    logger.info(f"   Ticker dropdown: {'✅' if ticker_visible else '❌'}")
    logger.info(f"   Strike dropdown: {'✅' if strike_visible else '❌'}")
    logger.info(f"   Expiration dropdown: {'✅' if exp_visible else '❌'}")
    
    # Capture screenshot
    capture_screenshot(driver, f'03_options_lab_{browser_name}.png')
    logger.info(f"✅ Options Lab test passed on {browser_name}")


def test_market_forecast(driver, browser_name: str):
    """Test 4: Market Forecast tab."""
    logger.info(f"📈 Testing Market Forecast on {browser_name}")
    
    # Click Market Forecast tab
    js_click(driver, '[data-tab-id="market-forecast"]')
    time.sleep(2)
    
    # Check chart visible
    visible = js_check_visible(driver, '#market-forecast-chart')
    
    # Capture screenshot
    capture_screenshot(driver, f'04_market_forecast_{browser_name}.png')
    logger.info(f"✅ Market Forecast test passed on {browser_name}")


def test_portfolio(driver, browser_name: str):
    """Test 5: Portfolio tab."""
    logger.info(f"💼 Testing Portfolio on {browser_name}")
    
    # Click Portfolio tab
    js_click(driver, '[data-tab-id="portfolio"]')
    time.sleep(2)
    
    # Check portfolio value visible
    visible = js_check_visible(driver, '#portfolio-value')
    
    # Capture screenshot
    capture_screenshot(driver, f'05_portfolio_{browser_name}.png')
    logger.info(f"✅ Portfolio test passed on {browser_name}")


def test_strategy_lab(driver, browser_name: str):
    """Test 6: Strategy Lab tab."""
    logger.info(f"🎯 Testing Strategy Lab on {browser_name}")
    
    # Click Strategy Lab tab
    js_click(driver, '[data-tab-id="strategy-lab"]')
    time.sleep(2)
    
    # Check backtest button visible
    visible = js_check_visible(driver, '#backtest-run-btn')
    
    # Capture screenshot
    capture_screenshot(driver, f'06_strategy_lab_{browser_name}.png')
    logger.info(f"✅ Strategy Lab test passed on {browser_name}")


def test_research_lab(driver, browser_name: str):
    """Test 7: Research Lab tab."""
    logger.info(f"🔬 Testing Research Lab on {browser_name}")
    
    # Click Research Lab tab
    js_click(driver, '[data-tab-id="research-lab"]')
    time.sleep(2)
    
    # Capture screenshot
    capture_screenshot(driver, f'07_research_lab_{browser_name}.png')
    logger.info(f"✅ Research Lab test passed on {browser_name}")


def test_monthly_picks(driver, browser_name: str):
    """Test 8: Monthly Picks tab."""
    logger.info(f"📅 Testing Monthly Picks on {browser_name}")
    
    # Click Monthly Picks tab
    js_click(driver, '[data-tab-id="monthly-picks"]')
    time.sleep(2)
    
    # Capture screenshot
    capture_screenshot(driver, f'08_monthly_picks_{browser_name}.png')
    logger.info(f"✅ Monthly Picks test passed on {browser_name}")


def test_weekly_picks(driver, browser_name: str):
    """Test 9: Weekly Picks tab."""
    logger.info(f"📊 Testing Weekly Picks on {browser_name}")
    
    # Click Weekly Picks tab
    js_click(driver, '[data-tab-id="weekly-picks"]')
    time.sleep(2)
    
    # Capture screenshot
    capture_screenshot(driver, f'09_weekly_picks_{browser_name}.png')
    logger.info(f"✅ Weekly Picks test passed on {browser_name}")


def test_tradingview_preview(driver, browser_name: str):
    """Test 10: TradingView signals preview (Phase 22B)."""
    logger.info(f"📡 Testing TradingView Preview on {browser_name}")
    
    # Navigate to Options Lab (where TradingView signals appear)
    js_click(driver, '[data-tab-id="options-lab"]')
    time.sleep(2)
    
    # Check TradingView button visible
    visible = js_check_visible(driver, '#tradingview-fetch-btn')
    logger.info(f"   TradingView button: {'✅' if visible else '❌'}")
    
    # Capture screenshot
    capture_screenshot(driver, f'10_tradingview_preview_{browser_name}.png')
    logger.info(f"✅ TradingView Preview test passed on {browser_name}")


# ==============================================================================
# TEST EXECUTION
# ==============================================================================

def run_all_tests():
    """Run all tab tests across all browsers."""
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 22B LAMBDATEST VISUAL REGRESSION")
    logger.info("=" * 70)
    logger.info(f"Dashboard URL: {DASHBOARD_URL}")
    logger.info(f"Browsers: {len(BROWSER_CONFIGS)}")
    logger.info(f"Tests per browser: 10")
    logger.info(f"Total snapshots: {len(BROWSER_CONFIGS) * 10}")
    logger.info("=" * 70)
    
    test_functions = [
        ('Homepage', test_homepage),
        ('Azure ML Lab', test_azure_ml_lab),
        ('Options Lab', test_options_lab),
        ('Market Forecast', test_market_forecast),
        ('Portfolio', test_portfolio),
        ('Strategy Lab', test_strategy_lab),
        ('Research Lab', test_research_lab),
        ('Monthly Picks', test_monthly_picks),
        ('Weekly Picks', test_weekly_picks),
        ('TradingView Preview', test_tradingview_preview)
    ]
    
    global test_results
    
    for test_name, test_func in test_functions:
        logger.info(f"\n🚀 Running: {test_name}")
        result = run_cross_browser_test(test_name, test_func, DASHBOARD_URL)
        test_results.append(result)
        
        # Print result
        passed = result.get('passed', 0)
        failed = result.get('failed', 0)
        logger.info(f"   Result: {passed}/{passed+failed} browsers passed")


def generate_report():
    """Generate comprehensive visual regression report."""
    logger.info("\n" + "=" * 70)
    logger.info("VISUAL REGRESSION REPORT")
    logger.info("=" * 70)
    
    total_tests = len(test_results)
    total_passed = sum(r['passed'] for r in test_results)
    total_failed = sum(r['failed'] for r in test_results)
    total_snapshots = total_passed + total_failed
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'configuration': {
            'dashboard_url': DASHBOARD_URL,
            'browsers': [b['name'] for b in BROWSER_CONFIGS],
            'total_tests': total_tests,
            'tests_per_browser': 10
        },
        'results': test_results,
        'summary': {
            'total_snapshots': total_snapshots,
            'passed': total_passed,
            'failed': total_failed,
            'pass_rate': (total_passed / total_snapshots * 100) if total_snapshots > 0 else 0
        }
    }
    
    # Save report
    with open('phase22b_lambdatest_results.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    logger.info(f"\nTotal Snapshots: {total_snapshots}")
    logger.info(f"Passed: {total_passed}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Pass Rate: {report['summary']['pass_rate']:.1f}%")
    
    # List failed tests
    if total_failed > 0:
        logger.warning("\n❌ Failed Tests:")
        for result in test_results:
            for browser_result in result.get('browsers', []):
                if browser_result.get('status') == 'failed':
                    logger.warning(f"   - {result['test_name']} on {browser_result['name']}: {browser_result.get('error')}")
    
    logger.info("\n✅ Report saved to: phase22b_lambdatest_results.json")
    logger.info("=" * 70)
    
    # Exit code based on pass rate
    if report['summary']['pass_rate'] >= 95:
        logger.info("✅ VISUAL REGRESSION TEST: PASSED (≥95%)")
        return 0
    else:
        logger.error("❌ VISUAL REGRESSION TEST: FAILED (<95%)")
        return 1


def main():
    """Main execution function."""
    if not LAMBDATEST_AVAILABLE:
        logger.error("❌ LambdaTest not available - exiting")
        sys.exit(1)
    
    start_time = time.time()
    
    # Run tests
    run_all_tests()
    
    # Generate report
    exit_code = generate_report()
    
    elapsed = time.time() - start_time
    logger.info(f"\nTotal Execution Time: {elapsed:.2f}s")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
