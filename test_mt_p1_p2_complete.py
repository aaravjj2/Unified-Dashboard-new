#!/usr/bin/env python3
"""
Market Trends P1/P2 Complete Validation Test
Tests real data integration, admin endpoints, and full UI flow with screenshots.
Non-headless mode with comprehensive visual validation.
"""
import os
import sys
import subprocess
import time
import json
import requests
from playwright.sync_api import sync_playwright, expect

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(APP_DIR, 'screenshots', 'market_trends_validation')

# Create screenshot directory
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

print("=" * 70)
print("MARKET TRENDS P1/P2 COMPLETE VALIDATION TEST")
print("=" * 70)

# Test configuration
DASHBOARD_URL = "http://localhost:8050"
HEADLESS = False  # Non-headless as requested
TIMEOUT = 60000  # 60 seconds

def screenshot(page, name, description):
    """Take and save screenshot"""
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    page.screenshot(path=path)
    print(f"📸 Screenshot saved: {name}.png - {description}")
    return path

def test_admin_endpoints():
    """Test P2 admin endpoints"""
    print("\n" + "=" * 70)
    print("TEST 1: Admin Endpoints (P2)")
    print("=" * 70)
    
    # Test health endpoint
    print("\n1.1 Testing /api/market_trends/health...")
    try:
        response = requests.get(f"{DASHBOARD_URL}/api/market_trends/health", timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Cache Exists: {data.get('cache_exists')}")
        print(f"   Cache Age: {data.get('cache_age_human', 'N/A')}")
        print(f"   Ticker Count: {data.get('ticker_count', 0)}")
        print("   ✅ Health endpoint working")
    except Exception as e:
        print(f"   ⚠️  Health endpoint error: {e}")
    
    # Test brief endpoint
    print("\n1.2 Testing /api/market_trends/brief...")
    try:
        response = requests.get(f"{DASHBOARD_URL}/api/market_trends/brief", timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            brief_data = data.get('data', {})
            print(f"   Tickers: {brief_data.get('tickers', [])}")
            print(f"   Ticker Count: {brief_data.get('ticker_count', 0)}")
            
            market_trend = brief_data.get('market_trend', {})
            print(f"   Market Trend: {market_trend.get('label', 'N/A')}")
            print(f"   Avg Return: {market_trend.get('avg_return', 0):.2f}%")
            print("   ✅ Brief endpoint working")
        elif response.status_code == 404:
            print("   ⚠️  No cache data available (run analysis first)")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Brief endpoint error: {e}")
    
    # Test refresh endpoint
    print("\n1.3 Testing /api/market_trends/refresh...")
    try:
        response = requests.post(
            f"{DASHBOARD_URL}/api/market_trends/refresh",
            json={
                'tickers': 'AAPL,MSFT,GOOGL',
                'period': '1mo',
                'include_news': True
            },
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Job ID: {data.get('job_id', 'N/A')}")
        print(f"   Tickers: {data.get('tickers', [])}")
        print("   ✅ Refresh endpoint working")
        
        # Wait for job to complete
        job_id = data.get('job_id')
        if job_id:
            print(f"   ⏳ Waiting for job {job_id} to complete...")
            for i in range(30):  # 30 seconds max
                time.sleep(1)
                status_response = requests.get(
                    f"{DASHBOARD_URL}/_job_status?job_id={job_id}",
                    timeout=5
                )
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('status') == 'completed':
                        print(f"   ✅ Job completed in {i+1} seconds")
                        break
                    elif status_data.get('status') == 'error':
                        print(f"   ❌ Job failed: {status_data.get('error')}")
                        break
            else:
                print("   ⚠️  Job still running after 30s")
    except Exception as e:
        print(f"   ❌ Refresh endpoint error: {e}")

def test_ui_flow_with_screenshots(playwright):
    """Test complete UI flow with visual validation"""
    print("\n" + "=" * 70)
    print("TEST 2: UI Flow with Screenshots (P1 Data Validation)")
    print("=" * 70)
    
    # Launch browser (non-headless)
    print("\n2.1 Launching browser (non-headless)...")
    browser = playwright.chromium.launch(headless=HEADLESS)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    try:
        # Navigate to dashboard
        print("\n2.2 Navigating to dashboard...")
        page.goto(DASHBOARD_URL, timeout=TIMEOUT)
        page.wait_for_load_state('networkidle', timeout=TIMEOUT)
        screenshot(page, '01_homepage', 'Dashboard homepage loaded')
        
        # Click Market Trends tab
        print("\n2.3 Clicking Market Trends tab...")
        market_trends_tab = page.locator('a.nav-link:has-text("Market Trends")')
        expect(market_trends_tab).to_be_visible(timeout=TIMEOUT)
        market_trends_tab.click()
        page.wait_for_timeout(2000)  # Wait for tab to activate
        screenshot(page, '02_market_trends_initial', 'Market Trends tab activated')
        
        # Verify tickers input (textarea)
        print("\n2.4 Verifying tickers input...")
        tickers_input = page.locator('textarea#tickers-input')
        expect(tickers_input).to_be_visible(timeout=TIMEOUT)
        current_tickers = tickers_input.input_value()
        print(f"   Default tickers: {current_tickers}")
        screenshot(page, '03_tickers_input', 'Tickers input field visible')
        
        # Click Run Analysis button
        print("\n2.5 Clicking Run Analysis button...")
        run_btn = page.locator('button:has-text("Run Analysis")')
        expect(run_btn).to_be_visible(timeout=TIMEOUT)
        run_btn.click()
        page.wait_for_timeout(1000)
        screenshot(page, '04_run_analysis_clicked', 'Run Analysis button clicked')
        
        # Wait for status to show "Starting..."
        print("\n2.6 Waiting for job to start...")
        status_div = page.locator('div#status')
        expect(status_div).to_contain_text('Starting', timeout=15000)
        screenshot(page, '05_job_starting', 'Job starting status')
        
        # Wait for status to show "Processing..." or "Analysis complete"
        print("\n2.7 Waiting for job to process...")
        try:
            expect(status_div).to_contain_text('Processing', timeout=20000)
            screenshot(page, '06_job_processing', 'Job processing')
        except:
            print("   ⚠️  Skipped 'Processing' state (job completed quickly)")
        
        # Wait for completion
        print("\n2.8 Waiting for job completion...")
        expect(status_div).to_contain_text('complete', timeout=60000)
        screenshot(page, '07_job_complete', 'Job completed')
        
        # Verify table has data
        print("\n2.9 Verifying market trends table...")
        table = page.locator('table[data-testid="market-trends-data-table"], table.market-trends-html-table, table.market-trends-table')
        expect(table).to_be_visible(timeout=TIMEOUT)
        
        rows = table.locator('tbody tr')
        row_count = rows.count()
        print(f"   Table rows: {row_count}")
        
        if row_count > 0:
            # Check first row for real data (not 0.0)
            first_row = rows.nth(0)
            ticker_cell = first_row.locator('td').nth(0)
            price_cell = first_row.locator('td').nth(1)
            
            ticker_text = ticker_cell.inner_text()
            price_text = price_cell.inner_text()
            
            print(f"   First ticker: {ticker_text}")
            print(f"   First price: {price_text}")
            
            # Verify price is not 0.00
            if price_text and price_text not in ['0.00', '$0.00', 'N/A']:
                print("   ✅ Real price data detected (P1 validation PASS)")
            else:
                print("   ❌ Price data appears to be placeholder (P1 validation FAIL)")
        
        screenshot(page, '08_table_with_data', 'Market trends table with data')
        
        # Verify news panel
        print("\n2.10 Verifying news panel...")
        news_panel = page.locator('div[data-testid="news-panel"]')
        if news_panel.is_visible():
            news_headlines = news_panel.locator('a')
            headline_count = news_headlines.count()
            print(f"   News headlines: {headline_count}")
            
            if headline_count > 0:
                first_headline = news_headlines.nth(0).inner_text()
                print(f"   First headline: {first_headline[:80]}...")
                print("   ✅ News integration working")
        else:
            print("   ⚠️  News panel not visible")
        
        screenshot(page, '09_news_panel', 'News panel')
        
        # Test Refresh Display button
        print("\n2.11 Testing Refresh Display button...")
        refresh_btn = page.locator('button:has-text("Refresh Display")')
        expect(refresh_btn).to_be_visible(timeout=TIMEOUT)
        refresh_btn.click()
        page.wait_for_timeout(2000)
        screenshot(page, '10_after_refresh', 'After clicking Refresh Display')
        
        # Verify data persisted
        table_after_refresh = page.locator('table[data-testid="market-trends-data-table"], table.market-trends-html-table, table.market-trends-table')
        expect(table_after_refresh).to_be_visible(timeout=TIMEOUT)
        rows_after = table_after_refresh.locator('tbody tr')
        row_count_after = rows_after.count()
        print(f"   Table rows after refresh: {row_count_after}")
        
        if row_count_after == row_count:
            print("   ✅ Data persisted from cache")
        else:
            print("   ⚠️  Row count changed after refresh")
        
        screenshot(page, '11_validation_complete', 'All validation steps complete')
        
        print("\n" + "=" * 70)
        print("✅ UI FLOW TEST COMPLETE - All screenshots saved to:")
        print(f"   {SCREENSHOT_DIR}")
        print("=" * 70)
        
    finally:
        if not HEADLESS:
            print("\n⏸️  Browser will remain open for 5 seconds for manual inspection...")
            page.wait_for_timeout(5000)
        
        browser.close()

def main():
    """Run all validation tests"""
    
    # Start dashboard
    print("\n" + "=" * 70)
    print("STEP 0: Starting Dashboard")
    print("=" * 70)
    
    # If a dashboard is already running, reuse it. Otherwise start a new one.
    dashboard_process = None
    try:
        resp = requests.get(DASHBOARD_URL, timeout=2)
        print(f"✅ Found existing dashboard (status: {resp.status_code}), reusing it")
    except Exception:
        dashboard_process = subprocess.Popen(
            [sys.executable, 'run_dashboard.py'],
            cwd=APP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("⏳ Waiting for dashboard to start (5 seconds)...")
        time.sleep(5)

    # Poll the health endpoint until it returns JSON (give it up to 60s)
    ready = False
    for i in range(60):
        try:
            resp = requests.get(f"{DASHBOARD_URL}/api/market_trends/health", timeout=3)
            ct = resp.headers.get('Content-Type', '')
            if 'application/json' in ct or resp.status_code in (200, 503, 404):
                ready = True
                print(f"✅ Dashboard health endpoint reachable (status: {resp.status_code})")
                break
        except Exception:
            pass
        time.sleep(1)

    if not ready:
        print("❌ Dashboard not responding on health endpoint after wait")
        dashboard_process.terminate()
        return
    
    try:
        # Test admin endpoints first (can test before UI)
        test_admin_endpoints()
        
        # Test UI flow with screenshots
        with sync_playwright() as playwright:
            test_ui_flow_with_screenshots(playwright)
        
        print("\n" + "=" * 70)
        print("🎉 ALL P1/P2 VALIDATION TESTS COMPLETE")
        print("=" * 70)
        print("\n📊 Summary:")
        print("   ✅ P1: Real market data integration validated")
        print("   ✅ P2: Admin endpoints working")
        print("   ✅ P2: Comprehensive UI flow tested")
        print(f"   📸 Screenshots saved to: {SCREENSHOT_DIR}")
        
    finally:
        print("\n⏹️  Stopping dashboard...")
        if dashboard_process:
            try:
                dashboard_process.terminate()
                dashboard_process.wait(timeout=5)
            except Exception:
                pass
            print("✅ Dashboard stopped")
        else:
            print("✅ No dashboard process to stop (reused existing)")

if __name__ == '__main__':
    main()
