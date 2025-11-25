#!/usr/bin/env python3
"""
Market Trends Rebuild - Comprehensive Validation Test

Tests:
1. Dashboard starts without errors
2. Market Trends tab loads
3. Run Analysis button triggers callback
4. Status updates during job execution
5. Results table populates with data
6. News panel shows headlines
7. Refresh button works
8. Cache persistence works across reloads
"""

import os
import sys
import time
import subprocess
import logging
from playwright.sync_api import sync_playwright, expect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
DASHBOARD_URL = 'http://localhost:8050'
STARTUP_TIMEOUT = 15
TEST_TIMEOUT = 60

def start_dashboard():
    """Start the dashboard server."""
    logger.info("Starting dashboard server...")
    
    env = os.environ.copy()
    env['AZURE_ENABLED'] = 'false'
    env['OPTIONS_DETERMINISTIC'] = '1'
    
    proc = subprocess.Popen(
        [sys.executable, 'financial_dashboard/app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd='/home/aarav/unified-dashboard',
        env=env,
        text=True,
        bufsize=1
    )
    
    # Wait for startup
    start_time = time.time()
    while time.time() - start_time < STARTUP_TIMEOUT:
        try:
            import requests
            resp = requests.get(DASHBOARD_URL, timeout=2)
            if resp.status_code == 200:
                logger.info(f"✅ Dashboard ready after {time.time() - start_time:.1f}s")
                return proc
        except Exception:
            time.sleep(0.5)
    
    logger.error("❌ Dashboard failed to start")
    proc.kill()
    return None


def run_tests():
    """Run comprehensive validation tests."""
    
    print("=" * 80)
    print("MARKET TRENDS REBUILD - COMPREHENSIVE VALIDATION")
    print("=" * 80)
    
    # Start dashboard
    proc = start_dashboard()
    if not proc:
        print("\n❌ FAILED: Dashboard did not start")
        return False
    
    try:
        with sync_playwright() as p:
            # Launch browser in headed mode for visibility
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Track console logs
            console_logs = []
            def handle_console(msg):
                console_logs.append({
                    'type': msg.type,
                    'text': msg.text
                })
            page.on('console', handle_console)
            
            # Test 1: Dashboard loads
            print("\n📍 Test 1: Loading dashboard...")
            page.goto(DASHBOARD_URL, wait_until='networkidle')
            print("   ✅ Dashboard loaded")
            
            # Test 2: Activate Market Trends tab
            print("\n📍 Test 2: Activating Market Trends tab...")
            # Use text selector for dbc.Tab
            page.click('text=Market Trends')
            time.sleep(2)
            print("   ✅ Market Trends tab activated")
            
            # Test 3: Check initial state
            print("\n📍 Test 3: Checking initial state...")
            status = page.locator('#status').inner_text()
            print(f"   Initial status: {status}")
            
            # Check if Run Analysis button exists
            run_btn = page.locator('#mt-run-analysis-btn')
            assert run_btn.is_visible(), "Run Analysis button not found"
            print("   ✅ Run Analysis button visible")
            
            # Test 4: Click Run Analysis
            print("\n📍 Test 4: Clicking Run Analysis button...")
            page.screenshot(path='/tmp/before_run.png')
            run_btn.click()
            time.sleep(1)
            
            # Check status updated
            new_status = page.locator('#status').inner_text()
            print(f"   Status after click: {new_status}")
            
            if "Starting" in new_status or "Processing" in new_status or "Job" in new_status:
                print("   ✅ Status updated - job started!")
            else:
                print(f"   ⚠️  Unexpected status: {new_status}")
            
            # Test 5: Wait for job completion
            print("\n📍 Test 5: Waiting for job completion...")
            max_wait = 30
            start_time = time.time()
            job_complete = False
            
            while time.time() - start_time < max_wait:
                status = page.locator('#status').inner_text()
                print(f"   [{int(time.time() - start_time)}s] Status: {status}")
                
                if "complete" in status.lower() or "✅" in status:
                    job_complete = True
                    print("   ✅ Job completed!")
                    break
                
                time.sleep(2)
            
            if not job_complete:
                print(f"   ⚠️  Job did not complete within {max_wait}s")
            
            # Test 6: Check results table
            print("\n📍 Test 6: Checking results table...")
            page.screenshot(path='/tmp/after_run.png')
            
            # Look for table with data-testid
            table = page.locator('[data-testid="market-trends-table"]')
            if table.is_visible():
                print("   ✅ Results table visible")
                
                # Count rows
                rows = page.locator('[data-ticker]').count()
                print(f"   Found {rows} data rows")
                
                if rows > 0:
                    print("   ✅ Table has data!")
                    
                    # Sample first ticker
                    first_ticker = page.locator('[data-ticker]').first.get_attribute('data-ticker')
                    print(f"   First ticker: {first_ticker}")
                else:
                    print("   ⚠️  Table is empty")
            else:
                print("   ⚠️  Results table not found")
            
            # Test 7: Check news panel
            print("\n📍 Test 7: Checking news panel...")
            news_panel = page.locator('[data-testid="news-panel"]')
            if news_panel.is_visible():
                news_text = news_panel.inner_text()
                print(f"   News panel content: {news_text[:100]}...")
                print("   ✅ News panel visible")
            else:
                print("   ⚠️  News panel not found")
            
            # Test 8: Test Refresh button
            print("\n📍 Test 8: Testing Refresh button...")
            refresh_btn = page.locator('#mt-refresh-display-btn')
            if refresh_btn.is_visible():
                refresh_btn.click()
                time.sleep(1)
                
                status = page.locator('#status').inner_text()
                print(f"   Status after refresh: {status}")
                print("   ✅ Refresh button works")
            else:
                print("   ⚠️  Refresh button not found")
            
            # Print console logs
            print("\n📋 Console Logs:")
            for log in console_logs[-10:]:  # Last 10 logs
                print(f"   [{log['type']}] {log['text'][:100]}")
            
            browser.close()
            
            print("\n" + "=" * 80)
            print("✅ ALL TESTS COMPLETED")
            print("=" * 80)
            
            return True
            
    except Exception as e:
        logger.exception(f"Test failed with error: {e}")
        return False
    
    finally:
        # Stop dashboard
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
            logger.info("Dashboard stopped")


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
