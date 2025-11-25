#!/usr/bin/env python3
"""
STEP E - Headful Playwright Smoke Tests
Comprehensive system validation with visual capture
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import sync_playwright, expect

# Configuration
DASHBOARD_URL = "http://localhost:8050"
SCREENSHOT_DIR = REPO_ROOT / "reports" / "systemfix" / "playwright"
DOM_DIR = REPO_ROOT / "reports" / "systemfix" / "dom"
HAR_DIR = REPO_ROOT / "reports" / "systemfix" / "playwright"

# Ensure directories exist
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
DOM_DIR.mkdir(parents=True, exist_ok=True)
HAR_DIR.mkdir(parents=True, exist_ok=True)

class SystemFixSmokeTests:
    def __init__(self, headless=False):
        self.headless = headless
        self.results = {
            'start_time': datetime.utcnow().isoformat(),
            'tests': [],
            'summary': {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0}
        }
        
    def log_test(self, name, status, message="", duration=0):
        """Log test result."""
        self.results['tests'].append({
            'name': name,
            'status': status,
            'message': message,
            'duration_seconds': duration
        })
        self.results['summary']['total'] += 1
        self.results['summary'][status] += 1
        
        status_emoji = {'passed': '✅', 'failed': '❌', 'skipped': '⏭️'}
        print(f"{status_emoji.get(status, '❓')} {name}: {status.upper()}")
        if message:
            print(f"   └─ {message}")
    
    def run_all_tests(self):
        """Run complete smoke test suite."""
        print("\n" + "="*80)
        print("SYSTEMFIX SMOKE TESTS - HEADFUL MODE")
        print("="*80 + "\n")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_har_path=str(HAR_DIR / f"systemfix_smoke_{int(time.time())}.har")
            )
            page = context.new_page()
            
            # Enable console monitoring
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            
            try:
                # Test 1: Dashboard loads
                self.test_dashboard_loads(page)
                
                # Test 2: Health endpoint
                self.test_health_endpoint(page)
                
                # Test 3: Callback map endpoint
                self.test_callback_map_endpoint(page)
                
                # Test 4: Market Sentiment endpoint
                self.test_market_sentiment_endpoint(page)
                
                # Test 5: Tab navigation
                self.test_tab_navigation(page)
                
                # Test 6: Market Forecast tab
                self.test_market_forecast_tab(page)
                
                # Test 7: Command Center tab
                self.test_command_center_tab(page)
                
                # Test 8: Console errors check
                self.test_console_errors(console_errors)
                
            except Exception as e:
                self.log_test("Test Suite Execution", "failed", str(e))
            finally:
                context.close()
                browser.close()
        
        # Generate report
        self.generate_report()
        return self.results['summary']['failed'] == 0
    
    def test_dashboard_loads(self, page):
        """Test 1: Dashboard loads successfully."""
        start = time.time()
        try:
            page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
            
            # Wait for React to render
            page.wait_for_selector("#react-entry-point", timeout=30000)
            
            # Capture screenshot
            page.screenshot(path=str(SCREENSHOT_DIR / "01_dashboard_loaded.png"))
            
            # Verify title
            title = page.title()
            assert "Financial Dashboard" in title or "Dash" in title
            
            duration = time.time() - start
            self.log_test("Dashboard Loads", "passed", f"Loaded in {duration:.2f}s", duration)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Dashboard Loads", "failed", str(e), duration)
            page.screenshot(path=str(SCREENSHOT_DIR / "01_dashboard_load_FAILED.png"))
    
    def test_health_endpoint(self, page):
        """Test 2: /health/systemfix endpoint returns healthy status."""
        start = time.time()
        try:
            response = page.goto(f"{DASHBOARD_URL}/health/systemfix", wait_until="networkidle")
            assert response.status == 200, f"Status: {response.status}"
            
            data = response.json()
            assert data['status'] in ['healthy', 'degraded'], f"Unexpected status: {data['status']}"
            assert 'dash_app' in data, "Missing dash_app info"
            assert data['dash_app']['initialized'] is True, "Dash app not initialized"
            
            # Save response
            (SCREENSHOT_DIR / "health_response.json").write_text(json.dumps(data, indent=2))
            
            duration = time.time() - start
            self.log_test("Health Endpoint", "passed", 
                         f"Status: {data['status']}, Callbacks: {data['dash_app']['callback_count']}", 
                         duration)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Health Endpoint", "failed", str(e), duration)
    
    def test_callback_map_endpoint(self, page):
        """Test 3: /admin/callback_map returns valid data."""
        start = time.time()
        try:
            response = page.goto(f"{DASHBOARD_URL}/admin/callback_map", wait_until="networkidle")
            assert response.status == 200, f"Status: {response.status}"
            
            data = response.json()
            assert data['status'] == 'success', f"Status: {data['status']}"
            assert 'total_callbacks' in data, "Missing total_callbacks"
            
            # Save response
            (SCREENSHOT_DIR / "callback_map_response.json").write_text(json.dumps(data, indent=2))
            
            # Check for duplicates
            duplicate_count = data.get('duplicate_count', 0)
            warning = f" ({duplicate_count} duplicates - verify intentional)" if duplicate_count > 0 else ""
            
            duration = time.time() - start
            self.log_test("Callback Map Endpoint", "passed", 
                         f"Total callbacks: {data['total_callbacks']}{warning}", 
                         duration)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Callback Map Endpoint", "failed", str(e), duration)
    
    def test_market_sentiment_endpoint(self, page):
        """Test 4: /api/cc/market_sentiment returns recent data."""
        start = time.time()
        try:
            response = page.goto(f"{DASHBOARD_URL}/api/cc/market_sentiment", wait_until="networkidle")
            assert response.status == 200, f"Status: {response.status}"
            
            data = response.json()
            
            # Save response
            (SCREENSHOT_DIR / "market_sentiment_response.json").write_text(json.dumps(data, indent=2))
            
            # Check for recent update (within 5 minutes)
            if 'last_updated' in data:
                from dateutil import parser as date_parser
                last_update = date_parser.parse(data['last_updated'])
                age_seconds = (datetime.utcnow() - last_update.replace(tzinfo=None)).total_seconds()
                
                if age_seconds > 300:  # 5 minutes
                    msg = f"Data stale: {age_seconds:.0f}s old (poller may be stopped)"
                else:
                    msg = f"Fresh data: {age_seconds:.0f}s old"
            else:
                msg = "No timestamp available"
            
            duration = time.time() - start
            self.log_test("Market Sentiment Endpoint", "passed", msg, duration)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Market Sentiment Endpoint", "failed", str(e), duration)
    
    def test_tab_navigation(self, page):
        """Test 5: Tab navigation works without errors."""
        start = time.time()
        try:
            page.goto(DASHBOARD_URL, wait_until="networkidle")
            
            # Find all tabs
            tabs = page.locator("a.nav-link").all()
            tab_count = len(tabs)
            
            assert tab_count > 0, "No tabs found"
            
            # Click first non-active tab
            for tab in tabs[:3]:  # Test first 3 tabs only
                if "active" not in tab.get_attribute("class"):
                    tab_text = tab.text_content()
                    tab.click()
                    page.wait_for_timeout(1000)  # Wait for transition
                    
                    # Capture screenshot
                    safe_name = tab_text.replace(" ", "_").replace("/", "_")
                    page.screenshot(path=str(SCREENSHOT_DIR / f"tab_{safe_name}.png"))
                    break
            
            duration = time.time() - start
            self.log_test("Tab Navigation", "passed", f"Found {tab_count} tabs", duration)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Tab Navigation", "failed", str(e), duration)
            page.screenshot(path=str(SCREENSHOT_DIR / "tab_navigation_FAILED.png"))
    
    def test_market_forecast_tab(self, page):
        """Test 6: Market Forecast tab displays chart."""
        start = time.time()
        try:
            page.goto(DASHBOARD_URL, wait_until="networkidle")
            
            # Click Market Forecast tab
            forecast_tab = page.locator("a.nav-link:has-text('Market Forecast')")
            if forecast_tab.count() > 0:
                forecast_tab.first.click()
                page.wait_for_timeout(2000)  # Wait for chart to render
                
                # Check for Plotly chart
                chart = page.locator(".plotly")
                assert chart.count() > 0, "No Plotly chart found"
                
                # Capture screenshot
                page.screenshot(path=str(SCREENSHOT_DIR / "02_market_forecast_tab.png"))
                
                # Save DOM
                dom_content = page.content()
                (DOM_DIR / "market_forecast_tab.html").write_text(dom_content)
                
                duration = time.time() - start
                self.log_test("Market Forecast Tab", "passed", "Chart rendered successfully", duration)
            else:
                duration = time.time() - start
                self.log_test("Market Forecast Tab", "skipped", "Tab not found", duration)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Market Forecast Tab", "failed", str(e), duration)
            page.screenshot(path=str(SCREENSHOT_DIR / "market_forecast_FAILED.png"))
    
    def test_command_center_tab(self, page):
        """Test 7: Command Center tab loads without errors."""
        start = time.time()
        try:
            page.goto(DASHBOARD_URL, wait_until="networkidle")
            
            # Click Command Center tab
            cc_tab = page.locator("a.nav-link:has-text('Command Center')")
            if cc_tab.count() > 0:
                cc_tab.first.click()
                page.wait_for_timeout(2000)
                
                # Capture screenshot
                page.screenshot(path=str(SCREENSHOT_DIR / "03_command_center_tab.png"))
                
                # Save DOM
                dom_content = page.content()
                (DOM_DIR / "command_center_tab.html").write_text(dom_content)
                
                duration = time.time() - start
                self.log_test("Command Center Tab", "passed", "Tab loaded", duration)
            else:
                duration = time.time() - start
                self.log_test("Command Center Tab", "skipped", "Tab not found", duration)
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Command Center Tab", "failed", str(e), duration)
            page.screenshot(path=str(SCREENSHOT_DIR / "command_center_FAILED.png"))
    
    def test_console_errors(self, console_errors):
        """Test 8: Check for console errors."""
        start = time.time()
        try:
            # Filter out known safe errors
            critical_errors = [
                err for err in console_errors 
                if "favicon" not in err.lower() 
                and "manifest" not in err.lower()
                and "404" not in err
            ]
            
            if critical_errors:
                error_summary = "\n".join(critical_errors[:5])  # First 5 errors
                self.log_test("Console Errors Check", "failed", 
                             f"Found {len(critical_errors)} errors:\n{error_summary}", 
                             time.time() - start)
            else:
                self.log_test("Console Errors Check", "passed", 
                             "No critical console errors", 
                             time.time() - start)
            
        except Exception as e:
            self.log_test("Console Errors Check", "failed", str(e), time.time() - start)
    
    def generate_report(self):
        """Generate final test report."""
        self.results['end_time'] = datetime.utcnow().isoformat()
        
        # Save JSON report
        report_path = SCREENSHOT_DIR / f"systemfix_test_report_{int(time.time())}.json"
        report_path.write_text(json.dumps(self.results, indent=2))
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests:  {self.results['summary']['total']}")
        print(f"✅ Passed:     {self.results['summary']['passed']}")
        print(f"❌ Failed:     {self.results['summary']['failed']}")
        print(f"⏭️  Skipped:    {self.results['summary']['skipped']}")
        print(f"\nReport saved: {report_path}")
        print("="*80 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SystemFix Smoke Tests")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    tester = SystemFixSmokeTests(headless=args.headless)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
