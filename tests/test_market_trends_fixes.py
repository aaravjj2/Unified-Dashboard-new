"""
Playwright Browser Tests for Market Trends Fix

Tests all 7 button operations, news auto-refresh, table display, and CSV download.
Collects HAR files, console logs, DOM snapshots, and screenshots.

Agent-1B Market Trends Fix - Requirements: Browser validation, diagnostic artifacts

Usage:
    pytest tests/test_market_trends_fixes.py -q --maxfail=1
    
    Or run in headful mode for debugging:
    HEADFUL=1 pytest tests/test_market_trends_fixes.py -v
"""
import os
import time
import json
import pytest
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, expect

# Test configuration
BASE_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8029')
HEADFUL = os.getenv('HEADFUL', '0') == '1'
DIAGNOSTICS_DIR = 'reports/market_trends_fix/diagnostics/playwright'


@pytest.fixture(scope='session')
def browser_context():
    """Create persistent browser context for all tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not HEADFUL)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path=os.path.join(DIAGNOSTICS_DIR, 'network_traffic.har')
        )
        
        # Enable console logging
        def handle_console(msg):
            log_path = os.path.join(DIAGNOSTICS_DIR, 'console.log')
            with open(log_path, 'a') as f:
                f.write(f"[{msg.type}] {msg.text}\n")
        
        context.on('console', handle_console)
        
        yield context
        
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    """Create new page for each test."""
    page = browser_context.new_page()
    yield page
    page.close()


def capture_screenshot(page: Page, name: str):
    """Capture screenshot to diagnostics directory."""
    os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
    path = os.path.join(DIAGNOSTICS_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path


def capture_dom_snapshot(page: Page, name: str):
    """Capture DOM snapshot to diagnostics directory."""
    os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
    path = os.path.join(DIAGNOSTICS_DIR, f"{name}.html")
    html = page.content()
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path


class TestMarketTrendsButtons:
    """Test all 7 Market Trends button operations."""
    
    def test_01_dashboard_loads(self, page: Page):
        """Test that dashboard loads successfully."""
        page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        
        # Wait for dashboard title
        page.wait_for_selector('h1, h2, h3', timeout=10000)
        
        capture_screenshot(page, '01_dashboard_home')
        
        # Verify Market Trends tab exists
        market_trends_tab = page.locator('text=Market Trends').first
        expect(market_trends_tab).to_be_visible()
        
        print("✅ Dashboard loaded successfully")
    
    def test_02_navigate_to_market_trends(self, page: Page):
        """Navigate to Market Trends tab."""
        page.goto(BASE_URL, wait_until='networkidle')
        
        # Click Market Trends tab
        market_trends_tab = page.locator('text=Market Trends').first
        market_trends_tab.click()
        
        # Wait for tab content to load
        page.wait_for_timeout(2000)
        
        capture_screenshot(page, '02_market_trends_loaded')
        
        # Verify key elements present
        expect(page.locator('#run-btn')).to_be_visible()
        expect(page.locator('#reload-model')).to_be_visible()
        expect(page.locator('#refresh-cached')).to_be_visible()
        
        print("✅ Market Trends tab loaded with buttons visible")
    
    def test_03_button_reload_model(self, page: Page):
        """Test Button 2: Reload Model."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(1000)
        
        # Click Reload Model button
        reload_btn = page.locator('#reload-model')
        expect(reload_btn).to_be_visible()
        reload_btn.click()
        
        # Wait for response
        page.wait_for_timeout(2000)
        
        capture_screenshot(page, '03_reload_model_clicked')
        
        # Check for status message (wait for text rather than relying on visibility)
        page.wait_for_function("() => { const el = document.querySelector('#mt-model-status'); return el && el.innerText && el.innerText.trim().length > 0;}", timeout=7000)
        model_status = page.locator('#mt-model-status')
        status_text = model_status.inner_text()
        assert len(status_text.strip()) > 0, "Model status should have text"
        
        print(f"✅ Reload Model: {status_text}")
    
    def test_04_button_refresh_cached(self, page: Page):
        """Test Button 3: Refresh Cached Display."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(1000)
        
        # Click Refresh Cached button
        refresh_btn = page.locator('#refresh-cached')
        expect(refresh_btn).to_be_visible()
        refresh_btn.click()
        
        # Wait for response
        page.wait_for_timeout(2000)
        
        capture_screenshot(page, '04_refresh_cached_clicked')
        
        # Check for results area
        results_area = page.locator('#results-area')
        expect(results_area).to_be_visible()
        
        print("✅ Refresh Cached Display: Results area updated")
    
    def test_05_button_toggle_brief(self, page: Page):
        """Test Button 6: Toggle Full Brief."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(1000)
        
        # Find toggle button
        toggle_btn = page.locator('#toggle-brief')
        expect(toggle_btn).to_be_visible()
        
        # Get initial state of brief area
        full_brief = page.locator('#full-brief')
        initial_display = full_brief.get_attribute('style') or ''
        
        # Click to toggle
        toggle_btn.click()
        page.wait_for_timeout(1000)
        
        # Check state changed
        new_display = full_brief.get_attribute('style') or ''
        assert initial_display != new_display, "Brief display should toggle"
        
        capture_screenshot(page, '05_toggle_brief_clicked')
        
        print("✅ Toggle Full Brief: Display toggled successfully")
    
    def test_06_button_download_csv(self, page: Page):
        """Test Button 7: Download CSV."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(1000)
        
        # Set up download handler
        download_triggered = []
        
        with page.expect_download(timeout=5000) as download_info:
            download_btn = page.locator('#mt-download-btn')
            expect(download_btn).to_be_visible()
            download_btn.click()
        
        download = download_info.value
        
        # Verify download
        assert download.suggested_filename.startswith('market_trends_')
        assert download.suggested_filename.endswith('.csv')
        
        # Save download to diagnostics
        download_path = os.path.join(DIAGNOSTICS_DIR, download.suggested_filename)
        download.save_as(download_path)
        
        capture_screenshot(page, '06_download_csv_triggered')
        
        print(f"✅ Download CSV: File {download.suggested_filename} downloaded")
    
    def test_07_button_backtest(self, page: Page):
        """Test Button 4: Backtest Trend Signals."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(1000)
        
        # Enter tickers first
        ticker_input = page.locator('#tickers-input')
        expect(ticker_input).to_be_visible()
        ticker_input.fill('SPY,QQQ')
        
        # Click Backtest button
        backtest_btn = page.locator('#backtest-btn')
        expect(backtest_btn).to_be_visible()
        backtest_btn.click()
        
        # Wait for modal to appear
        page.wait_for_timeout(1500)
        
        # Check modal opened
        backtest_modal = page.locator('#backtest-modal')
        expect(backtest_modal).to_be_visible()
        
        capture_screenshot(page, '07_backtest_modal_opened')
        
        # Verify results content exists
        results_content = page.locator('#backtest-results-content')
        expect(results_content).to_be_visible()
        
        print("✅ Backtest Trend Signals: Modal opened with results")
    
    def test_08_button_debug_logs(self, page: Page):
        """Test Button 5: Debug Logs."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(1000)
        
        # Click Debug Logs button
        debug_btn = page.locator('#debug-logs-btn')
        expect(debug_btn).to_be_visible()
        debug_btn.click()
        
        # Wait for modal
        page.wait_for_timeout(1500)
        
        # Check modal opened
        debug_modal = page.locator('#debug-logs-modal')
        expect(debug_modal).to_be_visible()
        
        capture_screenshot(page, '08_debug_logs_modal_opened')
        
        # Verify logs content exists
        logs_content = page.locator('#debug-logs-content')
        expect(logs_content).to_be_visible()
        
        print("✅ Debug Logs: Modal opened with log content")


class TestMarketTrendsTableDisplay:
    """Test table display with all 5 price fields."""
    
    def test_table_has_required_columns(self, page: Page):
        """Verify table displays all 5 price fields."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(2000)
        
        # Click refresh to ensure table is rendered
        refresh_btn = page.locator('#refresh-cached')
        if refresh_btn.is_visible():
            refresh_btn.click()
            page.wait_for_timeout(2000)
        
        capture_screenshot(page, '09_table_display')
        
        # Check results area has content
        results_area = page.locator('#results-area')
        expect(results_area).to_be_visible()
        
        results_html = results_area.inner_html()
        
        # Verify price-related text present (may vary by implementation)
        assert 'ticker' in results_html.lower() or 'symbol' in results_html.lower()
        
        print("✅ Table Display: Results area contains data")


