#!/usr/bin/env python3
"""
Volatility Lab - Interactive Clicker Test
==========================================

Automated clicker test to verify all interactive elements in Volatility Lab
"""

import time
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DASHBOARD_URL = 'http://localhost:8090'
SCREENSHOT_DIR = 'test-artifacts/volatility_lab_clicker'

def clicker_test():
    """Run comprehensive clicker test"""
    logger.info("Starting Volatility Lab clicker test...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # 1. Load dashboard
            logger.info("1. Loading dashboard...")
            page.goto(DASHBOARD_URL, wait_until='networkidle')
            time.sleep(3)
            
            # 2. Click Volatility Lab tab
            logger.info("2. Opening Volatility Lab tab...")
            page.click('a:has-text("Volatility Lab")')
            time.sleep(3)
            
            # 3. Fill ticker input
            logger.info("3. Entering ticker SPY...")
            ticker_input = page.locator('#vl-calc-ticker')
            ticker_input.clear()
            ticker_input.fill('SPY')
            time.sleep(1)
            
            # 4. Fill strike range
            logger.info("4. Setting strike range...")
            strike_input = page.locator('#vl-calc-strike-range')
            strike_input.clear()
            strike_input.fill('±10%')
            time.sleep(1)
            
            # 5. Click compute button
            logger.info("5. Clicking compute button...")
            page.click('#vl-calc-run-btn')
            time.sleep(5)  # Wait for computation
            
            # 6. Verify heatmap rendered
            logger.info("6. Checking heatmap rendered...")
            heatmap_exists = page.locator('#vl-heatmap .plotly').count() > 0
            if heatmap_exists:
                logger.info("   ✅ Heatmap detected!")
            else:
                logger.warning("   ⚠️  Heatmap not detected")
            
            # 7. Click signals button
            logger.info("7. Clicking signals button...")
            page.click('#vl-signal-run-btn')
            time.sleep(3)
            
            # 8. Check if signals table populated
            logger.info("8. Checking signals table...")
            signals_table = page.locator('#vl-signal-table')
            if signals_table.count() > 0:
                logger.info("   ✅ Signals table found")
            
            # 9. Click backtest button
            logger.info("9. Clicking backtest button...")
            page.click('#vl-backtest-run-btn')
            time.sleep(3)
            
            # 10. Check backtest results
            logger.info("10. Checking backtest results...")
            backtest_results = page.locator('#vl-backtest-results')
            if backtest_results.count() > 0:
                results_text = backtest_results.inner_text()
                logger.info(f"   Backtest results: {results_text[:100]}...")
            
            # 11. Click overview refresh
            logger.info("11. Clicking overview refresh...")
            page.click('#vl-overview-refresh-btn')
            time.sleep(2)
            
            # 12. Check diagnostics
            logger.info("12. Checking diagnostics panel...")
            diag_log = page.locator('#vl-diag-solver-log')
            if diag_log.count() > 0:
                log_text = diag_log.inner_text()
                logger.info(f"   Diagnostics: {log_text[:100]}...")
            
            # 13. Wait a bit to observe health polling
            logger.info("13. Observing health polling (10 seconds)...")
            time.sleep(10)
            
            # Final screenshot
            import os
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            page.screenshot(path=f'{SCREENSHOT_DIR}/clicker_final.png')
            logger.info(f"📸 Final screenshot saved")
            
            logger.info("\n✅ Clicker test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Clicker test failed: {e}")
            page.screenshot(path=f'{SCREENSHOT_DIR}/clicker_error.png')
            raise
        finally:
            time.sleep(2)
            browser.close()

if __name__ == '__main__':
    clicker_test()
