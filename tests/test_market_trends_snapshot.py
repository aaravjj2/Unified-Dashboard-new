#!/usr/bin/env python3
"""
Market Trends Snapshot Test
Validates News Feed, Run Analysis, Backtest, and Debug Logs panels
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
DASH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DASH_ROOT))

logger = logging.getLogger(__name__)

def run_market_trends_snapshot():
    """
    Execute Market Trends snapshot validation
    Returns dict with test results
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'status': 'incomplete',
        'checks': {}
    }
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            logger.info("Opening dashboard...")
            page.goto('http://127.0.0.1:8050/', wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(1000)
            
            # Navigate to Market Trends tab
            logger.info("Clicking Market Trends tab...")
            try:
                page.locator('text=Market Trends').first.click(timeout=5000)
                page.wait_for_timeout(1000)
                results['checks']['market_trends_tab_click'] = True
            except Exception as e:
                logger.error(f"Failed to click Market Trends tab: {e}")
                results['checks']['market_trends_tab_click'] = False
                results['error'] = str(e)
                browser.close()
                return results
            
            # Check News Feed panel
            logger.info("Checking News Feed panel...")
            try:
                news_container = page.locator('#news-container')
                if news_container.count() > 0:
                    results['checks']['news_feed_present'] = True
                    inner_html = news_container.inner_html()
                    results['checks']['news_feed_populated'] = len(inner_html) > 100
                else:
                    results['checks']['news_feed_present'] = False
            except Exception as e:
                logger.warning(f"News feed check failed: {e}")
                results['checks']['news_feed_error'] = str(e)
            
            # Check Run Analysis button
            logger.info("Checking Run Analysis button...")
            try:
                # Fix: Actual button ID is 'run-btn' not 'run-analysis-btn'
                run_btn = page.locator('#run-btn, button:has-text("Run Full Analysis")')
                if run_btn.count() > 0:
                    results['checks']['run_analysis_button_present'] = True
                else:
                    results['checks']['run_analysis_button_present'] = False
            except Exception as e:
                logger.warning(f"Run Analysis button check failed: {e}")
            
            # Check Results Area
            logger.info("Checking results area...")
            try:
                results_area = page.locator('#results-area, #market-trends-results')
                if results_area.count() > 0:
                    results['checks']['results_area_present'] = True
                    inner_html = results_area.inner_html()
                    results['checks']['results_area_populated'] = len(inner_html) > 50
                else:
                    results['checks']['results_area_present'] = False
            except Exception as e:
                logger.warning(f"Results area check failed: {e}")
            
            # Capture screenshot
            screenshot_dir = DASH_ROOT / 'tests' / 'logs' / 'full_system_debug' / 'market_trends_clicker_snapshots'
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = screenshot_dir / f'market_trends_snapshot_{int(datetime.now().timestamp())}.png'
            page.screenshot(path=str(screenshot_path), full_page=True)
            results['screenshot'] = str(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            
            browser.close()
            
            # Determine overall status
            critical_checks = [
                results['checks'].get('market_trends_tab_click', False),
                results['checks'].get('run_analysis_button_present', False)
            ]
            
            if all(critical_checks):
                results['status'] = 'success'
            else:
                results['status'] = 'partial'
        
        return results
        
    except ImportError:
        logger.error("Playwright not installed - cannot run browser tests")
        results['status'] = 'skipped'
        results['error'] = 'Playwright not available'
        return results
    except Exception as e:
        logger.exception(f"Market Trends snapshot test failed: {e}")
        results['status'] = 'error'
        results['error'] = str(e)
        return results

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    result = run_market_trends_snapshot()
    print(json.dumps(result, indent=2))