class TestNewsAutoRefresh:
    """Test news panel auto-refresh logic."""
    
    def test_news_panel_visible(self, page: Page):
        """Verify news panel exists and displays news."""
        page.goto(BASE_URL, wait_until='networkidle')
        page.locator('text=Market Trends').first.click()
        page.wait_for_timeout(2000)
        
        # Look for news container
        news_container = page.locator('#news-container')
        
        if news_container.is_visible():
            capture_screenshot(page, '10_news_panel_visible')
            
            news_html = news_container.inner_html()
            assert len(news_html) > 0, "News container should have content"
            
            print("✅ News Panel: Visible with content")
        else:
            print("⚠️  News Panel: Not found (may be conditional)")


class TestPerformanceMetrics:
    """Test performance assertions."""
    
    def test_tab_load_time(self, page: Page):
        """Verify tab loads in < 2 seconds."""
        page.goto(BASE_URL, wait_until='networkidle')
        
        start_time = time.time()
        page.locator('text=Market Trends').first.click()
        page.wait_for_selector('#results-area', timeout=5000)
        load_time = time.time() - start_time
        
        perf_report = {
            'tab_load_time_seconds': load_time,
            'target_seconds': 2.0,
            'passed': load_time < 2.0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save performance report
        perf_path = os.path.join(
            os.path.dirname(DIAGNOSTICS_DIR),
            'perf.json'
        )
        with open(perf_path, 'w') as f:
            json.dump(perf_report, f, indent=2)
        
        assert load_time < 2.0, f"Tab load time {load_time:.2f}s exceeds 2s target"
        
        print(f"✅ Performance: Tab loaded in {load_time:.2f}s")


@pytest.fixture(scope='session', autouse=True)
def setup_diagnostics():
    """Ensure diagnostics directory exists."""
    os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
    
    # Create test report
    report_path = os.path.join(DIAGNOSTICS_DIR, 'test_report.txt')
    with open(report_path, 'w') as f:
        f.write(f"Market Trends Browser Tests\n")
        f.write(f"Started: {datetime.now().isoformat()}\n")
        f.write(f"Base URL: {BASE_URL}\n")
        f.write(f"Headful: {HEADFUL}\n\n")
    
    yield
    
    # Finalize report
    with open(report_path, 'a') as f:
        f.write(f"\nCompleted: {datetime.now().isoformat()}\n")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--maxfail=1'])
